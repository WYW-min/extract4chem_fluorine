from __future__ import annotations

import argparse
from pathlib import Path

from .models import FinalMergeArgs


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Merge main_signal_after with characterization/property/process "
            "after outputs into final document-level jsonl."
        )
    )
    parser.add_argument(
        "-i",
        "--main-signal-jsonl",
        required=True,
        help="Input main_signal_after jsonl path.",
    )
    parser.add_argument(
        "-c",
        "--characterization-jsonl",
        default=None,
        help="Optional characterization_after jsonl path. Defaults to sibling characterization_after/<input_name>.jsonl.",
    )
    parser.add_argument(
        "-p",
        "--property-jsonl",
        default=None,
        help="Optional property_after jsonl path. Defaults to sibling property_after/<input_name>.jsonl.",
    )
    parser.add_argument(
        "-r",
        "--process-jsonl",
        default=None,
        help="Optional process_after jsonl path. Defaults to sibling process_after/<input_name>.jsonl.",
    )
    parser.add_argument(
        "-o",
        "--output-jsonl",
        default=None,
        help="Optional output jsonl path. Defaults to sibling final_merge/<input_name>.jsonl.",
    )
    parser.add_argument(
        "-e",
        "--encoding",
        default="utf-8",
        help="Input/output text encoding (default: utf-8).",
    )
    return parser


def parse_args() -> FinalMergeArgs:
    args = build_arg_parser().parse_args()
    return FinalMergeArgs(
        main_signal_jsonl=Path(args.main_signal_jsonl),
        characterization_jsonl=(
            Path(args.characterization_jsonl) if args.characterization_jsonl else None
        ),
        property_jsonl=Path(args.property_jsonl) if args.property_jsonl else None,
        process_jsonl=Path(args.process_jsonl) if args.process_jsonl else None,
        output_jsonl=args.output_jsonl,
        encoding=args.encoding,
    )

