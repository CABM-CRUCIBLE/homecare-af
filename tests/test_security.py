# Author: C A B M
# Date: 2026-09-17

"""Comprehensive security test suite: path traversal, secret scanning, redaction, and git staging."""

import logging
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from homecare_agent.config import Settings
from homecare_agent.graph.nodes.execute_prompt import write_generated_files
from homecare_agent.graph.nodes.git_ops import (
    GitSecurityViolationError,
    commit_and_push,
    is_forbidden_staging_file,
    scan_file_for_secrets,
)
from homecare_agent.graph.state import AgentState
from homecare_agent.security.redaction import SecretMaskingFilter, redact_secrets
from homecare_agent.tools.file_tools import (
    PathTraversalSecurityError,
    read_file,
    validate_safe_path,
    write_file,
)


def test_validate_safe_path_valid(tmp_path: Path):
    """Verify standard relative paths inside base_dir resolve correctly."""
    repo = tmp_path / "repo"
    repo.mkdir()

    safe = validate_safe_path("src/module/service.cs", repo)
    assert safe == (repo / "src/module/service.cs").resolve()


def test_validate_safe_path_traversal_blocked(tmp_path: Path):
    """Verify path traversal (..) outside base_dir is blocked."""
    repo = tmp_path / "repo"
    repo.mkdir()

    with pytest.raises(PathTraversalSecurityError) as exc_info:
        validate_safe_path("../../outside.txt", repo)
    assert "Path traversal detected" in str(exc_info.value)


def test_validate_safe_path_forbidden_git_dir(tmp_path: Path):
    """Verify writes to .git directory are rejected."""
    repo = tmp_path / "repo"
    repo.mkdir()

    with pytest.raises(PathTraversalSecurityError) as exc_info:
        validate_safe_path(".git/hooks/pre-commit", repo)
    assert "protected VCS directory forbidden" in str(exc_info.value)


def test_validate_safe_path_forbidden_workflows(tmp_path: Path):
    """Verify writes to GitHub CI/CD workflows are rejected."""
    repo = tmp_path / "repo"
    repo.mkdir()

    with pytest.raises(PathTraversalSecurityError) as exc_info:
        validate_safe_path(".github/workflows/deploy.yml", repo)
    assert "GitHub CI/CD workflows forbidden" in str(exc_info.value)


def test_validate_safe_path_forbidden_env_files(tmp_path: Path):
    """Verify writes to .env files are rejected."""
    repo = tmp_path / "repo"
    repo.mkdir()

    with pytest.raises(PathTraversalSecurityError) as exc_info:
        validate_safe_path(".env", repo)
    assert "sensitive configuration/secret file forbidden" in str(exc_info.value)

    with pytest.raises(PathTraversalSecurityError):
        validate_safe_path("subdir/.env.production", repo)


def test_validate_safe_path_forbidden_key_extensions(tmp_path: Path):
    """Verify writes to private key extensions are rejected."""
    repo = tmp_path / "repo"
    repo.mkdir()

    with pytest.raises(PathTraversalSecurityError) as exc_info:
        validate_safe_path("certs/private.key", repo)
    assert "cryptographic key file forbidden" in str(exc_info.value)

    with pytest.raises(PathTraversalSecurityError):
        validate_safe_path("certs/server.pem", repo)


def test_write_file_sandboxing(tmp_path: Path):
    """Verify write_file enforces base_dir sandboxing."""
    repo = tmp_path / "repo"
    repo.mkdir()

    # Valid write
    target = write_file("src/test.txt", "content", base_dir=repo)
    assert target.exists()
    assert read_file("src/test.txt", base_dir=repo) == "content"

    # Traversal write blocked
    with pytest.raises(PathTraversalSecurityError):
        write_file("../forbidden.txt", "bad", base_dir=repo)


@pytest.mark.asyncio
async def test_write_generated_files_blocks_path_traversal(tmp_path: Path):
    """Verify write_generated_files halts malicious traversal without disk writes."""
    repo = tmp_path / "repo"
    repo.mkdir()

    settings = Settings(openrouter_api_key="test-key", repo_path=str(repo))
    state: AgentState = {
        "repo_path": str(repo),
        "generated_code": {
            "valid/file.cs": "class Valid {}",
            "../../escaped.txt": "MALICIOUS",
            ".git/hooks/pre-commit": "#!/bin/sh\nrm -rf /",
        },
    }

    result = await write_generated_files(state, settings)
    assert "errors" in result
    errors = result["errors"]
    assert len(errors) == 2
    assert all(err.get("security_violation") is True for err in errors)

    # Valid file should be written
    assert (repo / "valid/file.cs").exists()
    # Malicious files must not exist
    assert not (tmp_path / "escaped.txt").exists()
    assert not (repo / ".git/hooks/pre-commit").exists()


def test_is_forbidden_staging_file():
    """Verify forbidden git staging file matching."""
    assert is_forbidden_staging_file(".env") is True
    assert is_forbidden_staging_file(".env.local") is True
    assert is_forbidden_staging_file("config/jwt_id_rsa") is True
    assert is_forbidden_staging_file("keys/server.pem") is True
    assert is_forbidden_staging_file("secrets/credentials.json") is True

    assert is_forbidden_staging_file("src/Entities/Customer.cs") is False
    assert is_forbidden_staging_file("docs/ADR-001.md") is False


def test_scan_file_for_secrets(tmp_path: Path):
    """Verify detection of hardcoded secrets in files."""
    secret_file = tmp_path / "secret.txt"
    secret_file.write_text("OPENROUTER_KEY = sk-or-v1-0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef\n")

    findings = scan_file_for_secrets(secret_file)
    assert "OpenRouter API Key" in findings

    pat_file = tmp_path / "pat.txt"
    pat_file.write_text("GITHUB_PAT = ghp_123456789012345678901234567890123456\n")
    assert "GitHub Personal Access Token" in scan_file_for_secrets(pat_file)

    clean_file = tmp_path / "clean.txt"
    clean_file.write_text("public class CleanClass { int count = 42; }")
    assert scan_file_for_secrets(clean_file) == []


def test_redact_secrets():
    """Verify redact_secrets masks credentials and database URLs."""
    raw = "My key is sk-or-v1-0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef and PAT is ghp_123456789012345678901234567890123456"
    redacted = redact_secrets(raw)
    assert "sk-or-v1-***REDACTED***" in redacted
    assert "ghp_***REDACTED***" in redacted
    assert "0123456789abcdef" not in redacted

    db_url = "postgresql://postgres:supersecretpassword123@localhost:5432/mydb"
    assert redact_secrets(db_url) == "postgresql://postgres:***REDACTED***@localhost:5432/mydb"


def test_secret_masking_filter():
    """Verify logging SecretMaskingFilter scrubs records."""
    filt = SecretMaskingFilter()
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="Connecting with key sk-ant-api03-abcdefghijklmnopqrstuvwxyz",
        args=(),
        exc_info=None,
    )
    filt.filter(record)
    assert "sk-ant-***REDACTED***" in record.msg
    assert "abcdefghijklmnopqrstuvwxyz" not in record.msg


@pytest.mark.asyncio
async def test_commit_and_push_halts_on_secret(tmp_path: Path):
    """Verify commit_and_push halts when an uncommitted file contains a secret."""
    repo_dir = tmp_path / "git_repo"
    repo_dir.mkdir()

    import subprocess
    subprocess.run(["git", "init"], cwd=str(repo_dir), capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=str(repo_dir), capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=str(repo_dir), capture_output=True)

    # Place a secret file
    secret_file = repo_dir / "secret_key.txt"
    secret_file.write_text("ghp_123456789012345678901234567890123456")

    settings = Settings(openrouter_api_key="test-key", repo_path=str(repo_dir))
    state: AgentState = {"repo_path": str(repo_dir), "feature_name": "test"}

    result = await commit_and_push(state, settings)
    assert "errors" in result
    assert "Secret detected" in result["errors"][0]["message"]
