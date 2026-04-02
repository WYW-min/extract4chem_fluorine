from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PropertyBeforeArgs:
    inpath: Path
    doc_split_jsonl: Path | None
    out_jsonl: str | None
    encoding: str
    result_window_lines: int


@dataclass(frozen=True)
class PropertyBeforePaths:
    jsonl_path: Path
    manifest_path: Path
    doc_split_jsonl_path: Path


@dataclass(frozen=True)
class PropertyBeforeStats:
    doc_count: int
    task_count: int
    empty_context_count: int
    no_method_match_count: int
    no_result_match_count: int
    result_fallback_count: int


@dataclass(frozen=True)
class PropertyBeforeResult:
    run_id: str
    paths: PropertyBeforePaths
    stats: PropertyBeforeStats
