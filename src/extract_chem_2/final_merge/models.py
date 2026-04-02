from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class FinalMergeArgs:
    main_signal_jsonl: Path
    characterization_jsonl: Path | None
    property_jsonl: Path | None
    process_jsonl: Path | None
    output_jsonl: str | None
    encoding: str


@dataclass(frozen=True)
class FinalMergePaths:
    stage_dir: Path
    jsonl_path: Path
    manifest_path: Path
    main_signal_jsonl: Path
    characterization_jsonl: Path
    property_jsonl: Path
    process_jsonl: Path


@dataclass(frozen=True)
class FinalMergeStats:
    total_doc_count: int
    total_polymer_count: int
    characterization_record_count: int
    property_record_count: int
    process_record_count: int
    matched_characterization_count: int
    matched_property_count: int
    matched_process_count: int
    written_count: int


@dataclass(frozen=True)
class FinalMergeResult:
    run_id: str
    paths: FinalMergePaths
    stats: FinalMergeStats

