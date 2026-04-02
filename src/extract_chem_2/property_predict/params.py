from __future__ import annotations

import argparse
from pathlib import Path

from .models import PropertyPredictArgs


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_PROMPT_DIR = REPO_ROOT / "prompts" / "extract_chem_2"
DEFAULT_LLM_CONFIG = REPO_ROOT / "configs" / "llm.toml"


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run property model prediction from property_before jsonl "
            "and write raw structured outputs into property_predict/temp."
        )
    )
    parser.add_argument(
        "-i", "--inpath", required=True, help="Input property_before jsonl path."
    )
    parser.add_argument(
        "-o",
        "--out-jsonl",
        default=None,
        help="Optional output path. Defaults to sibling property_predict/temp/<timestamp>.jsonl.",
    )
    parser.add_argument(
        "-p",
        "--prompt-name",
        default="property",
        help="Prompt name inside prompt-dir (default: property).",
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


def parse_args() -> PropertyPredictArgs:
    args = build_arg_parser().parse_args()
    if args.batch_size <= 0:
        raise ValueError("--batch-size must be positive")
    if args.limit < 0:
        raise ValueError("--limit must be >= 0")
    return PropertyPredictArgs(
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
