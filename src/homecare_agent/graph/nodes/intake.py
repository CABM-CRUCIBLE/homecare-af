"""Feature intake node — entry point for the agentic pipeline.

Receives the feature request, analyzes wireframes via vision LLM,
extracts initial requirements, and determines whether clarification
is needed before proceeding to architecture.
"""

from __future__ import annotations

import logging
from typing import Any

from homecare_agent.config import Settings
from homecare_agent.graph.state import AgentState
from homecare_agent.llm.provider import LLMProvider

logger = logging.getLogger(__name__)

INTAKE_SYSTEM_PROMPT = """\
You are a Senior Business Analyst and Requirements Engineer with 20+ years of experience
in enterprise healthcare software. You specialize in extracting precise, testable requirements
from natural language descriptions and visual wireframes.

Your goal is to:
1. Parse the feature request into structured functional and non-functional requirements
2. Identify ambiguities, missing information, and areas needing clarification
3. Determine the scope boundary (in-scope vs. explicitly out-of-scope)
4. Identify compliance implications (HIPAA, GDPR, PCI-DSS)
5. Map integration points with existing system modules

Output your analysis as a structured JSON object with these keys:
- "functional_requirements": list of {id, title, description, priority}
- "non_functional_requirements": list of {id, category, description, target_metric}
- "constraints": list of strings
- "assumptions": list of strings
- "out_of_scope": list of {item, reason}
- "clarification_needed": boolean
- "clarification_questions": list of {id, category, question, context, is_critical}
- "integration_points": list of strings (existing modules this feature touches)
- "compliance_implications": list of strings
"""

WIREFRAME_ANALYSIS_PROMPT = """\
Analyze the following wireframe/screenshot for a healthcare enterprise application.
Extract:
1. UI components visible (tables, forms, buttons, cards, modals, tabs, navigation)
2. Data fields shown (column names, form inputs, labels)
3. User actions/interactions implied (CRUD operations, filters, exports, navigation flows)
4. Layout structure (responsive considerations, grid patterns)
5. Accessibility requirements (ARIA labels, keyboard navigation, color contrast)
6. Status indicators and state management (badges, progress bars, toggles)

Return a structured JSON with these keys:
- "components": list of {type, description, data_fields}
- "user_actions": list of {action, trigger, expected_outcome}
- "layout": {structure, responsive_notes}
- "accessibility": list of requirements
- "state_indicators": list of {indicator, possible_values}
"""


async def intake_feature(state: AgentState, settings: Settings, llm: LLMProvider) -> dict[str, Any]:
    """Process the initial feature request and determine clarification needs.

    This node:
    1. Analyzes wireframes via vision LLM (if provided)
    2. Parses the feature description into structured requirements
    3. Identifies questions that need user clarification
    4. Sets clarification_complete based on whether questions exist

    Args:
        state: Current graph state.
        settings: Application settings.
        llm: LLM provider instance.

    Returns:
        State updates with extracted requirements and clarification questions.
    """
    logger.info("Starting feature intake for: %s", state.get("feature_name", "Unknown"))

    updates: dict[str, Any] = {
        "current_step": "intake_feature",
    }

    # Step 1: Analyze wireframes if provided
    wireframe_analysis = ""
    wireframe_paths = state.get("wireframe_paths", [])
    wireframe_urls = state.get("wireframe_urls", [])
    all_wireframes = wireframe_paths + wireframe_urls

    if all_wireframes:
        logger.info("Analyzing %d wireframe(s) via vision LLM...", len(all_wireframes))
        try:
            wireframe_analysis = await llm.ainvoke_with_vision(
                prompt=WIREFRAME_ANALYSIS_PROMPT,
                image_urls=all_wireframes,
                system_prompt="You are a UI/UX analyst for enterprise healthcare applications.",
                trace_name="intake_wireframe_analysis",
            )
            logger.info("Wireframe analysis complete (%d chars).", len(wireframe_analysis))
        except Exception:
            logger.exception("Wireframe analysis failed; continuing without it.")

    # Step 2: Parse feature description into requirements
    feature_description = state.get("feature_description", "")
    intake_prompt = f"""Analyze this feature request for an enterprise healthcare platform:

**Feature Name:** {state.get("feature_name", "")}

**Description:**
{feature_description}

{"**Wireframe Analysis:**" + chr(10) + wireframe_analysis if wireframe_analysis else ""}

Parse this into structured requirements following the format specified in your system prompt.
Consider the healthcare enterprise context: HIPAA compliance, audit trails, RBAC, multi-tenancy.
"""

    try:
        response = await llm.ainvoke(
            prompt=intake_prompt,
            system_prompt=INTAKE_SYSTEM_PROMPT,
            node_name="intake_feature",
            state_overrides=state,
            trace_name="intake_requirements_extraction",
            trace_metadata={"feature_name": state.get("feature_name", "")},
        )

        # Parse structured response
        import json
        # Try to extract JSON from the response
        json_start = response.find("{")
        json_end = response.rfind("}") + 1
        if json_start != -1 and json_end > json_start:
            parsed = json.loads(response[json_start:json_end])

            # Populate clarification questions
            questions = parsed.get("clarification_questions", [])
            updates["clarification_questions"] = questions
            if questions:
                updates["clarification_complete"] = False
                logger.info("Identified %d clarification question(s).", len(questions))
            else:
                updates["clarification_complete"] = True
                logger.info("No clarification needed; proceeding to analysis.")

            updates["codebase_analysis"] = {
                "functional_requirements": parsed.get("functional_requirements", []),
                "non_functional_requirements": parsed.get("non_functional_requirements", []),
                "constraints": parsed.get("constraints", []),
                "assumptions": parsed.get("assumptions", []),
                "out_of_scope": parsed.get("out_of_scope", []),
                "integration_points": parsed.get("integration_points", []),
                "compliance_implications": parsed.get("compliance_implications", []),
                "wireframe_analysis": wireframe_analysis,
            }
        else:
            logger.warning("Could not parse structured JSON from intake response.")
            updates["clarification_complete"] = True
            updates["codebase_analysis"] = {"raw_analysis": response}

    except Exception:
        logger.exception("Feature intake analysis failed.")
        updates["errors"] = [{"step": "intake_feature", "message": "Intake analysis failed"}]
        updates["clarification_complete"] = True

    updates["completed_steps"] = ["intake_feature"]
    return updates
