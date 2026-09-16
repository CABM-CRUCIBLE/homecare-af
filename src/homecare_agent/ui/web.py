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

        # Event handlers
        async def start_pipeline(name: str, desc: str, files: list[Any] | None, urls: str) -> str:
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
            return f"### ⏳ Pipeline Started\n**Feature:** {name}\n**Trace ID:** `{trace_id}`{trace_link}\n\nProcessing..."

        submit_btn.click(
            fn=start_pipeline,
            inputs=[feature_name, feature_desc, wireframe_files, wireframe_urls],
            outputs=[status_output],
        )

    port = settings.web_ui_port if hasattr(settings, "web_ui_port") else 7860
    auth = None
    if getattr(settings, "gradio_auth_user", "") and getattr(settings, "gradio_auth_password", ""):
        auth = (settings.gradio_auth_user, settings.gradio_auth_password)
        logger.info("Gradio Web UI basic authentication enabled for user '%s'", settings.gradio_auth_user)

    logger.info("Launching Gradio Web UI on 127.0.0.1:%d...", port)
    demo.launch(server_name="127.0.0.1", server_port=port, share=False, auth=auth)
