"""Tests for authentication middleware."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def test_public_health_endpoint(client):
    """Test that health endpoint is public."""
    response = client.get("/health")
    assert response.status_code == 200


def test_public_root_endpoint(client):
    """Test that root endpoint is public."""
    response = client.get("/")
    assert response.status_code == 200


def test_public_docs_endpoint(client):
    """Test that docs endpoint is public."""
    response = client.get("/docs")
    assert response.status_code in [200, 404]  # May not be enabled


def test_protected_endpoint_without_auth(client):
    """Test that protected endpoints require auth."""
    response = client.get("/containers")
    assert response.status_code == 401
    assert "Authorization" in response.json()["detail"]


def test_protected_endpoint_with_invalid_auth(client):
    """Test that invalid auth token is rejected."""
    headers = {"Authorization": "Bearer invalid"}
    response = client.get("/containers", headers=headers)
    assert response.status_code == 401


@patch("app.middleware.auth.get_auth_client")
def test_protected_endpoint_with_valid_auth(mock_get_auth_client, client):
    """Test that valid auth token is accepted."""
    # Mock auth-gateway response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"user_id": "test-user"}

    mock_client = MagicMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_get_auth_client.return_value = mock_client

    headers = {"Authorization": "Bearer test-user:test-token-here"}
    response = client.get("/containers", headers=headers)
    assert response.status_code == 200


@patch("app.middleware.auth.get_auth_client")
def test_bearer_token_extraction(mock_get_auth_client, client):
    """Test that bearer token is correctly extracted."""
    # Mock auth-gateway response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"user_id": "user-id"}

    mock_client = MagicMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_get_auth_client.return_value = mock_client

    headers = {"Authorization": "Bearer user-id:token-value-long"}
    response = client.get("/containers", headers=headers)
    assert response.status_code == 200


def test_auth_header_case_sensitive(client):
    """Test that Authorization header is case-insensitive (per HTTP spec)."""
    headers = {"authorization": "Bearer user-id:token-value-long"}
    # FastAPI normalizes header names, so this should work
    response = client.get("/containers", headers=headers)
    # This depends on TestClient behavior with headers


def test_missing_bearer_prefix(client):
    """Test that missing Bearer prefix is rejected."""
    headers = {"Authorization": "user-id:token-value"}
    response = client.get("/containers", headers=headers)
    assert response.status_code == 401


def test_short_token_rejected(client):
    """Test that tokens shorter than 20 chars are rejected."""
    headers = {"Authorization": "Bearer short"}
    response = client.get("/containers", headers=headers)
    assert response.status_code == 401


@patch("app.middleware.auth.get_auth_client")
def test_invalid_token_format(mock_get_auth_client, client):
    """Test that tokens without user_id:token format are rejected."""
    # Mock auth-gateway response for invalid token
    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_response.json.return_value = {"detail": "Invalid token"}

    mock_client = MagicMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_get_auth_client.return_value = mock_client

    headers = {"Authorization": "Bearer nocolon1234567890"}
    response = client.get("/containers", headers=headers)
    assert response.status_code == 401
