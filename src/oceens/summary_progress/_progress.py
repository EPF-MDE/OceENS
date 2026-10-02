"""La file `summaries` lue pour un sondage : avancement et temps restant."""

from dataclasses import dataclass

from sqlmodel import case, func, select

from oceens.models import Summary

# Durée typique d'un job. Le plus gros job de la base de démo a pris 55 s, et
# le GPU est partagé avec le cours de GenAI : 150 s est plus honnête que 20 s.
SECONDS_PER_JOB = 150

# `Summary.http_status` est l'état de la file : 0 en attente, 200 fait, tout
# autre code est un échec.
_PENDING = 0
_DONE = 200


@dataclass(frozen=True)
class SurveyProgress:
    """L'avancement des synthèses d'un sondage.

    `done + errors + pending == total`. `finished` : au moins un job, et plus
    aucun en attente. `estimated_seconds_left` vaut 0 une fois fini.
    """

    done: int
    total: int
    errors: int
    estimated_seconds_left: float
    finished: bool


def progress(session, survey_id, seconds_per_job=SECONDS_PER_JOB):
    """Avancement des synthèses de `survey_id`, et temps restant estimé.

    L'estimation compte toute la file, tous sondages confondus, × la durée
    d'un job : le daemon prend la première ligne en attente sans ordre par
    sondage, donc le dernier job d'un sondage peut attendre derrière tous les
    autres. Ne lit que `summaries`, ni l'horloge, ni le modèle.
    """
    total, done, pending = session.exec(
        select(
            func.count(Summary.summary_id),
            func.coalesce(func.sum(case((Summary.http_status == _DONE, 1), else_=0)), 0),
            func.coalesce(func.sum(case((Summary.http_status == _PENDING, 1), else_=0)), 0),
        ).where(Summary.survey_id == survey_id)
    ).one()
    finished = total > 0 and pending == 0

    queue_pending = 0
    if pending:
        queue_pending = session.exec(
            select(func.count(Summary.summary_id)).where(Summary.http_status == _PENDING)
        ).one()

    return SurveyProgress(
        done=done,
        total=total,
        errors=total - done - pending,
        estimated_seconds_left=queue_pending * seconds_per_job,
        finished=finished,
    )
