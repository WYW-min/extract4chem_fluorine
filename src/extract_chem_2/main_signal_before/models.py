from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class MainSignalBeforeArgs:
    inpath: Path
    out_jsonl: str | None
    encoding: str


@dataclass(frozen=True)
class MainSignalBeforePaths:
    jsonl_path: Path
    manifest_path: Path


@dataclass(frozen=True)
class MainSignalBeforeStats:
    doc_count: int
    task_count: int
    empty_experiment_count: int


@dataclass(frozen=True)
class MainSignalBeforeResult:
    run_id: str
    paths: MainSignalBeforePaths
    stats: MainSignalBeforeStats

