# Author: C A B M
# Date: 2026-09-17

"""Testing node for unit, E2E, and load test execution (ARCH-03)."""

from __future__ import annotations

import asyncio
import logging
import subprocess
import sys
from pathlib import Path
from typing import Any

from homecare_agent.config import Settings
from homecare_agent.graph.state import AgentState

logger = logging.getLogger(__name__)


async def run_tests(state: AgentState, settings: Settings, test_type: str = "unit") -> dict[str, Any]:
    """Run tests (unit, e2e, load) asynchronously without blocking the event loop.

    Args:
        state: Current graph state.
        settings: Application settings.
        test_type: "unit", "e2e", or "load".

    Returns:
        State updates containing test results and execution status.
    """
    trace_id = state.get("trace_id", "no-trace")
    feature_name = state.get("feature_name", "Unknown")
    step_name = f"run_{test_type}_tests"
    logger.info("[START:%s][trace_id=%s] Running %s tests for '%s'...", step_name, trace_id, test_type, feature_name)

    repo_path = Path(state.get("repo_path", settings.repo_path))
    results: dict[str, Any] = {"type": test_type, "passed": 0, "failed": 0, "total": 0}
    errors: list[dict[str, Any]] = []

    # Dynamic directory discovery
    backend_dir = repo_path / "code" / "backend"
    if not backend_dir.exists():
        sln_files = list(repo_path.glob("**/*.sln"))
        csproj_files = list(repo_path.glob("**/*.csproj"))
        if sln_files:
            backend_dir = sln_files[0].parent
        elif csproj_files:
            backend_dir = csproj_files[0].parent
        else:
            backend_dir = repo_path

    frontend_dir = repo_path / "code" / "frontend"
    if not frontend_dir.exists():
        package_files = [p for p in repo_path.glob("**/package.json") if "node_modules" not in str(p)]
        if package_files:
            frontend_dir = package_files[0].parent
        else:
            frontend_dir = repo_path

    if test_type == "unit":
        # Backend unit tests (.NET) - non-blocking thread execution
        try:
            if any(backend_dir.glob("*.sln")) or any(backend_dir.glob("*.csproj")) or (backend_dir / "code" / "backend").exists():
                proc = await asyncio.to_thread(
                    subprocess.run,
                    ["dotnet", "test", "--verbosity", "minimal"],
                    cwd=str(backend_dir),
                    capture_output=True,
                    text=True,
                    timeout=300,
                )
                results["backend_output"] = proc.stdout
                results["backend_returncode"] = proc.returncode
        except Exception as e:
            logger.error("[ERROR:%s][trace_id=%s] Backend tests failed to run: %s", step_name, trace_id, e, exc_info=True)
            results["backend_error"] = str(e)
            errors.append({"step": step_name, "trace_id": trace_id, "component": "backend", "message": str(e)})

        # Frontend unit tests (Node.js/Vitest) - non-blocking thread execution
        try:
            if (frontend_dir / "package.json").exists():
                proc = await asyncio.to_thread(
                    subprocess.run,
                    ["npm", "test", "--", "--run"],
                    cwd=str(frontend_dir),
                    capture_output=True,
                    text=True,
                    timeout=300,
                    shell=(sys.platform == "win32"),
                )
                results["frontend_output"] = proc.stdout
                results["frontend_returncode"] = proc.returncode
        except Exception as e:
            logger.error("[ERROR:%s][trace_id=%s] Frontend tests failed to run: %s", step_name, trace_id, e, exc_info=True)
            results["frontend_error"] = str(e)
            errors.append({"step": step_name, "trace_id": trace_id, "component": "frontend", "message": str(e)})

    elif test_type == "e2e":
        # End-to-end tests (Playwright)
        try:
            if (frontend_dir / "package.json").exists():
                proc = await asyncio.to_thread(
                    subprocess.run,
                    ["npx", "playwright", "test"],
                    cwd=str(frontend_dir),
                    capture_output=True,
                    text=True,
                    timeout=600,
                    shell=(sys.platform == "win32"),
                )
                results["e2e_output"] = proc.stdout
                results["e2e_returncode"] = proc.returncode
        except Exception as e:
            logger.error("[ERROR:%s][trace_id=%s] E2E tests failed: %s", step_name, trace_id, e, exc_info=True)
            results["e2e_error"] = str(e)

    elif test_type == "load":
        # Load tests (k6)
        load_test_file = repo_path / "tests" / "load" / "test.js"
        if load_test_file.exists():
            try:
                proc = await asyncio.to_thread(
                    subprocess.run,
                    ["k6", "run", str(load_test_file)],
                    cwd=str(repo_path),
                    capture_output=True,
                    text=True,
                    timeout=300,
                )
                results["load_output"] = proc.stdout
                results["load_returncode"] = proc.returncode
            except Exception as e:
                logger.error("[ERROR:%s][trace_id=%s] Load tests failed: %s", step_name, trace_id, e, exc_info=True)
                results["load_error"] = str(e)

    result_key = f"{test_type}_test_results"
    logger.info(
        "[COMPLETED:%s][trace_id=%s] Finished %s tests (passed=%s, failed=%s)",
        step_name,
        trace_id,
        test_type,
        results.get("passed", 0),
        results.get("failed", 0),
    )

    update: dict[str, Any] = {
        result_key: results,
        "current_step": step_name,
        "completed_steps": [step_name],
    }
    if errors:
        update["errors"] = errors
    return update
