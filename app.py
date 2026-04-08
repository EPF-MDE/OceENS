from dotenv import load_dotenv

load_dotenv()

import os
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from auth import router as auth_router
import uvicorn


VALID_ROLES = {"admin", "etudiant", "professeur"}


def create_app():
    app = FastAPI()

    # ── Session middleware (obligatoire pour MSAL) ──
    app.add_middleware(
        SessionMiddleware,
        secret_key=os.environ.get("SECRET_KEY", "changeme"),
    )

    # ── Routes Auth (login, callback Microsoft, logout) ──
    app.include_router(auth_router)

    # ── Configuration Static & Templates ──
    app.mount("/static", StaticFiles(directory="static"), name="static")
    templates = Jinja2Templates(directory="templates")

    # ── Pages publiques ──
    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request):
        # Si déjà connecté, rediriger directement vers le bon dashboard
        user = request.session.get("user")
        if user and user.get("role") in VALID_ROLES:
            return RedirectResponse(url=f"/dashboard/{user['role']}")
        return templates.TemplateResponse(request=request, name="index.html")

    @app.get("/parametrage", response_class=HTMLResponse)
    async def parametrage(request: Request):
        return templates.TemplateResponse(request=request, name="parametrage.html")

    # ── Dashboards (protégés par session) ──
    @app.get("/dashboard/{role}", response_class=HTMLResponse)
    async def dashboard(request: Request, role: str):
        user = request.session.get("user")

        # Pas connecté → retour à l'accueil
        if not user:
            return RedirectResponse(url="/")

        # Rôle inconnu → retour à l'accueil
        if role not in VALID_ROLES:
            return RedirectResponse(url="/")

        # L'utilisateur essaie d'accéder à un dashboard qui n'est pas le sien
        if user.get("role") != role:
            return RedirectResponse(url=f"/dashboard/{user['role']}")

        # Chaque rôle a son propre template dans /dashboard/
        template_map = {
            "admin": "dashboard/admin.html",
            "etudiant": "dashboard/etudiant.html",
            "professeur": "dashboard/professeur.html",
        }

        return templates.TemplateResponse(
            request=request,
            name=template_map[role],
            context={"user": user},
        )

    return app


app = create_app()

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=False)
