from __future__ import annotations

import json
import subprocess
from pathlib import Path

from .config import settings


def validate_csv_with_r(path: Path, timeout: int = 30) -> dict:
    script = settings.root / "r" / "validate_data.R"
    run = subprocess.run(
        ["Rscript", str(script), str(path)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=timeout,
        check=False,
    )
    if run.returncode:
        raise RuntimeError(f"R validation failed: {run.stderr.strip()}")
    return json.loads(run.stdout)
