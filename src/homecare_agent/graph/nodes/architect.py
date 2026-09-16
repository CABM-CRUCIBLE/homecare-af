"""Architect node — generates Strategy, Tactical Plan, and ADR documents.

This is the core architecture generation node that produces the complete
document pipeline following the proven HomeCare format:
  Strategy → Tactical Plan → ADRs → Agentic Prompts
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from homecare_agent.config import Settings
from homecare_agent.graph.state import AgentState
from homecare_agent.llm.provider import LLMProvider

logger = logging.getLogger(__name__)

ARCHITECT_PERSONA = """\
You are a Senior Solution Architect with 20+ years of experience building enterprise
healthcare platforms. You specialize in Clean Architecture, CQRS, Domain-Driven Design,
and regulatory compliance (HIPAA, GDPR, PCI-DSS).

You are generating architecture documents for an enterprise healthcare platform that uses:
- Backend: .NET 10, ASP.NET Core, Clean Architecture (4 layers), CQRS via MediatR,
  Repository + Unit of Work, FluentValidation, Serilog structured logging
- Frontend: Next.js 15 (App Router), React 19, TypeScript, Tailwind CSS,
  Server-First RSC, BFF proxy pattern, URL-driven state, Zod validation
- Database: PostgreSQL 16, EF Core Code-First, soft delete, audit logging,
  xmin concurrency tokens, CHECK constraints
- Auth: OIDC/PKCE, JWT Bearer, RBAC + Feature-Based Access Control (FBAC),
  fail-closed tenant identity
- Compliance: HIPAA, GDPR, PCI-DSS — No PII in logs, encrypted fields,
  audit trails, RFC 7807 errors

Your documents must be:
1. Evidence-based: cite specific file paths and code references
2. Precise: every requirement has an ID, every table has columns and constraints
3. Consistent: diagrams, schemas, and API specs must align perfectly
4. Complete: no placeholders, no "to be determined" — make decisions
5. Production-ready: security, compliance, performance considered throughout
"""


async def generate_strategy(state: AgentState, settings: Settings, llm: LLMProvider) -> dict[str, Any]:
    """Generate the Strategy document.

    Produces a comprehensive strategy following the format of the HomeCare
    architecture pipeline with these sections:
    1. Purpose and Scope
    2. Current-State Assessment
    3. Functional Requirements
    4. Non-Functional Requirements
    5. Constraints & Assumptions
    6. Strategic Position
    7. Use Case Diagram (Mermaid)
    8. Sequence Diagrams (Mermaid)
    9. C4 Container Diagram (Mermaid)
    10. C4 Component Diagram (Mermaid)
    11. Domain State Machines (if applicable)
    12. Gap Analysis vs. Existing Codebase
    13. Risk Register
    14. Open Questions & Execution Gate
    """
    logger.info("Generating Strategy document for: %s", state.get("feature_name"))

    # Load the strategy template
    template_path = Path(settings.templates_dir) / "STRATEGY_TEMPLATE.md"
    template = ""
    if template_path.exists():
        template = template_path.read_text(encoding="utf-8")

    codebase_analysis = state.get("codebase_analysis", {})
    clarification_answers = state.get("clarification_answers", [])

    strategy_prompt = f"""Generate a complete Strategy Document for this feature.

**Feature:** {state.get("feature_name")}
**Description:** {state.get("feature_description")}

**Codebase Analysis Results:**
{_format_analysis(codebase_analysis)}

**Clarification Answers:**
{_format_answers(clarification_answers)}

{f"**Template to follow:**{chr(10)}{template}" if template else ""}

REQUIREMENTS:
1. Follow the EXACT section structure from the template
2. Every functional requirement gets an ID (FR-01, FR-02, ...)
3. Every non-functional requirement gets an ID (NFR-01, NFR-02, ...)
4. Include Mermaid diagrams for: Use Case, Sequence, C4 Container, C4 Component
5. The Gap Analysis must cite specific existing files and patterns
6. The Risk Register must include likelihood, impact, and mitigation
7. Include state machine diagrams for any entity with a status lifecycle
8. Reference related ADRs from the existing codebase
9. Include an Execution Gate section listing prerequisites for implementation

Output the COMPLETE markdown document. No placeholders.
"""

    try:
        response = await llm.ainvoke(
            prompt=strategy_prompt,
            system_prompt=ARCHITECT_PERSONA,
            node_name="generate_strategy",
            state_overrides=state,
            trace_name="generate_strategy",
            trace_metadata={"feature_name": state.get("feature_name", "")},
        )

        return {
            "strategy_document": response,
            "current_step": "generate_strategy",
            "completed_steps": ["generate_strategy"],
        }

    except Exception:
        logger.exception("Strategy generation failed.")
        return {
            "errors": [{"step": "generate_strategy", "message": "Strategy generation failed"}],
            "current_step": "generate_strategy",
            "completed_steps": ["generate_strategy"],
        }


async def generate_tactical_plan(state: AgentState, settings: Settings, llm: LLMProvider) -> dict[str, Any]:
    """Generate the Tactical Plan — the implementation blueprint.

    Sections:
    1. Entity Relationship Diagram (Mermaid erDiagram)
    2. Database Schema Details (tables, indexes, CHECK constraints)
    3. Status Vocabularies and State Machines
    4. Migration Plan
    5. High-Level Design — Component Diagram
    6. API Endpoints (method, route, handler, auth, status codes)
    7. Data Transfer Objects
    8. Frontend Route and Component Map
    9. Responsive and Accessibility Specification
    10. Work Package Breakdown & Sequencing
    11. Test Strategy
    12. Observability
    13. Definition of Done
    """
    logger.info("Generating Tactical Plan for: %s", state.get("feature_name"))

    template_path = Path(settings.templates_dir) / "TACTICAL_PLAN_TEMPLATE.md"
    template = ""
    if template_path.exists():
        template = template_path.read_text(encoding="utf-8")

    tactical_prompt = f"""Generate a complete Tactical Plan for this feature.
This is the implementation blueprint that drives code generation.

**Feature:** {state.get("feature_name")}
**Strategy Document (already approved):**
{state.get("strategy_document", "")[:15000]}

{f"**Template to follow:**{chr(10)}{template}" if template else ""}

REQUIREMENTS:
1. ERD as a Mermaid erDiagram with complete column definitions
2. EVERY database table must list: columns (name, type, nullable), indexes, CHECK constraints, FK behaviors
3. Complete API endpoint table: #, method, route, handler class, description, request DTO, response DTO, auth policy, status codes
4. Complete frontend route map with render strategy (RSC vs client)
5. DTO specifications with all fields and types
6. Work Package Breakdown organized into waves with dependencies and estimated effort
7. Gantt chart (Mermaid) showing wave scheduling
8. File-ownership matrix for collision avoidance
9. Test strategy covering unit, integration, E2E, and load testing
10. Responsive breakpoints and accessibility (WCAG 2.1 AA) specifications

Output the COMPLETE markdown document. No placeholders.
"""

    try:
        response = await llm.ainvoke(
            prompt=tactical_prompt,
            system_prompt=ARCHITECT_PERSONA,
            node_name="generate_tactical_plan",
            state_overrides=state,
            trace_name="generate_tactical_plan",
            trace_metadata={"feature_name": state.get("feature_name", "")},
        )

        return {
            "tactical_plan": response,
            "current_step": "generate_tactical_plan",
            "completed_steps": ["generate_tactical_plan"],
        }

    except Exception:
        logger.exception("Tactical plan generation failed.")
        return {
            "errors": [{"step": "generate_tactical_plan", "message": "Tactical plan generation failed"}],
            "current_step": "generate_tactical_plan",
            "completed_steps": ["generate_tactical_plan"],
        }


async def generate_adrs(state: AgentState, settings: Settings, llm: LLMProvider) -> dict[str, Any]:
    """Generate Architecture Decision Records for significant decisions.

    Following the exhaustive ADR format from HomeCare ADR-021:
    - Status, Date, Deciders, Related ADRs, Scope
    - Context (the full problem statement)
    - Multiple numbered Decisions (D-01, D-02, ...) each with Decision, Rationale, Consequences
    - Alternatives Considered with rejection rationale
    - Consequences (positive, negative, risks with mitigation)
    - Compliance Notes
    - Validation criteria
    """
    logger.info("Generating ADRs for: %s", state.get("feature_name"))

    template_path = Path(settings.templates_dir) / "ADR_TEMPLATE.md"
    template = ""
    if template_path.exists():
        template = template_path.read_text(encoding="utf-8")

    adr_prompt = f"""Based on the Strategy and Tactical Plan, identify and generate
Architecture Decision Records (ADRs) for every architecturally significant decision.

**Feature:** {state.get("feature_name")}

**Strategy Document:**
{state.get("strategy_document", "")[:10000]}

**Tactical Plan:**
{state.get("tactical_plan", "")[:10000]}

{f"**ADR Template to follow:**{chr(10)}{template}" if template else ""}

REQUIREMENTS:
1. Use the EXHAUSTIVE ADR format with numbered decisions (D-01, D-02, ...)
2. Each ADR must include: Status metadata table, Context, multiple Decisions,
   Alternatives Considered, Consequences (positive/negative/risks), Compliance Notes, Validation
3. Every decision must have a clear Rationale explaining WHY
4. Alternatives must explain WHY each was rejected
5. Risks must have mitigations
6. Compliance notes must reference HIPAA/GDPR/PCI-DSS implications

Output as a JSON array of ADR objects, each with keys:
- "number": int
- "title": string
- "rendered_markdown": string (the complete ADR markdown)
"""

    try:
        response = await llm.ainvoke(
            prompt=adr_prompt,
            system_prompt=ARCHITECT_PERSONA,
            node_name="generate_adrs",
            state_overrides=state,
            trace_name="generate_adrs",
            trace_metadata={"feature_name": state.get("feature_name", "")},
        )

        # Parse ADR list
        import json
        adrs = []
        json_start = response.find("[")
        json_end = response.rfind("]") + 1
        if json_start != -1 and json_end > json_start:
            adrs = json.loads(response[json_start:json_end])
        else:
            # Treat the whole response as a single ADR document
            adrs = [{"number": 1, "title": state.get("feature_name", ""), "rendered_markdown": response}]

        return {
            "adr_documents": adrs,
            "current_step": "generate_adrs",
            "completed_steps": ["generate_adrs"],
        }

    except Exception:
        logger.exception("ADR generation failed.")
        return {
            "errors": [{"step": "generate_adrs", "message": "ADR generation failed"}],
            "current_step": "generate_adrs",
            "completed_steps": ["generate_adrs"],
        }


def _format_analysis(analysis: dict[str, Any]) -> str:
    """Format codebase analysis dict into a readable string."""
    import json
    try:
        return json.dumps(analysis, indent=2, default=str)[:8000]
    except Exception:
        return str(analysis)[:8000]


def _format_answers(answers: list[dict[str, Any]]) -> str:
    """Format clarification answers into a readable string."""
    if not answers:
        return "No clarification questions were needed."
    parts = []
    for a in answers:
        parts.append(f"Q: {a.get('question', '')} → A: {a.get('answer', '')}")
    return "\n".join(parts)
