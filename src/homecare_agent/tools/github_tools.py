# Author: C A B M
# Date: 2026-09-17

"""GitHub API tool using PyGithub.

Provides operations to interact with GitHub repositories:
- Creating remote branches
- Opening Pull Requests with rich markdown descriptions
- Adding review comments and submitting code reviews
- Fetching PR diffs and status
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def _get_github_client(token: str | None = None) -> Any:
    """Initialize a PyGithub Github client."""
    from github import Auth, Github

    if token:
        auth = Auth.Token(token)
        return Github(auth=auth)
    return Github()


def create_pull_request(
    repo_name_or_url: str,
    title: str,
    body: str,
    head: str,
    base: str = "main",
    token: str | None = None,
) -> dict[str, Any]:
    """Create a GitHub Pull Request.

    Args:
        repo_name_or_url: e.g. "owner/repo" or "https://github.com/owner/repo"
        title: PR title
        body: Markdown body description
        head: Source branch (e.g. "feature/order-service")
        base: Target branch (e.g. "main")
        token: GitHub PAT

    Returns:
        dict with pr_number, html_url, state.
    """
    repo_name = _clean_repo_name(repo_name_or_url)
    try:
        gh = _get_github_client(token)
        repo = gh.get_repo(repo_name)

        logger.info("Opening PR on %s: %s (%s -> %s)", repo_name, title, head, base)
        pr = repo.create_pull(title=title, body=body, head=head, base=base)

        logger.info("Successfully created PR #%d on %s: %s", pr.number, repo_name, pr.html_url)
        return {
            "pr_number": pr.number,
            "html_url": pr.html_url,
            "state": pr.state,
            "title": pr.title,
        }
    except Exception as e:
        logger.error("Failed to create PR on %s: %s", repo_name, e, exc_info=True)
        raise


def get_pr_diff(
    repo_name_or_url: str,
    pr_number: int,
    token: str | None = None,
) -> str:
    """Fetch the diff text for a Pull Request."""
    import httpx

    repo_name = _clean_repo_name(repo_name_or_url)
    try:
        gh = _get_github_client(token)
        repo = gh.get_repo(repo_name)
        pr = repo.get_pull(pr_number)

        # Fetch raw diff via diff_url with auth headers
        headers = {"Accept": "application/vnd.github.v3.diff"}
        if token:
            headers["Authorization"] = f"Bearer {token}"

        with httpx.Client() as client:
            response = client.get(pr.diff_url, headers=headers, follow_redirects=True)
            if response.status_code == 200:
                logger.info("Retrieved %d bytes diff for PR #%d on %s", len(response.text), pr_number, repo_name)
                return response.text
            else:
                logger.warning("Failed to fetch diff for PR #%d (status code: %d)", pr_number, response.status_code)
        return ""
    except Exception as e:
        logger.error("Error retrieving PR diff for #%d on %s: %s", pr_number, repo_name, e, exc_info=True)
        return ""


def add_review_comment(
    repo_name_or_url: str,
    pr_number: int,
    body: str,
    commit_id: str,
    path: str,
    line: int,
    token: str | None = None,
) -> dict[str, Any]:
    """Add a review comment to a specific line in a PR diff."""
    repo_name = _clean_repo_name(repo_name_or_url)
    try:
        gh = _get_github_client(token)
        repo = gh.get_repo(repo_name)
        pr = repo.get_pull(pr_number)
        commit = repo.get_commit(commit_id)

        comment = pr.create_review_comment(body=body, commit=commit, path=path, line=line)
        logger.info("Added review comment #%d to %s:%d on PR #%d", comment.id, path, line, pr_number)
        return {"id": comment.id, "html_url": comment.html_url}
    except Exception as e:
        logger.error("Failed to add review comment to PR #%d: %s", pr_number, e, exc_info=True)
        raise


def post_pr_review(
    repo_name_or_url: str,
    pr_number: int,
    body: str,
    event: str = "COMMENT",  # APPROVE, REQUEST_CHANGES, COMMENT
    comments: list[dict[str, Any]] | None = None,
    token: str | None = None,
) -> dict[str, Any]:
    """Submit a formal Pull Request Review."""
    repo_name = _clean_repo_name(repo_name_or_url)
    try:
        gh = _get_github_client(token)
        repo = gh.get_repo(repo_name)
        pr = repo.get_pull(pr_number)

        review_args: dict[str, Any] = {"body": body, "event": event}
        if comments:
            review_args["comments"] = comments

        review = pr.create_review(**review_args)
        logger.info("Submitted PR review #%d (%s) on PR #%d", review.id, event, pr_number)
        return {"id": review.id, "state": review.state, "html_url": review.html_url}
    except Exception as e:
        logger.error("Failed to submit PR review on PR #%d: %s", pr_number, e, exc_info=True)
        raise


def _clean_repo_name(repo_name_or_url: str) -> str:
    """Normalize 'https://github.com/owner/repo.git' to 'owner/repo'."""
    clean = repo_name_or_url.strip()
    if clean.endswith(".git"):
        clean = clean[:-4]
    if "github.com/" in clean:
        clean = clean.split("github.com/")[-1]
    return clean.strip("/")
