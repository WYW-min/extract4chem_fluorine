from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DocSplitArgs:
    inpath: Path
    run_id: str | None
    out_jsonl: str | None
    out_human_dir: str | None
    encoding: str
    strict_input: bool


@dataclass(frozen=True)
class DocSplitPaths:
    jsonl_path: Path
    human_dir: Path
    manifest_path: Path


@dataclass(frozen=True)
class DocSplitStats:
    doc_count: int
    block_count: int
    fallback_md5_count: int


@dataclass(frozen=True)
class DocSplitResult:
    run_id: str
    paths: DocSplitPaths
    stats: DocSplitStats

