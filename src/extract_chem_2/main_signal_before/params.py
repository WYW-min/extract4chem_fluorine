from __future__ import annotations

import argparse
from pathlib import Path

from .models import MainSignalBeforeArgs


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Build main-signal extraction inputs from doc_split jsonl "
            "without calling the model."
        )
    )
    parser.add_argument(
        "-i",
        "--inpath",
        required=True,
        help="Input doc_split jsonl path.",
    )
    parser.add_argument(
        "--out-jsonl",
        default=None,
        help="Optional output path. Defaults to sibling main_signal_before/<input_name>.jsonl.",
    )
    parser.add_argument(
        "--encoding",
        default="utf-8",
        help="Input file encoding (default: utf-8).",
    )
    return parser


def parse_args() -> MainSignalBeforeArgs:
    args = build_arg_parser().parse_args()
    return MainSignalBeforeArgs(
        inpath=Path(args.inpath),
        out_jsonl=args.out_jsonl,
        encoding=args.encoding,
    )
