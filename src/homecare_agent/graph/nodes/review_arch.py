# Author: C A B M
# Date: 2026-09-17

"""Architecture review node.

Performs a deep pre-implementation review of the Strategy, Tactical Plan,
ADRs, and Agentic Prompts following the format from HomeCare's
Architecture_Review.md — with graded scorecard, traceability, and findings.
"""

from __future__ import annotations

import logging
from typing import Any

from homecare_agent.config import Settings
from homecare_agent.graph.state import AgentState
from homecare_agent.llm.provider import LLMProvider

logger = logging.getLogger(__name__)

REVIEWER_PERSONA = """\
You are a Senior Software Architect with 20+ years of experience performing rigorous
architecture reviews. You are reviewing a pre-implementation proposal for an enterprise
healthcare platform.

Your review must be:
1. EVIDENCE-BASED: Every finding references specific content in the documents
2. GRADED: Use a scorecard (A+/A/A-/B+/B/C/F) for each category
3. ACTIONABLE: Every finding includes a severity and suggested resolution
4. TRACED: If there was a prior review, verify disposition of every prior finding
5. COMPLIANT: Check HIPAA, GDPR, PCI-DSS implications explicitly

Severity levels:
- BLOCKING: Must fix before implementation can start
- CRITICAL: Must address during implementation
- MAJOR: Important but won't prevent implementation
- MEDIUM: Should fix; improves quality
- MINOR: Nice to have
- OBSERVATION: No action needed but noted

Review categories:
1. Clean Architecture Compliance
2. SOLID Principles
3. Security & Compliance
4. Data Model & Schema Design
5. API Design
6. Frontend Architecture
7. Testing Strategy
8. Performance & Scalability
9. Observability
10. Documentation Quality
"""


async def review_architecture(state: AgentState, settings: Settings, llm: LLMProvider) -> dict[str, Any]:
    """Perform architecture review of the generated documents.

    Reviews the Strategy, Tactical Plan, ADRs, and Agentic Prompts for:
    - Consistency between documents
    - Clean Architecture compliance
    - Enterprise standards adherence
    - Security and compliance considerations
    - Missing edge cases
    - Performance implications

    Returns:
        State updates with review findings and approval status.
    """
    trace_id = state.get("trace_id", "no-trace")
    feature_name = state.get("feature_name", "Unknown")
    logger.info("[START:review_architecture][trace_id=%s] Performing architecture review for: %s", trace_id, feature_name)

    strategy = state.get("strategy_document", "")
    tactical = state.get("tactical_plan", "")
    adrs = state.get("adr_documents", [])
    prompts = state.get("agentic_prompts", [])

    adr_content = "\n\n---\n\n".join(
        adr.get("rendered_markdown", str(adr)) for adr in adrs
    )

    review_prompt = f"""Perform a comprehensive architecture review of the following proposal.

**Feature:** {feature_name}

**Strategy Document:**
{strategy[:15000]}

**Tactical Plan:**
{tactical[:15000]}

**ADRs:**
{adr_content[:10000]}

**Work Packages:**
{len(prompts)} work packages organized into waves.

REVIEW CHECKLIST:
1. Are Strategy and Tactical Plan internally consistent?
2. Do ADRs cover all architecturally significant decisions?
3. Is Clean Architecture (Domain → Application → Infrastructure → API) strictly enforced?
4. Are SOLID principles followed throughout?
5. Is the data model normalized appropriately with correct indexes and constraints?
6. Are all API endpoints properly authorized and validated?
7. Is the frontend architecture server-first with appropriate client islands?
8. Does the testing strategy cover unit, integration, E2E, and architecture tests?
9. Are there security gaps (PII exposure, tenant isolation, injection vectors)?
10. Is HIPAA/GDPR/PCI-DSS compliance maintained?
11. Are work packages properly scoped with no file collisions?
12. Are acceptance criteria testable and measurable?

OUTPUT FORMAT:
Generate the review as a COMPLETE markdown document following this structure:

# Architecture Review: [Feature Name]

## Metadata (table: Review Date, Reviewer Role, Review Type, Scope)
## 1. Executive Verdict (APPROVED / APPROVED WITH OBSERVATIONS / REQUEST CHANGES / REJECTED)
## 2. Review Scorecard (table: Category, Grade, Notes)
## 3-N. Section-by-section analysis with findings
## Final Section: Summary of all findings (table: ID, Severity, Category, Description)

At the very end of your response, output a structured verdict code block:
```verdict
{{"verdict": "APPROVED" | "APPROVED_WITH_OBSERVATIONS" | "REQUEST_CHANGES" | "REJECTED", "has_blocking_findings": true | false}}
```
"""

    try:
        logger.debug("[review_architecture][trace_id=%s] Invoking LLM for architecture review...", trace_id)
        response = await llm.ainvoke(
            prompt=review_prompt,
            system_prompt=REVIEWER_PERSONA,
            node_name="review_architecture",
            state_overrides=state,
            trace_name="architecture_review",
            trace_metadata={"feature_name": feature_name, "trace_id": trace_id},
        )

        # Determine if architecture is approved based on structured verdict or heuristics
        import json
        import re

        approved = False
        verdict_match = re.search(r"```verdict\s*(\{.*?\})\s*```", response, re.DOTALL)
        if verdict_match:
            try:
                verdict_data = json.loads(verdict_match.group(1))
                v = str(verdict_data.get("verdict", "")).upper()
                has_blocking = bool(verdict_data.get("has_blocking_findings", False))
                approved = v in ("APPROVED", "APPROVED_WITH_OBSERVATIONS") and not has_blocking
            except Exception as parse_err:
                logger.debug("Failed to parse verdict JSON block: %s", parse_err)
                verdict_match = None

        if not verdict_match:
            # Fallback heuristic: check executive verdict and finding severities
            response_lower = response.lower()
            is_explicit_rejection = any(term in response_lower for term in [
                "verdict: rejected",
                "verdict: request changes",
                "verdict: changes requested",
                "verdict**: rejected",
                "verdict**: request changes",
                "verdict**: changes requested",
                "executive verdict: rejected",
                "executive verdict: request changes",
            ])
            has_blocking_findings = bool(
                re.search(r"\|\s*b-\d+\s*\|\s*blocking\b", response_lower)
                or re.search(r"\bseverity:\s*blocking\b", response_lower)
            )
            approved = not (is_explicit_rejection or has_blocking_findings)

        logger.info(
            "[COMPLETED:review_architecture][trace_id=%s] Architecture review completed (approved=%s, %d chars generated)",
            trace_id,
            approved,
            len(response),
        )

        return {
            "architecture_review": response,
            "architecture_approved": approved,
            "current_step": "review_architecture",
            "completed_steps": ["review_architecture"],
        }

    except Exception as e:
        logger.error(
            "[ERROR:review_architecture][trace_id=%s] Architecture review failed for '%s': %s",
            trace_id,
            feature_name,
            e,
            exc_info=True,
        )
        return {
            "architecture_review": "Review failed — see errors.",
            "architecture_approved": False,
            "errors": [{"step": "review_architecture", "trace_id": trace_id, "message": f"Architecture review failed: {e}"}],
            "current_step": "review_architecture",
            "completed_steps": ["review_architecture"],
        }
