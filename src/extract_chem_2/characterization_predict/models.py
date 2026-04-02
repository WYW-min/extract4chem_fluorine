from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CharacterizationPredictArgs:
    inpath: Path
    out_jsonl: str | None
    prompt_name: str
    prompt_dir: Path
    model_name: str
    llm_config: Path
    batch_size: int
    encoding: str
    limit: int


@dataclass(frozen=True)
class CharacterizationPredictPaths:
    stage_dir: Path
    temp_dir: Path
    jsonl_path: Path
    manifest_path: Path


@dataclass(frozen=True)
class CharacterizationPredictStats:
    total_task_count: int
    existing_done_count: int
    todo_count: int
    processed_count: int
    skipped_done_count: int
    success_count: int
    parse_error_count: int
    invoke_error_count: int


@dataclass(frozen=True)
class CharacterizationPredictResult:
    run_id: str
    paths: CharacterizationPredictPaths
    stats: CharacterizationPredictStats
