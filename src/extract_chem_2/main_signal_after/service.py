from __future__ import annotations

import json

from tqdm import tqdm

from .helpers import build_output_record, is_good_predict_record
from .models import MainSignalAfterArgs, MainSignalAfterResult, MainSignalAfterStats
from .storage import (
    iter_predict_records,
    load_jsonl,
    peek_first_record,
    resolve_output_paths,
    write_manifest,
)


def run_main_signal_after(args: MainSignalAfterArgs) -> MainSignalAfterResult:
    if not args.before_jsonl.exists():
        raise FileNotFoundError(f'Before jsonl not found: {args.before_jsonl}')

    first_record = peek_first_record(args.before_jsonl, args.encoding)
    run_id = first_record.get('run_id')
    if not isinstance(run_id, str) or not run_id:
        raise ValueError(f'Missing run_id in main_signal_before record: {args.before_jsonl}')

    paths = resolve_output_paths(
        before_jsonl=args.before_jsonl,
        output_jsonl=args.output_jsonl,
        predict_temp_dir=args.predict_temp_dir,
    )
    if not paths.predict_temp_dir.exists():
        raise FileNotFoundError(f'Predict temp dir not found: {paths.predict_temp_dir}')
    if not any(paths.predict_temp_dir.glob('*.jsonl')):
        raise ValueError(f'No predict temp jsonl found in: {paths.predict_temp_dir}')

    tasks = load_jsonl(args.before_jsonl, args.encoding)
    good_predict_map: dict[str, dict] = {}
    for record in iter_predict_records(paths.predict_temp_dir, args.encoding):
        task_id = record.get('task_id')
        if not isinstance(task_id, str) or task_id in good_predict_map:
            continue
        if is_good_predict_record(record):
            good_predict_map[task_id] = record

    written_count = 0
    with paths.jsonl_path.open('w', encoding='utf-8') as fout:
        pbar = tqdm(total=len(tasks), desc='main_signal_after', unit='task')
        for task in tasks:
            predict_record = good_predict_map.get(task['task_id'])
            if predict_record is not None:
                out_record = build_output_record(task, predict_record['result']['parse'])
                fout.write(json.dumps(out_record, ensure_ascii=False) + '\n')
                written_count += 1
            pbar.update(1)
        pbar.close()

    stats = MainSignalAfterStats(
        total_task_count=len(tasks),
        good_predict_count=len(good_predict_map),
        written_count=written_count,
        missing_predict_count=len(tasks) - written_count,
    )
    write_manifest(paths=paths, run_id=run_id, before_jsonl=args.before_jsonl, stats=stats)
    return MainSignalAfterResult(run_id=run_id, paths=paths, stats=stats)


def print_run_summary(result: MainSignalAfterResult) -> None:
    print(f'run_id: {result.run_id}')
    print(
        'main_signal_after done: '
        f'total={result.stats.total_task_count} '
        f'good_predict={result.stats.good_predict_count} '
        f'written={result.stats.written_count} '
        f'missing_predict={result.stats.missing_predict_count}'
    )
    print(f'jsonl: {result.paths.jsonl_path}')
    print(f'manifest: {result.paths.manifest_path}')
