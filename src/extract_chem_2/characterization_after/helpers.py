from __future__ import annotations

from copy import deepcopy
from typing import Any

from src.extract_chem_2.entities.characterization import CharacterizationResult
from src.extract_chem_2.characterization_predict.helpers import is_valid_predict_result


def is_good_predict_record(record: dict[str, Any]) -> bool:
    return is_valid_predict_result(record.get("result"))


def is_empty_value(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (list, tuple, set, dict)):
        return len(value) == 0
    return False


def prune_empty_values(value: Any) -> Any:
    if isinstance(value, dict):
        pruned: dict[str, Any] = {}
        for key, item in value.items():
            cleaned = prune_empty_values(item)
            if not is_empty_value(cleaned):
                pruned[key] = cleaned
        return pruned
    if isinstance(value, list):
        pruned_list = [prune_empty_values(item) for item in value]
        return [item for item in pruned_list if not is_empty_value(item)]
    return value


def merge_list_values(left: list[Any], right: list[Any]) -> list[Any]:
    merged: list[Any] = []
    seen: set[str] = set()
    for item in list(left) + list(right):
        key = repr(item)
        if key in seen:
            continue
        seen.add(key)
        merged.append(item)
    return merged


def choose_scalar_value(left: Any, right: Any) -> Any:
    if is_empty_value(left):
        return right
    if is_empty_value(right):
        return left
    if left == right:
        return left
    if isinstance(left, str) and isinstance(right, str):
        return left if len(left.strip()) >= len(right.strip()) else right
    return left


def merge_values(left: Any, right: Any) -> Any:
    if is_empty_value(left):
        return deepcopy(right)
    if is_empty_value(right):
        return deepcopy(left)
    if isinstance(left, dict) and isinstance(right, dict):
        merged = deepcopy(left)
        for key, right_value in right.items():
            if key in merged:
                merged[key] = merge_values(merged[key], right_value)
            else:
                merged[key] = deepcopy(right_value)
        return merged
    if isinstance(left, list) and isinstance(right, list):
        return merge_list_values(left, right)
    return choose_scalar_value(left, right)


def merge_parse_records(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    left_payload = dict(left or {})
    right_payload = dict(right or {})
    left_char = left_payload.get("表征") or {}
    right_char = right_payload.get("表征") or {}
    merged_char = merge_values(left_char, right_char)
    merged = {"表征": merged_char}
    validated = CharacterizationResult.model_validate(merged).model_dump(mode="json", exclude_none=True)
    return {"表征": prune_empty_values(validated.get("表征", {}))}


def build_output_record(task: dict[str, Any], merged_parse: dict[str, Any]) -> dict[str, Any]:
    return {
        "run_id": task["run_id"],
        "doc_id": task["doc_id"],
        "sample_id": task["sample_id"],
        "task_id": task["task_id"],
        "表征": prune_empty_values(merged_parse["表征"]),
    }
