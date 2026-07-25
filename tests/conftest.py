import os
import sys
from pathlib import Path

# analyze_game.py requires this env var at import time.
os.environ.setdefault("LICHESS_USERNAME", "test_user")

ROOT = Path(__file__).resolve().parent.parent

# Each service directory is its own Docker build context and imports its
# siblings as bare top-level modules (e.g. report_generator.py does
# `from llm_client import call_llm`), so tests need the same layout on
# sys.path rather than treating each service as a package.
for path in (ROOT, ROOT / "engine", ROOT / "reporting", ROOT / "collectors", ROOT / "scheduler"):
    sys.path.insert(0, str(path))
