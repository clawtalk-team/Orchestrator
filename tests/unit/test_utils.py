"""Tests for utility functions."""

from unittest.mock import patch

import pytest

from app.utils import get_git_sha


def test_get_git_sha_success():
    """Test getting git SHA when GIT_COMMIT env var is set."""
    with patch.dict("os.environ", {"GIT_COMMIT": "abc1234"}):
        result = get_git_sha()
        assert result == "abc1234"


def test_get_git_sha_with_whitespace():
    """Test getting git SHA when GIT_COMMIT has whitespace."""
    with patch.dict("os.environ", {"GIT_COMMIT": "  abc1234  "}):
        result = get_git_sha()
        assert result == "abc1234"


def test_get_git_sha_not_set():
    """Test getting git SHA when GIT_COMMIT env var is not set."""
    with patch.dict("os.environ", {}, clear=True):
        result = get_git_sha()
        assert result is None


def test_get_git_sha_empty():
    """Test getting git SHA when GIT_COMMIT is empty."""
    with patch.dict("os.environ", {"GIT_COMMIT": ""}):
        result = get_git_sha()
        assert result is None


def test_get_git_sha_unknown():
    """Test getting git SHA when GIT_COMMIT is 'unknown' (build-time default)."""
    with patch.dict("os.environ", {"GIT_COMMIT": "unknown"}):
        result = get_git_sha()
        assert result is None
