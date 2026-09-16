# Author: C A B M
# Date: 2026-09-17

"""Build and test tools for .NET and Node.js projects.

Provides subprocess wrappers for building and testing the backend (.NET)
and frontend (Node.js) components of the target repository.
"""

from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class BuildResult:
    """Result from a build operation."""

    success: bool
    output: str
    errors: str
    return_code: int


@dataclass
class TestResult:
    """Result from a test execution."""

    success: bool
    output: str
    passed: int
    failed: int
    skipped: int
    return_code: int


def dotnet_build(project_path: str | Path, configuration: str = "Debug") -> BuildResult:
    """Build a .NET solution or project.

    Args:
        project_path: Path to .sln or .csproj file, or directory containing one.
        configuration: Build configuration (Debug/Release).

    Returns:
        BuildResult with success status and output.
    """
    path = Path(project_path)
    cmd = ["dotnet", "build", "--configuration", configuration, "--no-restore"]
    logger.info("Running .NET build: %s in %s", " ".join(cmd), path)

    try:
        proc = subprocess.run(
            cmd, cwd=str(path), capture_output=True, text=True, timeout=300,
        )
        logger.info(".NET build completed with returncode %d (success=%s)", proc.returncode, proc.returncode == 0)
        return BuildResult(
            success=proc.returncode == 0,
            output=proc.stdout,
            errors=proc.stderr,
            return_code=proc.returncode,
        )
    except subprocess.TimeoutExpired:
        logger.error(".NET build timed out after 300s at %s", path)
        return BuildResult(success=False, output="", errors="Build timed out (300s)", return_code=-1)
    except FileNotFoundError:
        logger.error("dotnet CLI not found on system path")
        return BuildResult(success=False, output="", errors="dotnet CLI not found", return_code=-1)
    except Exception as e:
        logger.error("Unexpected error during .NET build at %s: %s", path, e, exc_info=True)
        return BuildResult(success=False, output="", errors=str(e), return_code=-1)


def dotnet_test(project_path: str | Path, filter_expr: str = "") -> TestResult:
    """Run .NET tests.

    Args:
        project_path: Path to test project or solution.
        filter_expr: Optional test filter expression.

    Returns:
        TestResult with pass/fail counts.
    """
    path = Path(project_path)
    cmd = ["dotnet", "test", "--no-build", "--verbosity", "minimal"]
    if filter_expr:
        cmd.extend(["--filter", filter_expr])
    logger.info("Running .NET tests: %s in %s", " ".join(cmd), path)

    try:
        proc = subprocess.run(
            cmd, cwd=str(path), capture_output=True, text=True, timeout=600,
        )
        output = proc.stdout

        # Parse test counts from output
        passed = _extract_count(output, "Passed")
        failed = _extract_count(output, "Failed")
        skipped = _extract_count(output, "Skipped")
        logger.info(".NET tests finished: passed=%d, failed=%d, skipped=%d (code=%d)", passed, failed, skipped, proc.returncode)

        return TestResult(
            success=proc.returncode == 0,
            output=output,
            passed=passed,
            failed=failed,
            skipped=skipped,
            return_code=proc.returncode,
        )
    except subprocess.TimeoutExpired:
        logger.error(".NET tests timed out after 600s at %s", path)
        return TestResult(success=False, output="Test timed out (600s)", passed=0, failed=0, skipped=0, return_code=-1)
    except FileNotFoundError:
        logger.error("dotnet CLI not found for running tests")
        return TestResult(success=False, output="dotnet CLI not found", passed=0, failed=0, skipped=0, return_code=-1)
    except Exception as e:
        logger.error("Unexpected error running .NET tests at %s: %s", path, e, exc_info=True)
        return TestResult(success=False, output=str(e), passed=0, failed=0, skipped=0, return_code=-1)


def npm_build(frontend_path: str | Path) -> BuildResult:
    """Build the Next.js frontend.

    Args:
        frontend_path: Path to the frontend directory.

    Returns:
        BuildResult with success status.
    """
    path = Path(frontend_path)
    logger.info("Running frontend npm build in %s...", path)
    try:
        proc = subprocess.run(
            ["npm", "run", "build"],
            cwd=str(path), capture_output=True, text=True, timeout=300,
            shell=True,  # Required on Windows for npm
        )
        logger.info("npm build finished with returncode %d (success=%s)", proc.returncode, proc.returncode == 0)
        return BuildResult(
            success=proc.returncode == 0,
            output=proc.stdout,
            errors=proc.stderr,
            return_code=proc.returncode,
        )
    except subprocess.TimeoutExpired:
        logger.error("npm build timed out after 300s at %s", path)
        return BuildResult(success=False, output="", errors="Build timed out (300s)", return_code=-1)
    except FileNotFoundError:
        logger.error("npm CLI not found on system path")
        return BuildResult(success=False, output="", errors="npm not found", return_code=-1)
    except Exception as e:
        logger.error("Unexpected error during npm build at %s: %s", path, e, exc_info=True)
        return BuildResult(success=False, output="", errors=str(e), return_code=-1)


def npm_test(frontend_path: str | Path) -> TestResult:
    """Run frontend tests with Vitest.

    Args:
        frontend_path: Path to the frontend directory.

    Returns:
        TestResult with pass/fail counts.
    """
    path = Path(frontend_path)
    logger.info("Running frontend npm test in %s...", path)
    try:
        proc = subprocess.run(
            ["npm", "test", "--", "--run"],
            cwd=str(path), capture_output=True, text=True, timeout=300,
            shell=True,
        )
        output = proc.stdout
        passed = _extract_count(output, "passed")
        failed = _extract_count(output, "failed")
        logger.info("npm test finished: passed=%d, failed=%d (code=%d)", passed, failed, proc.returncode)

        return TestResult(
            success=proc.returncode == 0,
            output=output,
            passed=passed,
            failed=failed,
            skipped=0,
            return_code=proc.returncode,
        )
    except subprocess.TimeoutExpired:
        logger.error("npm test timed out after 300s at %s", path)
        return TestResult(success=False, output="Test timed out", passed=0, failed=0, skipped=0, return_code=-1)
    except FileNotFoundError:
        logger.error("npm CLI not found for running tests")
        return TestResult(success=False, output="npm not found", passed=0, failed=0, skipped=0, return_code=-1)
    except Exception as e:
        logger.error("Unexpected error running npm tests at %s: %s", path, e, exc_info=True)
        return TestResult(success=False, output=str(e), passed=0, failed=0, skipped=0, return_code=-1)


def npm_lint(frontend_path: str | Path) -> BuildResult:
    """Run ESLint on the frontend.

    Args:
        frontend_path: Path to the frontend directory.

    Returns:
        BuildResult with lint results.
    """
    path = Path(frontend_path)
    logger.info("Running npm lint in %s...", path)
    try:
        proc = subprocess.run(
            ["npm", "run", "lint"],
            cwd=str(path), capture_output=True, text=True, timeout=120,
            shell=True,
        )
        logger.info("npm lint completed with returncode %d", proc.returncode)
        return BuildResult(
            success=proc.returncode == 0,
            output=proc.stdout,
            errors=proc.stderr,
            return_code=proc.returncode,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        logger.error("npm lint failed: %s", e)
        return BuildResult(success=False, output="", errors=str(e), return_code=-1)
    except Exception as e:
        logger.error("Unexpected error during npm lint at %s: %s", path, e, exc_info=True)
        return BuildResult(success=False, output="", errors=str(e), return_code=-1)


def playwright_test(frontend_path: str | Path, spec: str = "") -> TestResult:
    """Run Playwright E2E tests.

    Args:
        frontend_path: Path to the frontend directory.
        spec: Optional specific test spec to run.

    Returns:
        TestResult with pass/fail counts.
    """
    path = Path(frontend_path)
    cmd = ["npx", "playwright", "test"]
    if spec:
        cmd.append(spec)
    logger.info("Running Playwright tests: %s in %s...", " ".join(cmd), path)

    try:
        proc = subprocess.run(
            cmd, cwd=str(path), capture_output=True, text=True, timeout=600,
            shell=True,
        )
        output = proc.stdout
        passed = _extract_count(output, "passed")
        failed = _extract_count(output, "failed")
        logger.info("Playwright finished: passed=%d, failed=%d (code=%d)", passed, failed, proc.returncode)

        return TestResult(
            success=proc.returncode == 0,
            output=output,
            passed=passed,
            failed=failed,
            skipped=0,
            return_code=proc.returncode,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        logger.error("Playwright test failed: %s", e)
        return TestResult(success=False, output=str(e), passed=0, failed=0, skipped=0, return_code=-1)
    except Exception as e:
        logger.error("Unexpected error running Playwright tests at %s: %s", path, e, exc_info=True)
        return TestResult(success=False, output=str(e), passed=0, failed=0, skipped=0, return_code=-1)


def _extract_count(output: str, label: str) -> int:
    """Extract a numeric count from test output.

    Args:
        output: Test runner output text.
        label: Label to search for (e.g., 'Passed', 'Failed').

    Returns:
        Extracted count, or 0 if not found.
    """
    import re
    match = re.search(rf"(\d+)\s+{label}", output, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return 0
