"""Signaux de production : les erreurs et les logs du service, envoyés à PostHog.

Trois réglages, lus dans l'environnement de chaque environnement déployé :

- `POSTHOG_PROJECT_TOKEN` : le jeton du projet PostHog (`phc_…`) ;
- `POSTHOG_HOST` : l'hôte d'ingestion, `https://eu.i.posthog.com` ;
- `POSTHOG_ENVIRONMENT` : `staging` ou `production`.

Les trois, ou aucun. Sans le jeton (poste de développement, clone neuf), rien
n'est branché : le service démarre et répond exactement comme avant. Avec le
jeton mais sans l'hôte ou l'environnement, le service refuse de démarrer
(`ValueError: POSTHOG_ENVIRONMENT missing`) : sinon les erreurs d'un staging
se mêleraient sans bruit à celles de la production. Aucune valeur n'est commitée.

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

from oceens.core.auth import get_current_user

# Chemin OTLP de PostHog Logs, ajouté à POSTHOG_HOST.
LOGS_PATH = "/i/v1/logs"

# Les loggers qu'utilise le code d'OcéENS. Sous uvicorn, `uvicorn` ne propage
# pas vers la racine (et `uvicorn.error` propage vers lui seul) : un handler
# posé sur la racine ne les verrait jamais.
SERVICE_LOGGERS = ("uvicorn", "uvicorn.error")


class ProductionSignals:
    """Ce que `start()` a branché, et de quoi le débrancher.

    Éteint (`client` à None) quand un réglage manque : les contextes, `report()`
    et `shutdown()` ne font alors rien.
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
            email = (get_current_user(request) or {}).get("email")
            if email:
                posthog.identify_context(email)
            yield

    def process_context(self, distinct_id):
        """Contexte PostHog d'un processus sans utilisateur, sous un nom fixe.

        Hors requête, personne n'est connecté : sans identité, le SDK donnerait
        à chaque événement un id aléatoire, et une erreur compterait autant
        d'utilisateurs que d'occurrences. Le processus signe donc tout ce qu'il
        envoie de son propre nom. Une exception qui sort du contexte est
        capturée sous ce nom, puis relancée : `sys.excepthook` la reconnaît
        alors comme déjà capturée, et ne l'envoie pas une seconde fois sans
        identité.
        """
        if self._client is None:
            return nullcontext()
        return self._named_context(distinct_id)

    @contextmanager
    def _named_context(self, distinct_id):
        with posthog.new_context(client=self._client):
            posthog.identify_context(distinct_id)
            yield

    def work_context(self, **properties):
        """Contexte PostHog d'un travail, ses `properties` sur tout ce qui s'y envoie.

        À ouvrir dans `process_context()`, dont il garde l'identité.
        """
        if self._client is None:
            return nullcontext()
        return self._tagged_context(properties)

    @contextmanager
    def _tagged_context(self, properties):
        with posthog.new_context(client=self._client):
            for name, value in properties.items():
                posthog.tag(name, value)
            yield

    def report(self, exception):
        """Envoie à Error tracking une exception que le code a rattrapée.

        Rattrapée, elle ne sort d'aucun contexte : rien ne la capturerait. Elle
        part avec l'identité et les propriétés du contexte ouvert.
        """
        if self._client is None:
            return
        self._client.capture_exception(exception)

    def shutdown(self):
        """Vide les files d'envoi et débranche le handler de logs."""
        if self._client is None:
            return
        for logger in self._loggers:
            logger.removeHandler(self._handler)
        self._logger_provider.shutdown()
        self._client.shutdown()


def read_settings():
    """Les trois réglages `(jeton, hôte, environnement)`, ou None sans jeton.

    Lève `ValueError`, en nommant le réglage, si le jeton est posé sans l'hôte
    ou sans l'environnement.
    """
    token = os.environ.get("POSTHOG_PROJECT_TOKEN", "").strip()
    if not token:
        return None
    host = os.environ.get("POSTHOG_HOST", "").strip().rstrip("/")
    if not host:
        raise ValueError("POSTHOG_HOST missing")
    environment = os.environ.get("POSTHOG_ENVIRONMENT", "").strip()
    if not environment:
        raise ValueError("POSTHOG_ENVIRONMENT missing")
    return token, host, environment


def start(service_name):
    """Branche erreurs et logs sur PostHog, si les trois réglages sont posés.

    Lève `ValueError` sur un réglage partiel, comme `read_settings()`.
    """
    settings = read_settings()
    if settings is None:
        return ProductionSignals()
    token, host, environment = settings

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
