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
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.logging import RichHandler

app = typer.Typer(
    name="homecare-agent",
    help="HomeCare Agentic Code Generation Framework — automated SDLC powered by LangGraph",
    rich_markup_mode="rich",
)
console = Console()


def _setup_logging(level: str = "INFO") -> None:
    """Configure structured logging with Rich handler."""
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True, show_path=False)],
    )


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
) -> None:
    """Run the full agentic pipeline from feature request to PR."""
    _setup_logging(log_level)
    from homecare_agent.ui.cli import display_banner, prompt_feature_request, prompt_model_selection

    display_banner()

    # Load settings
    from homecare_agent.config import get_settings
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
        settings = get_settings(**overrides)
    except Exception as e:
        console.print(f"[red]Configuration error: {e}[/red]")
        console.print("[dim]Create a .env file from .env.example and fill in required values.[/dim]")
        raise typer.Exit(1)

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

    # Prepare initial state
    initial_state = {
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
    console.print(f"\n[bold cyan]🚀 Starting pipeline for: {feature_name}[/bold cyan]\n")

    try:
        result = asyncio.run(_run_pipeline(graph, initial_state))

        from homecare_agent.ui.cli import display_completion_summary
        display_completion_summary(result)

    except KeyboardInterrupt:
        console.print("\n[yellow]Pipeline interrupted by user.[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Pipeline failed: {e}[/red]")
        logging.exception("Pipeline failed")
    finally:
        llm.flush_langfuse()


async def _run_pipeline(graph: object, initial_state: dict) -> dict:
    """Run the compiled graph pipeline.

    Args:
        graph: Compiled LangGraph runnable.
        initial_state: Initial state dictionary.

    Returns:
        Final state dictionary.
    """
    from homecare_agent.ui.cli import display_step_progress

    final_state = {}
    async for event in graph.astream(initial_state):  # type: ignore[union-attr]
        for node_name, state_update in event.items():
            step = state_update.get("current_step", node_name)
            display_step_progress(step, "completed")
            final_state.update(state_update)

            # Display errors if any
            errors = state_update.get("errors", [])
            for error in errors:
                from homecare_agent.ui.cli import display_error
                display_error(error)

    return final_state


@app.command()
def web(
    port: int = typer.Option(7860, "--port", "-p", help="Web UI port"),
    log_level: str = typer.Option("INFO", "--log-level", "-l", help="Logging level"),
) -> None:
    """Launch the Gradio web interface."""
    _setup_logging(log_level)
    from homecare_agent.ui.cli import display_banner
    display_banner()

    from homecare_agent.config import get_settings
    settings = get_settings()
    settings.web_ui_port = port  # type: ignore[assignment]

    from homecare_agent.ui.web import launch_web_ui
    launch_web_ui(settings)


@app.command()
def generate(
    feature_name: str = typer.Option(..., "--name", "-n", help="Feature name"),
    feature_description: str = typer.Option(..., "--desc", "-d", help="Feature description"),
    output_dir: str = typer.Option("output", "--output", "-o", help="Output directory"),
    log_level: str = typer.Option("INFO", "--log-level", "-l", help="Logging level"),
) -> None:
    """Generate architecture documents only (Strategy, Tactical, ADRs)."""
    _setup_logging(log_level)
    from homecare_agent.ui.cli import display_banner
    display_banner()

    console.print(f"[cyan]Generating architecture documents for: {feature_name}[/cyan]")
    console.print(f"[dim]Output: {output_dir}[/dim]")

    from homecare_agent.config import get_settings
    settings = get_settings(output_dir=output_dir)

    from homecare_agent.ui.cli import prompt_model_selection
    if not settings.openrouter_model:
        settings.openrouter_model = prompt_model_selection()

    from homecare_agent.llm.provider import LLMProvider
    llm = LLMProvider(settings)

    # Run only the architecture generation nodes
    async def _generate() -> None:
        from homecare_agent.graph.nodes.architect import generate_strategy, generate_tactical_plan, generate_adrs

        state = {
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
