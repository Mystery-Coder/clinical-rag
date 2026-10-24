"""Ask the pipeline from the command line."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from cdss.pipeline import consult


def main() -> None:
    parser = argparse.ArgumentParser(description="Run one CDSS consult.")
    parser.add_argument("question", nargs="?", default=None)
    parser.add_argument("--subject-id", default=None)
    parser.add_argument("--k", type=int, default=None)
    args = parser.parse_args()
    result = consult(args.question, args.subject_id, args.k)
    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
