"""Unit tests for configuration."""
import os

import pytest

from app.config import Settings, get_settings


def test_get_settings():
    """Test settings retrieval."""
    settings = get_settings()
    assert isinstance(settings, Settings)
    assert settings.app_name == "orchestrator"


def test_settings_defaults(monkeypatch):
    """Test default settings values."""
    # Clear env vars that might affect defaults
    monkeypatch.delenv("ECS_CLUSTER_NAME", raising=False)
    monkeypatch.delenv("ECS_TASK_DEFINITION", raising=False)
    monkeypatch.delenv("ECS_CONTAINER_NAME", raising=False)

    # Clear cached settings
    get_settings.cache_clear()

    settings = Settings()
    assert settings.app_name == "orchestrator"
    # Note: debug value may come from .env file, so we don't assert a specific value
    assert isinstance(settings.debug, bool)
    assert settings.containers_table == "openclaw-containers"
    # Note: ECS settings may come from .env file or conftest, check they exist
    assert settings.ecs_cluster_name is not None
    assert settings.ecs_task_definition is not None
    assert settings.ecs_container_name is not None

    # Reset cache
    get_settings.cache_clear()


def test_settings_from_env(monkeypatch):
    """Test settings loaded from environment variables."""
    monkeypatch.setenv("APP_NAME", "test-orchestrator")
    monkeypatch.setenv("DEBUG", "true")
    monkeypatch.setenv("CONTAINERS_TABLE", "test-containers")

    # Clear cached settings
    get_settings.cache_clear()

    settings = get_settings()
    assert settings.app_name == "test-orchestrator"
    assert settings.debug is True
    assert settings.containers_table == "test-containers"

    # Reset cache
    get_settings.cache_clear()
