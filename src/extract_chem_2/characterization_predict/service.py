from __future__ import annotations

import asyncio
import json
from itertools import batched

from tqdm import tqdm

from src.extract_chem_2.entities.characterization import CharacterizationResult
from src.llm.llm_factory import get_llm_manager
from src.llm.prompt_factory import get_prompt_manager
from src.llm.structured_chain import StructuredChain

from .helpers import build_output_record, summarize_result
from .models import CharacterizationPredictArgs, CharacterizationPredictResult, CharacterizationPredictStats
from .storage import collect_done_task_ids, load_tasks, peek_first_record, resolve_output_paths, write_manifest


async def run_characterization_predict(args: CharacterizationPredictArgs) -> CharacterizationPredictResult:
    if not args.inpath.exists():
        raise FileNotFoundError(f"Input file not found: {args.inpath}")
    if not args.prompt_dir.exists():
        raise FileNotFoundError(f"Prompt directory not found: {args.prompt_dir}")
    if not args.llm_config.exists():
        raise FileNotFoundError(f"LLM config not found: {args.llm_config}")

    first_record = peek_first_record(args.inpath, args.encoding)
    run_id = first_record.get("run_id")
    if not isinstance(run_id, str) or not run_id:
        raise ValueError(f"Missing run_id in characterization_before record: {args.inpath}")

    paths = resolve_output_paths(inpath=args.inpath, out_jsonl=args.out_jsonl)
    done_task_ids = collect_done_task_ids(paths.temp_dir, args.encoding, exclude=paths.jsonl_path)
    all_tasks = load_tasks(args.inpath, args.encoding)
    pending_tasks = [task for task in all_tasks if task["task_id"] not in done_task_ids]
    if args.limit > 0:
        pending_tasks = pending_tasks[: args.limit]

    prompt_manager = get_prompt_manager(prompt_dir=args.prompt_dir)
    llm_manager = get_llm_manager(config_path=args.llm_config)
    chain = StructuredChain(
        prompt_template=prompt_manager[args.prompt_name],
        data_model=CharacterizationResult,
        llm=llm_manager[args.model_name],
    )

    success_count = 0
    parse_error_count = 0
    invoke_error_count = 0

    with paths.jsonl_path.open("w", encoding="utf-8") as fout:
        pbar = tqdm(total=len(pending_tasks), desc="characterization_predict", unit="task")
        for batch_tasks in batched(pending_tasks, args.batch_size):
            batch_tasks = list(batch_tasks)
            if not batch_tasks:
                continue
            batch_inputs = [task["chain_input"] for task in batch_tasks]
            batch_responses = await chain.abatch(batch_inputs)
            for task, response in zip(batch_tasks, batch_responses):
                output = build_output_record(
                    task,
                    response,
                    prompt_name=args.prompt_name,
                    model_name=args.model_name,
                )
                status = summarize_result(output)
                if status == "ok":
                    success_count += 1
                elif status == "parse_error":
                    parse_error_count += 1
                else:
                    invoke_error_count += 1
                fout.write(json.dumps(output, ensure_ascii=False) + "\n")
            pbar.update(len(batch_tasks))
        pbar.close()

    stats = CharacterizationPredictStats(
        total_task_count=len(all_tasks),
        existing_done_count=len(done_task_ids),
        todo_count=len(pending_tasks),
        processed_count=len(pending_tasks),
        skipped_done_count=len(done_task_ids),
        success_count=success_count,
        parse_error_count=parse_error_count,
        invoke_error_count=invoke_error_count,
    )
    write_manifest(
        paths=paths,
        run_id=run_id,
        inpath=args.inpath,
        stats=stats,
        prompt_name=args.prompt_name,
        model_name=args.model_name,
        llm_config=args.llm_config,
        batch_size=args.batch_size,
    )
    return CharacterizationPredictResult(run_id=run_id, paths=paths, stats=stats)


def print_run_summary(result: CharacterizationPredictResult) -> None:
    print(f"run_id: {result.run_id}")
    print(
        "characterization_predict done: "
        f"total={result.stats.total_task_count} "
        f"todo={result.stats.todo_count} "
        f"skipped_done={result.stats.skipped_done_count}"
    )
    print(
        "result summary: "
        f"ok={result.stats.success_count} "
        f"parse_error={result.stats.parse_error_count} "
        f"invoke_error={result.stats.invoke_error_count}"
    )
    print(f"jsonl: {result.paths.jsonl_path}")
    print(f"manifest: {result.paths.manifest_path}")


def main_async(args: CharacterizationPredictArgs) -> CharacterizationPredictResult:
    return asyncio.run(run_characterization_predict(args))
