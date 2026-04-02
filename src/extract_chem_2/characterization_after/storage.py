from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator

from .models import CharacterizationAfterPaths, CharacterizationAfterStats


def make_created_at() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def parse_jsonl(path: Path, encoding: str, *, skip_invalid: bool = False) -> Iterator[dict[str, Any]]:
    with path.open("r", encoding=encoding) as fin:
        for line_no, line in enumerate(fin, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                yield json.loads(stripped)
            except json.JSONDecodeError:
                if skip_invalid:
                    continue
                raise ValueError(f"Invalid JSON at line {line_no} in {path}")


def load_jsonl(path: Path, encoding: str) -> list[dict[str, Any]]:
    return list(parse_jsonl(path, encoding))


def peek_first_record(path: Path, encoding: str) -> dict[str, Any]:
    for record in parse_jsonl(path, encoding):
        return record
    raise ValueError(f"Input jsonl has no records: {path}")


def resolve_output_paths(
    *,
    before_jsonl: Path,
    output_jsonl: str | None,
    predict_temp_dir: Path | None,
) -> CharacterizationAfterPaths:
    if output_jsonl:
        jsonl_path = Path(output_jsonl)
        stage_dir = jsonl_path.parent
    else:
        if before_jsonl.parent.name == "characterization_before":
            stage_dir = before_jsonl.parent.parent / "characterization_after"
        else:
            stage_dir = before_jsonl.parent / "characterization_after"
        jsonl_path = stage_dir / before_jsonl.name

    if predict_temp_dir is not None:
        temp_dir = predict_temp_dir
    elif before_jsonl.parent.name == "characterization_before":
        temp_dir = before_jsonl.parent.parent / "characterization_predict" / "temp"
    else:
        temp_dir = before_jsonl.parent / "characterization_predict" / "temp"

    stage_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = stage_dir / "manifest.json"
    return CharacterizationAfterPaths(
        stage_dir=stage_dir,
        jsonl_path=jsonl_path,
        manifest_path=manifest_path,
        predict_temp_dir=temp_dir,
    )


def iter_predict_records(temp_dir: Path, encoding: str) -> Iterator[dict[str, Any]]:
    if not temp_dir.exists():
        return
    for path in sorted(temp_dir.glob("*.jsonl")):
        yield from parse_jsonl(path, encoding, skip_invalid=True)


def write_manifest(
    *,
    paths: CharacterizationAfterPaths,
    run_id: str,
    before_jsonl: Path,
    stats: CharacterizationAfterStats,
) -> None:
    manifest = {
        "stage": "characterization_after",
        "run_id": run_id,
        "created_at": make_created_at(),
        "before_jsonl_path": str(before_jsonl),
        "predict_temp_dir": str(paths.predict_temp_dir),
        "output_jsonl_path": str(paths.jsonl_path),
        "total_task_count": stats.total_task_count,
        "good_predict_record_count": stats.good_predict_record_count,
        "matched_task_count": stats.matched_task_count,
        "written_count": stats.written_count,
        "merged_duplicate_count": stats.merged_duplicate_count,
        "missing_predict_count": stats.missing_predict_count,
    }
    with paths.manifest_path.open("w", encoding="utf-8") as fout:
        json.dump(manifest, fout, ensure_ascii=False, indent=2)
        fout.write("\n")

