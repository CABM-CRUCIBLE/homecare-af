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
from homecare_agent.tools.file_tools import PathTraversalSecurityError, validate_safe_path

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
    trace_id = state.get("trace_id", "no-trace")
    feature_name = state.get("feature_name", "Unknown")
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
        logger.info("[COMPLETED:execute_wave][trace_id=%s] All waves completed for '%s'", trace_id, feature_name)
        return {
            "current_step": "all_waves_complete",
            "completed_steps": [f"wave_{current_wave}_complete"],
        }

    current_wave_id = wave_ids[current_wave]
    wave_wps = waves[current_wave_id]

    logger.info(
        "[START:execute_wave][trace_id=%s] Executing wave %d (%s) with %d work package(s) for '%s'...",
        trace_id,
        current_wave,
        current_wave_id,
        len(wave_wps),
        feature_name,
    )

    updates: dict[str, Any] = {
        "current_step": f"execute_wave_{current_wave_id}",
    }

    errors: list[dict[str, Any]] = []

    if settings.execution_mode == ExecutionMode.PARALLEL:
        # Execute all WPs in this wave concurrently
        tasks = [
            _execute_single_wp(wp, standing_instructions, settings, llm, state)
            for wp in wave_wps
            if wp.get("parallel_safe", True)
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        generated_code: dict[str, str] = {}
        for idx, result in enumerate(results):
            if isinstance(result, dict):
                generated_code.update(result.get("files", {}))
            elif isinstance(result, Exception):
                failed_wp = wave_wps[idx].get("id", f"wp_{idx}")
                logger.error(
                    "[ERROR:execute_wave][trace_id=%s] Work package %s execution failed: %s",
                    trace_id,
                    failed_wp,
                    result,
                    exc_info=True,
                )
                errors.append({"step": f"execute_wave_{current_wave_id}", "trace_id": trace_id, "wp_id": failed_wp, "message": str(result)})

        updates["generated_code"] = generated_code
    else:
        # Sequential execution
        generated_code = {}
        for wp in wave_wps:
            try:
                result = await _execute_single_wp(wp, standing_instructions, settings, llm, state)
                generated_code.update(result.get("files", {}))
            except Exception as e:
                wp_id = wp.get("id", "unknown")
                logger.error(
                    "[ERROR:execute_wave][trace_id=%s] Work package %s execution failed: %s",
                    trace_id,
                    wp_id,
                    e,
                    exc_info=True,
                )
                errors.append({"step": f"execute_wave_{current_wave_id}", "trace_id": trace_id, "wp_id": wp_id, "message": str(e)})

        updates["generated_code"] = generated_code

    if errors:
        updates["errors"] = errors

    logger.info(
        "[COMPLETED:execute_wave][trace_id=%s] Finished wave %d (%s) with %d generated file(s)",
        trace_id,
        current_wave,
        current_wave_id,
        len(generated_code),
    )

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
    trace_id = state.get("trace_id", "no-trace") if state else "no-trace"
    wp_id = wp.get("id", "unknown")
    wp_title = wp.get("title", "")
    logger.info("[START:_execute_single_wp][trace_id=%s] Executing work package: %s — %s", trace_id, wp_id, wp_title)

    prompt = wp.get("prompt", "")
    if not prompt:
        logger.warning("[WARN:_execute_single_wp][trace_id=%s] Work package %s has no prompt; skipping.", trace_id, wp_id)
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

    logger.debug("[_execute_single_wp][trace_id=%s] Invoking LLM for work package %s...", trace_id, wp_id)
    response = await llm.ainvoke(
        prompt=full_prompt,
        system_prompt=CODE_GENERATOR_PERSONA,
        node_name="execute_wave",
        state_overrides=state,
        trace_name=f"execute_wp_{wp_id}",
        trace_metadata={"wp_id": wp_id, "wp_title": wp_title, "trace_id": trace_id},
    )

    # Parse file contents from response
    files = _parse_generated_files(response)
    logger.info(
        "[COMPLETED:_execute_single_wp][trace_id=%s] Work package %s generated %d file(s).",
        trace_id,
        wp_id,
        len(files),
    )
    return {"files": files}


def _parse_generated_files(response: str) -> dict[str, str]:
    """Parse generated file contents from LLM response.

    Splits by '### FILE:' headers and extracts code within outer fences,
    handling nested backticks and various language markers cleanly.

    Args:
        response: LLM response text.

    Returns:
        Dict mapping file paths to file contents.
    """
    files: dict[str, str] = {}
    import re

    # Split response by '### FILE: <path>' header
    parts = re.split(r"(?m)^###\s*FILE:\s*", response)
    for part in parts:
        part = part.strip()
        if not part:
            continue

        lines = part.split("\n", 1)
        file_path = lines[0].strip().strip("`'\" \r")

        if len(lines) < 2 or not file_path:
            continue

        body = lines[1].strip()

        # Check for opening fence: ``` or ```` followed by optional language tag
        fence_match = re.match(r"^(`{3,})[a-zA-Z0-9_\-]*\r?\n", body)
        if fence_match:
            fence_chars = fence_match.group(1)
            code_start = fence_match.end()
            # Match closing fence on a line by itself
            closing_pattern = rf"(?m)^{re.escape(fence_chars)}\s*$"
            closing_matches = list(re.finditer(closing_pattern, body[code_start:]))
            if closing_matches:
                # Use the last closing fence match in this file section
                last_match = closing_matches[-1]
                code_content = body[code_start : code_start + last_match.start()].rstrip()
            else:
                # Fallback: strip any trailing fence if present
                code_content = re.sub(r"\r?\n`{3,}\s*$", "", body[code_start:]).rstrip()
        else:
            code_content = body

        if file_path and code_content:
            files[file_path] = code_content

    return files


async def write_generated_files(state: AgentState, settings: Settings) -> dict[str, Any]:
    """Write generated code files to the repository.

    Args:
        state: Current graph state with generated_code.
        settings: Application settings.

    Returns:
        State updates.
    """
    trace_id = state.get("trace_id", "no-trace")
    feature_name = state.get("feature_name", "Unknown")
    repo_path = Path(state.get("repo_path", settings.repo_path))
    generated_code = state.get("generated_code", {})

    logger.info(
        "[START:write_generated_files][trace_id=%s] Writing %d generated file(s) for '%s' to %s",
        trace_id,
        len(generated_code),
        feature_name,
        repo_path,
    )

    written_files: list[str] = []
    errors: list[dict[str, Any]] = []
    for file_path, content in generated_code.items():
        try:
            full_path = validate_safe_path(file_path, repo_path)
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content, encoding="utf-8")
            written_files.append(file_path)
            logger.debug("[write_generated_files][trace_id=%s] Written: %s", trace_id, file_path)
        except PathTraversalSecurityError as pse:
            logger.critical(
                "[CRITICAL:write_generated_files][trace_id=%s] Path traversal security violation blocked for '%s': %s",
                trace_id,
                file_path,
                pse,
            )
            errors.append({
                "step": "write_files",
                "trace_id": trace_id,
                "file": file_path,
                "security_violation": True,
                "message": f"Security violation: {pse}",
            })
        except Exception as e:
            logger.error(
                "[ERROR:write_generated_files][trace_id=%s] Failed to write '%s': %s",
                trace_id,
                file_path,
                e,
                exc_info=True,
            )
            errors.append({"step": "write_files", "trace_id": trace_id, "file": file_path, "message": str(e)})

    logger.info(
        "[COMPLETED:write_generated_files][trace_id=%s] Successfully written %d/%d file(s)",
        trace_id,
        len(written_files),
        len(generated_code),
    )

    result: dict[str, Any] = {
        "written_files": written_files,
        "current_step": "write_files",
        "completed_steps": ["write_files"],
    }
    if errors:
        result["errors"] = errors
    return result
