from __future__ import annotations

import json
from pathlib import Path

from tqdm import tqdm

from .helpers import (
    merge_characterization_payloads,
    merge_doc_record,
    merge_process_payloads,
    merge_property_payloads,
)
from .models import FinalMergeArgs, FinalMergeResult, FinalMergeStats
from .storage import load_jsonl, peek_first_record, resolve_output_paths, write_manifest


def load_characterization_map(path: Path, encoding: str) -> dict[tuple[str, str], dict]:
    merged: dict[tuple[str, str], dict] = {}
    if not path.exists():
        return merged
    for record in load_jsonl(path, encoding):
        doc_id = str(record.get("doc_id") or "").strip()
        sample_id = str(record.get("sample_id") or "").strip()
        if not doc_id or not sample_id:
            continue
        payload = record.get("表征") or {}
        key = (doc_id, sample_id)
        if key not in merged:
            merged[key] = payload
        else:
            merged[key] = merge_characterization_payloads(merged[key], payload)
    return merged


def load_property_map(path: Path, encoding: str) -> dict[tuple[str, str], list[dict]]:
    merged: dict[tuple[str, str], list[dict]] = {}
    if not path.exists():
        return merged
    for record in load_jsonl(path, encoding):
        doc_id = str(record.get("doc_id") or "").strip()
        sample_id = str(record.get("sample_id") or "").strip()
        if not doc_id or not sample_id:
            continue
        payload = record.get("性质") or []
        key = (doc_id, sample_id)
        if key not in merged:
            merged[key] = payload
        else:
            merged[key] = merge_property_payloads(merged[key], payload)
    return merged


def load_process_map(path: Path, encoding: str) -> dict[tuple[str, str], list[dict]]:
    merged: dict[tuple[str, str], list[dict]] = {}
    if not path.exists():
        return merged
    for record in load_jsonl(path, encoding):
        doc_id = str(record.get("doc_id") or "").strip()
        sample_id = str(record.get("sample_id") or "").strip()
        if not doc_id or not sample_id:
            continue
        payload = record.get("工艺流程") or []
        key = (doc_id, sample_id)
        if key not in merged:
            merged[key] = payload
        else:
            merged[key] = merge_process_payloads(merged[key], payload)
    return merged


def run_final_merge(args: FinalMergeArgs) -> FinalMergeResult:
    if not args.main_signal_jsonl.exists():
        raise FileNotFoundError(f"Main signal jsonl not found: {args.main_signal_jsonl}")

    first_record = peek_first_record(args.main_signal_jsonl, args.encoding)
    run_id = first_record.get("run_id")
    if not isinstance(run_id, str) or not run_id:
        raise ValueError(f"Missing run_id in main_signal_after record: {args.main_signal_jsonl}")

    paths = resolve_output_paths(
        main_signal_jsonl=args.main_signal_jsonl,
        characterization_jsonl=args.characterization_jsonl,
        property_jsonl=args.property_jsonl,
        process_jsonl=args.process_jsonl,
        output_jsonl=args.output_jsonl,
    )

    main_records = load_jsonl(paths.main_signal_jsonl, args.encoding)
    characterization_map = load_characterization_map(paths.characterization_jsonl, args.encoding)
    property_map = load_property_map(paths.property_jsonl, args.encoding)
    process_map = load_process_map(paths.process_jsonl, args.encoding)

    total_polymer_count = 0
    matched_characterization_count = 0
    matched_property_count = 0
    matched_process_count = 0
    written_count = 0

    with paths.jsonl_path.open("w", encoding="utf-8") as fout:
        pbar = tqdm(total=len(main_records), desc="final_merge", unit="doc")
        for record in main_records:
            merged_record, polymer_count, char_count, prop_count, proc_count = merge_doc_record(
                record,
                characterization_map=characterization_map,
                property_map=property_map,
                process_map=process_map,
            )
            fout.write(json.dumps(merged_record["result"], ensure_ascii=False) + "\n")
            total_polymer_count += polymer_count
            matched_characterization_count += char_count
            matched_property_count += prop_count
            matched_process_count += proc_count
            written_count += 1
            pbar.update(1)
        pbar.close()

    stats = FinalMergeStats(
        total_doc_count=len(main_records),
        total_polymer_count=total_polymer_count,
        characterization_record_count=len(characterization_map),
        property_record_count=len(property_map),
        process_record_count=len(process_map),
        matched_characterization_count=matched_characterization_count,
        matched_property_count=matched_property_count,
        matched_process_count=matched_process_count,
        written_count=written_count,
    )
    write_manifest(paths=paths, run_id=run_id, stats=stats)
    return FinalMergeResult(run_id=run_id, paths=paths, stats=stats)


def print_run_summary(result: FinalMergeResult) -> None:
    print(f"run_id: {result.run_id}")
    print(
        "final_merge done: "
        f"docs={result.stats.total_doc_count} "
        f"polymers={result.stats.total_polymer_count} "
        f"char_records={result.stats.characterization_record_count} "
        f"prop_records={result.stats.property_record_count} "
        f"proc_records={result.stats.process_record_count} "
        f"matched_char={result.stats.matched_characterization_count} "
        f"matched_prop={result.stats.matched_property_count} "
        f"matched_proc={result.stats.matched_process_count} "
        f"written={result.stats.written_count}"
    )
    print(f"jsonl: {result.paths.jsonl_path}")
    print(f"manifest: {result.paths.manifest_path}")


def run_main(args: FinalMergeArgs) -> FinalMergeResult:
    return run_final_merge(args)
