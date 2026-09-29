"""Un job de synthèse : l'appel au modèle et le délai qui le borne."""

import json
import logging
from dataclasses import dataclass

from requests.exceptions import RequestException

from oceens.services.llm_client import (
    LLMConfigError,
    ask_model,
    format_error_text,
    format_metadata_text,
)

logger = logging.getLogger("uvicorn.error")

# Le nombre du Design Document (EPF-MDE/OceENS#105) : 45 jobs × 120 s + 30 s
# d'attente de la file ≈ 1 h 30 pour un sondage, même quand le GPU ne répond
# plus. L'attente du GPU compte à l'intérieur de ces 120 s. Le relever, c'est
# sortir de ce nombre.
JOB_DEADLINE_SECONDS = 120

# Codes écrits dans `Summary.http_status` pour les échecs qui ne viennent pas
# d'une réponse HTTP du fournisseur.
STATUS_TIMEOUT = 504
STATUS_CONFIG_ERROR = 500


@dataclass(frozen=True)
class SummaryOutcome:
    """Ce que le daemon écrit dans la ligne `summaries`.

    `status` n'est jamais 0 : la ligne sort toujours de la file. `answer` est
    le Markdown du modèle, `None` en cas d'échec ; `metadata_text` dit alors
    pourquoi, sous une forme qu'un responsable peut suivre. `metadata` porte
    les compteurs de tokens, et n'existe qu'en cas de succès.
    """

    status: int
    answer: str | None
    metadata_text: str
    metadata: dict | None = None


def generate_summary(provider, model, prompt, http_session):
    """Demande une synthèse au modèle, en `JOB_DEADLINE_SECONDS` au plus.

    Ne lève jamais pour un échec du modèle ou du fournisseur : tout appel
    revient réglé, avec un `SummaryOutcome`. Pas de nouvel essai : après un
    délai dépassé, il ne reste plus de temps pour un second appel.
    """
    try:
        answer, metadata, status_code = ask_model(
            provider,
            model,
            prompt,
            session=http_session,
            timeout=JOB_DEADLINE_SECONDS,
        )
    except LLMConfigError as error:
        logger.error("Fournisseur %s mal configuré : %s", provider.name, error)
        return SummaryOutcome(STATUS_CONFIG_ERROR, None, str(error))
    except RequestException as error:
        logger.warning("Appel au fournisseur %s en échec : %s", provider.name, error)
        return SummaryOutcome(STATUS_TIMEOUT, None, str(error))

    if not answer:
        # Le JSON brut du fournisseur part dans les logs, pour le diagnostic ;
        # la base reçoit la version lisible, qui dit quoi corriger (crédit
        # épuisé, débit dépassé, clé refusée…).
        error_text = format_error_text(provider, model, status_code, metadata)
        logger.warning(
            "Réponse vide (HTTP %s) — %s — réponse brute : %s",
            status_code,
            error_text,
            json.dumps(metadata, default=str),
        )
        return SummaryOutcome(status_code, None, error_text)

    return SummaryOutcome(status_code, answer, format_metadata_text(metadata), metadata)
