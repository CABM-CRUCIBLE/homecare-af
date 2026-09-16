# Author: C A B M
# Date: 2026-09-17

"""Agentic prompt generation node.

Generates self-contained, parallelisable work package prompts from the
Strategy and Tactical Plan. Each prompt is scoped so it can be executed
independently and in parallel with others in its wave, touching a
disjoint set of files.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from homecare_agent.config import Settings
from homecare_agent.graph.state import AgentState
from homecare_agent.llm.provider import LLMProvider

logger = logging.getLogger(__name__)

PROMPT_GENERATOR_PERSONA = """\
You are a Senior Technical Lead who specializes in decomposing large features into
self-contained, parallelisable work packages for execution by engineers or AI agents.

Each work package prompt you generate must be:
1. SELF-CONTAINED: Can be handed to an engineer verbatim without any other context
2. COLLISION-FREE: Specifies exactly which files it owns and must not touch
3. COMPLETE: Includes goal, scope, file-by-file deliverables, and acceptance criteria
4. TESTABLE: Every deliverable has measurable exit criteria (build passes, tests pass)
5. SEQUENCED: Organized into waves where packages within a wave run in parallel

The standing instructions (enterprise standards) are prepended to every prompt.
"""

STANDING_INSTRUCTIONS_TEMPLATE = """\
You are working in the {repo_name} repository at {repo_path}.

MANDATORY READING BEFORE YOU WRITE CODE
1. AI_Instructions.md (repository root) — Enterprise Code Quality Standards. Non-negotiable.
{architecture_docs}

NON-NEGOTIABLE RULES
- Clean Architecture layering: Domain -> Application -> Infrastructure -> API. Never
  reference Infrastructure from Application, or EF Core from Application.
- CQRS via MediatR. Commands/Queries/Handlers/Validators live under
  Application/Features/<Feature>/.
- Repository + Unit of Work for all data access. No DbContext in the Application layer.
- XML doc comments (/// <summary>) on every public type, member, and interface.
- C#: PascalCase types/methods, _camelCase private fields. TypeScript: camelCase
  values, PascalCase components. NO `any` in TypeScript — strict interfaces only.
- FluentValidation on the backend, Zod on the frontend. Both, never one.
- All errors as RFC 7807 ProblemDetails via the existing global exception middleware.
  Never leak stack traces.
- Structured Serilog logging. Logs must NEVER contain PII or PHI. Log identifiers only.
- Money is ALWAYS integer minor units (long / bigint) plus an ISO 4217 currency code.
  Never float, never decimal-for-money, never a hard-coded currency symbol.
- Every mutation writes an AuditLog entry via the existing IAuditLogService.
- Vendor identity comes ONLY from IVendorIdentityResolver (JWT claims, fail-closed).
  NEVER accept vendorId from a route, query string, or request body.
- No secrets in source or appsettings.json. Use User Secrets / environment variables.
- All external dependencies injected via interfaces so they can be mocked in unit tests.

DELIVERABLE FORMAT
- Provide COMPLETE file contents. No "// ... rest of code" placeholders.
- After each major code block, add a short "Architectural Decision" note explaining WHY
  the pattern, index, or structure was chosen.
- Include unit tests for everything you write. Run `dotnet build` and `dotnet test`
  (backend) or `npm run build` and `npm run lint` (frontend) before declaring done.

DO NOT
- Do not modify files owned by another work package (see the File-Ownership Matrix).
- Do not add mock, fixture, or fallback data to any runtime path.
- Do not change existing endpoint routes, verbs, or response field names.
"""


async def generate_agentic_prompts(
    state: AgentState, settings: Settings, llm: LLMProvider
) -> dict[str, Any]:
    """Generate self-contained work package prompts.

    This node:
    1. Generates standing instructions from the enterprise standards
    2. Decomposes the tactical plan into work packages organized by wave
    3. Generates a file-ownership matrix for collision avoidance
    4. Creates a complete prompt for each work package

    Returns:
        State updates with agentic prompts, file ownership matrix, and standing instructions.
    """
    trace_id = state.get("trace_id", "no-trace")
    feature_name = state.get("feature_name", "Unknown")
    logger.info("[START:generate_agentic_prompts][trace_id=%s] Generating agentic prompts for: %s", trace_id, feature_name)

    # Generate standing instructions
    repo_path = state.get("repo_path", settings.repo_path)
    repo_name = Path(repo_path).name if repo_path else "HomeCare"

    strategy_doc = state.get("strategy_document", "")
    tactical_plan = state.get("tactical_plan", "")
    adr_docs = state.get("adr_documents", [])

    architecture_docs = f"""\
2. Strategy Document for {feature_name}
3. Tactical Plan for {feature_name}
"""
    for adr in adr_docs:
        architecture_docs += f"4. {adr.get('title', 'ADR')}\n"

    standing_instructions = STANDING_INSTRUCTIONS_TEMPLATE.format(
        repo_name=repo_name,
        repo_path=repo_path,
        architecture_docs=architecture_docs,
    )

    template_path = Path(settings.templates_dir) / "AGENTIC_PROMPTS_TEMPLATE.md"
    template = ""
    if template_path.exists():
        template = template_path.read_text(encoding="utf-8")

    prompt_gen_prompt = f"""Generate self-contained agentic execution prompts for the following feature.

**Feature:** {feature_name}

**Standing Instructions (to be prepended to every prompt):**
{standing_instructions}

**Tactical Plan (contains work package breakdown):**
{tactical_plan[:20000]}

**Strategy Document (for context):**
{strategy_doc[:10000]}

{f"**Template to follow:**{chr(10)}{template}" if template else ""}

REQUIREMENTS:
1. Organize work packages into WAVES with a Gantt chart (Mermaid)
2. Wave 0 must be a BLOCKING gate — it creates shared foundations
3. Each wave's packages run in PARALLEL on disjoint file sets
4. Generate a FILE-OWNERSHIP MATRIX showing which package owns which files
5. Each prompt must include:
   - GOAL: What this package delivers
   - SCOPE: File-by-file deliverables with exact paths
   - ACCEPTANCE CRITERIA: Build passes, tests pass, specific validations
   - Estimated effort (days)
6. No file may be modified by more than one work package
7. Each prompt is self-contained — prepend the standing instructions

Output as a JSON object with keys:
- "execution_order": Mermaid gantt chart as a string
- "file_ownership_matrix": list of {{file_path, exclusive_owner, operation}}
- "waves": list of {{wave_id, name, is_gate, work_packages: [{{id, title, owner_role, depends_on, parallel_safe, scope_description, prompt, acceptance_criteria, estimated_days}}]}}
"""

    try:
        logger.debug("[generate_agentic_prompts][trace_id=%s] Invoking LLM for prompt decomposition...", trace_id)
        response = await llm.ainvoke(
            prompt=prompt_gen_prompt,
            system_prompt=PROMPT_GENERATOR_PERSONA,
            node_name="generate_agentic_prompts",
            state_overrides=state,
            trace_name="generate_agentic_prompts",
            trace_metadata={"feature_name": feature_name, "trace_id": trace_id},
        )

        import json
        parsed = {}
        json_start = response.find("{")
        json_end = response.rfind("}") + 1
        if json_start != -1 and json_end > json_start:
            parsed = json.loads(response[json_start:json_end])
        else:
            logger.warning("[WARN:generate_agentic_prompts][trace_id=%s] No valid JSON block found in LLM response", trace_id)

        waves = parsed.get("waves", [])
        all_wps = []
        for wave in waves:
            for wp in wave.get("work_packages", []):
                wp["wave"] = wave.get("wave_id", "")
                all_wps.append(wp)

        logger.info(
            "[COMPLETED:generate_agentic_prompts][trace_id=%s] Generated %d work packages across %d wave(s)",
            trace_id,
            len(all_wps),
            len(waves),
        )

        return {
            "standing_instructions": standing_instructions,
            "agentic_prompts": all_wps,
            "file_ownership_matrix": parsed.get("file_ownership_matrix", []),
            "work_packages": all_wps,
            "current_step": "generate_agentic_prompts",
            "completed_steps": ["generate_agentic_prompts"],
        }

    except Exception as e:
        logger.error(
            "[ERROR:generate_agentic_prompts][trace_id=%s] Agentic prompt generation failed for '%s': %s",
            trace_id,
            feature_name,
            e,
            exc_info=True,
        )
        return {
            "standing_instructions": standing_instructions,
            "errors": [{"step": "generate_agentic_prompts", "trace_id": trace_id, "message": f"Prompt generation failed: {e}"}],
            "current_step": "generate_agentic_prompts",
            "completed_steps": ["generate_agentic_prompts"],
        }
