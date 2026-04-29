"""
Tests for scripts/manage.py.

Validates that the CLI:
- Prints help text at top level and per-subcommand without error
- Exits non-zero with clear errors when required arguments are missing
- Rejects invalid argument values (e.g., malformed JSON) gracefully

These tests run subprocesses with a short timeout (≤ 10 s) and make no
AWS API calls, so they are safe to run in CI without credentials.
"""

import subprocess
import sys
from pathlib import Path

import pytest

MANAGE = Path(__file__).parents[2] / "scripts" / "manage.py"
PYTHON = sys.executable


def run(args: list[str], *, timeout: int = 10) -> subprocess.CompletedProcess:
    return subprocess.run(
        [PYTHON, str(MANAGE)] + args,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def assert_help_ok(result: subprocess.CompletedProcess, *keywords: str) -> None:
    """Assert the command printed help and exited cleanly."""
    assert result.returncode == 0, (
        f"Expected exit 0 but got {result.returncode}\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    output = result.stdout + result.stderr
    for kw in keywords:
        assert kw in output, f"Expected '{kw}' in help output but got:\n{output}"


def assert_fails(result: subprocess.CompletedProcess) -> None:
    """Assert the command exited non-zero."""
    assert result.returncode != 0, (
        f"Expected non-zero exit but got 0\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )


# ---------------------------------------------------------------------------
# Top-level help
# ---------------------------------------------------------------------------


def test_top_level_help():
    result = run(["--help"])
    assert_help_ok(result, "containers", "ecs", "config", "verify")


def test_no_args_fails():
    result = run([])
    assert_fails(result)


# ---------------------------------------------------------------------------
# containers subcommands — help
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("command", ["list", "launch", "delete", "inspect", "logs", "exec"])
def test_containers_help(command):
    result = run(["containers", command, "--help"])
    assert_help_ok(result)


def test_containers_no_command_fails():
    result = run(["containers"])
    assert_fails(result)


# ---------------------------------------------------------------------------
# ecs subcommands — help
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("command", ["list", "stop-all", "cleanup"])
def test_ecs_help(command):
    result = run(["ecs", command, "--help"])
    assert_help_ok(result)


def test_ecs_no_command_fails():
    result = run(["ecs"])
    assert_fails(result)


# ---------------------------------------------------------------------------
# config subcommands — help
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("command", ["load", "setup-test"])
def test_config_help(command):
    result = run(["config", command, "--help"])
    assert_help_ok(result)


def test_config_no_command_fails():
    result = run(["config"])
    assert_fails(result)


# ---------------------------------------------------------------------------
# verify — help
# ---------------------------------------------------------------------------


def test_verify_help():
    result = run(["verify", "--help"])
    assert_help_ok(result, "AWS")


# ---------------------------------------------------------------------------
# containers launch — argument validation
# ---------------------------------------------------------------------------


def test_containers_launch_missing_user_id():
    """launch requires --user-id."""
    result = run(["containers", "launch", "--token", "tok"])
    assert_fails(result)


def test_containers_launch_missing_token():
    """launch requires --token."""
    result = run(["containers", "launch", "--user-id", "usr"])
    assert_fails(result)


def test_containers_launch_invalid_json_config():
    """launch should reject malformed --config JSON."""
    result = run([
        "containers", "launch",
        "--user-id", "test-user",
        "--token", "test-token-abc123456789",
        "--config", "not-valid-json",
        "--local",
    ])
    assert_fails(result)


def test_containers_launch_no_api_connection():
    """launch with valid args but no local server should fail (connection refused)."""
    result = run([
        "containers", "launch",
        "--user-id", "test-user",
        "--token", "test-token-abc123456789",
        "--config", '{"memory": 512}',
        "--local",
    ], timeout=15)
    assert_fails(result)


# ---------------------------------------------------------------------------
# containers delete — argument validation
# ---------------------------------------------------------------------------


def test_containers_delete_id_without_user_id():
    """delete with a container ID but no --user-id should fail."""
    result = run(["containers", "delete", "oc-abc12345"])
    assert_fails(result)


def test_containers_delete_no_args():
    """delete with no container IDs and no --all or --status should fail."""
    result = run(["containers", "delete", "--user-id", "usr"])
    assert_fails(result)


# ---------------------------------------------------------------------------
# containers logs — argument validation
# ---------------------------------------------------------------------------


def test_containers_logs_missing_user_id():
    """logs with a container ID but no --user-id should fail."""
    result = run(["containers", "logs", "oc-abc12345"])
    assert_fails(result)


# ---------------------------------------------------------------------------
# containers exec — argument validation
# ---------------------------------------------------------------------------


def test_containers_exec_missing_user_id():
    """exec with a container ID but no --user-id should fail."""
    result = run(["containers", "exec", "oc-abc12345"])
    assert_fails(result)


# ---------------------------------------------------------------------------
# config load — argument validation
# ---------------------------------------------------------------------------


def test_config_load_no_target():
    """config load with no --system, --user-id, or --verify should fail."""
    result = run(["config", "load"])
    assert_fails(result)


# ---------------------------------------------------------------------------
# config setup-test — argument validation
# ---------------------------------------------------------------------------


def test_config_setup_test_missing_user_id():
    """config setup-test requires --user-id."""
    result = run(["config", "setup-test", "--anthropic-key", "sk-ant-test"])
    assert_fails(result)


def test_config_setup_test_missing_api_key():
    """config setup-test requires at least one API key."""
    result = run(["config", "setup-test", "--user-id", "test-user"])
    assert_fails(result)
