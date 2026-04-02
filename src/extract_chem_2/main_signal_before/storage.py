from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator

from .models import MainSignalBeforePaths, MainSignalBeforeStats


def make_created_at() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def parse_jsonl(path: Path, encoding: str) -> Iterator[dict[str, Any]]:
    with path.open("r", encoding=encoding) as fin:
        for line_no, line in enumerate(fin, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                yield json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON at line {line_no} in {path}") from exc


def peek_first_record(path: Path, encoding: str) -> dict[str, Any]:
    for record in parse_jsonl(path, encoding):
        return record
    raise ValueError(f"Input jsonl has no records: {path}")


def iter_doc_groups(path: Path, encoding: str) -> Iterator[tuple[dict[str, Any], list[dict[str, Any]]]]:
    current_meta: dict[str, Any] | None = None
    current_sections: list[dict[str, Any]] = []

    for record in parse_jsonl(path, encoding):
        key = (record["run_id"], record["doc_id"])
        if current_meta is None:
            current_meta = {
                "run_id": record["run_id"],
                "doc_id": record["doc_id"],
                "file_name": record["file_name"],
            }
            current_sections = [record]
            continue

        current_key = (current_meta["run_id"], current_meta["doc_id"])
        if key != current_key:
            yield current_meta, current_sections
            current_meta = {
                "run_id": record["run_id"],
                "doc_id": record["doc_id"],
                "file_name": record["file_name"],
            }
            current_sections = [record]
            continue

        current_sections.append(record)

    if current_meta is not None:
        yield current_meta, current_sections


def resolve_output_paths(
    *,
    inpath: Path,
    run_id: str,
    out_jsonl: str | None,
) -> MainSignalBeforePaths:
    if out_jsonl:
        jsonl_path = Path(out_jsonl)
        stage_dir = jsonl_path.parent
    else:
        if inpath.parent.name == "doc_split":
            stage_dir = inpath.parent.parent / "main_signal_before"
        else:
            stage_dir = inpath.parent / "main_signal_before"
        jsonl_path = stage_dir / inpath.name

    manifest_path = stage_dir / "manifest.json"
    jsonl_path.parent.mkdir(parents=True, exist_ok=True)
    return MainSignalBeforePaths(jsonl_path=jsonl_path, manifest_path=manifest_path)


def write_manifest(
    *,
    paths: MainSignalBeforePaths,
    run_id: str,
    inpath: Path,
    stats: MainSignalBeforeStats,
) -> None:
    manifest = {
        "stage": "main_signal_before",
        "run_id": run_id,
        "created_at": make_created_at(),
        "input_path": str(inpath),
        "output_path": str(paths.jsonl_path),
        "doc_count": stats.doc_count,
        "task_count": stats.task_count,
        "empty_experiment_count": stats.empty_experiment_count,
    }
    with paths.manifest_path.open("w", encoding="utf-8") as fout:
        json.dump(manifest, fout, ensure_ascii=False, indent=2)
        fout.write("\n")

