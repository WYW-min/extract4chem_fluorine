from __future__ import annotations

from typing import Any

from pydantic import BaseModel


def has_empty_error(result: dict[str, Any]) -> bool:
    error = result.get("error")
    if error is None:
        return True
    if isinstance(error, str):
        return not error.strip()
    return False


def is_valid_predict_result(result: Any) -> bool:
    return isinstance(result, dict) and isinstance(result.get("parse"), dict) and has_empty_error(result)


def is_task_done(record: dict[str, Any]) -> bool:
    task_id = record.get("task_id")
    if not isinstance(task_id, str) or not task_id.strip():
        return False
    return is_valid_predict_result(record.get("result"))


def build_output_record(
    task: dict[str, Any],
    response: BaseModel | Exception | Any,
    *,
    prompt_name: str,
    model_name: str,
) -> dict[str, Any]:
    if isinstance(response, Exception):
        result: Any = {
            "parse": None,
            "raw_text": "",
            "error": f"{type(response).__name__}: {response}",
        }
    elif isinstance(response, BaseModel):
        result = response.model_dump(mode="json")
    else:
        result = response

    return {
        "run_id": task["run_id"],
        "doc_id": task["doc_id"],
        "sample_id": task.get("sample_id"),
        "task_id": task["task_id"],
        "file_name": task.get("file_name"),
        "polymer_anchor": task.get("polymer_anchor"),
        "source_refs": task.get("source_refs", []),
        "prompt_name": prompt_name,
        "model_name": model_name,
        "result": result,
    }


def summarize_result(record: dict[str, Any]) -> str:
    result = record.get("result")
    if is_valid_predict_result(result):
        return "ok"
    if not isinstance(result, dict):
        return "invoke_error"
    if result.get("error"):
        return "parse_error"
    return "invoke_error"
