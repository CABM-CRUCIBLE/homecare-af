# Author: C A B M
# Date: 2026-09-17

"""CLI entry point for the HomeCare Agentic Framework.

Provides commands:
  homecare-agent run       — Run the full pipeline (CLI mode)
  homecare-agent web       — Launch the Gradio web UI
  homecare-agent generate  — Generate architecture documents only
  homecare-agent review    — Review existing architecture documents
  homecare-agent setup     — Interactive setup wizard
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.logging import RichHandler

from homecare_agent.security.redaction import SecretMaskingFilter

logger = logging.getLogger(__name__)

app = typer.Typer(
    name="homecare-agent",
    help="HomeCare Agentic Code Generation Framework — automated SDLC powered by LangGraph",
    rich_markup_mode="rich",
)
console = Console()


def _setup_logging(level: str = "INFO", log_file: str = "") -> None:
    """Configure structured logging with Rich console handler, file handler, and secret masking."""
    masking_filter = SecretMaskingFilter()
    console_handler = RichHandler(rich_tracebacks=True, show_path=False)
    console_handler.addFilter(masking_filter)
    handlers: list[logging.Handler] = [console_handler]

    if log_file:
        log_path = Path(log_file)
        try:
            log_path.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(str(log_path), encoding="utf-8")
            file_handler.setFormatter(
                logging.Formatter("[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s")
            )
            file_handler.addFilter(masking_filter)
            handlers.append(file_handler)
        except Exception as e:
            console.print(f"[yellow]Warning: Could not create log file at {log_path}: {e}[/yellow]")

    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(message)s",
        datefmt="[%X]",
        handlers=handlers,
        force=True,
    )
    logging.getLogger().addFilter(masking_filter)


@app.command()
def run(
    feature_name: str = typer.Option("", "--name", "-n", help="Feature name"),
    feature_description: str = typer.Option("", "--desc", "-d", help="Feature description"),
    repo_path: str = typer.Option("", "--repo", "-r", help="Path to target repository"),
    wireframes: list[str] = typer.Option([], "--wireframe", "-w", help="Wireframe paths or URLs"),
    model: str = typer.Option("", "--model", "-m", help="Default OpenRouter model"),
    model_arch: str = typer.Option("", "--model-arch", help="High-reasoning model for Architecture Analysis & Strategy (e.g., Claude Sonnet/Opus)"),
    model_code: str = typer.Option("", "--model-code", help="Cost-effective model for Work Package code generation (e.g., DeepSeek Coder, Haiku)"),
    model_review: str = typer.Option("", "--model-review", help="Model for Architecture and PR Code Reviews"),
    interactive: bool = typer.Option(True, "--interactive/--no-interactive", help="Interactive mode"),
    log_level: str = typer.Option("INFO", "--log-level", "-l", help="Logging level"),
    log_file: str = typer.Option("", "--log-file", help="Path to log file (defaults to logs/homecare-agent.log)"),
    local_code: bool | None = typer.Option(None, "--local-code/--no-local-code", help="Route code generation to local LLM (e.g. Ollama/vLLM)"),
    local_llm_url: str = typer.Option("", "--local-llm-url", help="Base URL for local LLM (default: http://localhost:11434/v1)"),
    local_llm_model: str = typer.Option("", "--local-llm-model", help="Model name on local LLM server (e.g. qwen2.5-coder:32b)"),
    resume: str = typer.Option("", "--resume", help="Resume from checkpoint (trace ID, or 'latest')"),
    from_step: str = typer.Option("", "--from-step", "-s", help="Step number (1-14) or name (e.g. 4 or generate_strategy) to resume from"),
) -> None:
    """Run the full agentic pipeline from feature request to PR, or resume an existing run."""
    if resume:
        target_id = "" if resume.lower() in ("true", "1", "latest") else resume
        _execute_resume(
            trace_id=target_id,
            from_step=from_step,
            log_level=log_level,
            log_file=log_file,
            local_code=local_code,
            local_llm_url=local_llm_url,
            local_llm_model=local_llm_model,
        )
        return

    from homecare_agent.config import get_settings
    from homecare_agent.ui.cli import display_banner, prompt_feature_request, prompt_model_selection

    try:
        overrides = {}
        if repo_path:
            overrides["repo_path"] = repo_path
        if model:
            overrides["openrouter_model"] = model
        if model_arch:
            overrides["model_architecture"] = model_arch
        if model_code:
            overrides["model_code"] = model_code
        if model_review:
            overrides["model_review"] = model_review
        if log_file:
            overrides["log_file"] = log_file
        if local_code is not None:
            overrides["local_llm_enabled"] = local_code
            overrides["local_llm_for_code"] = local_code
        if local_llm_url:
            overrides["local_llm_base_url"] = local_llm_url
        if local_llm_model:
            overrides["local_llm_code_model"] = local_llm_model
        settings = get_settings(**overrides)
    except Exception as e:
        console.print(f"[red]Configuration error: {e}[/red]")
        console.print("[dim]Create a .env file from .env.example and fill in required values.[/dim]")
        raise typer.Exit(1)

    _setup_logging(log_level or settings.log_level, settings.log_file)
    display_banner()

    # Prompt for model if not configured
    if not settings.openrouter_model:
        model = prompt_model_selection()
        settings.openrouter_model = model

    # Collect feature request
    if interactive and not feature_name:
        request = prompt_feature_request()
        feature_name = request["feature_name"]
        feature_description = request["feature_description"]
        wireframes = request.get("wireframe_paths", []) + request.get("wireframe_urls", [])

    if not feature_name:
        console.print("[red]Feature name is required.[/red]")
        raise typer.Exit(1)

    # Initialize LLM provider
    from homecare_agent.llm.provider import LLMProvider
    llm = LLMProvider(settings)

    # Build and compile the graph
    from homecare_agent.graph.main_graph import compile_graph
    graph = compile_graph(settings, llm)

    # Generate unified workflow trace ID (32-character hex)
    import uuid
    trace_id = uuid.uuid4().hex
    llm.set_workflow_trace(trace_id, trace_name=feature_name)

    # Prepare initial state with trace_id
    initial_state = {
        "trace_id": trace_id,
        "feature_name": feature_name,
        "feature_description": feature_description,
        "wireframe_paths": [w for w in wireframes if not w.startswith("http")],
        "wireframe_urls": [w for w in wireframes if w.startswith("http")],
        "repo_path": settings.repo_path,
        "repo_url": settings.repo_url,
        "model_architecture": settings.model_architecture,
        "model_code": settings.model_code,
        "model_review": settings.model_review,
        "current_wave": 0,
        "review_iteration": 0,
    }

    # Run the pipeline
    console.print(f"\n[bold cyan]🚀 Starting pipeline for: {feature_name}[/bold cyan]")
    console.print(f"[dim]Trace ID: {trace_id}[/dim]")
    if settings.langfuse_enabled:
        project_id = getattr(settings, "langfuse_init_project_id", "homecare")
        console.print(f"[dim]Langfuse Trace: {settings.langfuse_host.rstrip('/')}/project/{project_id}/traces/{trace_id}[/dim]\n")

    try:
        result = asyncio.run(_run_pipeline(graph, initial_state, trace_id=trace_id, llm=llm))

        from homecare_agent.ui.cli import display_completion_summary
        display_completion_summary(result)

    except KeyboardInterrupt:
        console.print("\n[yellow]Pipeline interrupted by user. State saved to checkpoint.[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Pipeline failed: {e}[/red]")
        logging.exception("Pipeline failed")
    finally:
        llm.flush_langfuse()


@app.command()
def resume(
    trace_id: str = typer.Option("", "--trace-id", "-t", help="Trace ID of the checkpoint to resume"),
    from_step: str = typer.Option("", "--from-step", "-s", help="Step number (1-14) or name (e.g. 4 or generate_strategy) to resume from"),
    list_checkpoints: bool = typer.Option(False, "--list", "-l", help="List all saved checkpoints"),
    log_level: str = typer.Option("INFO", "--log-level", help="Logging level"),
    log_file: str = typer.Option("", "--log-file", help="Path to log file"),
    local_code: bool | None = typer.Option(None, "--local-code/--no-local-code", help="Route code generation to local LLM"),
    local_llm_url: str = typer.Option("", "--local-llm-url", help="Base URL for local LLM"),
    local_llm_model: str = typer.Option("", "--local-llm-model", help="Model name on local LLM"),
) -> None:
    """Resume pipeline execution from a saved checkpoint at a specific step (e.g. Step 4)."""
    _execute_resume(
        trace_id=trace_id,
        from_step=from_step,
        list_checkpoints=list_checkpoints,
        log_level=log_level,
        log_file=log_file,
        local_code=local_code,
        local_llm_url=local_llm_url,
        local_llm_model=local_llm_model,
    )


def _execute_resume(
    trace_id: str = "",
    from_step: str = "",
    list_checkpoints: bool = False,
    log_level: str = "INFO",
    log_file: str = "",
    local_code: bool | None = None,
    local_llm_url: str = "",
    local_llm_model: str = "",
) -> None:
    """Internal handler for resuming pipeline execution."""
    from homecare_agent.config import get_settings
    from homecare_agent.graph.checkpoint import (
        CheckpointManager,
        get_step_number,
        resolve_next_step,
    )
    from homecare_agent.ui.cli import display_banner

    checkpoint_mgr = CheckpointManager()

    if list_checkpoints:
        _setup_logging(log_level, log_file)
        display_banner()
        cps = checkpoint_mgr.list_checkpoints()
        if not cps:
            console.print("[yellow]No checkpoints found in .homecare/checkpoints[/yellow]")
            return

        from rich.table import Table
        table = Table(title="Saved Pipeline Checkpoints", header_style="bold cyan")
        table.add_column("Trace ID", style="dim")
        table.add_column("Feature Name", style="bold")
        table.add_column("Last Completed Step", style="yellow")
        table.add_column("Next Recommended Step", style="green")
        table.add_column("Saved At", style="dim")

        for cp in cps:
            last_step = cp.get("last_completed_step", "None")
            last_num = cp.get("last_completed_step_number")
            step_display = f"Step {last_num}: {last_step}" if last_num else last_step
            next_step = cp.get("next_recommended_step", "intake_feature")
            next_num = get_step_number(next_step)
            next_display = f"Step {next_num}: {next_step}" if next_num else next_step
            table.add_row(
                cp["trace_id"][:12] + "...",
                cp["feature_name"],
                step_display,
                next_display,
                cp.get("timestamp", "")[:19].replace("T", " "),
            )
        console.print(table)
        console.print("\n[dim]To resume: homecare-agent resume --trace-id <id> [--from-step <step>][/dim]")
        return

    try:
        overrides = {}
        if log_file:
            overrides["log_file"] = log_file
        if local_code is not None:
            overrides["local_llm_enabled"] = local_code
            overrides["local_llm_for_code"] = local_code
        if local_llm_url:
            overrides["local_llm_base_url"] = local_llm_url
        if local_llm_model:
            overrides["local_llm_code_model"] = local_llm_model
        settings = get_settings(**overrides)
    except Exception as e:
        console.print(f"[red]Configuration error: {e}[/red]")
        raise typer.Exit(1)

    _setup_logging(log_level or settings.log_level, settings.log_file)
    display_banner()

    # If trace_id not specified, pick latest
    if not trace_id:
        cps = checkpoint_mgr.list_checkpoints()
        if not cps:
            console.print("[red]No saved checkpoints found in .homecare/checkpoints to resume.[/red]")
            console.print("[dim]Run `homecare-agent run` to start a new pipeline run.[/dim]")
            raise typer.Exit(1)
        latest = cps[0]
        trace_id = latest["trace_id"]
        console.print(f"[dim]No trace ID specified. Resuming latest run: {trace_id}[/dim]")

    try:
        checkpoint_data = checkpoint_mgr.load_checkpoint(trace_id)
    except FileNotFoundError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)

    saved_state = checkpoint_data.get("state", {})
    feature_name = saved_state.get("feature_name") or checkpoint_data.get("feature_name", "Unknown")

    # Determine step to resume from
    try:
        resume_step = resolve_next_step(saved_state, explicit_step=from_step)
    except ValueError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)

    step_num = get_step_number(resume_step)
    last_step = checkpoint_data.get("last_completed_step", "None")

    console.print(f"\n[bold cyan]🔄 Resuming Pipeline for: {feature_name}[/bold cyan]")
    console.print(f"[dim]Trace ID: {trace_id}[/dim]")
    console.print(f"[yellow]Last Completed Step: {last_step}[/yellow]")
    console.print(f"[bold green]▶ Resuming from Step {step_num or '?'}: {resume_step}[/bold green]")
    prior_steps = saved_state.get("completed_steps", [])
    if prior_steps:
        console.print(f"[dim]Prior completed steps: {', '.join(prior_steps)}[/dim]\n")

    # Set resume target in state
    saved_state["resume_from_step"] = resume_step
    saved_state["current_step"] = resume_step

    # Initialize LLM provider & Langfuse
    from homecare_agent.llm.provider import LLMProvider
    llm = LLMProvider(settings)
    llm.set_workflow_trace(trace_id, trace_name=feature_name)

    if settings.langfuse_enabled:
        project_id = getattr(settings, "langfuse_init_project_id", "homecare")
        console.print(f"[dim]Langfuse Trace: {settings.langfuse_host.rstrip('/')}/project/{project_id}/traces/{trace_id}[/dim]\n")

    # Build and compile graph
    from homecare_agent.graph.main_graph import compile_graph
    graph = compile_graph(settings, llm)

    try:
        result = asyncio.run(_run_pipeline(graph, saved_state, trace_id=trace_id, llm=llm))
        from homecare_agent.ui.cli import display_completion_summary
        display_completion_summary(result)
    except KeyboardInterrupt:
        console.print("\n[yellow]Pipeline interrupted by user. State saved to checkpoint.[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Pipeline failed: {e}[/red]")
        logging.exception("Pipeline failed during resume")
    finally:
        llm.flush_langfuse()


async def _run_pipeline(graph: object, initial_state: dict, trace_id: str = "", llm: Any = None) -> dict:
    """Run the compiled graph pipeline with state checkpointing and tracing.

    Args:
        graph: Compiled LangGraph runnable.
        initial_state: Initial state dictionary.
        trace_id: Unified workflow trace ID.
        llm: LLMProvider instance with callback handler.

    Returns:
        Final state dictionary.
    """
    from homecare_agent.graph.checkpoint import CheckpointManager
    from homecare_agent.ui.cli import display_error, display_step_progress

    checkpoint_mgr = CheckpointManager()
    config: dict[str, Any] = {}
    if llm and trace_id:
        handler = llm.get_langfuse_handler(trace_id)
        if handler:
            config["callbacks"] = [handler]

    final_state = dict(initial_state)
    stream_kwargs: dict[str, Any] = {}
    if config:
        stream_kwargs["config"] = config

    # Save initial checkpoint
    if trace_id:
        try:
            checkpoint_mgr.save_checkpoint(trace_id, final_state, last_step="")
        except Exception as e:
            logger.debug("Initial checkpoint save note: %s", e)

    async for event in graph.astream(initial_state, **stream_kwargs):  # type: ignore[union-attr]
        for node_name, state_update in event.items():
            step = state_update.get("current_step", node_name)
            display_step_progress(step, "completed")
            final_state.update(state_update)

            # Auto-save checkpoint after each completed node
            if trace_id:
                try:
                    checkpoint_mgr.save_checkpoint(trace_id, final_state, last_step=step)
                except Exception as e:
                    logger.warning("Could not auto-save checkpoint for %s: %s", step, e)

            # Display errors if any
            errors = state_update.get("errors", [])
            for error in errors:
                display_error(error)

    return final_state


@app.command()
def web(
    port: int = typer.Option(7860, "--port", "-p", help="Web UI port"),
    log_level: str = typer.Option("", "--log-level", "-l", help="Logging level"),
) -> None:
    """Launch the Gradio web interface."""
    from homecare_agent.config import get_settings
    settings = get_settings()
    settings.web_ui_port = port  # type: ignore[assignment]
    _setup_logging(log_level or settings.log_level, settings.log_file)

    from homecare_agent.ui.cli import display_banner
    display_banner()

    from homecare_agent.ui.web import launch_web_ui
    launch_web_ui(settings)


@app.command()
def generate(
    feature_name: str = typer.Option(..., "--name", "-n", help="Feature name"),
    feature_description: str = typer.Option(..., "--desc", "-d", help="Feature description"),
    output_dir: str = typer.Option("output", "--output", "-o", help="Output directory"),
    log_level: str = typer.Option("", "--log-level", "-l", help="Logging level"),
) -> None:
    """Generate architecture documents only (Strategy, Tactical, ADRs)."""
    from homecare_agent.config import get_settings
    settings = get_settings(output_dir=output_dir)
    _setup_logging(log_level or settings.log_level, settings.log_file)

    from homecare_agent.ui.cli import display_banner
    display_banner()

    console.print(f"[cyan]Generating architecture documents for: {feature_name}[/cyan]")
    console.print(f"[dim]Output: {output_dir}[/dim]")

    from homecare_agent.ui.cli import prompt_model_selection
    if not settings.openrouter_model:
        settings.openrouter_model = prompt_model_selection()

    from homecare_agent.llm.provider import LLMProvider
    llm = LLMProvider(settings)

    import uuid
    trace_id = uuid.uuid4().hex
    llm.set_workflow_trace(trace_id, trace_name=f"generate_{feature_name}")
    console.print(f"[dim]Trace ID: {trace_id}[/dim]")

    # Run only the architecture generation nodes
    async def _generate() -> None:
        from homecare_agent.graph.nodes.architect import generate_strategy, generate_tactical_plan, generate_adrs

        state = {
            "trace_id": trace_id,
            "feature_name": feature_name,
            "feature_description": feature_description,
            "repo_path": settings.repo_path,
            "codebase_analysis": {},
            "clarification_answers": [],
        }

        console.print("  ⏳ Generating Strategy...")
        result = await generate_strategy(state, settings, llm)
        state.update(result)

        console.print("  ⏳ Generating Tactical Plan...")
        result = await generate_tactical_plan(state, settings, llm)
        state.update(result)

        console.print("  ⏳ Generating ADRs...")
        result = await generate_adrs(state, settings, llm)
        state.update(result)

        # Write outputs
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)

        (out / "STRATEGY.md").write_text(state.get("strategy_document", ""), encoding="utf-8")
        (out / "TACTICAL-PLAN.md").write_text(state.get("tactical_plan", ""), encoding="utf-8")

        for adr in state.get("adr_documents", []):
            filename = f"ADR-{adr.get('number', 0):03d}.md"
            content = adr.get("rendered_markdown", str(adr))
            (out / filename).write_text(content, encoding="utf-8")

        console.print(f"\n[green]✅ Documents written to: {out}[/green]")

    asyncio.run(_generate())
    llm.flush_langfuse()


@app.command()
def setup() -> None:
    """Interactive setup wizard."""
    _setup_logging("INFO")
    from homecare_agent.ui.cli import display_banner
    display_banner()

    console.print("\n[bold cyan]🔧 Setup Wizard[/bold cyan]\n")

    from rich.prompt import Prompt

    env_lines = []

    # OpenRouter
    api_key = Prompt.ask("OpenRouter API Key", password=True)
    env_lines.append(f"OPENROUTER_API_KEY={api_key}")

    from homecare_agent.ui.cli import prompt_model_selection
    model = prompt_model_selection()
    env_lines.append(f"OPENROUTER_MODEL={model}")

    # GitHub
    github_token = Prompt.ask("GitHub Token (optional, press Enter to skip)", default="", password=True)
    if github_token:
        env_lines.append(f"GITHUB_TOKEN={github_token}")

    # Repository
    repo_path = Prompt.ask("Target repository path", default="")
    if repo_path:
        env_lines.append(f"REPO_PATH={repo_path}")

    repo_url = Prompt.ask("GitHub repository URL", default="")
    if repo_url:
        env_lines.append(f"REPO_URL={repo_url}")

    # Langfuse
    from rich.prompt import Confirm
    if Confirm.ask("Enable Langfuse tracing?", default=False):
        langfuse_pk = Prompt.ask("Langfuse Public Key", password=True)
        langfuse_sk = Prompt.ask("Langfuse Secret Key", password=True)
        langfuse_host = Prompt.ask("Langfuse Host", default="https://cloud.langfuse.com")
        env_lines.extend([
            f"LANGFUSE_PUBLIC_KEY={langfuse_pk}",
            f"LANGFUSE_SECRET_KEY={langfuse_sk}",
            f"LANGFUSE_HOST={langfuse_host}",
            "LANGFUSE_ENABLED=true",
        ])

    # Write .env
    env_content = "\n".join(env_lines) + "\n"
    Path(".env").write_text(env_content, encoding="utf-8")
    console.print("\n[green]✅ Configuration saved to .env[/green]")
    console.print("[dim]Run `homecare-agent run` to start the pipeline.[/dim]")


if __name__ == "__main__":
    app()
