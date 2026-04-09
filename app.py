from dotenv import load_dotenv

load_dotenv()

import os
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from auth import router as auth_router, get_current_user
import uvicorn

VALID_ROLES = {"admin", "etudiant", "professeur", "teacher"}


def create_app():
    app = FastAPI()

    app.add_middleware(
        SessionMiddleware,
        secret_key=os.environ.get("SECRET_KEY", "changeme"),
        # https_only=True en production, False en dev local (cert auto-signé)
        https_only=True,
        same_site="lax",
    )

    app.include_router(auth_router)

    app.mount("/static", StaticFiles(directory="static"), name="static")
    templates = Jinja2Templates(directory="templates")

    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request):
        user = get_current_user(request)
        if user and user.get("role") in VALID_ROLES:
            return RedirectResponse(url=f"/dashboard/{user['role']}")
        return templates.TemplateResponse(request=request, name="index.html")

    @app.get("/parametrage", response_class=HTMLResponse)
    async def parametrage(request: Request):
        return templates.TemplateResponse(request=request, name="parametrage.html")

    @app.get("/dashboard/{role}", response_class=HTMLResponse)
    async def dashboard(request: Request, role: str):
        user = get_current_user(request)

        if not user:
            return RedirectResponse(url="/")

        if role not in VALID_ROLES:
            return RedirectResponse(url="/")

        if user.get("role") != role:
            return RedirectResponse(url=f"/dashboard/{user['role']}")

        template_map = {
            "admin": "dashboard/admin.html",
            "etudiant": "dashboard/etudiant.html",
            "professeur": "dashboard/professeur.html",
            "teacher": "dashboard/professeur.html",
        }

        return templates.TemplateResponse(
            request=request,
            name=template_map[role],
            context={"user": user},
        )

    return app


app = create_app()

if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=443,
        ssl_keyfile="oceens.key",
        ssl_certfile="oceens.crt",
        reload=False,
    )
