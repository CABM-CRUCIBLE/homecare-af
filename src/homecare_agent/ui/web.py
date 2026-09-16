# Author: C A B M
# Date: 2026-09-17

"""Gradio Web UI for the HomeCare Agentic Framework.

Provides a browser-based chat interface for feature requests,
clarification Q&A, and workflow monitoring.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

logger = logging.getLogger(__name__)


def launch_web_ui(settings: Any) -> None:
    """Launch the Gradio web interface.

    Args:
        settings: Application settings.
    """
    try:
        import gradio as gr
    except ImportError:
        logger.error("Gradio is not installed. Install with: uv add gradio")
        return

    with gr.Blocks(
        title="HomeCare Agentic Framework",
        theme=gr.themes.Soft(
            primary_hue="teal",
            secondary_hue="cyan",
        ),
    ) as demo:
        gr.Markdown(
            "# 🏥 HomeCare Agentic Code Generation Framework\n"
            "Automated SDLC from feature request to PR — powered by LangGraph"
        )

        with gr.Tabs():
            # Tab 1: Feature Request
            with gr.Tab("📋 Feature Request"):
                with gr.Row():
                    with gr.Column(scale=2):
                        feature_name = gr.Textbox(
                            label="Feature Name",
                            placeholder="e.g., Order Service Request Fulfillment Workflow",
                        )
                        feature_desc = gr.Textbox(
                            label="Feature Description",
                            placeholder="Describe the feature in detail...",
                            lines=10,
                        )
                        with gr.Accordion("⚙️ Multi-Tier Model Configuration", open=False):
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
                            )
                            model_code = gr.Dropdown(
                                label="Code Generation Model (Medium/Low Cost)",
                                choices=[
                                    "deepseek/deepseek-coder",
                                    "meta-llama/llama-3.3-70b-instruct",
                                    "anthropic/claude-3.5-haiku",
                                    "openai/gpt-4o-mini",
                                    "anthropic/claude-sonnet-4",
                                ],
                                value=getattr(settings, "model_code", "") or "deepseek/deepseek-coder",
                                allow_custom_value=True,
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
                            )
                            with gr.Accordion("💻 Local LLM for Code Generation (Ollama / vLLM / LM Studio)", open=False):
                                local_llm_toggle = gr.Checkbox(
                                    label="Route Code Generation to Local LLM (Zero Token Cost)",
                                    value=getattr(settings, "local_llm_enabled", False),
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
                        wireframe_files = gr.File(
                            label="Wireframes / Screenshots",
                            file_count="multiple",
                            file_types=["image"],
                        )
                        wireframe_urls = gr.Textbox(
                            label="Wireframe URLs (one per line)",
                            lines=3,
                        )
                        submit_btn = gr.Button("🚀 Start Pipeline", variant="primary")

                    with gr.Column(scale=1):
                        status_output = gr.Markdown("### Status\nReady to start.")

            # Tab 2: Clarification Q&A
            with gr.Tab("❓ Clarification"):
                chatbot = gr.Chatbot(
                    label="Clarification Questions",
                    height=500,
                )
                answer_input = gr.Textbox(
                    label="Your Answer",
                    placeholder="Type your answer...",
                )
                answer_btn = gr.Button("Submit Answer")

            # Tab 3: Architecture Documents
            with gr.Tab("📐 Architecture"):
                with gr.Tabs():
                    with gr.Tab("Strategy"):
                        strategy_output = gr.Markdown("_Strategy document will appear here_")
                    with gr.Tab("Tactical Plan"):
                        tactical_output = gr.Markdown("_Tactical plan will appear here_")
                    with gr.Tab("ADRs"):
                        adr_output = gr.Markdown("_ADRs will appear here_")
                    with gr.Tab("Architecture Review"):
                        review_output = gr.Markdown("_Architecture review will appear here_")

            # Tab 4: Execution Log
            with gr.Tab("⚡ Execution"):
                execution_log = gr.Markdown("### Execution Log\n_Pipeline not started_")
                progress_bar = gr.Slider(
                    label="Progress",
                    minimum=0,
                    maximum=100,
                    value=0,
                    interactive=False,
                )

            # Tab 5: Code Review
            with gr.Tab("🔍 Code Review"):
                code_review_output = gr.Markdown("_Code review will appear here_")

            # Tab 6: Resume Pipeline
            with gr.Tab("🔄 Resume Pipeline"):
                gr.Markdown(
                    "### 🔄 Resume an Interrupted or Failed Pipeline Run\n"
                    "Select a previous run from disk checkpoints and choose which step to resume from without starting over."
                )
                from homecare_agent.graph.checkpoint import (
                    CheckpointManager,
                    ORDERED_STEPS,
                    get_step_number,
                    resolve_next_step,
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
                            help="Choose the step to start from. Prior completed steps will NOT be re-executed.",
                        )
                        with gr.Row():
                            refresh_cps_btn = gr.Button("🔄 Refresh List")
                            resume_run_btn = gr.Button("▶ Resume Execution", variant="primary")

                    with gr.Column(scale=1):
                        resume_status_output = gr.Markdown("### Resume Status\nReady to resume from selected checkpoint.")

        # Event handlers
        async def start_pipeline(
            name: str,
            desc: str,
            files: list[Any] | None,
            urls: str,
            use_local: bool,
            local_url: str,
            local_model_name: str,
        ) -> str:
            """Start the agentic pipeline."""
            if not name or not desc:
                return "### ⚠️ Error\nPlease provide both a feature name and description."
            import uuid
            trace_id = uuid.uuid4().hex
            trace_link = ""
            if settings.langfuse_enabled:
                project_id = getattr(settings, "langfuse_init_project_id", "homecare")
                trace_url = f"{settings.langfuse_host.rstrip('/')}/project/{project_id}/traces/{trace_id}"
                trace_link = f"\n\n🔗 **Langfuse Trace:** [{trace_id}]({trace_url})"

            code_engine = f"Local LLM (`{local_model_name}` at `{local_url}`)" if use_local else f"OpenRouter (`{getattr(settings, 'model_code', '') or 'deepseek/deepseek-coder'}`)"
            return (
                f"### ⏳ Pipeline Initialized\n"
                f"**Feature:** {name}\n"
                f"**Code Engine:** {code_engine}\n"
                f"**Trace ID:** `{trace_id}`{trace_link}\n\n"
                f"> **Note:** To run full automated execution with real-time terminal streaming and interactive approvals, run `homecare-agent run` via CLI."
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
            return gr.update(choices=choices, value=new_val)

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

    port = settings.web_ui_port if hasattr(settings, "web_ui_port") else 7860
    auth = None
    if getattr(settings, "gradio_auth_user", "") and getattr(settings, "gradio_auth_password", ""):
        auth = (settings.gradio_auth_user, settings.gradio_auth_password)
        logger.info("Gradio Web UI basic authentication enabled for user '%s'", settings.gradio_auth_user)

    logger.info("Launching Gradio Web UI on 127.0.0.1:%d...", port)
    demo.launch(server_name="127.0.0.1", server_port=port, share=False, auth=auth)
