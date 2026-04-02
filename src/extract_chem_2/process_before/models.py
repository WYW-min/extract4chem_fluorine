from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ProcessBeforeArgs:
    inpath: Path
    doc_split_jsonl: Path | None
    out_jsonl: str | None
    encoding: str


@dataclass(frozen=True)
class ProcessBeforePaths:
    jsonl_path: Path
    manifest_path: Path
    doc_split_jsonl_path: Path


@dataclass(frozen=True)
class ProcessBeforeStats:
    doc_count: int
    task_count: int
    empty_context_count: int
    no_method_match_count: int
    no_support_match_count: int
    method_fallback_count: int


@dataclass(frozen=True)
class ProcessBeforeResult:
    run_id: str
    paths: ProcessBeforePaths
    stats: ProcessBeforeStats
