"""Où en sont les synthèses d'un sondage, et combien de temps il leur reste.

Les tableaux de bord et le template demandent `progress(session, survey_id)`
et reçoivent un `SurveyProgress`. Ils ne savent ni lire la file `summaries`,
ni ce que « terminé » veut dire, ni comment le temps restant est estimé.
"""

from oceens.summary_progress._progress import (
    SECONDS_PER_JOB,
    SurveyProgress,
    progress,
)

__all__ = ["SECONDS_PER_JOB", "SurveyProgress", "progress"]
