from __future__ import annotations

import argparse
from pathlib import Path

from .models import PropertyAfterArgs


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Aggregate valid property_predict temp records into minimal "
            "sample-level property outputs."
        )
    )
    parser.add_argument(
        "-i",
        "--before-jsonl",
        required=True,
        help="Input property_before jsonl path.",
    )
    parser.add_argument(
        "-o",
        "--output-jsonl",
        default=None,
        help="Optional output jsonl path. Defaults to sibling property_after/<input_name>.jsonl.",
    )
    parser.add_argument(
        "-t",
        "--predict-temp-dir",
        default=None,
        help="Optional property_predict temp directory. Defaults to sibling property_predict/temp.",
    )
    parser.add_argument(
        "-e",
        "--encoding",
        default="utf-8",
        help="Input/output text encoding (default: utf-8).",
    )
    return parser


def parse_args() -> PropertyAfterArgs:
    args = build_arg_parser().parse_args()
    return PropertyAfterArgs(
        before_jsonl=Path(args.before_jsonl),
        output_jsonl=args.output_jsonl,
        predict_temp_dir=Path(args.predict_temp_dir) if args.predict_temp_dir else None,
        encoding=args.encoding,
    )
