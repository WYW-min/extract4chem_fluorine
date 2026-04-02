from __future__ import annotations

import argparse
from pathlib import Path

from .models import CharacterizationBeforeArgs


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Build characterization extraction inputs from main_signal_after jsonl "
            "without calling the model."
        )
    )
    parser.add_argument(
        "-i",
        "--inpath",
        required=True,
        help="Input main_signal_after jsonl path.",
    )
    parser.add_argument(
        "-d",
        "--doc-split-jsonl",
        default=None,
        help="Optional doc_split jsonl path. Defaults to sibling doc_split/<input_name>.jsonl.",
    )
    parser.add_argument(
        "-o",
        "--out-jsonl",
        default=None,
        help="Optional output path. Defaults to sibling characterization_before/<input_name>.jsonl.",
    )
    parser.add_argument(
        "-e",
        "--encoding",
        default="utf-8",
        help="Input file encoding (default: utf-8).",
    )
    parser.add_argument(
        "-r",
        "--result-window-lines",
        type=int,
        default=6,
        help="Context lines to include on each side of result hits (default: 6).",
    )
    return parser


def parse_args() -> CharacterizationBeforeArgs:
    args = build_arg_parser().parse_args()
    return CharacterizationBeforeArgs(
        inpath=Path(args.inpath),
        doc_split_jsonl=Path(args.doc_split_jsonl) if args.doc_split_jsonl else None,
        out_jsonl=args.out_jsonl,
        encoding=args.encoding,
        result_window_lines=max(0, args.result_window_lines),
    )
