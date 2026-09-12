#!/usr/bin/env python3
"""Run this project's OPEN SPORT demo with its prepared JSON and existing item.

    python3 run_open_sport.py --publish --fullscreen
    python3 run_open_sport.py --prepare-only

Uses the project's virtual environment when available. All additional flags are
passed to shopee_run.py; --publish is required to submit the prepared form.
"""
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parent
INPUT = ROOT / "products/jlab-open-sport-demo/persona-input.v1.json"
EXISTING_PRODUCT_ID = "43834400022"


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    interpreter = ROOT / ".venv/bin/python"
    command = [str(interpreter) if interpreter.is_file() else sys.executable,
               str(ROOT / "shopee_run.py"),
               "--input", str(INPUT),
               "--product-id", EXISTING_PRODUCT_ID,
               *args]
    try:
        return subprocess.call(command)
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
