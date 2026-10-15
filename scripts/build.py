"""Same production assets for a cloud function or Docker image."""

import shutil
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

# Vercel serves public/** through its CDN. The FastAPI function continues
# to serve API routes and the application shell independently.
dist = ROOT / "frontend" / "dist"
assets = dist / "assets"
if not (dist / "index.html").is_file() or not assets.is_dir():
    raise RuntimeError("Frontend build did not create index.html and assets")
public_assets = ROOT / "public" / "assets"
if public_assets.exists():
    shutil.rmtree(public_assets)
shutil.copytree(assets, public_assets)
print(f"Published {len(list(public_assets.rglob('*')))} frontend asset entries to public/assets")
