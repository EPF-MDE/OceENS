"""Signaux de production : les erreurs et les logs du service, envoyés à PostHog.

Trois réglages, lus dans l'environnement de chaque environnement déployé :

- `POSTHOG_PROJECT_TOKEN` : le jeton du projet PostHog (`phc_…`) ;
- `POSTHOG_HOST` : l'hôte d'ingestion, `https://eu.i.posthog.com` ;
- `POSTHOG_ENVIRONMENT` : `staging` ou `production`.

S'il en manque un (poste de développement, clone neuf), rien n'est branché : le
service démarre et répond exactement comme avant. Aucune valeur n'est commitée.

`start()` s'appelle au démarrage de chaque processus du service (le `lifespan`
de l'application, le `main()` du daemon), jamais à l'import : uvicorn applique
sa propre configuration de logging après l'import, et retirerait le handler
posé ici. `shutdown()` vide les files à l'arrêt, pour qu'un redéploiement ne
perde pas les derniers envois.
"""

from contextlib import contextmanager, nullcontext
import logging
import os

import posthog
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.resources import Resource

# Chemin OTLP de PostHog Logs, ajouté à POSTHOG_HOST.
LOGS_PATH = "/i/v1/logs"

# Les loggers qu'utilise le code d'OcéENS. Sous uvicorn, `uvicorn` ne propage
# pas vers la racine (et `uvicorn.error` propage vers lui seul) : un handler
# posé sur la racine ne les verrait jamais.
SERVICE_LOGGERS = ("uvicorn", "uvicorn.error")

# En-tête que posent les SDK web de PostHog sur les requêtes qu'ils émettent.
SESSION_HEADER = "X-POSTHOG-SESSION-ID"


class ProductionSignals:
    """Ce que `start()` a branché, et de quoi le débrancher.

    Éteint (`client` à None) quand un réglage manque : `request_context()` ne
    fait alors rien, et `shutdown()` non plus.
    """

    def __init__(self, client=None, logger_provider=None, handler=None, loggers=()):
        self._client = client
        self._logger_provider = logger_provider
        self._handler = handler
        self._loggers = loggers

    def request_context(self, request):
        """Contexte PostHog d'une requête, identifié par l'utilisateur connecté.

        Une exception qui en sort est capturée avec cette identité, puis
        relancée telle quelle : la réponse ne change pas. À ouvrir à
        l'intérieur de `SessionMiddleware`, qui charge la session.
        """
        if self._client is None:
            return nullcontext()
        return self._identified_context(request)

    @contextmanager
    def _identified_context(self, request):
        # Sans le client, le contexte capturerait par le client global de
        # PostHog, jamais initialisé : aucune exception n'arriverait.
        with posthog.new_context(client=self._client):
            # Sans utilisateur connecté, pas d'identité : on n'en invente pas.
            email = (request.session.get("user") or {}).get("email")
            if email:
                posthog.identify_context(email)
            session_id = request.headers.get(SESSION_HEADER)
            if session_id:
                posthog.set_context_session(session_id)
            yield

    def shutdown(self):
        """Vide les files d'envoi et débranche le handler de logs."""
        if self._client is None:
            return
        for logger in self._loggers:
            logger.removeHandler(self._handler)
        self._logger_provider.shutdown()
        self._client.shutdown()


def start(service_name):
    """Branche erreurs et logs sur PostHog, si les trois réglages sont posés."""
    token = os.environ.get("POSTHOG_PROJECT_TOKEN", "").strip()
    host = os.environ.get("POSTHOG_HOST", "").strip().rstrip("/")
    environment = os.environ.get("POSTHOG_ENVIRONMENT", "").strip()
    if not (token and host and environment):
        return ProductionSignals()

    client = posthog.Posthog(
        token,
        host=host,
        enable_exception_autocapture=True,
        super_properties={"environment": environment},
    )

    logger_provider = LoggerProvider(
        resource=Resource.create(
            {"service.name": service_name, "deployment.environment": environment}
        )
    )
    logger_provider.add_log_record_processor(
        BatchLogRecordProcessor(
            OTLPLogExporter(
                endpoint=host + LOGS_PATH,
                headers={"Authorization": f"Bearer {token}"},
            )
        )
    )
    handler = LoggingHandler(logger_provider=logger_provider)

    # La racine, plus chaque logger du service qui ne propage pas. Jamais un
    # logger qui propage : sa ligne partirait deux fois.
    loggers = [logging.getLogger()] + [
        logger
        for logger in map(logging.getLogger, SERVICE_LOGGERS)
        if not logger.propagate
    ]
    for logger in loggers:
        logger.addHandler(handler)

    return ProductionSignals(client, logger_provider, handler, loggers)
