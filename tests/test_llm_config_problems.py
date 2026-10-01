"""`config_problems` : ce qui empêchera un fournisseur de servir, sans l'appeler."""

from types import SimpleNamespace

from oceens.services.llm_client import config_problems


def provider(api_type="ollama", api_key_env="LLM_API_KEY"):
    return SimpleNamespace(api_type=api_type, api_key_env=api_key_env)


def test_a_valid_provider_has_no_problem():
    assert config_problems(provider()) == []


def test_a_provider_without_key_variable_has_no_problem():
    assert config_problems(provider(api_key_env=None)) == []


def test_an_unknown_api_type_is_a_problem():
    (problem,) = config_problems(provider(api_type="mistral"))
    assert "mistral" in problem


def test_a_refused_key_variable_is_a_problem():
    (problem,) = config_problems(provider(api_key_env="SECRET_KEY"))
    assert "SECRET_KEY" in problem
