"""Download version-pinned weights during setup/build, never during a user request."""

import hashlib
import json
import os
import shutil
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DESTINATION = Path(os.getenv("MODEL_DIR", ROOT / "models"))
MODELS = {
    "embedding": (
        "minishlab/potion-base-8M",
        "bf8b056651a2c21b8d2565580b8569da283cab23",
        ["config.json", "tokenizer.json", "model.safetensors"],
    ),
    "reranker": (
        "Xenova/ms-marco-TinyBERT-L-2-v2",
        "b76bb5e1fefd66aa36cd108622d768e86c015ff1",
        ["config.json", "tokenizer.json", "onnx/model_quantized.onnx"],
    ),
    "verifier": (
        "Xenova/nli-deberta-v3-xsmall",
        "2a4f614a701367a02d51389039afc998faeda637",
        ["config.json", "tokenizer.json", "onnx/model_quantized.onnx"],
    ),
}


def download(item):
    name, repo, revision, filename = item
    target = DESTINATION / name / Path(filename).name
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        url = f"https://huggingface.co/{repo}/resolve/{revision}/{filename}"
        for attempt in range(3):
            try:
                with (
                    urllib.request.urlopen(url, timeout=60) as response,
                    target.with_suffix(".part").open("wb") as out,
                ):
                    shutil.copyfileobj(response, out)
                target.with_suffix(".part").replace(target)
                break
            except Exception:
                if attempt == 2:
                    raise
                time.sleep(1 + attempt)
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    print(f"Ready: {name}/{target.name} ({target.stat().st_size:,} bytes)", flush=True)
    return {
        "path": f"{name}/{target.name}",
        "repository": repo,
        "revision": revision,
        "sha256": digest,
    }


if __name__ == "__main__":
    tasks = [
        (name, repo, revision, filename)
        for name, (repo, revision, files) in MODELS.items()
        for filename in files
    ]
    with ThreadPoolExecutor(max_workers=3) as executor:
        manifest = list(executor.map(download, tasks))
    (DESTINATION / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
