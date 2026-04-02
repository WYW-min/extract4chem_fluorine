from __future__ import annotations

import hashlib
import json
from datetime import datetime

from .models import DocSplitArgs, DocSplitResult, DocSplitStats
from .splitter import split_markdown
from .storage import parse_jsonl, resolve_output_paths, write_human_chunk, write_manifest


def make_run_id() -> str:
    return datetime.now().strftime("%Y%m%d%H%M%S")


def make_created_at() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def compute_md5(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def run_doc_split(args: DocSplitArgs) -> DocSplitResult:
    if not args.inpath.exists():
        raise FileNotFoundError(f"Input file not found: {args.inpath}")

    run_id = args.run_id or make_run_id()
    paths = resolve_output_paths(
        inpath=args.inpath,
        run_id=run_id,
        out_jsonl=args.out_jsonl,
        out_human_dir=args.out_human_dir,
    )

    doc_count = 0
    block_count = 0
    fallback_md5_count = 0

    with paths.jsonl_path.open("w", encoding="utf-8") as fout_jsonl:
        for doc_idx, record in enumerate(parse_jsonl(args.inpath, encoding=args.encoding), start=1):
            doc_count += 1
            file_name = record.get("file_name")
            content = record.get("content")
            md5_value = record.get("md5")

            if args.strict_input and (
                file_name is None or content is None or (not isinstance(md5_value, str))
            ):
                raise ValueError(
                    f"Record {doc_idx} missing required input fields "
                    "(file_name, md5, content) under --strict-input mode."
                )

            if not isinstance(file_name, str) or not file_name.strip():
                file_name = f"unknown_{doc_idx}"

            if not isinstance(content, str):
                content = "" if content is None else str(content)

            if isinstance(md5_value, str) and md5_value.strip():
                doc_id = md5_value.strip().lower()
            else:
                doc_id = compute_md5(content)
                fallback_md5_count += 1

            sections = split_markdown(content)
            block_count += len(sections)

            for section in sections:
                chunk_index = section["section_index"] - 1
                out_record = {
                    "run_id": run_id,
                    "doc_index": doc_idx,
                    "doc_id": doc_id,
                    "file_name": file_name,
                    "chunk_index": chunk_index,
                    **section,
                }
                fout_jsonl.write(json.dumps(out_record, ensure_ascii=False) + "\n")
                write_human_chunk(
                    human_dir=paths.human_dir,
                    file_name=file_name,
                    doc_id=doc_id,
                    chunk_index=chunk_index,
                    section=section,
                )

    stats = DocSplitStats(
        doc_count=doc_count,
        block_count=block_count,
        fallback_md5_count=fallback_md5_count,
    )
    write_manifest(
        paths=paths,
        run_id=run_id,
        inpath=args.inpath,
        created_at=make_created_at(),
        stats=stats,
    )
    return DocSplitResult(run_id=run_id, paths=paths, stats=stats)


def print_run_summary(result: DocSplitResult) -> None:
    print(f"run_id: {result.run_id}")
    print(
        "doc_split done: "
        f"docs={result.stats.doc_count} blocks={result.stats.block_count}"
    )
    print(f"fallback md5 count: {result.stats.fallback_md5_count}")
    print(f"jsonl: {result.paths.jsonl_path}")
    print(f"human_dir: {result.paths.human_dir}")
    print(f"manifest: {result.paths.manifest_path}")

