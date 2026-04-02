from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class MainSignalAfterArgs:
    before_jsonl: Path
    output_jsonl: str | None
    predict_temp_dir: Path | None
    encoding: str


@dataclass(frozen=True)
class MainSignalAfterPaths:
    stage_dir: Path
    jsonl_path: Path
    manifest_path: Path
    predict_temp_dir: Path


@dataclass(frozen=True)
class MainSignalAfterStats:
    total_task_count: int
    good_predict_count: int
    written_count: int
    missing_predict_count: int


@dataclass(frozen=True)
class MainSignalAfterResult:
    run_id: str
    paths: MainSignalAfterPaths
    stats: MainSignalAfterStats
