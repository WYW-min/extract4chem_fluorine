from __future__ import annotations

import json

from tqdm import tqdm

from .helpers import (
    build_output_record,
    is_good_predict_record,
    merge_parse_records,
    recover_parse_from_raw_text,
)
from .models import ProcessAfterArgs, ProcessAfterResult, ProcessAfterStats
from .storage import iter_predict_records, load_jsonl, peek_first_record, resolve_output_paths, write_manifest


def run_process_after(args: ProcessAfterArgs) -> ProcessAfterResult:
    if not args.before_jsonl.exists():
        raise FileNotFoundError(f"Before jsonl not found: {args.before_jsonl}")

    first_record = peek_first_record(args.before_jsonl, args.encoding)
    run_id = first_record.get("run_id")
    if not isinstance(run_id, str) or not run_id:
        raise ValueError(f"Missing run_id in process_before record: {args.before_jsonl}")

    paths = resolve_output_paths(
        before_jsonl=args.before_jsonl,
        output_jsonl=args.output_jsonl,
        predict_temp_dir=args.predict_temp_dir,
    )
    if not paths.predict_temp_dir.exists():
        raise FileNotFoundError(f"Predict temp dir not found: {paths.predict_temp_dir}")
    if not any(paths.predict_temp_dir.glob("*.jsonl")):
        raise ValueError(f"No predict temp jsonl found in: {paths.predict_temp_dir}")

    tasks = load_jsonl(args.before_jsonl, args.encoding)
    merged_predict_map: dict[str, dict] = {}
    good_predict_record_count = 0
    merged_duplicate_count = 0

    for record in iter_predict_records(paths.predict_temp_dir, args.encoding):
        task_id = record.get("task_id")
        if not isinstance(task_id, str) or not task_id.strip():
            continue
        if is_good_predict_record(record):
            parse_payload = record["result"]["parse"]
        else:
            parse_payload = recover_parse_from_raw_text(record)
            if parse_payload is None:
                continue
        good_predict_record_count += 1
        if task_id not in merged_predict_map:
            merged_predict_map[task_id] = parse_payload
        else:
            merged_predict_map[task_id] = merge_parse_records(merged_predict_map[task_id], parse_payload)
            merged_duplicate_count += 1

    written_count = 0
    matched_task_count = 0
    with paths.jsonl_path.open("w", encoding="utf-8") as fout:
        pbar = tqdm(total=len(tasks), desc="process_after", unit="task")
        for task in tasks:
            merged_parse = merged_predict_map.get(task["task_id"])
            if merged_parse is not None:
                out_record = build_output_record(task, merged_parse)
                fout.write(json.dumps(out_record, ensure_ascii=False) + "\n")
                matched_task_count += 1
                written_count += 1
            pbar.update(1)
        pbar.close()

    stats = ProcessAfterStats(
        total_task_count=len(tasks),
        good_predict_record_count=good_predict_record_count,
        matched_task_count=matched_task_count,
        written_count=written_count,
        merged_duplicate_count=merged_duplicate_count,
        missing_predict_count=len(tasks) - matched_task_count,
    )
    write_manifest(paths=paths, run_id=run_id, before_jsonl=args.before_jsonl, stats=stats)
    return ProcessAfterResult(run_id=run_id, paths=paths, stats=stats)


def print_run_summary(result: ProcessAfterResult) -> None:
    print(f"run_id: {result.run_id}")
    print(
        "process_after done: "
        f"total={result.stats.total_task_count} "
        f"good_predict_records={result.stats.good_predict_record_count} "
        f"matched={result.stats.matched_task_count} "
        f"written={result.stats.written_count} "
        f"merged_duplicates={result.stats.merged_duplicate_count} "
        f"missing_predict={result.stats.missing_predict_count}"
    )
    print(f"jsonl: {result.paths.jsonl_path}")
    print(f"manifest: {result.paths.manifest_path}")


def run_main(args: ProcessAfterArgs) -> ProcessAfterResult:
    return run_process_after(args)
