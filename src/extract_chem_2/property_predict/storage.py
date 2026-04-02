from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator

from .helpers import is_task_done
from .models import PropertyPredictPaths, PropertyPredictStats


def make_created_at() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def make_now_id() -> str:
    return datetime.now().strftime("%Y%m%d%H%M%S")


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


def peek_first_record(path: Path, encoding: str) -> dict[str, Any]:
    for record in parse_jsonl(path, encoding):
        return record
    raise ValueError(f"Input jsonl has no records: {path}")


def load_tasks(path: Path, encoding: str) -> list[dict[str, Any]]:
    return list(parse_jsonl(path, encoding))


def resolve_output_paths(*, inpath: Path, out_jsonl: str | None) -> PropertyPredictPaths:
    if out_jsonl:
        jsonl_path = Path(out_jsonl)
        if jsonl_path.parent.name == "temp":
            stage_dir = jsonl_path.parent.parent
            temp_dir = jsonl_path.parent
        else:
            stage_dir = jsonl_path.parent
            temp_dir = stage_dir / "temp"
    else:
        if inpath.parent.name == "property_before":
            stage_dir = inpath.parent.parent / "property_predict"
        else:
            stage_dir = inpath.parent / "property_predict"
        temp_dir = stage_dir / "temp"
        jsonl_path = temp_dir / f"{make_now_id()}.jsonl"

    temp_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = stage_dir / "manifest.json"
    return PropertyPredictPaths(
        stage_dir=stage_dir,
        temp_dir=temp_dir,
        jsonl_path=jsonl_path,
        manifest_path=manifest_path,
    )


def collect_done_task_ids(temp_dir: Path, encoding: str, *, exclude: Path | None = None) -> set[str]:
    done_ids: set[str] = set()
    if not temp_dir.exists():
        return done_ids

    for path in sorted(temp_dir.glob("*.jsonl")):
        if exclude is not None and path.resolve() == exclude.resolve():
            continue
        for record in parse_jsonl(path, encoding, skip_invalid=True):
            if is_task_done(record):
                done_ids.add(record["task_id"])
    return done_ids


def write_manifest(
    *,
    paths: PropertyPredictPaths,
    run_id: str,
    inpath: Path,
    stats: PropertyPredictStats,
    prompt_name: str,
    model_name: str,
    llm_config: Path,
    batch_size: int,
) -> None:
    manifest = {
        "stage": "property_predict",
        "run_id": run_id,
        "created_at": make_created_at(),
        "input_path": str(inpath),
        "output_path": str(paths.jsonl_path),
        "temp_dir": str(paths.temp_dir),
        "prompt_name": prompt_name,
        "model_name": model_name,
        "llm_config": str(llm_config),
        "batch_size": batch_size,
        "total_task_count": stats.total_task_count,
        "existing_done_count": stats.existing_done_count,
        "todo_count": stats.todo_count,
        "processed_count": stats.processed_count,
        "skipped_done_count": stats.skipped_done_count,
        "success_count": stats.success_count,
        "parse_error_count": stats.parse_error_count,
        "invoke_error_count": stats.invoke_error_count,
    }
    with paths.manifest_path.open("w", encoding="utf-8") as fout:
        json.dump(manifest, fout, ensure_ascii=False, indent=2)
        fout.write("\n")
