#!/usr/bin/env python3
"""Run from a repository checkout; see data/egvqa/README.md."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
try:
    from egvqa_subset import main
except ModuleNotFoundError as exc:
    if exc.name != "requests":
        raise
    raise SystemExit("缺少 requests；请运行 python -m pip install -r data/egvqa/requirements.txt") from None

if __name__ == "__main__":
    raise SystemExit(main())
