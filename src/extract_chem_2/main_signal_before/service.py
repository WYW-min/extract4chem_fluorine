from __future__ import annotations

import json

from .builder import build_main_signal_task
from .models import MainSignalBeforeArgs, MainSignalBeforeResult, MainSignalBeforeStats
from .storage import iter_doc_groups, peek_first_record, resolve_output_paths, write_manifest


def run_main_signal_before(args: MainSignalBeforeArgs) -> MainSignalBeforeResult:
    if not args.inpath.exists():
        raise FileNotFoundError(f"Input file not found: {args.inpath}")

    first_record = peek_first_record(args.inpath, args.encoding)
    run_id = first_record.get("run_id")
    if not isinstance(run_id, str) or not run_id:
        raise ValueError(f"Missing run_id in doc_split record: {args.inpath}")

    paths = resolve_output_paths(
        inpath=args.inpath,
        run_id=run_id,
        out_jsonl=args.out_jsonl,
    )

    doc_count = 0
    task_count = 0
    empty_experiment_count = 0

    with paths.jsonl_path.open("w", encoding="utf-8") as fout:
        for meta, sections in iter_doc_groups(args.inpath, args.encoding):
            doc_count += 1
            task = build_main_signal_task(
                run_id=meta["run_id"],
                doc_id=meta["doc_id"],
                file_name=meta["file_name"],
                sections=sections,
            )
            has_experiment = any(
                "experimental" in ref.get("roles", []) for ref in task["source_refs"]
            )
            if not has_experiment:
                empty_experiment_count += 1
            task_count += 1
            fout.write(json.dumps(task, ensure_ascii=False) + "\n")

    stats = MainSignalBeforeStats(
        doc_count=doc_count,
        task_count=task_count,
        empty_experiment_count=empty_experiment_count,
    )
    write_manifest(paths=paths, run_id=run_id, inpath=args.inpath, stats=stats)
    return MainSignalBeforeResult(run_id=run_id, paths=paths, stats=stats)


def print_run_summary(result: MainSignalBeforeResult) -> None:
    print(f"run_id: {result.run_id}")
    print(
        "main_signal_before done: "
        f"docs={result.stats.doc_count} tasks={result.stats.task_count}"
    )
    print(f"empty experiment count: {result.stats.empty_experiment_count}")
    print(f"jsonl: {result.paths.jsonl_path}")
    print(f"manifest: {result.paths.manifest_path}")
