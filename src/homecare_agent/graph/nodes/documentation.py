# Author: C A B M
# Date: 2026-09-17

"""Documentation generation and persistence node for architecture blueprints, ADRs, and QA testing guides."""

from __future__ import annotations

import logging
import re
import shutil
from pathlib import Path
from typing import Any

from homecare_agent.config import Settings
from homecare_agent.graph.state import AgentState
from homecare_agent.llm.provider import LLMProvider
from homecare_agent.tools.file_tools import validate_safe_path

logger = logging.getLogger(__name__)


def get_feature_slug(feature_name: str) -> str:
    """Generate a clean, sanitized kebab-case slug for a feature name."""
    slug = re.sub(r"[^a-z0-9]+", "-", (feature_name or "feature").lower()).strip("-")
    return slug or "feature"


def get_feature_docs_dir(repo_path: str | Path, feature_name: str) -> Path:
    """Derive the destination directory for a feature's architecture documentation.

    Structure: <repo_path>/docs/architecture/<feature-slug>/
    """
    slug = get_feature_slug(feature_name)
    return Path(repo_path) / "docs" / "architecture" / slug


def save_architecture_documents(state: AgentState, settings: Settings) -> list[str]:
    """Persist architecture documents, ADRs, and visual screenshot resources to disk.

    Writes to: <repo_path>/docs/architecture/<feature-slug>/
      ├── STRATEGY.md
      ├── TACTICAL-PLAN.md
      ├── adrs/
      │   ├── ADR-001.md
      │   └── ...
      └── Resources/
          ├── wireframe_01.png
          └── ...

    Returns:
        List of relative paths of successfully written and archived files.
    """
    trace_id = state.get("trace_id", "no-trace")
    feature_name = state.get("feature_name", "feature")
    raw_repo = state.get("repo_path") or settings.repo_path or "."
    repo_path = Path(raw_repo).resolve()

    target_dir = get_feature_docs_dir(repo_path, feature_name)
    adrs_dir = target_dir / "adrs"
    resources_dir = target_dir / "Resources"

    logger.info(
        "[START:save_architecture_documents][trace_id=%s] Saving architecture blueprints for '%s' to %s...",
        trace_id,
        feature_name,
        target_dir,
    )

    written_files: list[str] = []

    # 1. Strategy Document
    strategy_doc = state.get("strategy_document", "")
    if strategy_doc:
        try:
            strat_path = target_dir / "STRATEGY.md"
            safe_strat = validate_safe_path(strat_path, repo_path)
            safe_strat.parent.mkdir(parents=True, exist_ok=True)
            safe_strat.write_text(strategy_doc, encoding="utf-8")
            written_files.append(str(strat_path.relative_to(repo_path)).replace("\\", "/"))
            logger.info("[save_architecture_documents][trace_id=%s] Persisted STRATEGY.md (%d bytes)", trace_id, len(strategy_doc))
        except Exception as err:
            logger.error("[save_architecture_documents][trace_id=%s] Failed to write STRATEGY.md: %s", trace_id, err)

    # 2. Tactical Plan
    tactical_plan = state.get("tactical_plan", "")
    if tactical_plan:
        try:
            tact_path = target_dir / "TACTICAL-PLAN.md"
            safe_tact = validate_safe_path(tact_path, repo_path)
            safe_tact.parent.mkdir(parents=True, exist_ok=True)
            safe_tact.write_text(tactical_plan, encoding="utf-8")
            written_files.append(str(tact_path.relative_to(repo_path)).replace("\\", "/"))
            logger.info("[save_architecture_documents][trace_id=%s] Persisted TACTICAL-PLAN.md (%d bytes)", trace_id, len(tactical_plan))
        except Exception as err:
            logger.error("[save_architecture_documents][trace_id=%s] Failed to write TACTICAL-PLAN.md: %s", trace_id, err)

    # 3. ADR Documents
    adr_docs = state.get("adr_documents") or state.get("adrs") or []
    if adr_docs:
        try:
            safe_adrs_dir = validate_safe_path(adrs_dir, repo_path)
            safe_adrs_dir.mkdir(parents=True, exist_ok=True)
            for idx, adr in enumerate(adr_docs, start=1):
                adr_num = adr.get("number", idx) if isinstance(adr, dict) else idx
                filename = f"ADR-{adr_num:03d}.md"
                content = ""
                if isinstance(adr, dict):
                    content = adr.get("rendered_markdown") or adr.get("content") or str(adr)
                else:
                    content = str(adr)
                adr_path = adrs_dir / filename
                safe_adr = validate_safe_path(adr_path, repo_path)
                safe_adr.write_text(content, encoding="utf-8")
                written_files.append(str(adr_path.relative_to(repo_path)).replace("\\", "/"))
            logger.info("[save_architecture_documents][trace_id=%s] Persisted %d ADR(s) in %s", trace_id, len(adr_docs), adrs_dir)
        except Exception as err:
            logger.error("[save_architecture_documents][trace_id=%s] Failed to write ADRs: %s", trace_id, err)

    # 4. Screenshots & Wireframes inside Resources/
    wireframe_paths = state.get("wireframe_paths", [])
    if wireframe_paths:
        try:
            safe_res_dir = validate_safe_path(resources_dir, repo_path)
            safe_res_dir.mkdir(parents=True, exist_ok=True)
            valid_exts = {".png", ".jpg", ".jpeg", ".webp", ".svg", ".gif", ".bmp"}
            for wf in wireframe_paths:
                src_p = Path(wf)
                if src_p.exists() and src_p.is_file() and src_p.suffix.lower() in valid_exts:
                    dest_p = resources_dir / src_p.name
                    safe_dest = validate_safe_path(dest_p, repo_path)
                    shutil.copy2(src_p, safe_dest)
                    written_files.append(str(dest_p.relative_to(repo_path)).replace("\\", "/"))
                    logger.info(
                        "[save_architecture_documents][trace_id=%s] Archived screenshot '%s' to Resources/",
                        trace_id,
                        src_p.name,
                    )
        except Exception as err:
            logger.error("[save_architecture_documents][trace_id=%s] Failed to archive screenshots: %s", trace_id, err)

    logger.info(
        "[COMPLETED:save_architecture_documents][trace_id=%s] Successfully persisted %d architecture file(s) under %s",
        trace_id,
        len(written_files),
        target_dir,
    )
    return written_files


def save_manual_test_doc(state: AgentState, settings: Settings, content: str) -> str:
    """Save the QA manual testing guide to the feature's documentation directory."""
    trace_id = state.get("trace_id", "no-trace")
    feature_name = state.get("feature_name", "feature")
    raw_repo = state.get("repo_path") or settings.repo_path or "."
    repo_path = Path(raw_repo).resolve()

    target_dir = get_feature_docs_dir(repo_path, feature_name)
    test_doc_path = target_dir / "MANUAL_TEST_GUIDE.md"
    safe_path = validate_safe_path(test_doc_path, repo_path)
    safe_path.parent.mkdir(parents=True, exist_ok=True)
    safe_path.write_text(content, encoding="utf-8")

    rel_path = str(test_doc_path.relative_to(repo_path)).replace("\\", "/")
    logger.info(
        "[save_manual_test_doc][trace_id=%s] Saved manual testing guide to %s (%d bytes)",
        trace_id,
        rel_path,
        len(content),
    )
    return rel_path


async def generate_manual_test_doc(state: AgentState, settings: Settings, llm: LLMProvider) -> dict[str, Any]:
    """Generate manual testing guide for QA teams and persist it to disk.

    Args:
        state: Current graph state.
        settings: Application settings.
        llm: LLM provider instance.

    Returns:
        State updates containing documentation status and written files.
    """
    trace_id = state.get("trace_id", "no-trace")
    feature_name = state.get("feature_name", "Unknown")
    logger.info("[START:generate_manual_test_doc][trace_id=%s] Generating manual test guide for '%s'...", trace_id, feature_name)

    prompt = f"""Generate a comprehensive Manual Testing Guide for:
**Feature:** {feature_name}
**Strategy:** {state.get("strategy_document", "")[:5000]}

Include step-by-step test scenarios for every functional requirement.
Format as markdown following a standard QA testing guide template.
"""
    try:
        response = await llm.ainvoke(
            prompt=prompt,
            system_prompt="You are a QA Lead generating a manual testing guide.",
            node_name="generate_manual_test_doc",
            state_overrides=state,
            trace_name="generate_manual_test_doc",
            trace_metadata={"feature_name": feature_name, "trace_id": trace_id},
        )
        logger.info(
            "[COMPLETED:generate_manual_test_doc][trace_id=%s] Manual test guide generated successfully (%d chars)",
            trace_id,
            len(response),
        )

        # Also persist to disk
        rel_path = save_manual_test_doc(state, settings, response)

        return {
            "manual_test_doc": response,
            "written_doc_files": [rel_path],
            "current_step": "generate_manual_test_doc",
            "completed_steps": ["generate_manual_test_doc"],
        }
    except Exception as e:
        logger.error(
            "[ERROR:generate_manual_test_doc][trace_id=%s] Manual test guide generation failed: %s",
            trace_id,
            e,
            exc_info=True,
        )
        return {
            "errors": [{"step": "generate_manual_test_doc", "trace_id": trace_id, "message": f"Manual test guide generation failed: {e}"}],
            "current_step": "generate_manual_test_doc",
            "completed_steps": ["generate_manual_test_doc"],
        }
