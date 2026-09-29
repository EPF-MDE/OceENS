"""Le nombre du Design Document (EPF-MDE/OceENS#105), tenu par un test.

Un sondage qu'on vient de lancer affiche un temps restant, pas un « 12/45 » nu :
environ 15 min pour 45 jobs, et jamais au-delà de 1 h 30, même si chaque job
va jusqu'aux 120 s que le daemon lui laisse. La file est la table `summaries`,
dans une base en mémoire passée en argument, comme la route passe la sienne.
Ni faux LLM, ni horloge.
"""

from datetime import timedelta

import pytest
from sqlmodel import Session, SQLModel, create_engine

from oceens.models import Summary
from oceens.summary_progress import progress

# Hypothèse A du Design Document : 3 questions ouvertes × 12 modules × 1,2
# enseignant, plus quelques questions sur tout le sondage.
JOBS_PER_SURVEY = 45

# Hypothèse B : durée typique d'un job.
TYPICAL_JOB = timedelta(seconds=20)

# Ce que le daemon laisse au plus à un job avant de le marquer en échec.
JOB_CAP = timedelta(seconds=120)

# D : au-delà, le Design Document exige un temps affiché.
WITHIN = timedelta(hours=1, minutes=30)

PENDING, DONE, TIMED_OUT = 0, 200, 504

SURVEY, OTHER_SURVEY = 1, 2


@pytest.fixture
def session():
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def fill(session, survey_id, count, status, text="<p>Synthèse</p>"):
    session.add_all(
        Summary(
            survey_id=survey_id,
            http_status=status,
            summary_text=text if status == DONE else None,
        )
        for _ in range(count)
    )
    session.commit()


def left(survey_progress):
    return timedelta(seconds=survey_progress.estimated_seconds_left)


def test_a_survey_just_clicked_shows_about_15_min_left(session):
    fill(session, SURVEY, JOBS_PER_SURVEY, PENDING)

    p = progress(session, SURVEY)

    assert (p.total, p.done, p.errors, p.finished) == (JOBS_PER_SURVEY, 0, 0, False)
    assert left(p) <= WITHIN
    assert left(p) == JOBS_PER_SURVEY * TYPICAL_JOB  # 15 min


def test_the_estimate_stays_within_1h30_even_if_every_job_hits_its_cap(session):
    fill(session, SURVEY, JOBS_PER_SURVEY, PENDING)

    p = progress(session, SURVEY, seconds_per_job=JOB_CAP.total_seconds())

    assert left(p) == JOBS_PER_SURVEY * JOB_CAP  # 1 h 30
    assert left(p) <= WITHIN


def test_the_estimate_counts_every_survey_waiting_in_the_queue(session):
    # Le daemon prend la première ligne en attente, sans ordre par sondage :
    # le dernier job d'un sondage peut attendre derrière tous les autres.
    fill(session, SURVEY, JOBS_PER_SURVEY, PENDING)
    fill(session, OTHER_SURVEY, JOBS_PER_SURVEY, PENDING)

    p = progress(session, SURVEY)

    assert p.total == JOBS_PER_SURVEY
    assert left(p) == 2 * JOBS_PER_SURVEY * TYPICAL_JOB  # 30 min


def test_a_survey_with_nothing_pending_is_finished_errors_included(session):
    fill(session, SURVEY, 39, DONE)
    fill(session, SURVEY, 1, DONE, text=None)  # un 200 sans texte est fait
    fill(session, SURVEY, 5, TIMED_OUT)
    fill(session, OTHER_SURVEY, JOBS_PER_SURVEY, PENDING)

    p = progress(session, SURVEY)

    assert (p.total, p.done, p.errors, p.finished) == (JOBS_PER_SURVEY, 40, 5, True)
    assert left(p) == timedelta(0)


def test_a_survey_with_no_job_is_not_finished(session):
    fill(session, OTHER_SURVEY, JOBS_PER_SURVEY, PENDING)

    p = progress(session, SURVEY)

    assert (p.total, p.done, p.errors, p.finished) == (0, 0, 0, False)
    assert left(p) == timedelta(0)
