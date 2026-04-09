from dotenv import load_dotenv

load_dotenv()

import uuid
import requests
import msal
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse, Response
import os

router = APIRouter()

CLIENT_ID = os.environ.get("ENTRA_CLIENT_ID")
CLIENT_SECRET = os.environ.get("ENTRA_CLIENT_SECRET")
TENANT_ID = os.environ.get("ENTRA_TENANT_ID")
AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
REDIRECT_URI = os.environ.get("REDIRECT_URI", "https://localhost/auth/callback")
SCOPES = ["User.Read"]

# ── Fallbacks en mémoire (dev local avec certificat auto-signé) ───────────────
# En production (vrai certificat), les cookies de session fonctionnent
# normalement et ces dictionnaires ne sont jamais utilisés.
_pending_states: set = set()
_user_sessions: dict = {}  # session_token → user dict


def _build_msal_app():
    return msal.ConfidentialClientApplication(
        CLIENT_ID, authority=AUTHORITY, client_credential=CLIENT_SECRET
    )


@router.get("/login")
async def login(request: Request):
    state = str(uuid.uuid4())

    # Stockage du state : session Starlette (prod) + mémoire (dev fallback)
    request.session["auth_state"] = state
    # _pending_states.add(state)

    auth_url = _build_msal_app().get_authorization_request_url(
        scopes=SCOPES, state=state, redirect_uri=REDIRECT_URI
    )
    return RedirectResponse(auth_url)


@router.get("/auth/callback")
async def auth_callback(request: Request):
    from database import get_role

    received_state = request.query_params.get("state")

    # Vérification du state :
    # - en prod : comparaison avec la session Starlette
    # - en dev  : comparaison avec le set en mémoire (session vide à cause du cert auto-signé)
    session_state = request.session.get("auth_state")
    if session_state:
        # Cas prod : session disponible
        if received_state != session_state:
            return Response("State invalide", status_code=400)
    # else:
    # Cas dev : session vide, on vérifie via mémoire
    #    if received_state not in _pending_states:
    #        return Response("State invalide", status_code=400)

    # _pending_states.discard(received_state)

    token_result = _build_msal_app().acquire_token_by_authorization_code(
        code=request.query_params["code"],
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI,
    )

    if "error" in token_result:
        return Response(
            f"Erreur token : {token_result.get('error_description')}", status_code=400
        )

    graph = requests.get(
        "https://graph.microsoft.com/v1.0/me",
        headers={"Authorization": f"Bearer {token_result['access_token']}"},
    ).json()

    email = graph.get("mail") or graph.get("userPrincipalName")
    role = get_role(email)

    user = {
        "name": graph.get("displayName"),
        "email": email,
        "role": role,
    }

    # Stockage de l'utilisateur : session Starlette (prod) + cookie manuel (dev)
    request.session["user"] = user

    session_token = str(uuid.uuid4())
    _user_sessions[session_token] = user

    response = RedirectResponse(url=f"/dashboard/{role}")
    # response.set_cookie(
    #    key="session_token",
    #    value=session_token,
    #    httponly=True,
    #    secure=True,
    #    samesite="none",
    # )
    return response


def get_current_user(request: Request) -> dict | None:
    """
    Récupère l'utilisateur connecté.
    1. Session Starlette  → fonctionne en production (vrai certificat)
    2. Cookie manuel      → fallback dev local (certificat auto-signé)
    """
    user = request.session.get("user")
    if user:
        return user

    # session_token = request.cookies.get("session_token")
    # if session_token and session_token in _user_sessions:
    #    return _user_sessions[session_token]

    return None


@router.get("/logout")
async def logout(request: Request):
    # Nettoyer la session mémoire
    session_token = request.cookies.get("session_token")
    if session_token:
        _user_sessions.pop(session_token, None)

    # Nettoyer la session Starlette
    request.session.clear()

    response = RedirectResponse(
        f"{AUTHORITY}/oauth2/v2.0/logout?post_logout_redirect_uri={REDIRECT_URI.split('/auth')[0]}"
    )
    response.delete_cookie("session_token")
    return response
