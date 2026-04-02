from __future__ import annotations

import argparse
from pathlib import Path

from .models import MainSignalAfterArgs


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Merge main_signal_predict temp outputs and normalize them into "
            "main_signal_after jsonl."
        )
    )
    parser.add_argument(
        "-b",
        "--before-jsonl",
        required=True,
        help="Input main_signal_before jsonl path.",
    )
    parser.add_argument(
        "-t",
        "--predict-temp-dir",
        required=True,
        help="Optional main_signal_predict temp dir. Defaults to sibling main_signal_predict/temp.",
    )
    parser.add_argument(
        "--output-jsonl",
        default=None,
        help="Optional output path. Defaults to sibling main_signal_after/<input_name>.jsonl.",
    )

    parser.add_argument(
        "--encoding",
        default="utf-8",
        help="Input/output encoding (default: utf-8).",
    )
    return parser


def parse_args() -> MainSignalAfterArgs:
    args = build_arg_parser().parse_args()
    before_jsonl = args.before_jsonl
    if before_jsonl is None:
        raise SystemExit("Missing required argument: --before-jsonl")
    return MainSignalAfterArgs(
        before_jsonl=Path(before_jsonl),
        output_jsonl=args.output_jsonl,
        predict_temp_dir=(
            None if args.predict_temp_dir is None else Path(args.predict_temp_dir)
        ),
        encoding=args.encoding,
    )
