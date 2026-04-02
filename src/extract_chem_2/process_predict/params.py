from __future__ import annotations

import argparse
from pathlib import Path

from .models import ProcessPredictArgs


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_PROMPT_DIR = REPO_ROOT / "prompts" / "extract_chem_2"
DEFAULT_LLM_CONFIG = REPO_ROOT / "configs" / "llm.toml"


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run process model prediction from process_before jsonl "
            "and write raw structured outputs into process_predict/temp."
        )
    )
    parser.add_argument(
        "-i", "--inpath", required=True, help="Input process_before jsonl path."
    )
    parser.add_argument(
        "-o",
        "--out-jsonl",
        default=None,
        help="Optional output path. Defaults to sibling process_predict/temp/<timestamp>.jsonl.",
    )
    parser.add_argument(
        "-p",
        "--prompt-name",
        default="process",
        help="Prompt name inside prompt-dir (default: process).",
    )
    parser.add_argument(
        "--prompt-dir",
        default=str(DEFAULT_PROMPT_DIR),
        help=f"Prompt directory path (default: {DEFAULT_PROMPT_DIR}).",
    )
    parser.add_argument(
        "-m",
        "--model-name",
        default="gpt-low",
        help="Model name from configs/llm.toml (default: gpt-low).",
    )
    parser.add_argument(
        "--llm-config",
        default=str(DEFAULT_LLM_CONFIG),
        help=f"LLM TOML config path (default: {DEFAULT_LLM_CONFIG}).",
    )
    parser.add_argument(
        "-b",
        "--batch-size",
        type=int,
        default=20,
        help="Concurrent batch size for model calls (default: 20).",
    )
    parser.add_argument(
        "-e",
        "--encoding",
        default="utf-8",
        help="Input/output text encoding (default: utf-8).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Maximum number of tasks to process after resume filtering; 0 means no limit.",
    )
    return parser


def parse_args() -> ProcessPredictArgs:
    args = build_arg_parser().parse_args()
    if args.batch_size <= 0:
        raise ValueError("--batch-size must be positive")
    if args.limit < 0:
        raise ValueError("--limit must be >= 0")
    return ProcessPredictArgs(
        inpath=Path(args.inpath),
        out_jsonl=args.out_jsonl,
        prompt_name=args.prompt_name,
        prompt_dir=Path(args.prompt_dir),
        model_name=args.model_name,
        llm_config=Path(args.llm_config),
        batch_size=args.batch_size,
        encoding=args.encoding,
        limit=args.limit,
    )
