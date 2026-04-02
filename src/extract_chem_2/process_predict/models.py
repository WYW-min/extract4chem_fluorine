from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ProcessPredictArgs:
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
class ProcessPredictPaths:
    stage_dir: Path
    temp_dir: Path
    jsonl_path: Path
    manifest_path: Path


@dataclass(frozen=True)
class ProcessPredictStats:
    total_task_count: int
    existing_done_count: int
    todo_count: int
    processed_count: int
    skipped_done_count: int
    success_count: int
    parse_error_count: int
    invoke_error_count: int


@dataclass(frozen=True)
class ProcessPredictResult:
    run_id: str
    paths: ProcessPredictPaths
    stats: ProcessPredictStats
