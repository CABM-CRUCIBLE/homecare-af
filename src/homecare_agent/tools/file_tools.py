# Author: C A B M
# Date: 2026-09-17

"""File operations tool for reading, writing, tree scanning, and code extraction."""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def read_file(file_path: str | Path) -> str:
    """Read full text content of a file."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    return path.read_text(encoding="utf-8")


def write_file(file_path: str | Path, content: str, overwrite: bool = True) -> Path:
    """Write text content to a file, ensuring parent directories exist."""
    path = Path(file_path)
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
        return True
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

    return extracted
