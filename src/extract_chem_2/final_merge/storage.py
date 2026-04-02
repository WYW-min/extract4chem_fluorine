from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator

from .models import FinalMergePaths, FinalMergeStats


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


def infer_sibling_jsonl(main_signal_jsonl: Path, stage_name: str) -> Path:
    if main_signal_jsonl.parent.name == "main_signal_after":
        return main_signal_jsonl.parent.parent / stage_name / main_signal_jsonl.name
    return main_signal_jsonl.parent / stage_name / main_signal_jsonl.name


def resolve_output_paths(
    *,
    main_signal_jsonl: Path,
    characterization_jsonl: Path | None,
    property_jsonl: Path | None,
    process_jsonl: Path | None,
    output_jsonl: str | None,
) -> FinalMergePaths:
    if output_jsonl:
        jsonl_path = Path(output_jsonl)
        stage_dir = jsonl_path.parent
    else:
        if main_signal_jsonl.parent.name == "main_signal_after":
            stage_dir = main_signal_jsonl.parent.parent / "final_merge"
        else:
            stage_dir = main_signal_jsonl.parent / "final_merge"
        jsonl_path = stage_dir / main_signal_jsonl.name

    stage_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = stage_dir / "manifest.json"
    return FinalMergePaths(
        stage_dir=stage_dir,
        jsonl_path=jsonl_path,
        manifest_path=manifest_path,
        main_signal_jsonl=main_signal_jsonl,
        characterization_jsonl=characterization_jsonl or infer_sibling_jsonl(main_signal_jsonl, "characterization_after"),
        property_jsonl=property_jsonl or infer_sibling_jsonl(main_signal_jsonl, "property_after"),
        process_jsonl=process_jsonl or infer_sibling_jsonl(main_signal_jsonl, "process_after"),
    )


def write_manifest(
    *,
    paths: FinalMergePaths,
    run_id: str,
    stats: FinalMergeStats,
) -> None:
    manifest = {
        "stage": "final_merge",
        "run_id": run_id,
        "created_at": make_created_at(),
        "main_signal_jsonl_path": str(paths.main_signal_jsonl),
        "characterization_jsonl_path": str(paths.characterization_jsonl),
        "characterization_exists": paths.characterization_jsonl.exists(),
        "property_jsonl_path": str(paths.property_jsonl),
        "property_exists": paths.property_jsonl.exists(),
        "process_jsonl_path": str(paths.process_jsonl),
        "process_exists": paths.process_jsonl.exists(),
        "output_jsonl_path": str(paths.jsonl_path),
        "total_doc_count": stats.total_doc_count,
        "total_polymer_count": stats.total_polymer_count,
        "characterization_record_count": stats.characterization_record_count,
        "property_record_count": stats.property_record_count,
        "process_record_count": stats.process_record_count,
        "matched_characterization_count": stats.matched_characterization_count,
        "matched_property_count": stats.matched_property_count,
        "matched_process_count": stats.matched_process_count,
        "written_count": stats.written_count,
    }
    with paths.manifest_path.open("w", encoding="utf-8") as fout:
        json.dump(manifest, fout, ensure_ascii=False, indent=2)
        fout.write("\n")

