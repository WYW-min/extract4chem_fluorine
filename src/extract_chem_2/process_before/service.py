from __future__ import annotations

import json

from .builder import CONFIG_PATH, build_process_task
from .models import ProcessBeforeArgs, ProcessBeforeResult, ProcessBeforeStats
from .storage import (
    group_doc_split_sections,
    load_jsonl,
    peek_first_record,
    resolve_output_paths,
    write_manifest,
)


def run_process_before(args: ProcessBeforeArgs) -> ProcessBeforeResult:
    if not args.inpath.exists():
        raise FileNotFoundError(f"Input file not found: {args.inpath}")

    first_record = peek_first_record(args.inpath, args.encoding)
    run_id = first_record.get("run_id")
    if not isinstance(run_id, str) or not run_id:
        raise ValueError(f"Missing run_id in main_signal_after record: {args.inpath}")

    paths = resolve_output_paths(
        inpath=args.inpath,
        doc_split_jsonl=args.doc_split_jsonl,
        out_jsonl=args.out_jsonl,
    )
    if not paths.doc_split_jsonl_path.exists():
        raise FileNotFoundError(f"doc_split jsonl not found: {paths.doc_split_jsonl_path}")

    after_records = load_jsonl(args.inpath, args.encoding)
    doc_split_map = group_doc_split_sections(paths.doc_split_jsonl_path, args.encoding)

    doc_count = 0
    task_count = 0
    empty_context_count = 0
    no_method_match_count = 0
    no_support_match_count = 0
    method_fallback_count = 0

    with paths.jsonl_path.open("w", encoding="utf-8") as fout:
        for record in after_records:
            doc_id = record.get("doc_id")
            if not isinstance(doc_id, str) or not doc_id:
                raise ValueError(f"Missing doc_id in main_signal_after record: {args.inpath}")
            sections = doc_split_map.get(doc_id)
            if not sections:
                raise ValueError(f"Missing doc_split sections for doc_id={doc_id} in {paths.doc_split_jsonl_path}")

            result = record.get("result")
            if not isinstance(result, dict):
                raise ValueError(f"Missing result object in main_signal_after record: doc_id={doc_id}")
            polymers = result.get("聚合物")
            if not isinstance(polymers, list):
                raise ValueError(f"Missing 聚合物 array in main_signal_after record: doc_id={doc_id}")

            doc_count += 1
            for polymer_index, polymer in enumerate(polymers, start=1):
                if not isinstance(polymer, dict):
                    continue
                task = build_process_task(
                    run_id=record["run_id"],
                    doc_id=doc_id,
                    file_name=record.get("file_name") or "",
                    polymer=polymer,
                    polymer_index=polymer_index,
                    sections=sections,
                )
                route_stats = task["route_stats"]
                if route_stats["method_excerpt_count"] == 0:
                    no_method_match_count += 1
                if route_stats["support_excerpt_count"] == 0:
                    no_support_match_count += 1
                if route_stats["used_method_fallback"]:
                    method_fallback_count += 1
                if route_stats["method_excerpt_count"] == 0 and route_stats["support_excerpt_count"] == 0:
                    empty_context_count += 1
                task_count += 1
                fout.write(json.dumps(task, ensure_ascii=False) + "\n")

    stats = ProcessBeforeStats(
        doc_count=doc_count,
        task_count=task_count,
        empty_context_count=empty_context_count,
        no_method_match_count=no_method_match_count,
        no_support_match_count=no_support_match_count,
        method_fallback_count=method_fallback_count,
    )
    write_manifest(
        paths=paths,
        run_id=run_id,
        inpath=args.inpath,
        stats=stats,
        routing_config_path=str(CONFIG_PATH),
    )
    return ProcessBeforeResult(run_id=run_id, paths=paths, stats=stats)


def print_run_summary(result: ProcessBeforeResult) -> None:
    print(f"run_id: {result.run_id}")
    print(
        "process_before done: "
        f"docs={result.stats.doc_count} tasks={result.stats.task_count}"
    )
    print(f"empty context count: {result.stats.empty_context_count}")
    print(f"no method match count: {result.stats.no_method_match_count}")
    print(f"no support match count: {result.stats.no_support_match_count}")
    print(f"method fallback count: {result.stats.method_fallback_count}")
    print(f"jsonl: {result.paths.jsonl_path}")
    print(f"manifest: {result.paths.manifest_path}")
