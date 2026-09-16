"""Unit tests for LLM prompt templates."""

from homecare_agent.llm.prompts import (
    ADR_GENERATION_PROMPT,
    ARCHITECTURE_REVIEW_PROMPT,
    CLARIFICATION_GENERATION_PROMPT,
    CODE_GENERATION_PROMPT,
    CODE_REVIEW_PROMPT,
    CODEBASE_ANALYSIS_PROMPT,
    E2E_TEST_PROMPT,
    FEATURE_ANALYSIS_PROMPT,
    GAP_ANALYSIS_PROMPT,
    LOAD_TEST_PROMPT,
    STRATEGY_GENERATION_PROMPT,
    TACTICAL_PLAN_PROMPT,
    UNIT_TEST_PROMPT,
    WORK_PACKAGE_GENERATION_PROMPT,
)


def test_intake_prompts_format():
    formatted = FEATURE_ANALYSIS_PROMPT.format(
        feature_name="Vendor Payouts",
        feature_description="Automated reconciliation of invoices",
    )
    assert "Vendor Payouts" in formatted
    assert "Automated reconciliation" in formatted


def test_clarification_prompt_format():
    formatted = CLARIFICATION_GENERATION_PROMPT.format(
        feature_name="Vendor Payouts",
        feature_description="Automated reconciliation",
        known_requirements="Tenant isolated",
    )
    assert "Vendor Payouts" in formatted
    assert "Tenant isolated" in formatted


def test_architecture_prompts_format():
    strat = STRATEGY_GENERATION_PROMPT.format(
        feature_name="Vendor Payouts",
        feature_description="Payout system",
        clarification_context="Bi-weekly schedule",
        gap_analysis="Missing tables",
    )
    assert "Vendor Payouts" in strat

    tact = TACTICAL_PLAN_PROMPT.format(
        feature_name="Vendor Payouts",
        strategy_summary="Strategy summary",
        gap_analysis="Missing tables",
    )
    assert "Vendor Payouts" in tact

    adr = ADR_GENERATION_PROMPT.format(
        feature_name="Vendor Payouts",
        decision_topic="Payout Gateway",
        decision_context="Stripe Connect vs Direct ACH",
        options_considered="Stripe, ACH",
        adr_number="005",
        title="Stripe Connect Integration",
        status="Accepted",
    )
    assert "ADR-005" in adr


def test_review_prompts_format():
    arch_rev = ARCHITECTURE_REVIEW_PROMPT.format(
        feature_name="Vendor Payouts",
        strategy_document="# Strategy",
        tactical_plan="# Tactical Plan",
        adr_summaries="ADR-005",
    )
    assert "Staff Software Architect" in arch_rev

    code_rev = CODE_REVIEW_PROMPT.format(
        pr_number=42,
        pr_title="Vendor Payout Implementation",
        files_changed="PaymentService.cs",
        diff_content="+ line added",
        standing_instructions="No truncation",
    )
    assert "Pull Request: #42" in code_rev


def test_code_and_test_prompts_format():
    wp_gen = WORK_PACKAGE_GENERATION_PROMPT.format(
        feature_name="Vendor Payouts",
        tactical_plan="# Tactical Plan",
    )
    assert "WP-01" in wp_gen

    code_gen = CODE_GENERATION_PROMPT.format(
        standing_instructions="Strict Clean Architecture",
        wp_id="WP-01",
        wp_title="Domain Entities",
        layer="Domain",
        target_files="Payout.cs",
        wp_prompt="Create Payout entity",
    )
    assert "WP-01" in code_gen
    assert "Payout.cs" in code_gen
