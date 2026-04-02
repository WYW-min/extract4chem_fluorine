from __future__ import annotations

import argparse
from pathlib import Path

from .models import DocSplitArgs


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Split markdown content from raw jsonl into section-level jsonl "
            "and human-readable txt."
        )
    )
    parser.add_argument(
        "-i",
        "--inpath",
        default="data/out/聚酰亚胺/raw_20260316.jsonl",
        help="Input jsonl path. Expected fields: file_name, md5, content.",
    )
    parser.add_argument(
        "--run-id",
        default=None,
        help="Optional fixed run_id. Defaults to current timestamp in %Y%m%d%H%M%S.",
    )
    parser.add_argument(
        "--out-jsonl", default=None, help="Section-level jsonl output path."
    )
    parser.add_argument(
        "--out-human-dir",
        "--out-txt",
        dest="out_human_dir",
        default=None,
        help="Directory for human-readable chunk txt files.",
    )
    parser.add_argument(
        "--encoding",
        default="utf-8",
        help="Input file encoding (default: utf-8).",
    )
    parser.add_argument(
        "--strict-input",
        action="store_true",
        help="Require input records to contain file_name, md5, content.",
    )
    return parser


def parse_args() -> DocSplitArgs:
    args = build_arg_parser().parse_args()
    return DocSplitArgs(
        inpath=Path(args.inpath),
        run_id=args.run_id,
        out_jsonl=args.out_jsonl,
        out_human_dir=args.out_human_dir,
        encoding=args.encoding,
        strict_input=args.strict_input,
    )
