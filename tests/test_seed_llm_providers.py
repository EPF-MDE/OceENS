"""Fournisseur LLM par défaut, créé par `seed_llm_providers` sur une base vide."""

import pytest
from sqlmodel import Session, SQLModel, create_engine, select

from oceens.core.seed import DEFAULT_PROVIDER_NAME, seed_llm_providers
from oceens.models import LLMProvider
from oceens.services.llm_client import config_problems, is_allowed_api_key_env

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


def seeded_provider(session):
    seed_llm_providers(session)
    return session.exec(
        select(LLMProvider).where(LLMProvider.name == DEFAULT_PROVIDER_NAME)
    ).one()


def test_without_settings_seeds_locallm(session):
    provider = seeded_provider(session)

    assert provider.api_type == "ollama"
    assert provider.base_url == "https://locallm.mde.epf.fr/ollama"
    assert provider.api_key_env == "LLM_API_KEY"
    assert provider.default_model == "gemma4:26b"
    assert provider.is_active


def test_settings_describe_the_seeded_provider(session, monkeypatch):
    monkeypatch.setenv("DEFAULT_PROVIDER_API_TYPE", "openai")
    monkeypatch.setenv("DEFAULT_PROVIDER_BASE_URL", "https://api.openai.com/v1")
    monkeypatch.setenv("DEFAULT_PROVIDER_MODEL", "gpt-4o-mini")
    monkeypatch.setenv("DEFAULT_PROVIDER_KEY_ENV", "OPENAI_API_KEY")

    provider = seeded_provider(session)

    assert provider.api_type == "openai"
    assert provider.base_url == "https://api.openai.com/v1"
    assert provider.api_key_env == "OPENAI_API_KEY"
    assert provider.default_model == "gpt-4o-mini"


@pytest.mark.parametrize("name", PROVIDER_SETTINGS)
def test_no_setting_can_be_read_as_a_key(name):
    assert not is_allowed_api_key_env(name)


def test_settings_a_provider_would_refuse_seed_a_row_with_problems(
    session, monkeypatch
):
    monkeypatch.setenv("DEFAULT_PROVIDER_API_TYPE", "mistral")
    monkeypatch.setenv("DEFAULT_PROVIDER_KEY_ENV", "SECRET_KEY")

    assert len(config_problems(seeded_provider(session))) == 2


def test_default_settings_seed_a_row_without_problem(session):
    assert config_problems(seeded_provider(session)) == []


def test_empty_settings_keep_locallm(session, monkeypatch):
    for name in PROVIDER_SETTINGS:
        monkeypatch.setenv(name, "")

    provider = seeded_provider(session)

    assert provider.base_url == "https://locallm.mde.epf.fr/ollama"
    assert provider.api_key_env == "LLM_API_KEY"
