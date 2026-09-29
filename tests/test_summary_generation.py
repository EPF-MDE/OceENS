"""Le nombre du Design Document (EPF-MDE/OceENS#105), tenu par un test.

Pire cas, un sondage : 30 s + 45 × 120 s ≈ 1 h 30 entre le clic sur « générer »
et la dernière synthèse sortie de la file, même quand le GPU ne répond plus.
Le faux serveur LLM entre par où entre déjà la vraie session HTTP : en argument.
"""

from datetime import timedelta
from types import SimpleNamespace

import requests

from oceens.summary_generation import generate_summary

# Hypothèse A du Design Document : 3 questions ouvertes × 12 modules × 1,2
# enseignant, plus quelques questions sur tout le sondage.
JOBS_PER_SURVEY = 45

# Le daemon attend jusqu'à 30 s avant de voir une file qui vient de se remplir.
POLL_INTERVAL = timedelta(seconds=30)

ONE_SURVEY_WORST_CASE = timedelta(hours=1, minutes=30, seconds=30)

PROVIDER = SimpleNamespace(
    name="Ollama EPF",
    api_type="ollama",
    base_url="http://gpu.invalid",
    api_key_env=None,
)


class GPUThatNeverAnswers:
    """Faux serveur LLM : chaque appel attend tout son délai, puis expire.

    Il ne dort pas, il compte : `waited` est le temps qu'aurait passé le daemon.
    """

    def __init__(self):
        self.waited = timedelta(0)

    def post(self, url, *, headers, json, timeout):
        if timeout is None:
            raise AssertionError(
                "Appel sans timeout : face à ce GPU, le daemon attendrait indéfiniment."
            )
        # requests accepte aussi (connexion, lecture) : le pire cas est la somme.
        seconds = sum(timeout) if isinstance(timeout, tuple) else timeout
        self.waited += timedelta(seconds=seconds)
        raise requests.Timeout(f"Pas de réponse en {seconds} s")


def test_a_survey_is_settled_within_1h30_when_the_gpu_never_answers():
    gpu = GPUThatNeverAnswers()

    outcomes = [
        generate_summary(PROVIDER, "gemma4:26b", "Synthétise : {ANSWERS}", gpu)
        for _ in range(JOBS_PER_SURVEY)
    ]

    # Chaque synthèse sort de la file (`http_status` différent de 0), en échec,
    # avec une raison lisible : manquante, mais pas bloquée.
    assert all(outcome.answer is None for outcome in outcomes)
    assert all(outcome.status not in (0, 200) for outcome in outcomes)
    assert all(outcome.metadata_text for outcome in outcomes)
    assert POLL_INTERVAL + gpu.waited <= ONE_SURVEY_WORST_CASE
