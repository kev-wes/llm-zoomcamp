"""Download a subset of the official n8n documentation.

The docs live in https://github.com/n8n-io/n8n-docs (Apache 2.0 + Commons
Clause). We pin a specific commit so the dataset is reproducible, and only
keep the sections relevant for a "how do I build workflows?" assistant.

Usage:
    python ingestion/download_docs.py
"""

import io
import shutil
import zipfile
from pathlib import Path

import requests

# Pinned commit of n8n-io/n8n-docs (main branch, 2026-07-16)
COMMIT = "f83df2c6574c7a3d9aa980322a9abb5f57e4751d"
ZIP_URL = f"https://github.com/n8n-io/n8n-docs/archive/{COMMIT}.zip"

# Subset of the docs we index: core workflow-building topics
INCLUDE_DIRS = [
    "docs/build",        # code, flow logic, AI, data handling, workflow management
    "docs/get-started",  # first workflow, key concepts, glossary
]
EXCLUDE_NAMES = {"SUMMARY.md"}  # mkdocs navigation stubs

RAW_DIR = Path(__file__).parent.parent / "data" / "raw"


def main():
    print(f"Downloading n8n-docs @ {COMMIT[:12]} ...")
    resp = requests.get(ZIP_URL, timeout=120)
    resp.raise_for_status()

    if RAW_DIR.exists():
        shutil.rmtree(RAW_DIR)
    RAW_DIR.mkdir(parents=True)

    prefix = f"n8n-docs-{COMMIT}/"
    kept = 0

    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        for member in zf.namelist():
            rel = member.removeprefix(prefix)
            in_dir = any(rel.startswith(d + "/") for d in INCLUDE_DIRS)
            if not in_dir or not rel.endswith(".md"):
                continue
            if rel.rsplit("/", 1)[-1] in EXCLUDE_NAMES:
                continue

            target = RAW_DIR / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(zf.read(member))
            kept += 1

    print(f"Saved {kept} markdown files to {RAW_DIR}")


if __name__ == "__main__":
    main()
