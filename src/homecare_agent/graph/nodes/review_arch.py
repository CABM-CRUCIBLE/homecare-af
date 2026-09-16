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
    logger.info("Performing architecture review for: %s", state.get("feature_name"))

    strategy = state.get("strategy_document", "")
    tactical = state.get("tactical_plan", "")
    adrs = state.get("adr_documents", [])
    prompts = state.get("agentic_prompts", [])

    adr_content = "\n\n---\n\n".join(
        adr.get("rendered_markdown", str(adr)) for adr in adrs
    )

    review_prompt = f"""Perform a comprehensive architecture review of the following proposal.

**Feature:** {state.get("feature_name")}

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
"""

    try:
        response = await llm.ainvoke(
            prompt=review_prompt,
            system_prompt=REVIEWER_PERSONA,
            node_name="review_architecture",
            state_overrides=state,
            trace_name="architecture_review",
            trace_metadata={"feature_name": state.get("feature_name", "")},
        )

        # Determine if architecture is approved based on review content
        response_lower = response.lower()
        has_blocking = "blocking" in response_lower and ("finding" in response_lower or "severity" in response_lower)
        is_rejected = "rejected" in response_lower or "request changes" in response_lower

        approved = not (has_blocking and is_rejected)

        return {
            "architecture_review": response,
            "architecture_approved": approved,
            "current_step": "review_architecture",
            "completed_steps": ["review_architecture"],
        }

    except Exception:
        logger.exception("Architecture review failed.")
        return {
            "architecture_review": "Review failed — see errors.",
            "architecture_approved": False,
            "errors": [{"step": "review_architecture", "message": "Architecture review failed"}],
            "current_step": "review_architecture",
            "completed_steps": ["review_architecture"],
        }
