"""Same production assets for a cloud function or Docker image."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
subprocess.run([sys.executable, str(ROOT / "scripts/download_models.py")], check=True, cwd=ROOT)
subprocess.run(
    ["npm", "ci", "--prefix", "frontend", "--no-audit", "--no-fund"],
    check=True,
    cwd=ROOT,
)
subprocess.run(["npm", "run", "build", "--prefix", "frontend"], check=True, cwd=ROOT)
