# Author: C A B M
# Date: 2026-09-17

"""Prompt templates package for the HomeCare Agentic Framework."""

from homecare_agent.llm.prompts.analysis_prompts import (
    CODEBASE_ANALYSIS_PROMPT,
    GAP_ANALYSIS_PROMPT,
)
from homecare_agent.llm.prompts.architecture_prompts import (
    ADR_GENERATION_PROMPT,
    STRATEGY_GENERATION_PROMPT,
    TACTICAL_PLAN_PROMPT,
)
from homecare_agent.llm.prompts.code_prompts import (
    CODE_GENERATION_PROMPT,
    WORK_PACKAGE_GENERATION_PROMPT,
)
from homecare_agent.llm.prompts.intake_prompts import (
    CLARIFICATION_GENERATION_PROMPT,
    FEATURE_ANALYSIS_PROMPT,
)
from homecare_agent.llm.prompts.review_prompts import (
    ARCHITECTURE_REVIEW_PROMPT,
    CODE_REVIEW_PROMPT,
)
from homecare_agent.llm.prompts.test_prompts import (
    E2E_TEST_PROMPT,
    LOAD_TEST_PROMPT,
    UNIT_TEST_PROMPT,
)

__all__ = [
    "CLARIFICATION_GENERATION_PROMPT",
    "FEATURE_ANALYSIS_PROMPT",
    "CODEBASE_ANALYSIS_PROMPT",
    "GAP_ANALYSIS_PROMPT",
    "STRATEGY_GENERATION_PROMPT",
    "TACTICAL_PLAN_PROMPT",
    "ADR_GENERATION_PROMPT",
    "ARCHITECTURE_REVIEW_PROMPT",
    "CODE_REVIEW_PROMPT",
    "WORK_PACKAGE_GENERATION_PROMPT",
    "CODE_GENERATION_PROMPT",
    "UNIT_TEST_PROMPT",
    "E2E_TEST_PROMPT",
    "LOAD_TEST_PROMPT",
]
