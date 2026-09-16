"""Git operations node.

Handles branch creation, staging, committing, pushing, and PR creation.
Supports both GitHub PAT and GitHub App authentication.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from homecare_agent.config import AuthMode, Settings
from homecare_agent.graph.state import AgentState

logger = logging.getLogger(__name__)


async def create_branch(state: AgentState, settings: Settings) -> dict[str, Any]:
    """Create a feature branch and push to origin.

    Branch naming: feature/<module-name-kebab-case>

    Returns:
        State updates with branch_name.
    """
    from git import Repo

    feature_name = state.get("feature_name", "feature")
    # Convert to kebab-case
    branch_name = "feature/" + re.sub(r"[^a-z0-9]+", "-", feature_name.lower()).strip("-")

    repo_path = state.get("repo_path", settings.repo_path)
    logger.info("Creating branch: %s at %s", branch_name, repo_path)

    try:
        repo = Repo(repo_path)

        # Ensure we're on the latest default branch
        default_branch = settings.repo_default_branch
        if default_branch in [ref.name for ref in repo.heads]:
            repo.heads[default_branch].checkout()  # type: ignore[index]
            if repo.remotes:
                repo.remotes.origin.pull()

        # Create and checkout new branch
        if branch_name.split("/")[-1] in [ref.name for ref in repo.heads]:
            logger.info("Branch already exists; checking out.")
            repo.heads[branch_name.split("/")[-1]].checkout()  # type: ignore[index]
        else:
            new_branch = repo.create_head(branch_name)
            new_branch.checkout()

        # Push to origin
        if repo.remotes:
            repo.remotes.origin.push(branch_name, set_upstream=True)
            logger.info("Branch pushed to origin: %s", branch_name)

        return {
            "branch_name": branch_name,
            "current_step": "create_branch",
            "completed_steps": ["create_branch"],
        }

    except Exception:
        logger.exception("Branch creation failed.")
        return {
            "branch_name": branch_name,
            "errors": [{"step": "create_branch", "message": "Branch creation failed"}],
            "current_step": "create_branch",
            "completed_steps": ["create_branch"],
        }


async def commit_and_push(
    state: AgentState,
    settings: Settings,
    message: str = "",
    step_name: str = "commit",
) -> dict[str, Any]:
    """Stage all changes, commit, and push.

    Args:
        state: Current graph state.
        settings: Application settings.
        message: Commit message.
        step_name: Name of this step for tracking.

    Returns:
        State updates with commit log entry.
    """
    from git import Repo

    repo_path = state.get("repo_path", settings.repo_path)
    branch_name = state.get("branch_name", "")

    if not message:
        message = f"feat({state.get('feature_name', 'feature')}): {step_name}"

    try:
        repo = Repo(repo_path)
        repo.git.add(A=True)

        if repo.is_dirty() or repo.untracked_files:
            repo.index.commit(message)
            if repo.remotes and branch_name:
                repo.remotes.origin.push(branch_name)
            logger.info("Committed and pushed: %s", message)
        else:
            logger.info("No changes to commit.")

        return {
            "commit_log": [{"step": step_name, "message": message}],
            "current_step": step_name,
            "completed_steps": [step_name],
        }

    except Exception:
        logger.exception("Commit/push failed.")
        return {
            "errors": [{"step": step_name, "message": "Commit/push failed"}],
            "current_step": step_name,
            "completed_steps": [step_name],
        }


async def create_pull_request(state: AgentState, settings: Settings, llm: Any = None) -> dict[str, Any]:
    """Create a GitHub Pull Request.

    Creates a PR with a detailed description including:
    - Feature summary
    - Files changed
    - Test results
    - Architecture decisions referenced

    Returns:
        State updates with PR number and URL.
    """
    logger.info("Creating Pull Request...")

    branch_name = state.get("branch_name", "")
    feature_name = state.get("feature_name", "")

    # Build PR description
    pr_body = f"""## Feature: {feature_name}

### Summary
{state.get("feature_description", "")}

### Architecture Documents
- Strategy Document
- Tactical Plan
- {len(state.get("adr_documents", []))} ADR(s)

### Changes
- {len(state.get("generated_code", {}))} files generated/modified
- Organized into {state.get("current_wave", 0)} wave(s)

### Test Results
- Backend: {_summarize_test(state.get("backend_test_results", {}))}
- Frontend: {_summarize_test(state.get("frontend_test_results", {}))}
- E2E: {_summarize_test(state.get("e2e_test_results", {}))}

### Code Review
- Iterations: {state.get("review_iteration", 0)}
- Status: {"Approved" if not state.get("review_changes_needed") else "Changes Requested"}
"""

    try:
        from github import Github, Auth

        if settings.github_auth_mode == AuthMode.PAT:
            gh = Github(auth=Auth.Token(settings.github_token))
        else:
            from github import GithubIntegration
            integration = GithubIntegration(
                integration_id=settings.github_app_id,
                private_key=open(settings.github_app_private_key_path).read(),
            )
            installation = integration.get_installations()[0]
            gh = installation.get_github_for_installation()

        # Extract owner/repo from URL
        repo_url = state.get("repo_url", settings.repo_url)
        repo_match = re.search(r"github\.com[:/](.+/.+?)(?:\.git)?$", repo_url)
        if not repo_match:
            raise ValueError(f"Could not parse repo from URL: {repo_url}")

        repo = gh.get_repo(repo_match.group(1))
        pr = repo.create_pull(
            title=f"feat: {feature_name}",
            body=pr_body,
            head=branch_name,
            base=settings.repo_default_branch,
        )

        logger.info("PR created: #%d — %s", pr.number, pr.html_url)

        return {
            "pr_number": pr.number,
            "pr_url": pr.html_url,
            "current_step": "create_pr",
            "completed_steps": ["create_pr"],
        }

    except Exception:
        logger.exception("PR creation failed.")
        return {
            "errors": [{"step": "create_pr", "message": "PR creation failed"}],
            "current_step": "create_pr",
            "completed_steps": ["create_pr"],
        }


def _summarize_test(results: dict[str, Any]) -> str:
    """Summarize test results into a brief string."""
    if not results:
        return "Not run"
    passed = results.get("passed", 0)
    failed = results.get("failed", 0)
    total = results.get("total", passed + failed)
    status = "✅ Pass" if failed == 0 else "❌ Fail"
    return f"{status} ({passed}/{total})"
