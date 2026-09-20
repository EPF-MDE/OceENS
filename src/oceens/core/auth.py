"""=============================================================================
Gestion de l'authentification avec Microsoft Entra ID (Azure AD)
=============================================================================

Ce module gère tout le flux OAuth 2.0 / OpenID Connect avec Microsoft :

1. /login
   - Génère une URL d'authentification Microsoft
   - L'utilisateur sera redirigé vers Microsoft pour se connecter

2. /auth/callback
   - Microsoft redirige l'utilisateur avec un code d'authentification
   - On échange ce code contre un token d'accès
   - On récupère les infos utilisateur du Microsoft Graph
   - On stocke l'utilisateur en session

3. /logout
   - Efface la session de l'utilisateur
   - Redirige vers Microsoft pour se déconnecter proprement

Flux typique :
Utilisateur → /login → Microsoft Login → /auth/callback → Dashboard

Connexion de développement (`AUTH_MODE=dev`) :
Aucun fournisseur d'identité : `GET /dev/login` affiche une page listant les
utilisateurs par rôle, et `POST /dev/login` (champs `email`, `name`
optionnel, `key`) connecte directement en tant que l'utilisateur choisi.
`/login` redirige vers `/dev/login`, `/auth/callback` n'existe pas et
`/logout` se contente d'effacer la session. Ne jamais utiliser en production.
"""

from sqlmodel import select, func
from oceens.models import (
    User,
    Role,
)
from dotenv import load_dotenv

import hmac
import secrets
import uuid
import requests
import msal
from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from oceens.core.database import SessionDep
from oceens.core.dependencies import templates
import logging

import os
import sys
load_dotenv()

logger = logging.getLogger("uvicorn")

# ┌─ Mode d'authentification ─────────────────────────────────────────────────┐
# "entra" (défaut) : Microsoft Entra ID ; "dev" : connexion de développement
AUTH_MODE = os.environ.get("AUTH_MODE", "entra").strip().lower() or "entra"
if AUTH_MODE not in ("entra", "dev"):
    logger.critical(f"INVALID AUTH_MODE {AUTH_MODE!r}: expected 'entra' or 'dev'")
    sys.exit(1)

# Clé optionnelle exigée par POST /dev/login (vide = non définie)
DEV_LOGIN_KEY = os.environ.get("DEV_LOGIN_KEY") or None
if AUTH_MODE == "dev":
    logger.warning(
        "AUTH_MODE=dev: connexion de développement active, NE PAS UTILISER EN PRODUCTION "
        f"(DEV_LOGIN_KEY {'définie' if DEV_LOGIN_KEY else 'non définie : connexion ouverte'})"
    )
elif DEV_LOGIN_KEY:
    logger.warning("DEV_LOGIN_KEY est ignorée car AUTH_MODE=entra")

# Exposés à tous les templates (bandeau du mode dev dans le header partagé)
templates.env.globals["auth_mode"] = AUTH_MODE
templates.env.globals["dev_login_key_set"] = bool(DEV_LOGIN_KEY)
# └───────────────────────────────────────────────────────────────────────────┘

# ┌─ Domaines autorisés ──────────────────────────────────────────────────────┐
ALLOWED_DOMAINS = (
    os.environ.get("ALLOWED_DOMAINS")
    or ("epf.fr,epfedu.fr" if AUTH_MODE == "dev" else "")
).split(",")
# Format : "example.com,company.fr" en variable d'environnement
# Accepte des domaines multiples séparés par des virgules
# └───────────────────────────────────────────────────────────────────────────┘


# Un seul des deux routeurs est exposé (`router`, en bas du module)
entra_router = APIRouter()
dev_router = APIRouter()

# ┌─ Configuration Azure Entra ID (variables d'environnement) ──────────────┐
# Ces informations viennent du portail Azure Entra ID
CLIENT_ID = os.environ.get("ENTRA_CLIENT_ID")
# ID unique de l'application dans Azure Entra
CLIENT_SECRET = os.environ.get("ENTRA_CLIENT_SECRET")
# Clé secrète pour l'authentification (confidentielle)
TENANT_ID = os.environ.get("ENTRA_TENANT_ID")
if AUTH_MODE == "entra" and (CLIENT_ID == None or CLIENT_SECRET == None or TENANT_ID == None):
    logger.critical("MISSING ENTRA INFO. Please check .env")
    sys.exit(1)
# ID du "tenant" (organisation) dans Azure Entra
AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
# URL de base pour toutes les demandes d'authentification Microsoft
REDIRECT_URI = os.environ.get("REDIRECT_URI", "https://localhost/auth/callback")
# URL où Microsoft redirige après authentification
SCOPES = ["User.Read"]
# Droits demandés à l'utilisateur (accès au profil basique)
# └───────────────────────────────────────────────────────────────────────────┘

# ┌─ Clé de session ──────────────────────────────────────────────────────────┐
# Clé de signature des cookies de session (vide = non définie). Sans elle, un
# cookie forgé suffirait pour se connecter en tant que n'importe qui.
SECRET_KEY = os.environ.get("SECRET_KEY", "").strip() or None
if SECRET_KEY is None:
    if AUTH_MODE == "entra":
        logger.critical("MISSING SECRET_KEY. Required with AUTH_MODE=entra, please check .env")
        sys.exit(1)
    # Mode dev : clé aléatoire, les sessions ne survivent pas à un redémarrage
    SECRET_KEY = secrets.token_urlsafe(32)
    logger.warning("SECRET_KEY non définie : clé de session aléatoire, les sessions seront perdues au redémarrage")
# └───────────────────────────────────────────────────────────────────────────┘

# ┌─ Stockage en mémoire (fallback pour développement local) ──────────────────┐
# En production (vrai certificat SSL), les cookies de session Starlette fonctionnent
# bien et ces structures ne sont jamais utilisées.
# En développement local (certificat auto-signé), les sessions sont vides,
# donc on les stocke temporairement en mémoire comme fallback.
_pending_states: set = set()
# Stockage temporaire des "states" en attente de confirmation
_user_sessions: dict = {}
# Stockage temporaire des sessions utilisateur : session_token → user dict
# └───────────────────────────────────────────────────────────────────────────┘


def _build_msal_app():
    """
    Crée et retourne une instance MSAL (Microsoft Authentication Library)

    MSAL gère tout le flux OAuth 2.0 :
    - Génération d'URL d'authentification
    - Échange du code contre un token
    - Stockage et renouvellement des tokens
    """
    return msal.ConfidentialClientApplication(
        CLIENT_ID,
        authority=AUTHORITY,
        client_credential=CLIENT_SECRET,  # Authentification de l'application
    )


def _is_email_allowed(email: str) -> bool:
    """Vérifie que l'email appartient à un domaine autorisé"""
    if not email:
        return False
    domain = email.split("@")[1].lower()
    return domain in [d.lower().strip() for d in ALLOWED_DOMAINS if d]


# ┌─ Route 1/3 : Initier la connexion ────────────────────────────────────────┐


@entra_router.get("/login")
async def login(request: Request):
    """
    Initié le flux de connexion OAuth 2.0 avec Microsoft

    Mécanisme de sécurité (CSRF Protection) :
    - Génère un "state" aléatoire et unique (UUID)
    - Le stocke en session
    - Le transmet à Microsoft
    - Microsoft le renvoie inchangé
    - On vérifie qu'il correspond

    Flux :
    1. Générer state aléatoire
    2. Stocker state en session
    3. Construire URL de connexion Microsoft
    4. Rediriger l'utilisateur vers Microsoft
    """
    # Génère un identifiant unique pour cette tentative de connexion
    state = str(uuid.uuid4())

    # Stocke le state en session Starlette (fonctionne en production)
    request.session["auth_state"] = state
    # _pending_states.add(state)  # Optionnel : fallback pour dev

    # Construit l'URL de redirection vers Microsoft Login
    auth_url = _build_msal_app().get_authorization_request_url(
        scopes=SCOPES,  # Droits demandés
        state=state,  # Code de sécurité CSRF
        redirect_uri=REDIRECT_URI,  # Où revenir après authentification
    )
    return RedirectResponse(auth_url)


# └───────────────────────────────────────────────────────────────────────────┘

# ┌─ Route 2/3 : Callback après authentification Microsoft ─────────────────────┐


@entra_router.get("/auth/callback")
async def auth_callback(request: Request):
    """
    Callback endpoint (la route où Microsoft redirige l'utilisateur après authentification)

    Paramètres transmis par Microsoft en GET :
    - code : code d'authentification (sécurisé, valide 10 min)
    - state : le state qu'on a envoyé (vérification CSRF)

    Étapes :
    1. Vérifier que le state est correct (CSRF check)
    2. Échanger le code contre un token d'accès
    3. Utiliser le token pour récupérer les infos utilisateur
    4. Récupérer le rôle de l'utilisateur depuis la base de données
    5. Stocker l'utilisateur en session
    6. Rediriger vers le dashboard
    """
    from oceens.core.database import get_or_create_user

    # Récupère le state que Microsoft a renvoyé
    received_state = request.query_params.get("state")

    # ┌─ Vérification CSRF : le state doit correspondre ─────────────────────┐
    # Cas production : la session Starlette fonctionne, on l'utilise
    # Cas développement : certificat auto-signé, session vide, on utilise la mémoire
    session_state = request.session.get("auth_state")
    if session_state:
        # Production : session disponible
        if received_state != session_state:
            return Response("State invalide - attaque CSRF détectée", status_code=400)
    # En dev, cette vérification est commentée car session est vide
    # else:
    #     if received_state not in _pending_states:
    #         return Response("State invalide", status_code=400)
    #     _pending_states.discard(received_state)
    # └──────────────────────────────────────────────────────────────────────┘

    # Échange le code d'authentification contre un token d'accès
    # C'est un appel sécurisé de serveur à serveur (CLIENT_SECRET est transmis)
    token_result = _build_msal_app().acquire_token_by_authorization_code(
        code=request.query_params["code"],
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI,
    )

    # Vérification d'erreur : Microsoft a-t-il rejeté le code?
    if "error" in token_result:
        return Response(
            f"Erreur lors de l'authentification : {token_result.get('error_description')}",
            status_code=400,
        )

    # Utilise le token pour récupérer les infos utilisateur depuis Microsoft Graph
    # Microsoft Graph = API de Microsoft pour accéder aux infos utilisateur
    graph = requests.get(
        "https://graph.microsoft.com/v1.0/me",
        headers={"Authorization": f"Bearer {token_result['access_token']}"},
    ).json()

    # Extrait l'email (mail est prioritaire, fallback sur userPrincipalName)
    email = graph.get("mail") or graph.get("userPrincipalName")

    #  Vérifier le domaine de l'email
    if not _is_email_allowed(email):
        return Response(
            f"Accès refusé : domaine non autorisé. Domaines acceptés: {', '.join(ALLOWED_DOMAINS)}",
            status_code=403,
        )

    # Récupère le rôle de cet utilisateur depuis notre base de données
    # Si l'utilisateur n'existe pas, il est créé avec le rôle "student"
    get_or_create_user(email)

    # Construit l'objet utilisateur avec les infos Microsoft + notre rôle
    user = {
        "name": graph.get("displayName"),
        "email": email,
    }

    # Stocke l'utilisateur en session Starlette (fonctionne en production)
    request.session["user"] = user

    # Optionnel : génère aussi un token de session pour fallback en dev
    session_token = str(uuid.uuid4())
    _user_sessions[session_token] = user

    # Redirige vers la racine
    response = RedirectResponse(url=f"/")

    # Code commenté : stockage du token en cookie sécurisé
    # Utilisé uniquement en développement avec certificat auto-signé
    # response.set_cookie(
    #     key="session_token",
    #     value=session_token,
    #     httponly=True,            # Protégé contre le vol JavaScript
    #     secure=True,              # Transmis uniquement en HTTPS
    #     samesite="none",          # Pour les cross-site requests
    # )
    return response


# └───────────────────────────────────────────────────────────────────────────┘

# ┌─ Fonction utilitaire : Récupérer l'utilisateur courant ─────────────────────┐


def get_current_user(request: Request) -> dict | None:
    """
    Récupère l'utilisateur actuellement connecté

    Mécanisme de fallback :
    1. D'abord : session Starlette (fonctionne en production)
    2. Sinon : cookie manuel (fallback pour dev local avec cert auto-signé)
    3. Sinon : None (utilisateur non connecté)

    Return : dict avec {"name", "email", "role"} ou None si pas connecté
    """
    # Essaie de récupérer l'utilisateur depuis la session Starlette
    user = request.session.get("user")
    if user:
        return user

    # Fallback : essaie de récupérer depuis le cookie et la mémoire (dev local)
    # session_token = request.cookies.get("session_token")
    # if session_token and session_token in _user_sessions:
    #     return _user_sessions[session_token]

    # Aucune session trouvée
    return None


# └───────────────────────────────────────────────────────────────────────────┘




# └───────────────────────────────────────────────────────────────────────────┘

# ┌─ Route 3/3 : Déconnexion ──────────────────────────────────────────────────┐


@entra_router.get("/logout")
async def logout(request: Request):
    """
    Déconnexion de l'utilisateur

    Étapes :
    1. Efface la session en mémoire (dev fallback)
    2. Efface la session Starlette
    3. Efface le cookie de session
    4. Redirige vers le logout Microsoft pour nettoyer les cookies Microsoft
    """
    # Efface la session en mémoire (optimisation pour dev)
    session_token = request.cookies.get("session_token")
    if session_token:
        _user_sessions.pop(session_token, None)

    # Efface la session Starlette (détruit l'utilisateur stocké)
    request.session.clear()

    # Redirige vers le logout Microsoft pour déconnecter aussi de là-bas
    # Les utilisateurs seront déconnectés de tous les services Microsoft
    response = RedirectResponse(
        f"{AUTHORITY}/oauth2/v2.0/logout?post_logout_redirect_uri={REDIRECT_URI.split('/auth')[0]}"
    )
    # Supprime le cookie de session (dev fallback)
    response.delete_cookie("session_token")
    return response


# └───────────────────────────────────────────────────────────────────────────┘

# ┌─ Connexion de développement (AUTH_MODE=dev) ───────────────────────────────┐


def _name_from_email(email: str) -> str:
    """Construit un nom affichable depuis le mail : bob.leponge@… → "Bob Leponge"."""
    local_part = email.split("@")[0].replace(".", " ").replace("_", " ")
    return " ".join(local_part.split()).title()


@dev_router.get("/login")
async def dev_login_redirect():
    """En mode dev, la connexion passe par /dev/login."""
    return RedirectResponse("/dev/login")


# Ordre d'affichage des groupes ; un rôle inconnu est ajouté à la fin
_DEV_LOGIN_ROLE_ORDER = ["admin", "program_manager", "campus_manager", "facilitator", "student"]


@dev_router.get("/dev/login", response_class=HTMLResponse)
def dev_login_page(request: Request, session: SessionDep):
    """
    Page de connexion de développement : choisir en tant que qui se connecter

    Les utilisateurs sont regroupés par nom de rôle, sans périmètre
    (`program_manager:INFO` → `program_manager`). Sans ligne `roles`, un
    utilisateur est rangé sous `student` ; avec plusieurs rôles, il apparaît
    dans chaque groupe. Chaque formulaire poste vers `POST /dev/login`.
    """
    rows = session.exec(
        select(User.mail, Role.role)
        .join(Role, Role.user_id == User.user_id, isouter=True)
        .where(User.mail != None)
        .order_by(User.mail)
    ).all()

    groups: dict[str, list[str]] = {}
    for mail, role in rows:
        role_name = role.split(":")[0] if role else "student"
        mails = groups.setdefault(role_name, [])
        if mail not in mails:
            mails.append(mail)

    rank = {role_name: i for i, role_name in enumerate(_DEV_LOGIN_ROLE_ORDER)}
    ordered_groups = sorted(
        groups.items(),
        key=lambda item: (rank.get(item[0], len(rank)), item[0]),
    )
    return templates.TemplateResponse(
        request=request,
        name="dev_login.html",
        context={
            "role_groups": ordered_groups,
            "key_required": bool(DEV_LOGIN_KEY),
            "user": get_current_user(request),
        },
    )


@dev_router.post("/dev/login")
async def dev_login(
    request: Request,
    email: str = Form(...),
    name: str | None = Form(None),
    key: str | None = Form(None),
):
    """
    Connecte directement en tant que l'utilisateur `email`, sans preuve d'identité

    Étapes :
    1. Si DEV_LOGIN_KEY est définie, vérifier `key` (comparaison à temps constant)
    2. Vérifier le domaine de l'email (comme au callback Entra)
    3. Récupérer ou créer l'utilisateur (mail inconnu = nouvel étudiant)
    4. Remplacer la session par {name, email} puis rediriger vers la racine
    """
    from oceens.core.database import get_or_create_user

    if DEV_LOGIN_KEY and not hmac.compare_digest(
        (key or "").encode(), DEV_LOGIN_KEY.encode()
    ):
        return Response("Clé de connexion de développement invalide", status_code=401)

    email = email.strip()
    if "@" not in email or not _is_email_allowed(email):
        return Response(
            f"Accès refusé : domaine non autorisé. Domaines acceptés: {', '.join(ALLOWED_DOMAINS)}",
            status_code=403,
        )

    get_or_create_user(email)

    # Une nouvelle connexion écrase la session : c'est ainsi qu'on change d'utilisateur
    request.session.clear()
    request.session["user"] = {
        "name": (name or "").strip() or _name_from_email(email),
        "email": email,
    }
    return RedirectResponse(url="/", status_code=303)


@dev_router.get("/logout")
async def dev_logout(request: Request):
    """En mode dev, efface la session sans passer par la déconnexion Microsoft."""
    request.session.clear()
    return RedirectResponse(url="/")


router = dev_router if AUTH_MODE == "dev" else entra_router

# └───────────────────────────────────────────────────────────────────────────┘
