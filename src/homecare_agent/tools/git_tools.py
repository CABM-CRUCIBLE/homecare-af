# Author: C A B M
# Date: 2026-09-17

"""Local git operations tool using GitPython.

Handles branch management, staging, committing, pushing, and diff inspection.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def _get_repo(repo_path: str | Path) -> Any:
    """Initialize a GitPython Repo instance."""
    from git import Repo

    path = Path(repo_path).resolve()
    if not (path / ".git").exists():
        # Check if parent is git repo
        for parent in path.parents:
            if (parent / ".git").exists():
                return Repo(str(parent))
    return Repo(str(path))


def get_current_branch(repo_path: str | Path) -> str:
    """Get the active branch name."""
    try:
        repo = _get_repo(repo_path)
        return str(repo.active_branch.name)
    except Exception as e:
        logger.warning("Failed to get current branch: %s", e)
        return "main"


def git_checkout(repo_path: str | Path, branch_name: str, create_if_missing: bool = True) -> bool:
    """Check out an existing or new git branch."""
    try:
        repo = _get_repo(repo_path)
        if branch_name in [h.name for h in repo.heads]:
            repo.heads[branch_name].checkout()
            logger.info("Checked out existing branch %s", branch_name)
        elif create_if_missing:
            repo.create_head(branch_name).checkout()
            logger.info("Created and checked out branch %s", branch_name)
        else:
            raise ValueError(f"Branch {branch_name} does not exist")
        return True
    except Exception as e:
        logger.error("Error during git checkout of %s: %s", branch_name, e)
        raise


def git_add(repo_path: str | Path, files: list[str] | None = None) -> bool:
    """Stage files for commit."""
    try:
        repo = _get_repo(repo_path)
        if not files:
            repo.git.add(A=True)
            logger.info("Staged all modified and untracked files")
        else:
            for f in files:
                repo.git.add(f)
            logger.info("Staged %d specific files", len(files))
        return True
    except Exception as e:
        logger.error("Error during git add: %s", e)
        raise


def git_commit(repo_path: str | Path, message: str) -> str:
    """Create a commit with the staged changes."""
    try:
        repo = _get_repo(repo_path)
        commit = repo.index.commit(message)
        logger.info("Created commit %s: %s", commit.hexsha[:8], message.splitlines()[0])
        return commit.hexsha
    except Exception as e:
        logger.error("Error during git commit: %s", e)
        raise


def git_push(repo_path: str | Path, branch_name: str, remote_name: str = "origin") -> bool:
    """Push local commits to remote branch."""
    try:
        repo = _get_repo(repo_path)
        if remote_name in [r.name for r in repo.remotes]:
            remote = repo.remote(remote_name)
            remote.push(refspec=f"{branch_name}:{branch_name}", set_upstream=True)
            logger.info("Pushed %s to %s", branch_name, remote_name)
            return True
        else:
            logger.warning("Remote '%s' not configured. Skipping git push.", remote_name)
            return False
    except Exception as e:
        logger.error("Error during git push: %s", e)
        raise


def git_status(repo_path: str | Path) -> dict[str, Any]:
    """Get the current repository status (untracked, modified, staged)."""
    try:
        repo = _get_repo(repo_path)
        return {
            "branch": repo.active_branch.name,
            "is_dirty": repo.is_dirty(untracked_files=True),
            "untracked_files": repo.untracked_files,
            "modified_files": [diff.a_path for diff in repo.index.diff(None)],
            "staged_files": [diff.a_path for diff in repo.index.diff("HEAD")] if repo.head.is_valid() else [],
        }
    except Exception as e:
        logger.error("Error getting git status: %s", e)
        return {"error": str(e)}


def git_diff(repo_path: str | Path, ref: str = "HEAD~1") -> str:
    """Get the git diff compared to a reference."""
    try:
        repo = _get_repo(repo_path)
        return str(repo.git.diff(ref))
    except Exception as e:
        logger.warning("Could not obtain git diff from %s: %s", ref, e)
        return ""
