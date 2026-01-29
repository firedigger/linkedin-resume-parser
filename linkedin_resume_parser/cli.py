from __future__ import annotations

import argparse
import json
from pathlib import Path

from .parser import parse_pdf


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Parse a LinkedIn profile PDF into JSON Resume schema."
    )
    parser.add_argument("pdf", type=Path, help="Path to LinkedIn PDF")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("resume.json"),
        help="Output JSON file path",
    )
    return parser


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()
    resume = parse_pdf(str(args.pdf))
    args.output.write_text(json.dumps(resume, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
