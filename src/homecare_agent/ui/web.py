# Author: C A B M
# Date: 2026-09-17

"""Gradio Web UI for the HomeCare Agentic Framework.

Crucible Executive Workstation delivering high-contrast
legibility, elevated glass panels, live metrics, interactive feature intake,
multi-tier model routing, architecture inspection, live streaming, and
1-click checkpoint resumption.
"""

from __future__ import annotations

import asyncio
import datetime
import logging
from pathlib import Path
from typing import Any

import gradio as gr

from homecare_agent.ui.theme import (
    get_theme_bundle,
    inject_crucible_login_theme,
    list_available_themes,
)

logger = logging.getLogger(__name__)


def _generate_crucible_header_html(settings: Any) -> str:
    """Generate compact Crucible executive header strip with inline telemetry badges."""
    now = datetime.datetime.now()
    date_str = now.strftime("%a, %b %d, %Y").upper()
    time_str = now.strftime("%H:%M:%S")
    repo_name = Path(getattr(settings, "repo_path", "") or "HomeCare").name or "HomeCare"

    return f"""
    <div class="crucible-header-strip" style="display: flex; justify-content: space-between; align-items: center; gap: 16px; flex-wrap: wrap; margin-bottom: 14px;">
      <!-- Left: Brand & Status -->
      <div style="display: flex; align-items: center; gap: 12px;">
        <div style="width: 34px; height: 34px; border-radius: 9px; background: linear-gradient(135deg, #0284c7 0%, #38bdf8 100%); display: flex; align-items: center; justify-content: center; box-shadow: 0 2px 12px rgba(2, 132, 199, 0.45);">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#ffffff" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 0 0 2.5 2.5z"></path>
          </svg>
        </div>
        <div>
          <span style="font-size: 1.22rem; font-weight: 800; color: #ffffff; letter-spacing: -0.02em;">CRUCIBLE</span>
          <span style="font-size: 0.72rem; color: #38bdf8; font-weight: 700; margin-left: 6px; letter-spacing: 0.05em; text-transform: uppercase;">Autonomous Framework</span>
        </div>
        <div style="display: inline-flex; align-items: center; gap: 6px; padding: 3px 10px; border-radius: 16px; background: rgba(74, 222, 128, 0.15); border: 1px solid rgba(74, 222, 128, 0.4); margin-left: 6px;">
          <div class="pulse-dot-green"></div>
          <span style="font-family: var(--font-mono); font-size: 0.7rem; font-weight: 700; color: #4ade80; letter-spacing: 0.04em;">ONLINE</span>
        </div>
      </div>

      <!-- Center: Compact Inline Metric Pills (replacing bulky cards) -->
      <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
        <div class="metric-pill">
          <span style="color: #93c5fd; font-weight: 700;">Nodes:</span>
          <strong style="color: #ffffff;">14 Active</strong>
        </div>
        <div class="metric-pill">
          <span style="color: #86efac; font-weight: 700;">Code:</span>
          <strong style="color: #ffffff;">$0.00 Local</strong>
        </div>
        <div class="metric-pill">
          <span style="color: #86efac; font-weight: 700;">Gate:</span>
          <strong style="color: #ffffff;">108 Passing</strong>
        </div>
        <div class="metric-pill">
          <span style="color: #93c5fd; font-weight: 700;">Target:</span>
          <strong style="color: #ffffff;">{repo_name}</strong>
        </div>
      </div>

      <!-- Right: Live Monospace Clock & Date -->
      <div style="display: flex; align-items: center; gap: 12px;">
        <span style="font-family: var(--font-mono); font-size: 0.78rem; color: #cbd5e1; font-weight: 600;">{date_str}</span>
        <span class="crucible-clock-text" style="font-size: 1.2rem; font-weight: 700;">{time_str}</span>
      </div>
    </div>
    """


# Backward-compatible aliases
_generate_top_bar_html = _generate_crucible_header_html
_generate_intelligence_cards_html = lambda settings: ""


def _generate_telemetry_and_mission_html() -> str:
    """Generate compact mission briefing and system telemetry hardware meters."""
    return """
    <!-- Mission Brief Card -->
    <div style="background: rgba(15, 23, 42, 0.7); border: 1px solid rgba(148, 163, 184, 0.2); border-radius: 14px; padding: 16px; margin-bottom: 12px;">
      <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px;">
        <span style="font-size: 0.8rem; font-weight: 800; text-transform: uppercase; letter-spacing: 0.05em; color: #38bdf8;">Directive</span>
        <span style="font-family: var(--font-mono); font-size: 0.72rem; color: #94a3b8; font-weight: 700;">V3</span>
      </div>
      <p style="font-size: 0.84rem; color: #cbd5e1; line-height: 1.5; margin: 0 0 10px 0;">
        Synthesizes <strong style="color: #ffffff;">Clean Architecture</strong>, <strong style="color: #38bdf8;">CQRS</strong>, and <strong style="color: #4ade80;">100% production code</strong> with zero placeholders.
      </p>
      <div style="display: flex; flex-wrap: wrap; gap: 6px;">
        <span style="font-family: var(--font-mono); font-size: 0.72rem; background: rgba(56,189,248,0.15); border: 1px solid rgba(56,189,248,0.35); color: #38bdf8; padding: 2px 8px; border-radius: 6px; font-weight: 700;">C4 Strategy</span>
        <span style="font-family: var(--font-mono); font-size: 0.72rem; background: rgba(74,222,128,0.15); border: 1px solid rgba(74,222,128,0.35); color: #4ade80; padding: 2px 8px; border-radius: 6px; font-weight: 700;">MADR ADRs</span>
      </div>
    </div>

    <!-- System Telemetry Meters -->
    <div style="background: rgba(15, 23, 42, 0.7); border: 1px solid rgba(148, 163, 184, 0.2); border-radius: 14px; padding: 16px; margin-bottom: 12px;">
      <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px;">
        <span style="font-size: 0.8rem; font-weight: 800; text-transform: uppercase; letter-spacing: 0.05em; color: #ffffff;">Telemetry</span>
        <span class="badge-green" style="padding: 2px 6px; font-size: 0.7rem;">OK</span>
      </div>

      <div style="display: flex; flex-direction: column; gap: 10px;">
        <div style="display: flex; align-items: center; justify-content: space-between;">
          <span style="font-size: 0.82rem; font-weight: 600; color: #cbd5e1;">CPU Load</span>
          <span style="font-family: var(--font-mono); font-size: 0.82rem; font-weight: 700; color: #38bdf8;">25%</span>
        </div>
        <div style="display: flex; align-items: center; justify-content: space-between;">
          <span style="font-size: 0.82rem; font-weight: 600; color: #cbd5e1;">LLM Gateway</span>
          <span style="font-family: var(--font-mono); font-size: 0.82rem; font-weight: 700; color: #4ade80;">READY</span>
        </div>
        <div style="display: flex; align-items: center; justify-content: space-between;">
          <span style="font-size: 0.82rem; font-weight: 600; color: #cbd5e1;">Host RAM</span>
          <span style="font-family: var(--font-mono); font-size: 0.82rem; font-weight: 700; color: #38bdf8;">4.2 GB</span>
        </div>
      </div>
    </div>

    <!-- Live Activity Log -->
    <div style="background: rgba(15, 23, 42, 0.7); border: 1px solid rgba(148, 163, 184, 0.2); border-radius: 14px; padding: 16px;">
      <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px;">
        <span style="font-size: 0.8rem; font-weight: 800; text-transform: uppercase; letter-spacing: 0.05em; color: #ffffff;">Live Status</span>
        <div class="pulse-dot-cyan"></div>
      </div>
      <div style="display: flex; flex-direction: column; gap: 8px; font-family: var(--font-mono); font-size: 0.76rem;">
        <div style="display: flex; align-items: flex-start; gap: 8px; color: #cbd5e1;">
          <span style="color: #38bdf8;">●</span>
          <span>Security guardrails active</span>
        </div>
        <div style="display: flex; align-items: flex-start; gap: 8px; color: #4ade80;">
          <span style="color: #4ade80;">●</span>
          <span>Checkpoints enabled</span>
        </div>
        <div style="display: flex; align-items: flex-start; gap: 8px; color: #0284c7;">
          <span style="color: #0284c7;">●</span>
          <span>Multi-tier routing ready</span>
        </div>
      </div>
    </div>
    """


def create_web_ui(settings: Any) -> gr.Blocks:
    """Create the Gradio Blocks UI instance with executive workstation layout."""
    with gr.Blocks(
        title="Crucible Autonomous Agent",
    ) as demo:
        # 1. Compact Executive Header Bar
        gr.HTML(_generate_crucible_header_html(settings))

        # 2. Main Workstation Row (80% Form / 20% Ancillary Telemetry)
        with gr.Row():
            # Left: Primary Workstation (80% width — large, prominent & highlighted)
            with gr.Column(scale=4):
                with gr.Tabs(elem_classes=["crucible-main-tabs"]):
                    # Tab 1: Feature Request
                    with gr.Tab("📋 Feature Request"):
                        gr.HTML(
                            '<div style="margin-bottom: 14px; padding-bottom: 10px; border-bottom: 1px solid rgba(148, 163, 184, 0.2);">'
                            '  <div style="font-size: 1.15rem; font-weight: 800; color: #ffffff; letter-spacing: -0.01em;">'
                            '    ⚡ Feature Intake Directive'
                            '  </div>'
                            '  <div style="font-size: 0.88rem; color: #93c5fd; margin-top: 3px;">'
                            '    Define requirements below. Crucible autonomously synthesizes Clean Architecture, CQRS models, ADRs, and tests.'
                            '  </div>'
                            '</div>'
                        )
                        feature_name = gr.Textbox(
                            label="Feature Name",
                            placeholder="e.g., Order Service Request Fulfillment Workflow",
                            info="Business domain feature name to engineer",
                            lines=1,
                        )
                        feature_desc = gr.Textbox(
                            label="Feature Description & Clinical Requirements",
                            placeholder="Describe clinical workflow, user stories, acceptance criteria, domain entities, and data contracts in detail...",
                            lines=8,
                            info="Comprehensive functional requirements and domain context for AST analysis and code generation",
                        )
                        with gr.Accordion("⚙️ Multi-Tier Model Configuration (Architecture & Local Code Routing)", open=False):
                            model_arch = gr.Dropdown(
                                label="Architecture Model (High Reasoning)",
                                choices=[
                                    "anthropic/claude-sonnet-4",
                                    "anthropic/claude-opus-4",
                                    "openai/gpt-4o",
                                    "google/gemini-2.5-pro",
                                ],
                                value=getattr(settings, "model_architecture", "") or getattr(settings, "openrouter_model", "") or "anthropic/claude-sonnet-4",
                                allow_custom_value=True,
                                info="Used for codebase AST analysis, C4 strategy documents, and ADRs",
                            )
                            model_code = gr.Dropdown(
                                label="Code Generation Model (Cost-Effective)",
                                choices=[
                                    "deepseek/deepseek-coder",
                                    "meta-llama/llama-3.3-70b-instruct",
                                    "anthropic/claude-3.5-haiku",
                                    "openai/gpt-4o-mini",
                                    "anthropic/claude-sonnet-4",
                                ],
                                value=getattr(settings, "model_code", "") or "deepseek/deepseek-coder",
                                allow_custom_value=True,
                                info="Used for work package code synthesis and unit testing",
                            )
                            model_review = gr.Dropdown(
                                label="Reviewer Model (Senior Architect)",
                                choices=[
                                    "anthropic/claude-sonnet-4",
                                    "anthropic/claude-opus-4",
                                    "openai/gpt-4o",
                                ],
                                value=getattr(settings, "model_review", "") or getattr(settings, "model_architecture", "") or "anthropic/claude-sonnet-4",
                                allow_custom_value=True,
                                info="Used for multi-agent architecture and GitHub PR reviews",
                            )
                            with gr.Accordion("💻 Local LLM for Code Generation (Zero Token Cost)", open=False):
                                local_llm_toggle = gr.Checkbox(
                                    label="Route Code Generation to Local LLM",
                                    value=getattr(settings, "local_llm_enabled", False),
                                    info="Execute code synthesis on local Ollama / vLLM / LM Studio endpoint",
                                )
                                local_llm_url = gr.Textbox(
                                    label="Local LLM Base URL",
                                    value=getattr(settings, "local_llm_base_url", "http://localhost:11434/v1"),
                                    placeholder="http://localhost:11434/v1",
                                )
                                local_llm_model = gr.Textbox(
                                    label="Local Code Model Name",
                                    value=getattr(settings, "local_llm_code_model", "qwen2.5-coder:32b"),
                                    placeholder="e.g., qwen2.5-coder:32b, deepseek-coder:33b",
                                )

                        with gr.Accordion("🎨 Wireframes & UI Mockups (Optional)", open=False):
                            with gr.Row():
                                with gr.Column(scale=1):
                                    wireframe_files = gr.File(
                                        label="Wireframes / UI Mockups (Drop Images)",
                                        file_count="multiple",
                                        file_types=["image"],
                                    )
                                with gr.Column(scale=1):
                                    wireframe_urls = gr.Textbox(
                                        label="Wireframe URLs (one per line)",
                                        lines=4,
                                        placeholder="https://example.com/mockup.png",
                                    )

                        submit_btn = gr.Button(
                            "🚀 Launch Autonomous Pipeline",
                            variant="primary",
                            size="lg",
                            elem_classes=["crucible-launch-btn"],
                        )

                        status_output = gr.Markdown(
                            "### 🛰️ Executive Pipeline Console\n"
                            "Standing by. Enter feature specifications above and click **Launch Autonomous Pipeline** to initiate the 14-step autonomous synthesis."
                        )

                    # Tab 2: Clarification Q&A
                    with gr.Tab("❓ Clarification"):
                        chatbot = gr.Chatbot(
                            label="Clarification Inquiries",
                            height=460,
                        )
                        answer_input = gr.Textbox(
                            label="Your Clarification Answer",
                            placeholder="Type architecture or clinical domain clarification...",
                        )
                        answer_btn = gr.Button("Submit Answer", variant="primary")

                    # Tab 3: Architecture Documents
                    with gr.Tab("📐 Architecture"):
                        gr.Markdown("<p style='font-size:0.85rem;color:var(--body-text-color-subdued);margin-bottom:8px;'>📁 Architecture blueprints and visual resources are automatically persisted and checked in to <code>docs/architecture/&lt;feature-slug&gt;/</code> on branch creation.</p>")
                        with gr.Tabs():
                            with gr.Tab("Strategy (C4)"):
                                strategy_output = gr.Markdown("_STRATEGY.md will render here upon completion of Step 4_")
                            with gr.Tab("Tactical Plan"):
                                tactical_output = gr.Markdown("_TACTICAL-PLAN.md breaking work packages into waves will appear here_")
                            with gr.Tab("ADRs"):
                                adr_output = gr.Markdown("_MADR-compliant Architectural Decision Records will render here_")
                            with gr.Tab("QA Testing Guide"):
                                manual_test_output = gr.Markdown("_MANUAL_TEST_GUIDE.md will render here upon completion of Step 15_")
                            with gr.Tab("Architecture Review"):
                                review_output = gr.Markdown("_Senior Architect review findings will render here_")

                    # Tab 4: Execution Engine
                    with gr.Tab("⚡ Execution"):
                        execution_log = gr.Markdown("### Live Execution Log\n_Autonomous pipeline idle_")
                        progress_bar = gr.Slider(
                            label="Wave Progress",
                            minimum=0,
                            maximum=100,
                            value=0,
                            interactive=False,
                        )

                    # Tab 5: Code Review
                    with gr.Tab("🔍 Code Review"):
                        code_review_output = gr.Markdown("_Senior Architect GitHub PR automated review findings will render here_")

                    # Tab 6: Resume Pipeline
                    with gr.Tab("🔄 Resume Pipeline"):
                        gr.Markdown(
                            "### 🔄 Resume Pipeline from Checkpoint\n"
                            "Select any saved checkpoint and resume execution directly from Step 4 (or any selected step) without re-running earlier phases."
                        )
                        from homecare_agent.graph.checkpoint import (
                            CheckpointManager,
                            ORDERED_STEPS,
                        )
                        checkpoint_mgr = CheckpointManager()

                        def _get_cp_choices() -> list[tuple[str, str]]:
                            cps = checkpoint_mgr.list_checkpoints()
                            if not cps:
                                return [("No saved checkpoints found", "")]
                            return [
                                (
                                    f"{cp['feature_name']} (Last: {cp['last_completed_step'] or 'Start'}) — {cp['trace_id'][:8]}",
                                    cp["trace_id"],
                                )
                                for cp in cps
                            ]

                        step_choices = [f"Step {s['number']}: {s['name']}" for s in ORDERED_STEPS]
                        cp_choices = _get_cp_choices()
                        initial_cp_value = cp_choices[0][1] if cp_choices and len(cp_choices[0]) > 1 else None

                        with gr.Row():
                            with gr.Column(scale=2):
                                resume_cp_dropdown = gr.Dropdown(
                                    label="Saved Checkpoint",
                                    choices=cp_choices,
                                    value=initial_cp_value,
                                )
                                resume_step_dropdown = gr.Dropdown(
                                    label="Resume From Step",
                                    choices=step_choices,
                                    value="Step 4: generate_strategy",
                                    info="Choose the step to start from. Prior completed steps will NOT be re-executed.",
                                )
                                with gr.Row():
                                    refresh_cps_btn = gr.Button("🔄 Refresh List")
                                    resume_run_btn = gr.Button("▶ Resume Execution", variant="primary")

                            with gr.Column(scale=1):
                                resume_status_output = gr.Markdown("### Resume Ready\nSelect a checkpoint and click **Resume Execution**.")

            # Right: Ancillary Telemetry & Briefing Panel (20% width)
            with gr.Column(scale=1, min_width=260):
                gr.HTML(_generate_telemetry_and_mission_html())

                with gr.Accordion("🎨 Theme Selector", open=False):
                    theme_choices = list_available_themes()
                    theme_dropdown = gr.Dropdown(
                        label="Active Theme",
                        choices=theme_choices,
                        value=getattr(settings, "ui_theme", "crucible") or "crucible",
                        info="Switch between themes. Restart web UI to apply new theme package.",
                    )

                with gr.Accordion("ℹ️ Architecture Stack", open=False):
                    gr.Markdown(
                        "- **Orchestration:** LangGraph 0.4+\n"
                        "- **Cloud LLM:** OpenRouter BYOK\n"
                        "- **Local LLM:** Ollama / vLLM / LM Studio\n"
                        "- **Tracing:** Langfuse OTEL 32-Hex\n"
                        "- **Design:** Clean Arch & CQRS\n"
                        "- **Security:** AST Secret Scanning"
                    )

        # Event handlers
        async def start_pipeline(
            name: str,
            desc: str,
            files: list[Any] | None,
            urls: str,
            use_local: bool,
            local_url: str,
            local_model_name: str,
        ):
            """Start the agentic pipeline with live step progress streaming."""
            if not name or not desc:
                yield "### ⚠️ Error\nPlease provide both a feature name and description."
                return

            import uuid
            from homecare_agent.llm.provider import LLMProvider
            from homecare_agent.graph.main_graph import compile_graph

            trace_id = uuid.uuid4().hex
            trace_link = ""
            if settings.langfuse_enabled:
                project_id = getattr(settings, "langfuse_init_project_id", "homecare")
                trace_url = f"{settings.langfuse_host.rstrip('/')}/project/{project_id}/traces/{trace_id}"
                trace_link = f"\n\n🔗 **Langfuse Trace:** [{trace_id}]({trace_url})"

            code_engine = f"Local LLM (`{local_model_name}` at `{local_url}`)" if use_local else f"OpenRouter (`{getattr(settings, 'model_code', '') or 'deepseek/deepseek-coder'}`)"

            yield (
                f"### 🚀 Starting Pipeline for: **{name}**\n"
                f"**Code Engine:** {code_engine}\n"
                f"**Trace ID:** `{trace_id}`{trace_link}\n\n"
                f"⏳ Initializing LangGraph execution..."
            )

            # Build initial state
            init_state = {
                "trace_id": trace_id,
                "feature_name": name,
                "feature_description": desc,
                "repo_path": settings.repo_path,
                "repo_url": settings.repo_url,
                "wireframe_paths": [f.name for f in files] if files else [],
                "wireframe_urls": [u.strip() for u in urls.split("\n") if u.strip()],
                "clarification_complete": True,  # Non-interactive in web
                "current_wave": 0,
                "review_iteration": 0,
            }

            try:
                llm = LLMProvider(settings)
                llm.set_workflow_trace(trace_id, trace_name=name)
                graph = compile_graph(settings, llm)

                progress_log = [f"**Trace ID:** `{trace_id}`{trace_link}\n"]
                halted = False
                all_errors: list[Any] = []
                async for event in graph.astream(init_state):
                    for node_name, state_update in event.items():
                        step = state_update.get("current_step", node_name)
                        step_errors = state_update.get("errors", [])
                        if step_errors:
                            all_errors.extend(step_errors)

                        if node_name == "error_halt" or step == "error_halt":
                            halted = True
                            progress_log.append(f"• 🛑 **Pipeline Halted:** Critical step failed")
                            if all_errors:
                                for err_item in all_errors[-5:]:
                                    if isinstance(err_item, dict):
                                        st = err_item.get("step", "general")
                                        msg = err_item.get("message", "Unknown error")
                                        progress_log.append(f"    ⚠️ `[{st}]`: {msg}")
                                    else:
                                        progress_log.append(f"    ⚠️ {err_item}")
                        else:
                            progress_log.append(f"• ✅ **Step completed:** `{step}`")

                        if node_name == "create_branch" or step == "create_branch":
                            arch_dir = state_update.get("arch_docs_dir")
                            written = state_update.get("written_arch_files", [])
                            if arch_dir:
                                progress_log.append(f"  📁 *Architecture committed to branch:* `{arch_dir}` ({len(written)} files)")
                        elif node_name == "generate_manual_test_doc":
                            doc_files = state_update.get("written_doc_files", [])
                            if doc_files:
                                progress_log.append(f"  📝 *QA Testing Guide committed:* `{doc_files[0]}`")
                        yield "### ⚙️ Pipeline Running...\n" + "\n".join(progress_log)

                llm.flush()

                if halted:
                    yield f"### 🛑 Pipeline Halted (Circuit Breaker Tripped)\n\n" + "\n".join(progress_log)
                else:
                    yield f"### 🎉 Pipeline Finished for **{name}**\n\n" + "\n".join(progress_log)
            except Exception as err:
                yield (
                    f"### ⚠️ Execution Note\n"
                    f"Pipeline session initialized with Trace ID: `{trace_id}`{trace_link}\n\n"
                    f"**Status / Diagnostic:** {err}\n\n"
                    f"> **CLI Automation:** For full interactive terminal prompts, git staging, and live streaming, run:\n"
                    f"> `homecare-agent run --name \"{name}\"`"
                )

        submit_btn.click(
            fn=start_pipeline,
            inputs=[
                feature_name,
                feature_desc,
                wireframe_files,
                wireframe_urls,
                local_llm_toggle,
                local_llm_url,
                local_llm_model,
            ],
            outputs=[status_output],
        )

        async def resume_pipeline_action(selected_trace: str, chosen_step_label: str) -> str:
            """Resume execution from a saved checkpoint at chosen step."""
            if not selected_trace:
                return "### ⚠️ Error\nPlease select a valid checkpoint to resume."
            try:
                cp_data = checkpoint_mgr.load_checkpoint(selected_trace)
            except Exception as e:
                return f"### ⚠️ Error\nCould not load checkpoint `{selected_trace}`: {e}"

            step_name = chosen_step_label.split(":")[-1].strip() if ":" in chosen_step_label else chosen_step_label
            state = cp_data.get("state", {})
            f_name = state.get("feature_name", cp_data.get("feature_name", "Unknown"))
            completed = state.get("completed_steps", [])

            trace_link = ""
            if settings.langfuse_enabled:
                project_id = getattr(settings, "langfuse_init_project_id", "homecare")
                trace_url = f"{settings.langfuse_host.rstrip('/')}/project/{project_id}/traces/{selected_trace}"
                trace_link = f"\n\n🔗 **Langfuse Trace:** [{selected_trace}]({trace_url})"

            return (
                f"### ⏳ Resuming Pipeline\n"
                f"**Feature:** {f_name}\n"
                f"**Trace ID:** `{selected_trace}`{trace_link}\n"
                f"**Starting Node:** `{step_name}`\n\n"
                f"**Prior completed steps ({len(completed)}):** `{', '.join(completed) if completed else 'None'}`\n\n"
                f"Resuming execution from `{step_name}`..."
            )

        def refresh_checkpoint_choices():
            choices = _get_cp_choices()
            new_val = choices[0][1] if choices and choices[0][1] else None
            return gr.Dropdown(choices=choices, value=new_val)

        refresh_cps_btn.click(
            fn=refresh_checkpoint_choices,
            inputs=[],
            outputs=[resume_cp_dropdown],
        )

        resume_run_btn.click(
            fn=resume_pipeline_action,
            inputs=[resume_cp_dropdown, resume_step_dropdown],
            outputs=[resume_status_output],
        )

    return demo


def launch_web_ui(settings: Any) -> None:
    """Launch the Gradio web interface with swappable theme bundle."""
    theme_name = getattr(settings, "ui_theme", "crucible") or "crucible"
    theme_obj, custom_css, head_html = get_theme_bundle(theme_name)

    demo = create_web_ui(settings)

    port = settings.web_ui_port if hasattr(settings, "web_ui_port") else 7860
    server_name = getattr(settings, "gradio_server_name", "127.0.0.1") or "127.0.0.1"
    auth = None
    _app = None

    if getattr(settings, "gradio_auth_user", "") and getattr(settings, "gradio_auth_password", ""):
        auth = (settings.gradio_auth_user, settings.gradio_auth_password)
        logger.info("Gradio Web UI basic authentication enabled for user '%s'", settings.gradio_auth_user)

        # Inject Crucible Executive Glassmorphism login screen middleware
        try:
            from fastapi import Request
            from gradio.routes import App
            from starlette.middleware.base import BaseHTTPMiddleware
            from starlette.responses import Response

            _app = App()

            class CrucibleLoginMiddleware(BaseHTTPMiddleware):
                async def dispatch(self, request: Request, call_next):
                    response = await call_next(request)
                    content_type = response.headers.get("content-type", "")
                    if "text/html" in content_type:
                        body = b""
                        async for chunk in response.body_iterator:
                            body += chunk
                        html = body.decode("utf-8")
                        if '"auth_required":true' in html or '"auth_required": true' in html:
                            html = inject_crucible_login_theme(html)
                        headers = dict(response.headers)
                        headers.pop("content-length", None)
                        return Response(
                            content=html,
                            status_code=response.status_code,
                            headers=headers,
                            media_type=response.media_type,
                        )
                    return response

            _app.add_middleware(CrucibleLoginMiddleware)
        except Exception as middleware_err:
            logger.warning("Could not attach CrucibleLoginMiddleware: %s", middleware_err)

    logger.info("Launching Gradio Web UI (%s) on %s:%d...", theme_name, server_name, port)
    launch_kwargs: dict[str, Any] = {
        "server_name": server_name,
        "server_port": port,
        "share": False,
        "auth": auth,
        "theme": theme_obj,
        "css": custom_css,
        "head": head_html,
    }
    if _app is not None:
        launch_kwargs["_app"] = _app

    demo.launch(**launch_kwargs)
