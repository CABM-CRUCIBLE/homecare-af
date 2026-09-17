# Author: C A B M
# Date: 2026-09-17

"""Root entrypoint script delegating to the HomeCare Agent CLI."""

import sys
from pathlib import Path

# Ensure src directory is on pythonpath for direct script execution
sys.path.insert(0, str(Path(__file__).parent / "src"))

from homecare_agent.main import app

if __name__ == "__main__":
    app()
