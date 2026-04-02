from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CharacterizationAfterArgs:
    before_jsonl: Path
    output_jsonl: str | None
    predict_temp_dir: Path | None
    encoding: str


@dataclass(frozen=True)
class CharacterizationAfterPaths:
    stage_dir: Path
    jsonl_path: Path
    manifest_path: Path
    predict_temp_dir: Path


@dataclass(frozen=True)
class CharacterizationAfterStats:
    total_task_count: int
    good_predict_record_count: int
    matched_task_count: int
    written_count: int
    merged_duplicate_count: int
    missing_predict_count: int


@dataclass(frozen=True)
class CharacterizationAfterResult:
    run_id: str
    paths: CharacterizationAfterPaths
    stats: CharacterizationAfterStats

