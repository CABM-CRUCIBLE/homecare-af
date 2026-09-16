"""Rich CLI interface for the HomeCare Agentic Framework.

Provides an interactive terminal interface with progress tracking,
step-by-step status updates, and clarification prompts.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.prompt import Confirm, Prompt
from rich.table import Table
from rich.tree import Tree

logger = logging.getLogger(__name__)
console = Console()


def display_banner() -> None:
    """Display the framework banner."""
    console.print(Panel(
        "[bold cyan]HomeCare Agentic Code Generation Framework[/bold cyan]\n"
        "[dim]Automated SDLC from feature request to PR — powered by LangGraph[/dim]",
        border_style="cyan",
        padding=(1, 2),
    ))


def display_settings_summary(settings: dict[str, Any]) -> None:
    """Display a summary of the current configuration.

    Args:
        settings: Configuration key-value pairs to display.
    """
    table = Table(title="Configuration", show_header=True, header_style="bold cyan")
    table.add_column("Setting", style="bold")
    table.add_column("Value")

    for key, value in settings.items():
        # Mask secrets
        if "key" in key.lower() or "token" in key.lower() or "secret" in key.lower():
            display_val = f"{str(value)[:8]}..." if value else "[dim]Not set[/dim]"
        else:
            display_val = str(value) if value else "[dim]Not set[/dim]"
        table.add_row(key, display_val)

    console.print(table)


def prompt_model_selection() -> str:
    """Prompt the user to select an LLM model.

    Returns:
        Selected model identifier.
    """
    console.print("\n[bold yellow]No default LLM model configured.[/bold yellow]")
    console.print("Popular OpenRouter models:")

    table = Table(show_header=True, header_style="bold")
    table.add_column("#", width=3)
    table.add_column("Model")
    table.add_column("Provider")
    table.add_column("Notes")

    models = [
        ("anthropic/claude-sonnet-4", "Anthropic", "Strong coding, vision support"),
        ("anthropic/claude-opus-4", "Anthropic", "Most capable, higher cost"),
        ("openai/gpt-4o", "OpenAI", "Fast, good coding"),
        ("google/gemini-2.5-pro", "Google", "Long context, good reasoning"),
        ("deepseek/deepseek-chat", "DeepSeek", "Cost-effective coding"),
    ]

    for i, (model, provider, notes) in enumerate(models, 1):
        table.add_row(str(i), model, provider, notes)

    console.print(table)

    choice = Prompt.ask(
        "Enter model name or number",
        default="1",
    )

    try:
        idx = int(choice) - 1
        if 0 <= idx < len(models):
            return models[idx][0]
    except ValueError:
        pass

    return choice  # Return as-is if not a number


def prompt_feature_request() -> dict[str, Any]:
    """Interactively collect feature request details.

    Returns:
        Dict with feature_name, feature_description, wireframe_paths, wireframe_urls.
    """
    console.print("\n[bold cyan]📋 Feature Request[/bold cyan]\n")

    name = Prompt.ask("[bold]Feature name[/bold]")
    description = Prompt.ask("[bold]Feature description[/bold] (detailed)")

    wireframe_paths: list[str] = []
    wireframe_urls: list[str] = []

    if Confirm.ask("Do you have wireframes/screenshots?", default=False):
        console.print("[dim]Enter paths or URLs (empty line to finish)[/dim]")
        while True:
            entry = Prompt.ask("  Path or URL", default="")
            if not entry:
                break
            if entry.startswith(("http://", "https://")):
                wireframe_urls.append(entry)
            else:
                wireframe_paths.append(entry)

    return {
        "feature_name": name,
        "feature_description": description,
        "wireframe_paths": wireframe_paths,
        "wireframe_urls": wireframe_urls,
    }


def display_step_progress(step: str, status: str = "running") -> None:
    """Display the current step status.

    Args:
        step: Step name.
        status: 'running', 'completed', 'failed'.
    """
    icons = {"running": "⏳", "completed": "✅", "failed": "❌"}
    colors = {"running": "yellow", "completed": "green", "failed": "red"}

    icon = icons.get(status, "⏳")
    color = colors.get(status, "yellow")

    console.print(f"  {icon} [{color}]{step}[/{color}]")


def display_workflow_tree(completed_steps: list[str], current_step: str) -> None:
    """Display the workflow progress as a tree.

    Args:
        completed_steps: List of completed step names.
        current_step: Currently executing step.
    """
    tree = Tree("[bold cyan]Workflow Progress[/bold cyan]")

    all_steps = [
        "intake_feature",
        "analyze_codebase",
        "generate_strategy",
        "generate_tactical_plan",
        "generate_adrs",
        "generate_agentic_prompts",
        "review_architecture",
        "create_branch",
        "execute_wave",
        "run_unit_tests",
        "run_e2e_tests",
        "run_load_tests",
        "create_pr",
        "code_review",
        "notify_ready_for_merge",
    ]

    for step in all_steps:
        if step in completed_steps:
            tree.add(f"[green]✅ {step}[/green]")
        elif step == current_step:
            tree.add(f"[yellow]⏳ {step} (running...)[/yellow]")
        else:
            tree.add(f"[dim]⬜ {step}[/dim]")

    console.print(tree)


def display_error(error: dict[str, str]) -> None:
    """Display an error message.

    Args:
        error: Dict with 'step' and 'message' keys.
    """
    console.print(Panel(
        f"[bold red]Error in step: {error.get('step', 'unknown')}[/bold red]\n"
        f"{error.get('message', 'Unknown error')}",
        border_style="red",
        title="⚠️ Error",
    ))


def display_completion_summary(state: dict[str, Any]) -> None:
    """Display the final completion summary.

    Args:
        state: Final graph state.
    """
    console.print(Panel(
        f"""[bold green]✅ Feature Implementation Complete![/bold green]

[bold]Feature:[/bold] {state.get("feature_name", "N/A")}
[bold]Branch:[/bold] {state.get("branch_name", "N/A")}
[bold]PR:[/bold] #{state.get("pr_number", "N/A")} — {state.get("pr_url", "")}
[bold]Commits:[/bold] {len(state.get("commit_log", []))}
[bold]Files Generated:[/bold] {len(state.get("generated_code", {}))}
[bold]Review Iterations:[/bold] {state.get("review_iteration", 0)}
[bold]Steps Completed:[/bold] {len(state.get("completed_steps", []))}
""",
        title="🎉 HomeCare Agentic Framework",
        border_style="green",
    ))
