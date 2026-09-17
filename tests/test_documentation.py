# Author: C A B M
# Date: 2026-09-17

"""Tests for Architecture Documentation & Visual Resource Persistence.

Verifies:
- Sanitized feature-slug generation and directory layout
- Saving STRATEGY.md, TACTICAL-PLAN.md, and ADRs
- Archiving wireframe screenshots into Resources/
- Saving MANUAL_TEST_GUIDE.md
- Early branch creation commit of architecture docs and resources into Git
"""

import os
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from homecare_agent.config import Settings
from homecare_agent.graph.nodes.documentation import (
    generate_manual_test_doc,
    get_feature_docs_dir,
    get_feature_slug,
    save_architecture_documents,
    save_manual_test_doc,
)
from homecare_agent.graph.nodes.git_ops import create_branch
from homecare_agent.graph.state import AgentState


# ─── 1. Slug & Directory Tests ──────────────────────────────────────────────


def test_get_feature_slug_transformations():
    """Verify robust sanitization of various feature names into kebab-case slugs."""
    assert get_feature_slug("Patient Vitals Tracking") == "patient-vitals-tracking"
    assert get_feature_slug("Real-Time Alerting System!") == "real-time-alerting-system"
    assert get_feature_slug("Feature #42: CQRS & Event Sourcing") == "feature-42-cqrs-event-sourcing"
    assert get_feature_slug("   ---Multiple---Spaces & Underscores___   ") == "multiple-spaces-underscores"
    assert get_feature_slug("") == "feature"
    assert get_feature_slug("!!!") == "feature"


def test_get_feature_docs_dir(tmp_path: Path):
    """Verify target path is repo_path / docs / architecture / <feature-slug>."""
    docs_dir = get_feature_docs_dir(tmp_path, "Clinical Notes Feature")
    assert docs_dir == tmp_path / "docs" / "architecture" / "clinical-notes-feature"


# ─── 2. Architecture Docs & Resources Persistence Tests ────────────────────


def test_save_architecture_documents_writes_files_and_archives_resources(tmp_path: Path):
    """Verify STRATEGY.md, TACTICAL-PLAN.md, ADRs, and wireframes are saved properly."""
    # Create sample wireframe images
    img1 = tmp_path / "wireframe1.png"
    img1.write_bytes(b"\x89PNG\r\n\x1a\nfake_image_bytes_1")
    img2 = tmp_path / "mockup.jpg"
    img2.write_bytes(b"\xff\xd8\xfffake_jpg_bytes_2")

    state: AgentState = {
        "repo_path": str(tmp_path),
        "feature_name": "Medication Reconciliation",
        "strategy_document": "# Strategy for Medication Reconciliation\nC4 Model and Clean Arch details.",
        "tactical_plan": "# Tactical Plan\nWave 1: Entities\nWave 2: CQRS.",
        "adr_documents": [
            {
                "id": "ADR-001",
                "title": "Use Outbox Pattern for Audit Events",
                "content": "# ADR-001: Use Outbox Pattern\nContext and decision details.",
            },
            {
                "id": "ADR-002",
                "title": "Adopt MediatR Pipeline Behaviors",
                "content": "# ADR-002: Adopt MediatR Pipeline Behaviors\nContext and validation.",
            },
        ],
        "wireframe_paths": [str(img1), str(img2)],
    }

    settings = Settings(repo_path=str(tmp_path))
    written_files = save_architecture_documents(state, settings)

    target_dir = tmp_path / "docs" / "architecture" / "medication-reconciliation"

    # Verify STRATEGY.md
    strategy_file = target_dir / "STRATEGY.md"
    assert strategy_file.exists()
    assert "Strategy for Medication Reconciliation" in strategy_file.read_text(encoding="utf-8")

    # Verify TACTICAL-PLAN.md
    tactical_file = target_dir / "TACTICAL-PLAN.md"
    assert tactical_file.exists()
    assert "Wave 1: Entities" in tactical_file.read_text(encoding="utf-8")

    # Verify ADR files
    adr1 = target_dir / "adrs" / "ADR-001.md"
    assert adr1.exists()
    assert "Use Outbox Pattern" in adr1.read_text(encoding="utf-8")

    adr2 = target_dir / "adrs" / "ADR-002.md"
    assert adr2.exists()
    assert "Adopt MediatR Pipeline Behaviors" in adr2.read_text(encoding="utf-8")

    # Verify Resources/ wireframe copies
    res1 = target_dir / "Resources" / "wireframe1.png"
    assert res1.exists()
    assert res1.read_bytes() == b"\x89PNG\r\n\x1a\nfake_image_bytes_1"

    res2 = target_dir / "Resources" / "mockup.jpg"
    assert res2.exists()
    assert res2.read_bytes() == b"\xff\xd8\xfffake_jpg_bytes_2"

    # Verify written files list
    assert len(written_files) == 6
    assert any("docs/architecture/medication-reconciliation/STRATEGY.md" in f for f in written_files)
    assert any("docs/architecture/medication-reconciliation/TACTICAL-PLAN.md" in f for f in written_files)
    assert any("docs/architecture/medication-reconciliation/Resources/wireframe1.png" in f for f in written_files)


def test_save_manual_test_doc(tmp_path: Path):
    """Verify MANUAL_TEST_GUIDE.md is written to the feature docs directory."""
    state: AgentState = {
        "repo_path": str(tmp_path),
        "feature_name": "Shift Scheduler",
    }
    settings = Settings(repo_path=str(tmp_path))
    content = "# Manual Test Guide\nStep 1: Open calendar.\nStep 2: Assign nurse."

    rel_path = save_manual_test_doc(state, settings, content)

    target_file = tmp_path / "docs" / "architecture" / "shift-scheduler" / "MANUAL_TEST_GUIDE.md"
    assert target_file.exists()
    assert "Assign nurse" in target_file.read_text(encoding="utf-8")
    assert rel_path == "docs/architecture/shift-scheduler/MANUAL_TEST_GUIDE.md"


@pytest.mark.asyncio
async def test_generate_manual_test_doc_node(tmp_path: Path):
    """Verify generate_manual_test_doc node invokes LLM and persists file."""
    from unittest.mock import AsyncMock

    mock_llm = MagicMock()
    mock_llm.ainvoke = AsyncMock(return_value="# Generated QA Test Scenarios\n- Test Happy Path\n- Test Edge Case")

    state: AgentState = {
        "repo_path": str(tmp_path),
        "feature_name": "Telehealth Visits",
        "strategy_document": "# Telehealth Strategy",
        "tactical_plan": "# Tactical Plan",
    }
    settings = Settings(repo_path=str(tmp_path))

    result = await generate_manual_test_doc(state, settings, mock_llm)

    target_file = tmp_path / "docs" / "architecture" / "telehealth-visits" / "MANUAL_TEST_GUIDE.md"
    assert target_file.exists()
    assert "Generated QA Test Scenarios" in target_file.read_text(encoding="utf-8")
    assert "manual_test_doc" in result
    assert result["current_step"] == "generate_manual_test_doc"
    assert "docs/architecture/telehealth-visits/MANUAL_TEST_GUIDE.md" in result["written_doc_files"]


# ─── 3. Git Ops Early Branch Commit Test ────────────────────────────────────


@pytest.mark.asyncio
async def test_create_branch_commits_architecture_and_resources_early(tmp_path: Path):
    """Verify create_branch saves and commits architecture blueprints + resources to Git."""
    import git

    # Initialize a clean git repo with initial commit
    repo = git.Repo.init(str(tmp_path))
    # Configure user for git commits
    repo.config_writer().set_value("user", "name", "Test User").release()
    repo.config_writer().set_value("user", "email", "test@example.com").release()

    readme = tmp_path / "README.md"
    readme.write_text("# HomeCare Test Repo", encoding="utf-8")
    repo.index.add(["README.md"])
    repo.index.commit("chore: initial commit")

    # Wireframe sample
    img = tmp_path / "nurse_schedule.png"
    img.write_bytes(b"image_content")

    state: AgentState = {
        "repo_path": str(tmp_path),
        "feature_name": "Nurse Roster",
        "feature_description": "Automated schedule dispatching for in-home nurses.",
        "strategy_document": "# Strategy: Nurse Roster\nC4 diagram here.",
        "tactical_plan": "# Tactical: Nurse Roster\nWave 1: Entities.",
        "adr_documents": [
            {
                "id": "ADR-001",
                "title": "Use SQLite for Dev Testing",
                "content": "# ADR-001 SQLite Decision",
            }
        ],
        "wireframe_paths": [str(img)],
    }
    # Set default branch to match the initialized branch (master or main)
    active_branch = repo.active_branch.name
    settings = Settings(repo_path=str(tmp_path), repo_default_branch=active_branch)

    # Run create_branch
    update = await create_branch(state, settings)

    assert update["branch_name"] == "feature/nurse-roster"
    assert update["arch_docs_dir"] == "docs/architecture/nurse-roster"
    assert len(update["written_arch_files"]) > 0

    # Verify Git commit
    latest_commit = repo.head.commit
    assert "docs(architecture): add strategy, tactical plan, ADRs, and visual resources" in latest_commit.message
    assert "Nurse Roster" in latest_commit.message

    # Verify files committed in Git tree
    committed_files = [item.path for item in latest_commit.tree.traverse()]
    norm_paths = [p.replace("\\", "/") for p in committed_files]
    assert any("docs/architecture/nurse-roster/STRATEGY.md" in p for p in norm_paths)
    assert any("docs/architecture/nurse-roster/TACTICAL-PLAN.md" in p for p in norm_paths)
    assert any("docs/architecture/nurse-roster/adrs/ADR-001.md" in p for p in norm_paths)
    assert any("docs/architecture/nurse-roster/Resources/nurse_schedule.png" in p for p in norm_paths)
