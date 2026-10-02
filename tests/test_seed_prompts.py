"""Prompt de synthèse créé par `seed_prompts` sur une base vide."""

import pytest
from sqlmodel import Session, SQLModel, create_engine, select

from oceens.core.seed import DEFAULT_PROVIDER_NAME, seed_llm_providers, seed_prompts
from oceens.models import LLMProvider, Prompt

PROVIDER_SETTINGS = (
    "DEFAULT_PROVIDER_API_TYPE",
    "DEFAULT_PROVIDER_BASE_URL",
    "DEFAULT_PROVIDER_MODEL",
    "DEFAULT_PROVIDER_KEY_ENV",
)


@pytest.fixture
def session():
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture(autouse=True)
def no_provider_settings(monkeypatch):
    for name in PROVIDER_SETTINGS:
        monkeypatch.delenv(name, raising=False)


def model_asked_for(session):
    """Le modèle qu'une synthèse demande, résolu comme le fait le démon."""
    seed_llm_providers(session)
    seed_prompts(session)
    provider = session.exec(
        select(LLMProvider).where(LLMProvider.name == DEFAULT_PROVIDER_NAME)
    ).one()
    prompt = session.exec(select(Prompt)).one()
    return prompt.model or provider.default_model


def test_seeded_prompt_asks_for_the_model_of_the_settings(session, monkeypatch):
    monkeypatch.setenv("DEFAULT_PROVIDER_API_TYPE", "openai")
    monkeypatch.setenv("DEFAULT_PROVIDER_BASE_URL", "https://gateway.example/v1")
    monkeypatch.setenv("DEFAULT_PROVIDER_MODEL", "ministral-14b-latest")
    monkeypatch.setenv("DEFAULT_PROVIDER_KEY_ENV", "GATEWAY_API_KEY")

    assert model_asked_for(session) == "ministral-14b-latest"


def test_without_settings_seeded_prompt_asks_for_locallm_model(session):
    assert model_asked_for(session) == "gemma4:26b"
