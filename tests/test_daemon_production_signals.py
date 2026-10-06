"""Le daemon de synthèses signale à PostHog les échecs qu'il rattrape, sous son nom.

Deux serveurs locaux tiennent lieu de l'extérieur : un fournisseur compatible
OpenAI dont la génération répond `500`, et un hôte PostHog qui enregistre ce
qu'il reçoit. Le daemon y passe par son propre client LLM et par le SDK PostHog,
comme en production.
"""

import json
import logging
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
import requests
from markdown_it import MarkdownIt
from sqlmodel import Session, SQLModel, create_engine

from oceens import production_signals
from oceens import summaries_generator_daemon as daemon
from oceens.models import Answer, LLMProvider, Prompt, Submission, Summary

SURVEY_ID = 7
MODEL = "mistral-small-latest"
PROVIDER_FAILURE = {"object": "error", "message": "Internal server error"}
POSTHOG_SETTINGS = ("POSTHOG_PROJECT_TOKEN", "POSTHOG_HOST", "POSTHOG_ENVIRONMENT")


class Stub(ThreadingHTTPServer):
    """Un serveur HTTP local, sur un port libre, servi dans un thread."""

    def __init__(self, handler):
        super().__init__(("127.0.0.1", 0), handler)
        self.received = []
        threading.Thread(target=self.serve_forever, daemon=True).start()

    @property
    def url(self):
        return f"http://127.0.0.1:{self.server_address[1]}"


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def answer(self, status, payload):
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def body(self):
        return self.rfile.read(int(self.headers.get("Content-Length", 0)))


class FailingProvider(Handler):
    """Connaît le modèle, mais répond `500` à chaque génération."""

    def do_GET(self):
        self.answer(200, {"data": [{"id": MODEL}]})

    def do_POST(self):
        self.body()
        self.answer(500, PROVIDER_FAILURE)


class RecordingPostHog(Handler):
    """Enregistre les événements reçus ; les logs OTLP sont acceptés et ignorés."""

    def do_POST(self):
        body = self.body()
        if self.path.startswith("/batch"):
            self.server.received.extend(json.loads(body)["batch"])
        self.answer(200, {"status": 1})


@pytest.fixture
def provider_stub():
    server = Stub(FailingProvider)
    yield server
    server.shutdown()


@pytest.fixture
def posthog_stub():
    server = Stub(RecordingPostHog)
    yield server
    server.shutdown()


@pytest.fixture
def session(provider_stub):
    """Une base où un sondage attend la synthèse d'une question."""
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(
            LLMProvider(
                provider_id=1,
                name="Mistral",
                api_type="openai",
                base_url=provider_stub.url,
                default_model=MODEL,
            )
        )
        session.add(Prompt(prompt_id=1, provider_id=1, prompt_text="{ANSWERS}"))
        session.add(Submission(submission_id=1, survey_id=SURVEY_ID))
        session.add(Answer(submission_id=1, question_id=1, value="Trop de TP."))
        session.add(
            Summary(
                summary_id=1,
                survey_id=SURVEY_ID,
                question_id=1,
                prompt_id=1,
                http_status=0,
            )
        )
        session.commit()
        yield session


@pytest.fixture
def signals(posthog_stub, monkeypatch):
    """Les signaux du daemon, branchés sur l'hôte PostHog local."""
    monkeypatch.setenv("POSTHOG_PROJECT_TOKEN", "phc_test")
    monkeypatch.setenv("POSTHOG_HOST", posthog_stub.url)
    monkeypatch.setenv("POSTHOG_ENVIRONMENT", "staging")
    hook = sys.excepthook
    signals = production_signals.start(daemon.DAEMON_NAME)
    yield signals
    signals.shutdown()
    sys.excepthook = hook


def work_on_the_summary(session, signals):
    """Le travail d'une ligne, sous le contexte que `main()` ouvre au daemon."""
    summary_row = session.get(Summary, 1)
    with signals.process_context(daemon.DAEMON_NAME):
        daemon.work_on_summary(
            session, summary_row, requests.Session(), MarkdownIt(), {}, signals
        )
    return summary_row


def exceptions_received(posthog_stub, signals):
    signals.shutdown()
    return [e for e in posthog_stub.received if e["event"] == "$exception"]


def test_a_provider_failure_is_captured_as_the_daemon_with_its_survey(
    session, signals, posthog_stub
):
    work_on_the_summary(session, signals)

    [exception] = exceptions_received(posthog_stub, signals)
    assert exception["distinct_id"] == daemon.DAEMON_NAME
    properties = exception["properties"]
    assert properties["survey_id"] == SURVEY_ID
    assert properties["environment"] == "staging"
    assert "$process_person_profile" not in properties
    [raised] = properties["$exception_list"]
    assert raised["type"] == "ProviderError"
    assert "HTTP 500" in raised["value"]


def test_the_failure_is_still_logged_and_filed_as_before(session, signals, caplog):
    with caplog.at_level(logging.WARNING, logger="uvicorn.error"):
        summary_row = work_on_the_summary(session, signals)

    assert summary_row.http_status == 500
    assert summary_row.summary_text is None
    assert "HTTP 500" in summary_row.metadata_text
    [warning] = caplog.records
    assert warning.levelno == logging.WARNING
    assert "réponse vide (HTTP 500)" in warning.getMessage()
    assert "Internal server error" in warning.getMessage()


def test_an_unexpected_exception_is_captured_as_the_daemon_with_its_survey(
    session, signals, posthog_stub, monkeypatch
):
    def broken(*args):
        raise RuntimeError("boom")

    monkeypatch.setattr(daemon, "load_verbatims", broken)

    summary_row = work_on_the_summary(session, signals)

    assert summary_row.http_status == daemon.STATUS_CONFIG_ERROR
    [exception] = exceptions_received(posthog_stub, signals)
    assert exception["distinct_id"] == daemon.DAEMON_NAME
    assert exception["properties"]["survey_id"] == SURVEY_ID


def test_an_exception_that_kills_the_daemon_is_sent_once_as_the_daemon(
    signals, posthog_stub, capsys
):
    with pytest.raises(RuntimeError) as raised:
        with signals.process_context(daemon.DAEMON_NAME):
            raise RuntimeError("the daemon dies")
    # Ce que fait l'interpréteur de l'exception qui sort de `main()`.
    sys.excepthook(raised.type, raised.value, raised.tb)

    [exception] = exceptions_received(posthog_stub, signals)
    assert exception["distinct_id"] == daemon.DAEMON_NAME
    assert "$process_person_profile" not in exception["properties"]


def test_without_posthog_settings_nothing_is_sent_and_the_failure_is_filed(
    session, posthog_stub, monkeypatch
):
    for name in POSTHOG_SETTINGS:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(production_signals.posthog, "Posthog", None)
    signals = production_signals.start(daemon.DAEMON_NAME)

    summary_row = work_on_the_summary(session, signals)
    signals.shutdown()

    assert summary_row.http_status == 500
    assert posthog_stub.received == []
