"""=============================================================================
OceENS - Application principale FastAPI
=============================================================================

Ce module initialise et configure l'application web FastAPI avec :
- La gestion des sessions utilisateur (SessionMiddleware)
- L'authentification via le routeur auth (Azure Entra ID / Microsoft)
- Le rendu de templates HTML (Jinja2)
- La distribution de fichiers statiques (CSS, JS, images)
- Les routes pour les dashboards selon les rôles d'utilisateurs

Structure :
- app.py (ce fichier) : Configuration et routes principales
- auth.py : Authentification MSAL et routes /login, /logout, /auth/callback
- database.py : Gestion de la base de données SQLite et des rôles
- remplir_db.py : Script pour initialiser les données de test
"""

from dotenv import load_dotenv
load_dotenv()  # Charge les variables d'environnement depuis .env

import os
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from auth import router as auth_router, get_current_user
import uvicorn

# ┌─ Configuration ────────────────────────────────────────────────────────┐
# Les trois rôles utilisateurs reconnus par l'application
VALID_ROLES = {"admin", "etudiant", "professeur"}


# └───────────────────────────────────────────────────────────────────┘

def create_app():
    """
    Crée et configure l'instance FastAPI
    
    Configuration :
    - SessionMiddleware : Gère l'authentification et les sessions utilisateur
    - Routeur d'authentification : Endpoints /login, /logout, /auth/callback
    - Fichiers statiques : CSS, JS, images depuis le dossier /static
    - Templates Jinja2 : Moteur de rendu HTML depuis /templates
    """
    app = FastAPI(
        title="OceENS",
        description="Système de gestion et de connexion pour étudiants, professeurs et admins"
    )

    # ┌─ Middleware de gestion des sessions ────────────────────────────┐
    # Chaque utilisateur connecté a une session stockée (cookies sécurisés)
    # SECRET_KEY : Clé pour signer les sessions (doit être sécurisée en prod)
    app.add_middleware(
        SessionMiddleware,
        secret_key=os.environ.get("SECRET_KEY", "changeme"),
        https_only=True,        # Enforce HTTPS (important en production)
        same_site="lax",        # Protection contre les attaques CSRF
    )
    # └────────────────────────────────────────────────────────────────┘

    # Importe les routes d'authentification (login, logout, callback)
    app.include_router(auth_router)

    # Configuration des fichiers statiques (CSS, JavaScript, images)
    app.mount("/static", StaticFiles(directory="static"), name="static")
    
    # Configuration du moteur de templates HTML
    templates = Jinja2Templates(directory="templates")

    # ┌─ Route : Page d'accueil ───────────────────────────────────────┐
    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request):
        """
        Route racine de l'application (page d'accueil)
        
        Logique :
        1. Récupère l'utilisateur connecté (s'il existe)
        2. Si connecté + rôle valide → redirige vers son dashboard
        3. Sinon → affiche index.html (page de login)
        """
        user = get_current_user(request)
        if user and user.get("role") in VALID_ROLES:
            # Utilisateur authentifié avec un rôle valide
            return RedirectResponse(url=f"/dashboard/{user['role']}")
        # Utilisateur non authentifié → page de login
        return templates.TemplateResponse(request=request, name="index.html")

    # └────────────────────────────────────────────────────────────────┘

    # ┌─ Route : Page de paramétrage ──────────────────────────────────┐
    @app.get("/parametrage", response_class=HTMLResponse)
    async def parametrage(request: Request):
        """
        Route de paramétrage (configuration de l'application)
        Affiche simplement le template parametrage.html
        """
        return templates.TemplateResponse(request=request, name="parametrage.html")

    # └────────────────────────────────────────────────────────────────┘

    # ┌─ Route : Dashboards personnalisés par rôle ────────────────────┐
    @app.get("/dashboard/{role}", response_class=HTMLResponse)
    async def dashboard(request: Request, role: str):
        """
        Route du tableau de bord principal (dashboard)
        
        Sécurité :
        1. Vérifier que l'utilisateur est connecté
        2. Vérifier que le rôle demandé existe
        3. Vérifier que l'utilisateur a le droit d'accéder à ce rôle
           (empêche un étudiant d'accéder au dashboard admin)
        
        Affiche le template correspondant au rôle :
        - admin → dashboard/admin.html
        - etudiant → dashboard/etudiant.html
        - professeur → dashboard/professeur.html
        """
        
        # Récupère l'utilisateur de la session
        user = get_current_user(request)

        # Vérification 1 : Utilisateur connecté ?
        if not user:
            return RedirectResponse(url="/")

        # Vérification 2 : Rôle valide dans l'URL ?
        if role not in VALID_ROLES:
            return RedirectResponse(url="/")

        # Vérification 3 : L'utilisateur essaie-t-il d'accéder à un rôle qui n'est pas le sien ?
        # Cela empêche un étudiant d'accéder au dashboard professeur en tapant l'URL
        if user.get("role") != role:
            return RedirectResponse(url=f"/dashboard/{user['role']}")

        # Mappage des rôles vers les templates HTML
        template_map = {
            "admin": "dashboard/admin.html",
            "etudiant": "dashboard/etudiant.html",
            "professeur": "dashboard/professeur.html",
        }

        # Affiche le template avec les données de l'utilisateur
        return templates.TemplateResponse(
            request=request,
            name=template_map[role],
            context={"user": user},  # Passe l'utilisateur au template (accès à {{user}})
        )

    # └────────────────────────────────────────────────────────────────┘

    return app


# Crée l'instance FastAPI unique qui sera servie
app = create_app()


if __name__ == "__main__":
    """
    Point d'entrée principal - Lance le serveur de développement
    
    Configuration :
    - host="0.0.0.0" : Écoute sur toutes les interfaces réseau
    - port=8000 : Port d'écoute (HTTP ou HTTPS selon config)
    - reload=False : Pas de rechargement automatique (à True en dev)
    
    Certificats SSL (commentés) :
    - En production : utiliser des certificats Let's Encrypt
    - En local : générer avec OpenSSL ou utiliser mkcert
    """
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        # ssl_keyfile="oceens.key",      # Clé privée SSL
        # ssl_certfile="oceens.crt",    # Certificat SSL
    )
