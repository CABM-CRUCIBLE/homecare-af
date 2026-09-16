# Author: C A B M
# Date: 2026-09-17

"""File operations tool for reading, writing, tree scanning, and code extraction."""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class PathTraversalSecurityError(Exception):
    """Raised when an operation attempts path traversal or writes to protected directories."""

    pass


FORBIDDEN_COMPONENTS = {".git", ".svn", ".hg"}
FORBIDDEN_FILE_EXTENSIONS = {".pem", ".key", ".pfx", ".p12"}
FORBIDDEN_FILENAMES = {".env", ".env.local", ".env.production", "id_rsa", "id_ed25519"}


def validate_safe_path(target_path: str | Path, base_dir: str | Path) -> Path:
    """Validate that a target path is safely contained within base_dir and does not target protected files.

    Args:
        target_path: Target relative or absolute file path.
        base_dir: Safe root directory (e.g. repository root).

    Returns:
        The validated absolute Path.

    Raises:
        PathTraversalSecurityError: If the path attempts to escape base_dir or target forbidden files.
    """
    base_resolved = Path(base_dir).resolve()
    target_str = str(target_path).strip()

    if "\x00" in target_str:
        raise PathTraversalSecurityError(f"Target path contains null bytes: {target_str}")

    target_p = Path(target_str)
    if target_p.is_absolute():
        resolved_target = target_p.resolve()
    else:
        resolved_target = (base_resolved / target_p).resolve()

    # Verify target is strictly within base directory
    try:
        rel = resolved_target.relative_to(base_resolved)
    except ValueError:
        raise PathTraversalSecurityError(
            f"Path traversal detected: '{target_str}' resolves outside base directory '{base_resolved}'."
        )

    # Reject writes to VCS directories
    for part in rel.parts:
        if part.lower() in FORBIDDEN_COMPONENTS:
            raise PathTraversalSecurityError(f"Write to protected VCS directory forbidden: '{rel}'")

    # Reject writes to GitHub CI/CD workflows
    rel_posix = rel.as_posix().lower()
    if rel_posix.startswith(".github/workflows") or rel_posix.startswith(".github/actions"):
        raise PathTraversalSecurityError(f"Write to GitHub CI/CD workflows forbidden: '{rel}'")

    # Reject sensitive environment / secret files
    filename = rel.name.lower()
    if filename in FORBIDDEN_FILENAMES or filename.startswith(".env"):
        raise PathTraversalSecurityError(f"Write to sensitive configuration/secret file forbidden: '{rel}'")

    if resolved_target.suffix.lower() in FORBIDDEN_FILE_EXTENSIONS:
        raise PathTraversalSecurityError(f"Write to cryptographic key file forbidden: '{rel}'")

    return resolved_target


def read_file(file_path: str | Path, base_dir: str | Path | None = None) -> str:
    """Read full text content of a file, with optional path sandboxing."""
    path = validate_safe_path(file_path, base_dir) if base_dir else Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    return path.read_text(encoding="utf-8")


def write_file(
    file_path: str | Path,
    content: str,
    overwrite: bool = True,
    base_dir: str | Path | None = None,
) -> Path:
    """Write text content to a file, ensuring parent directories exist and path is sandboxed."""
    path = validate_safe_path(file_path, base_dir) if base_dir else Path(file_path)
    if path.exists() and not overwrite:
        raise FileExistsError(f"File already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    logger.debug("Wrote %d bytes to %s", len(content), path)
    return path


def delete_file(file_path: str | Path) -> bool:
    """Delete a file if it exists."""
    path = Path(file_path)
    if path.exists():
        path.unlink()
        logger.info("Deleted file %s", path)
        return True
    logger.debug("File %s does not exist; cannot delete", path)
    return False


def list_files(
    directory: str | Path,
    pattern: str = "*",
    recursive: bool = True,
    ignore_patterns: list[str] | None = None,
) -> list[Path]:
    """List files in directory matching pattern, filtering ignored paths."""
    base = Path(directory)
    if not base.exists():
        return []

    ignores = ignore_patterns or [
        ".git",
        "node_modules",
        "bin",
        "obj",
        ".vs",
        "__pycache__",
        ".pytest_cache",
        "dist",
        "build",
    ]

    results: list[Path] = []
    generator = base.rglob(pattern) if recursive else base.glob(pattern)

    for path in generator:
        if path.is_file():
            # Check if any parent or name matches ignore list
            parts = set(path.parts)
            if not any(ig in parts for ig in ignores):
                results.append(path)

    return sorted(results)


def extract_files_from_markdown(markdown_text: str) -> dict[str, str]:
    """Parse Markdown text and extract files delimited by code blocks with filepath attributes.

    Supported patterns:
    ```csharp filepath="code/backend/Domain/Entities/Order.cs"
    ... code ...
    ```
    or
    <!-- file: code/backend/Domain/Entities/Order.cs -->
    ```csharp
    ... code ...
    ```
    or
    ### `code/backend/Domain/Entities/Order.cs`
    ```csharp
    ... code ...
    ```

    Returns:
        Mapping of relative file path -> file content string.
    """
    extracted: dict[str, str] = {}

    # Pattern 1: ```lang filepath="..."
    pattern_attr = re.compile(
        r"```[a-zA-Z0-9_\-]*\s+filepath=[\"']([^\"']+)[\"']\s*\n(.*?)```",
        re.DOTALL,
    )
    for match in pattern_attr.finditer(markdown_text):
        file_path = match.group(1).strip()
        content = match.group(2)
        extracted[file_path] = content

    # Pattern 2: <!-- file: ... --> followed by code block
    pattern_comment = re.compile(
        r"<!--\s*file:\s*([^\s>]+)\s*-->\s*\n```[a-zA-Z0-9_\-]*\s*\n(.*?)```",
        re.DOTALL,
    )
    for match in pattern_comment.finditer(markdown_text):
        file_path = match.group(1).strip()
        content = match.group(2)
        if file_path not in extracted:
            extracted[file_path] = content

    # Pattern 3: Heading with backticks e.g. ### `code/backend/...`
    pattern_heading = re.compile(
        r"###?\s*[`\"']([a-zA-Z0-9_./\\-]+\.[a-zA-Z0-9]+)[`\"']\s*\n```[a-zA-Z0-9_\-]*\s*\n(.*?)```",
        re.DOTALL,
    )
    for match in pattern_heading.finditer(markdown_text):
        file_path = match.group(1).strip().replace("\\", "/")
        content = match.group(2)
        if file_path not in extracted:
            extracted[file_path] = content

    logger.debug("Extracted %d file(s) from markdown input (%d chars)", len(extracted), len(markdown_text))
    return extracted
