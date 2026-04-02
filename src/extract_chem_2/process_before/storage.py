from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator

from .models import ProcessBeforePaths, ProcessBeforeStats


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


def load_jsonl(path: Path, encoding: str) -> list[dict[str, Any]]:
    return list(parse_jsonl(path, encoding))


def peek_first_record(path: Path, encoding: str) -> dict[str, Any]:
    for record in parse_jsonl(path, encoding):
        return record
    raise ValueError(f"Input jsonl has no records: {path}")


def group_doc_split_sections(path: Path, encoding: str) -> dict[str, list[dict[str, Any]]]:
    doc_sections: dict[str, list[dict[str, Any]]] = {}
    for record in parse_jsonl(path, encoding):
        doc_id = record.get("doc_id")
        if not isinstance(doc_id, str) or not doc_id:
            raise ValueError(f"Missing doc_id in doc_split record: {path}")
        doc_sections.setdefault(doc_id, []).append(record)

    for sections in doc_sections.values():
        sections.sort(key=lambda item: item["chunk_index"])
    return doc_sections


def resolve_output_paths(
    *,
    inpath: Path,
    doc_split_jsonl: Path | None,
    out_jsonl: str | None,
) -> ProcessBeforePaths:
    if out_jsonl:
        jsonl_path = Path(out_jsonl)
        stage_dir = jsonl_path.parent
    else:
        if inpath.parent.name == "main_signal_after":
            stage_dir = inpath.parent.parent / "process_before"
        else:
            stage_dir = inpath.parent / "process_before"
        jsonl_path = stage_dir / inpath.name

    if doc_split_jsonl is not None:
        split_path = doc_split_jsonl
    elif inpath.parent.name == "main_signal_after":
        split_path = inpath.parent.parent / "doc_split" / inpath.name
    else:
        split_path = inpath.parent / "doc_split" / inpath.name

    stage_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = stage_dir / "manifest.json"
    return ProcessBeforePaths(
        jsonl_path=jsonl_path,
        manifest_path=manifest_path,
        doc_split_jsonl_path=split_path,
    )


def write_manifest(
    *,
    paths: ProcessBeforePaths,
    run_id: str,
    inpath: Path,
    stats: ProcessBeforeStats,
    routing_config_path: str | None = None,
) -> None:
    manifest = {
        "stage": "process_before",
        "run_id": run_id,
        "created_at": make_created_at(),
        "input_path": str(inpath),
        "doc_split_jsonl_path": str(paths.doc_split_jsonl_path),
        "output_path": str(paths.jsonl_path),
        "doc_count": stats.doc_count,
        "task_count": stats.task_count,
        "empty_context_count": stats.empty_context_count,
        "no_method_match_count": stats.no_method_match_count,
        "no_support_match_count": stats.no_support_match_count,
        "method_fallback_count": stats.method_fallback_count,
    }
    if routing_config_path is not None:
        manifest["routing_config_path"] = routing_config_path
    with paths.manifest_path.open("w", encoding="utf-8") as fout:
        json.dump(manifest, fout, ensure_ascii=False, indent=2)
        fout.write("\n")
