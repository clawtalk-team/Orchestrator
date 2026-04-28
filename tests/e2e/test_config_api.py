"""
E2E smoke test for the Config API.

Tests config creation and retrieval without spinning up containers or ECS tasks.
Requires live AWS endpoints and auth-gateway.

Environment variables required:
  ANTHROPIC_API_KEY   Anthropic API key
  E2E_TESTS=1         Enable this test suite (skipped by default)

Run:
  E2E_TESTS=1 ANTHROPIC_API_KEY=sk-ant-... pytest tests/e2e/test_config_api.py -v
"""

import os
import time

import pytest

from tests.e2e.test_end_to_end_flow import (
    AUTH_GATEWAY_URL,
    ORCHESTRATOR_URL,
    make_request,
    print_header,
    print_step,
    print_success,
    print_error,
    print_info,
    GREEN,
    RESET,
)

pytestmark = pytest.mark.skipif(
    not os.environ.get("E2E_TESTS"),
    reason="E2E tests disabled — set E2E_TESTS=1 to enable",
)


def test_config_api_smoke():
    """Create and retrieve config via the Config API without launching a container."""
    print_header("Config API Smoke Test")

    anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
    assert anthropic_api_key, "ANTHROPIC_API_KEY must be set"

    timestamp = int(time.time())
    test_email = f"config-test-{timestamp}@example.com"
    test_display_name = f"Config Test {timestamp}"

    # Step 1: Create test user
    print_step(1, "Create test user")
    response = make_request(
        "POST", f"{AUTH_GATEWAY_URL}/users",
        json_data={"email": test_email, "display_name": test_display_name},
    )
    assert response.status_code == 201, f"Failed to create user: {response.status_code} {response.text}"
    user_data = response.json()
    user_id = user_data["uuid"]
    api_key = user_data["api_key"]
    print_success(f"User created: {user_id}")

    # Step 2: Create config via API
    print_step(2, "Create config via Config API")
    response = make_request(
        "POST", f"{ORCHESTRATOR_URL}/config",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json_data={
            "config_name": "default",
            "llm_provider": "anthropic",
            "openclaw_model": "claude-3-5-sonnet-20241022",
            "anthropic_api_key": anthropic_api_key,
            "auth_gateway_api_key": api_key,
        },
    )
    assert response.status_code in (200, 201), f"Failed to create config: {response.status_code} {response.text}"
    print_success("Config created")

    # Step 3: Retrieve config via API
    print_step(3, "Retrieve config via Config API")
    response = make_request(
        "GET", f"{ORCHESTRATOR_URL}/config/default",
        headers={"Authorization": f"Bearer {api_key}"},
    )
    assert response.status_code == 200, f"Failed to retrieve config: {response.status_code} {response.text}"

    config_data = response.json()
    assert config_data["config_name"] == "default", \
        f"Expected config_name 'default', got {config_data.get('config_name')}"
    assert config_data["llm_provider"] == "anthropic", \
        f"Expected llm_provider 'anthropic', got {config_data.get('llm_provider')}"
    assert config_data["openclaw_model"] == "claude-3-5-sonnet-20241022", \
        f"Expected model 'claude-3-5-sonnet-20241022', got {config_data.get('openclaw_model')}"
    assert "anthropic_api_key" in config_data, "anthropic_api_key missing from response"
    assert "auth_gateway_api_key" in config_data, "auth_gateway_api_key missing from response"

    print_success("Config data validated")
    print(f"\n{GREEN}Config API smoke test passed!{RESET}\n")
