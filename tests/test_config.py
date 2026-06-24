"""Tests for AgentConfig."""

from project_june import AgentConfig


def test_client_kwargs_defaults():
    kw = AgentConfig().client_kwargs()
    assert kw == {"max_retries": 4}  # no timeout by default


def test_client_kwargs_with_timeout():
    kw = AgentConfig(max_retries=2, request_timeout=30.0).client_kwargs()
    assert kw == {"max_retries": 2, "timeout": 30.0}


def test_defaults_are_capable():
    cfg = AgentConfig()
    assert cfg.model == "claude-opus-4-8"
    assert cfg.thinking is True
    assert cfg.cache is True
    assert cfg.effort == "high"
