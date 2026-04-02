from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterator

from .models import DocSplitPaths, DocSplitStats


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


def resolve_output_paths(
    *,
    inpath: Path,
    run_id: str,
    out_jsonl: str | None,
    out_human_dir: str | None,
) -> DocSplitPaths:
    if out_jsonl:
        jsonl_path = Path(out_jsonl)
        split_dir = jsonl_path.parent
    else:
        split_dir = inpath.parent / run_id / "doc_split"
        jsonl_path = split_dir / inpath.name

    if out_human_dir:
        human_dir = Path(out_human_dir)
    else:
        human_dir = split_dir / "human" / inpath.stem

    manifest_path = split_dir / "manifest.json"
    jsonl_path.parent.mkdir(parents=True, exist_ok=True)
    human_dir.mkdir(parents=True, exist_ok=True)
    return DocSplitPaths(
        jsonl_path=jsonl_path,
        human_dir=human_dir,
        manifest_path=manifest_path,
    )


def write_human_chunk(
    *,
    human_dir: Path,
    file_name: str,
    doc_id: str,
    chunk_index: int,
    section: dict[str, Any],
) -> None:
    human_path = human_dir / f"{doc_id}_{chunk_index}.txt"
    start_line, end_line = section["line_span"]
    start_char, end_char = section["char_span"]
    content_lines = section["content"].splitlines()

    with human_path.open("w", encoding="utf-8") as fout:
        fout.write(f"source_file: {file_name}\n")
        fout.write(f"doc_id: {doc_id}\n")
        fout.write(f"chunk_index: {chunk_index}\n")
        fout.write(f"block_id: {section['block_id']}\n")
        fout.write(f"section_number: {section['section_number']}\n")
        fout.write(f"header_level: {section['header_level']}\n")
        fout.write(f"outline_level: {section['outline_level']}\n")
        fout.write(f"title_level: {section['title_level']}\n")
        fout.write(f"section_title: {section['section_title']}\n")
        fout.write(f"line_span: [{start_line}, {end_line}]\n")
        fout.write(f"char_span: [{start_char}, {end_char}]\n")
        fout.write(f"line_count: {len(content_lines)}\n")
        fout.write(
            "effective_body_non_empty_lines: "
            f"{section['effective_body_non_empty_lines']}\n\n"
        )
        fout.write("lines:\n")
        fout.write(f"--- chunk ({section['block_id']}: {section['section_title']}) ---\n")
        for offset, line in enumerate(content_lines, start=start_line):
            fout.write(f"{offset}: {line}\n")


def write_manifest(
    *,
    paths: DocSplitPaths,
    run_id: str,
    inpath: Path,
    created_at: str,
    stats: DocSplitStats,
) -> None:
    manifest = {
        "stage": "doc_split",
        "run_id": run_id,
        "created_at": created_at,
        "input_path": str(inpath),
        "output_path": str(paths.jsonl_path),
        "human_dir": str(paths.human_dir),
        "doc_count": stats.doc_count,
        "block_count": stats.block_count,
        "fallback_md5_count": stats.fallback_md5_count,
    }
    with paths.manifest_path.open("w", encoding="utf-8") as fout:
        json.dump(manifest, fout, ensure_ascii=False, indent=2)
        fout.write("\n")

