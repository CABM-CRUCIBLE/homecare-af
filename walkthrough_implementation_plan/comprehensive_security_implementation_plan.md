# Implementation Plan: Comprehensive Security Hardening

Implement multi-layered security controls to protect the agentic framework against path traversal, secret exposure via git, plaintext secrets in logs/traces, insecure container exposure, and unauthorized web UI access.

## Proposed Changes

### 1. Path Traversal & Sandboxing
#### [MODIFY] [file_tools.py](file:///c:/WorkingFolder/homecare-af/src/homecare_agent/tools/file_tools.py)
- Implement `validate_safe_path(target_path: str | Path, base_dir: str | Path) -> Path`:
  - Resolves target path and ensures it remains strictly within `base_dir.resolve()`.
  - Explicitly blocks writes targeting `.git/`, `.github/workflows/`, `.env*`, `*.pem`, `*.key`.
  - Raises `PathTraversalSecurityError` if violations occur.

#### [MODIFY] [execute_prompt.py](file:///c:/WorkingFolder/homecare-af/src/homecare_agent/graph/nodes/execute_prompt.py)
- In `write_generated_files`, validate every generated file path against `repo_path` using `validate_safe_path`.
- Abort writing forbidden or traversal files and record security error in state.

---

### 2. Secret Leakage Prevention & Safe Git Staging
#### [MODIFY] [git_ops.py](file:///c:/WorkingFolder/homecare-af/src/homecare_agent/graph/nodes/git_ops.py)
- Implement `scan_for_secrets(text: str) -> list[str]` and `is_forbidden_git_file(path: str) -> bool`.
- In `commit_and_push`:
  - Scan modified/untracked files for secrets (API keys, private keys, tokens) before staging.
  - Reject commits if secrets or forbidden files (`.env*`, `*.pem`, `*.key`) are detected.
  - Stage only authorized generated code and documentation rather than blindly running `git add -A`.

---

### 3. Sensitive Data Redaction in Logs and Traces
#### [NEW] [src/homecare_agent/security/redaction.py](file:///c:/WorkingFolder/homecare-af/src/homecare_agent/security/redaction.py)
- Implement `redact_secrets(text: str) -> str` and `SecretMaskingFilter(logging.Filter)`.
- Scrubs OpenRouter tokens (`sk-or-v1-*`), Anthropic tokens (`sk-ant-*`), OpenAI tokens (`sk-*`), GitHub PATs (`ghp_*`), JWTs, and database URLs containing passwords.

#### [MODIFY] [main.py](file:///c:/WorkingFolder/homecare-af/src/homecare_agent/main.py)
- Attach `SecretMaskingFilter` to console and file log handlers in `_setup_logging`.

---

### 4. Docker Container Localhost Binding
#### [MODIFY] [docker-compose.yml](file:///c:/WorkingFolder/homecare-af/docker-compose.yml)
- Bind all host ports explicitly to `127.0.0.1` (`127.0.0.1:13000:3000`, `127.0.0.1:${LANGFUSE_DB_PORT:-15432}:5432`, `127.0.0.1:7860:7860`).

---

### 5. Web UI Access Control
#### [MODIFY] [config.py](file:///c:/WorkingFolder/homecare-af/src/homecare_agent/config.py)
- Add `gradio_auth_user: str = Field(default="")` and `gradio_auth_password: str = Field(default="")`.

#### [MODIFY] [web.py](file:///c:/WorkingFolder/homecare-af/src/homecare_agent/ui/web.py)
- Bind `server_name="127.0.0.1"` and configure `auth=(user, pass)` if credentials are set.

---

### 6. Automated Security Test Suite
#### [NEW] [tests/test_security.py](file:///c:/WorkingFolder/homecare-af/tests/test_security.py)
- Verify `validate_safe_path` blocks `../`, absolute paths, `.git`, and `.env`.
- Verify `scan_for_secrets` catches private keys, API tokens, and PATs.
- Verify `SecretMaskingFilter` redacts tokens in logs.
- Verify `commit_and_push` halts on secret presence.

## Verification Plan
1. Run `pytest tests/ -v` to ensure all existing 52 tests + new security tests pass cleanly.
2. Verify Docker compose file syntax and configuration.
