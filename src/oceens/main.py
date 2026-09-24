"""
=============================================================================
OceENS - Application principale FastAPI
=============================================================================
Fabrique l'application et assemble les routeurs. La logique métier vit dans
les modules dédiés :

- `oceens.routers` : les routes, découpées par domaine ;
- `oceens.core.security` : authentification, rôles et périmètres ;
- `oceens.core.dependencies` : `templates` et `logger` partagés ;
- `oceens.services.helpers` : navigation, statistiques, filtres, tri ;
- `oceens.services` : agrégations, export CSV, client LLM ;
- `oceens.production_signals` : erreurs et logs envoyés à PostHog.
"""

from contextlib import asynccontextmanager
import os
import shutil
import sys
import subprocess
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
import uvicorn

from oceens import production_signals
from oceens.core.auth import AUTH_MODE, SECRET_KEY, router as auth_router
from oceens.core.database import create_db_and_tables
from oceens.core.dependencies import logger
from oceens.core.seed import seed_all_if_necessary

from oceens.routers import (
    pages,
    prompts,
    sections_questions,
    students,
    summaries,
    survey_templates,
    surveys,
    users,
)
from oceens.routers.llm import costs as llm_costs
from oceens.routers.llm import prices as llm_prices
from oceens.routers.llm import providers as llm_providers

load_dotenv()


# Fichiers statiques livrés dans le paquet : comme les templates, on les
# localise par rapport à ce fichier pour ne pas dépendre du répertoire courant.
STATIC_DIR = Path(__file__).resolve().parent / "static"

# Valeurs de RUN_SUMMARIES_DAEMON interprétées comme "activé"
_TRUTHY = {"1", "true", "yes", "on"}


def _maybe_start_summaries_daemon():
    """Lance le daemon de synthèses en process séparé si demandé par l'env.

    Activé uniquement si RUN_SUMMARIES_DAEMON est vrai (1/true/yes/on). En
    production, `launch.sh` s'en charge déjà : on ne veut donc pas le lancer
    systématiquement. Retourne le Popen (ou None si non lancé).
    """
    if os.environ.get("RUN_SUMMARIES_DAEMON", "").strip().lower() not in _TRUTHY:
        return None

    logger.info("Démarrage du daemon de synthèses (RUN_SUMMARIES_DAEMON activé)...")
    # Le point d'entrée installé, celui-là même que lance `launch.sh`. On le
    # cherche d'abord à côté de l'interpréteur courant, pour rester dans
    # l'environnement d'uvicorn même si le PATH pointe ailleurs. À défaut, le
    # module derrière ce point d'entrée, avec le même interpréteur : un
    # environnement où le script manque doit quand même générer ses synthèses.
    command = _summaries_daemon_command()
    return subprocess.Popen(command)


def _summaries_daemon_command():
    """Commande de lancement du daemon : le point d'entrée, sinon son module."""
    bin_dir = Path(sys.executable).parent
    for name in ("oceens-summaries", "oceens-summaries.exe"):
        entry_point = bin_dir / name
        if entry_point.exists():
            return [str(entry_point)]

    entry_point = shutil.which("oceens-summaries")
    if entry_point:
        return [entry_point]

    return [sys.executable, "-m", "oceens.summaries_generator_daemon"]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Cycle de vie de l'application : setup au démarrage, teardown à l'arrêt.

    Avant le `yield` : signaux de production, création des tables, seed
    initial, et lancement optionnel du daemon de synthèses en parallèle (si
    RUN_SUMMARIES_DAEMON est activé).
    Après le `yield` (à l'arrêt) : arrêt du daemon, journalisation, puis envoi
    des derniers signaux de production.
    """
    # Ici et non à l'import : uvicorn a déjà appliqué sa configuration de
    # logging, qui retirerait le handler de logs.
    signals = production_signals.start("oceens")
    app.state.production_signals = signals

    logger.info("Initialisation de la base de données...")
    create_db_and_tables()
    seed_all_if_necessary()

    # Lancer le daemon de synthèses en parallèle d'uvicorn (optionnel)
    daemon_process = _maybe_start_summaries_daemon()

    yield

    # Arrêter proprement le daemon à la fermeture de l'application
    if daemon_process is not None:
        logger.info("Arrêt du daemon de synthèses...")
        daemon_process.terminate()  # SIGTERM : le daemon quitte sa boucle
        try:
            daemon_process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            daemon_process.kill()  # forcer si toujours vivant après 10s

    logger.info("Fermeture de la connexion...")
    signals.shutdown()


def create_app():
    """
    Crée et configure l'application FastAPI fusionnée.
    """
    app = FastAPI(
        title="OceENS",
        description="Système de gestion et de connexion pour étudiants, professeurs et admins",
        lifespan=lifespan,
    )
    # Remplacé au démarrage par `lifespan`, si les réglages PostHog sont posés.
    app.state.production_signals = production_signals.ProductionSignals()

    # Ajouté avant SessionMiddleware, donc exécuté à l'intérieur : la session
    # est déjà chargée quand il lit l'utilisateur connecté.
    @app.middleware("http")
    async def production_signals_context(request: Request, call_next):
        """Capture l'exception d'une requête avec l'identité de l'utilisateur."""
        with request.app.state.production_signals.request_context(request):
            return await call_next(request)

    # SessionMiddleware (authentification)
    app.add_middleware(
        SessionMiddleware,
        secret_key=SECRET_KEY,
        # En mode dev, le cookie doit passer en http://localhost
        https_only=AUTH_MODE != "dev",
        same_site="lax",
    )

    @app.middleware("http")
    async def redirect_errors(request: Request, call_next):
        """Renvoie toute erreur vers l'accueil, qui choisit le dashboard."""
        response = await call_next(request)

        if response.status_code == 404 and request.url.path != "/":
            return RedirectResponse(url="/", status_code=303)
        return response

    # Routeur d'authentification (login/logout/callback Azure Entra ID)
    app.include_router(auth_router)

    # Fichiers statiques (les templates Jinja sont montés dans dependencies.py)
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    # ┌─ Assemblage des routeurs ──────────────────────────────────────────┐
    # L'ordre reproduit celui de l'ancien app.py : api, puis dashboard,
    # puis backend. La page d'accueil reste sans préfixe.
    app.include_router(pages.router)

    for module in (surveys, students, users, summaries, sections_questions):
        app.include_router(module.router)

    for module in (prompts, survey_templates, llm_costs):
        app.include_router(module.api_router)

    app.include_router(pages.dashboard_router)

    for module in (prompts, survey_templates, llm_providers, llm_prices, llm_costs):
        app.include_router(module.backend_router)
    # └────────────────────────────────────────────────────────────────────┘

    return app


# ┌─ Instance applicative globale ───────────────────────────────────────┐
app = create_app()
# └──────────────────────────────────────────────────────────────────────┘


def run():
    """Point d'entrée de la commande `oceens` : démarre le serveur ASGI."""
    uvicorn.run(
        "oceens.main:app",
        host="0.0.0.0",
        port=8000,
    )


if __name__ == "__main__":
    run()
