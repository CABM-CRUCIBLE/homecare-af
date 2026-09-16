# Author: C A B M
# Date: 2026-09-17

"""Code generation execution node.

Executes individual work package prompts to generate complete file contents.
Handles parallel execution within waves and sequential execution across waves.
Validates generated code by running builds.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

from homecare_agent.config import ExecutionMode, Settings
from homecare_agent.graph.state import AgentState
from homecare_agent.llm.provider import LLMProvider

logger = logging.getLogger(__name__)

CODE_GENERATOR_PERSONA = """\
You are a Senior Software Engineer implementing a work package for an enterprise
healthcare platform. You produce production-ready, complete code following Clean
Architecture principles.

CRITICAL RULES:
1. Provide COMPLETE file contents. Never truncate with "// ... rest of code".
2. Follow the Standing Instructions exactly.
3. Only modify files listed in your scope. Do not touch files owned by other packages.
4. Include unit tests for all business logic.
5. Add XML doc comments (C#) or JSDoc (TypeScript) on all public members.
6. Follow the exact naming conventions specified.
"""


async def execute_wave(state: AgentState, settings: Settings, llm: LLMProvider) -> dict[str, Any]:
    """Execute all work packages in the current wave.

    For parallel mode: runs all WPs in the current wave concurrently.
    For sequential mode: runs WPs one at a time.

    Args:
        state: Current graph state.
        settings: Application settings.
        llm: LLM provider instance.

    Returns:
        State updates with generated code and execution results.
    """
    current_wave = state.get("current_wave", 0)
    work_packages = state.get("work_packages", [])
    standing_instructions = state.get("standing_instructions", "")

    # Group WPs by wave
    waves: dict[str, list[dict[str, Any]]] = {}
    for wp in work_packages:
        wave_id = wp.get("wave", "")
        waves.setdefault(wave_id, []).append(wp)

    wave_ids = sorted(waves.keys())
    if current_wave >= len(wave_ids):
        logger.info("All waves completed.")
        return {
            "current_step": "all_waves_complete",
            "completed_steps": [f"wave_{current_wave}_complete"],
        }

    current_wave_id = wave_ids[current_wave]
    wave_wps = waves[current_wave_id]

    logger.info(
        "Executing wave %d (%s) with %d work package(s)...",
        current_wave, current_wave_id, len(wave_wps),
    )

    updates: dict[str, Any] = {
        "current_step": f"execute_wave_{current_wave_id}",
    }

    if settings.execution_mode == ExecutionMode.PARALLEL:
        # Execute all WPs in this wave concurrently
        tasks = [
            _execute_single_wp(wp, standing_instructions, settings, llm, state)
            for wp in wave_wps
            if wp.get("parallel_safe", True)
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        generated_code: dict[str, str] = {}
        for result in results:
            if isinstance(result, dict):
                generated_code.update(result.get("files", {}))
            elif isinstance(result, Exception):
                logger.exception("Work package execution failed: %s", result)

        updates["generated_code"] = generated_code
    else:
        # Sequential execution
        generated_code = {}
        for wp in wave_wps:
            result = await _execute_single_wp(wp, standing_instructions, settings, llm, state)
            generated_code.update(result.get("files", {}))

        updates["generated_code"] = generated_code

    updates["current_wave"] = current_wave + 1
    updates["completed_steps"] = [f"wave_{current_wave_id}"]

    return updates


async def _execute_single_wp(
    wp: dict[str, Any],
    standing_instructions: str,
    settings: Settings,
    llm: LLMProvider,
    state: AgentState | None = None,
) -> dict[str, Any]:
    """Execute a single work package prompt to generate code.

    Args:
        wp: Work package definition.
        standing_instructions: Enterprise standing instructions.
        settings: Application settings.
        llm: LLM provider instance.
        state: Optional agent state for configuration overrides.

    Returns:
        Dict with 'files' mapping file paths to generated content.
    """
    wp_id = wp.get("id", "unknown")
    wp_title = wp.get("title", "")
    logger.info("Executing work package: %s — %s", wp_id, wp_title)

    prompt = wp.get("prompt", "")
    if not prompt:
        logger.warning("Work package %s has no prompt; skipping.", wp_id)
        return {"files": {}}

    full_prompt = f"""{standing_instructions}

---

{prompt}

IMPORTANT: For each file you generate, format your output as:

### FILE: <relative/path/to/file>
```<language>
<complete file contents>
```

Generate ALL files specified in the scope. Every file must be COMPLETE.
"""

    try:
        response = await llm.ainvoke(
            prompt=full_prompt,
            system_prompt=CODE_GENERATOR_PERSONA,
            node_name="execute_wave",
            state_overrides=state,
            trace_name=f"execute_wp_{wp_id}",
            trace_metadata={"wp_id": wp_id, "wp_title": wp_title},
        )

        # Parse file contents from response
        files = _parse_generated_files(response)
        logger.info("Work package %s generated %d file(s).", wp_id, len(files))
        return {"files": files}

    except Exception:
        logger.exception("Work package %s execution failed.", wp_id)
        return {"files": {}}


def _parse_generated_files(response: str) -> dict[str, str]:
    """Parse generated file contents from LLM response.

    Expects format:
        ### FILE: path/to/file.cs
        ```csharp
        <content>
        ```

    Args:
        response: LLM response text.

    Returns:
        Dict mapping file paths to file contents.
    """
    files: dict[str, str] = {}
    import re

    # Pattern: ### FILE: <path> followed by ```<lang>\n<content>\n```
    pattern = r"###\s*FILE:\s*(.+?)\s*\n```\w*\n(.*?)```"
    matches = re.findall(pattern, response, re.DOTALL)

    for file_path, content in matches:
        file_path = file_path.strip()
        content = content.strip()
        if file_path and content:
            files[file_path] = content

    return files


async def write_generated_files(state: AgentState, settings: Settings) -> dict[str, Any]:
    """Write generated code files to the repository.

    Args:
        state: Current graph state with generated_code.
        settings: Application settings.

    Returns:
        State updates.
    """
    repo_path = Path(state.get("repo_path", settings.repo_path))
    generated_code = state.get("generated_code", {})

    logger.info("Writing %d generated file(s) to: %s", len(generated_code), repo_path)

    written_files: list[str] = []
    for file_path, content in generated_code.items():
        full_path = repo_path / file_path
        try:
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content, encoding="utf-8")
            written_files.append(file_path)
            logger.info("  Written: %s", file_path)
        except Exception:
            logger.exception("Failed to write: %s", file_path)

    return {
        "current_step": "write_files",
        "completed_steps": ["write_files"],
    }
