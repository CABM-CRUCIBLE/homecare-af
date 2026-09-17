# Author: C A B M
# Date: 2026-09-17

"""Code review node.

Performs post-implementation code review of generated code against
enterprise standards. Following the format from Code_Review.md with
graded scorecard and actionable findings.
"""

from __future__ import annotations

import logging
from typing import Any

from homecare_agent.config import Settings
from homecare_agent.graph.state import AgentState
from homecare_agent.llm.provider import LLMProvider

logger = logging.getLogger(__name__)

CODE_REVIEWER_PERSONA = """\
You are a Senior Software Architect with 20+ years of experience performing critical
code reviews for enterprise healthcare applications.

Standards reference: AI_Instructions.md — Enterprise Code Quality Standards

Your code review must check:
1. SOLID Principles — Single Responsibility, Dependency Inversion enforced?
2. Clean Architecture — Domain → Application → Infrastructure → API layering respected?
3. Design Patterns — Repository, State Machine, Strategy, Factory used correctly?
4. Security — CSRF, PII redaction, CSV injection guards, tenant isolation, input validation?
5. Type Safety — Zero `any` types in TypeScript?
6. Testing — Unit/integration/E2E/architecture tests with adequate coverage?
7. Observability — Structured logging, PII filtering, metrics?
8. Frontend Architecture — Server-first RSC, BFF proxy, URL-driven state?
9. Concurrency Control — PostgreSQL xmin, If-Match/ETag?
10. Documentation — XML docs, ADRs, inline rationale comments?
11. Code Organization — Feature folders, file naming conventions?

Output as a COMPLETE markdown document:
# Critical Code Review — [Feature Name]
## Executive Summary (verdict: APPROVE / APPROVE WITH OBSERVATIONS / REQUEST CHANGES)
## Review Scorecard (table: Category, Grade, Notes)
## Section analyses
## Findings (table: ID, Severity, Category, Title, File, Suggestion)
"""


async def perform_code_review(state: AgentState, settings: Settings, llm: LLMProvider) -> dict[str, Any]:
    """Perform code review of the generated code.

    Reviews all generated code against enterprise standards and the
    architectural decisions made in the Strategy and ADRs.

    Returns:
        State updates with review findings and whether changes are needed.
    """
    trace_id = state.get("trace_id", "no-trace")
    feature_name = state.get("feature_name", "Unknown")
    generated_code = state.get("generated_code", {})
    logger.info(
        "[START:perform_code_review][trace_id=%s] Performing code review for '%s' (%d file(s))...",
        trace_id,
        feature_name,
        len(generated_code),
    )

    strategy = state.get("strategy_document", "")
    tactical = state.get("tactical_plan", "")

    # Prepare code summary for review
    code_summary_parts = []
    for file_path, content in list(generated_code.items())[:50]:  # Cap at 50 files
        code_summary_parts.append(f"### {file_path}\n```\n{content[:3000]}\n```")

    code_summary = "\n\n".join(code_summary_parts)

    review_prompt = f"""Perform a critical code review of the following generated code.

**Feature:** {feature_name}
**Branch:** {state.get("branch_name", "")}
**Files Changed:** {len(generated_code)}

**Code:**
{code_summary[:30000]}

**Strategy (for architectural alignment):**
{strategy[:5000]}

**Tactical Plan (for schema/API alignment):**
{tactical[:5000]}

Review against ALL enterprise standards. Be thorough but fair.
Generate the complete review document with scorecard and findings.
"""

    try:
        logger.debug("[perform_code_review][trace_id=%s] Invoking LLM for critical code review...", trace_id)
        response = await llm.ainvoke(
            prompt=review_prompt,
            system_prompt=CODE_REVIEWER_PERSONA,
            node_name="perform_code_review",
            state_overrides=state,
            trace_name="code_review",
            trace_metadata={
                "feature_name": feature_name,
                "files_count": len(generated_code),
                "trace_id": trace_id,
            },
        )

        # Check if changes are needed
        response_lower = response.lower()
        changes_needed = "request changes" in response_lower or (
            "blocking" in response_lower and "finding" in response_lower
        )

        review_iteration = state.get("review_iteration", 0) + 1

        logger.info(
            "[COMPLETED:perform_code_review][trace_id=%s] Code review finished for '%s' (iteration %d, changes_needed=%s, %d chars)",
            trace_id,
            feature_name,
            review_iteration,
            changes_needed,
            len(response),
        )

        return {
            "code_review_findings": [{"iteration": review_iteration, "review": response}],
            "review_changes_needed": changes_needed,
            "review_iteration": review_iteration,
            "current_step": "code_review",
            "completed_steps": ["code_review"],
        }

    except Exception as e:
        logger.error(
            "[ERROR:perform_code_review][trace_id=%s] Code review failed for '%s': %s",
            trace_id,
            feature_name,
            e,
            exc_info=True,
        )
        return {
            "review_changes_needed": False,
            "errors": [{"step": "code_review", "trace_id": trace_id, "message": f"Code review failed: {e}"}],
            "current_step": "code_review",
            "completed_steps": ["code_review"],
        }


async def apply_review_fixes(state: AgentState, settings: Settings, llm: LLMProvider) -> dict[str, Any]:
    """Apply fixes based on code review findings.

    Takes the review findings and generates corrected code for
    files with blocking or critical findings.

    Returns:
        State updates with corrected generated code.
    """
    trace_id = state.get("trace_id", "no-trace")
    feature_name = state.get("feature_name", "Unknown")
    iteration = state.get("review_iteration", 0)
    logger.info(
        "[START:apply_review_fixes][trace_id=%s] Applying code review fixes for '%s' (iteration %d)...",
        trace_id,
        feature_name,
        iteration,
    )

    findings = state.get("code_review_findings", [])
    generated_code = state.get("generated_code", {})

    latest_review = findings[-1] if findings else {}
    review_text = latest_review.get("review", "")

    fix_prompt = f"""Based on the following code review findings, generate corrected versions
of the affected files. Only fix files with BLOCKING, CRITICAL, or MAJOR findings.

**Code Review Findings:**
{review_text[:15000]}

**Current Code:**
(Only files that need fixes)

For each file you fix, output in this format:
### FILE: <relative/path/to/file>
```<language>
<complete corrected file contents>
```

Fix ALL blocking and critical issues. Provide COMPLETE file contents.
"""

    try:
        logger.debug("[apply_review_fixes][trace_id=%s] Invoking LLM to generate fixes for iteration %d...", trace_id, iteration)
        response = await llm.ainvoke(
            prompt=fix_prompt,
            system_prompt=CODE_REVIEWER_PERSONA,
            node_name="apply_review_fixes",
            state_overrides=state,
            trace_name="apply_review_fixes",
            trace_metadata={"iteration": iteration, "feature_name": feature_name, "trace_id": trace_id},
        )

        # Parse fixed files using standard parser
        from homecare_agent.graph.nodes.execute_prompt import _parse_generated_files

        fixed_code = _parse_generated_files(response)

        logger.info(
            "[COMPLETED:apply_review_fixes][trace_id=%s] Applied fixes to %d file(s) for '%s'",
            trace_id,
            len(fixed_code),
            feature_name,
        )

        return {
            "generated_code": fixed_code,
            "current_step": "apply_fixes",
            "completed_steps": ["apply_review_fixes"],
        }

    except Exception as e:
        logger.error(
            "[ERROR:apply_review_fixes][trace_id=%s] Applying review fixes failed for '%s': %s",
            trace_id,
            feature_name,
            e,
            exc_info=True,
        )
        return {
            "errors": [{"step": "apply_review_fixes", "trace_id": trace_id, "message": f"Fix application failed: {e}"}],
            "current_step": "apply_fixes",
            "completed_steps": ["apply_review_fixes"],
        }
