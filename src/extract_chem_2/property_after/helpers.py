from __future__ import annotations

from copy import deepcopy
import re
from typing import Any

from src.extract_chem_2.entities.property import PropertyResult
from src.extract_chem_2.property_predict.helpers import is_valid_predict_result


BROAD_PROPERTY_NAME_PATTERNS = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"^thermal\s+stability$",
        r"^mechanical\s+properties?$",
        r"^rheological\s+properties?$",
        r"^electrical\s+properties?$",
        r"^dielectric\s+properties?$",
        r"^physical\s+properties?$",
        r"^processing\s+properties?$",
        r"^热稳定性$",
        r"^力学性能$",
        r"^流变性能$",
        r"^电学性能$",
        r"^介电性能$",
        r"^物理性能$",
        r"^加工性能$",
    )
)
FAILED_MEASUREMENT_PATTERNS = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"未能.{0,8}(?:获得|得到).{0,8}(?:准确|可靠).{0,8}(?:测量|结果|数值)",
        r"无法.{0,8}(?:获得|得到|测得).{0,8}(?:准确|可靠).{0,8}(?:测量|结果|数值)",
        r"could\s+not\s+obtain\s+an?\s+accurate\s+(?:measurement|value|result)",
        r"unable\s+to\s+obtain\s+an?\s+accurate\s+(?:measurement|value|result)",
        r"not\s+measured\s+accurately",
    )
)


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


def normalize_key_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip().lower()


def property_entry_key(entry: dict[str, Any]) -> tuple[str, str, str]:
    return (
        normalize_key_text(entry.get("类别")),
        normalize_key_text(entry.get("名称")),
        normalize_key_text(entry.get("缩写")),
    )


def has_structured_numeric_value(value: dict[str, Any]) -> bool:
    if not isinstance(value, dict):
        return False
    for key in ("单值", "最小", "最大", "误差"):
        item = value.get(key)
        if not is_empty_value(item):
            return True
    return False


def is_broad_summary_property(entry: dict[str, Any]) -> bool:
    name = normalize_key_text(entry.get("名称"))
    if not name:
        return False
    return any(pattern.match(name) for pattern in BROAD_PROPERTY_NAME_PATTERNS)


def is_failed_measurement_property(entry: dict[str, Any]) -> bool:
    value = entry.get("值") or {}
    if has_structured_numeric_value(value):
        return False
    explanation = normalize_key_text((value or {}).get("说明"))
    if not explanation:
        return False
    return any(pattern.search(explanation) for pattern in FAILED_MEASUREMENT_PATTERNS)


def has_more_specific_peer(
    *,
    entry: dict[str, Any],
    all_entries: list[dict[str, Any]],
) -> bool:
    category = normalize_key_text(entry.get("类别"))
    name = normalize_key_text(entry.get("名称"))
    for peer in all_entries:
        if peer is entry:
            continue
        if normalize_key_text(peer.get("类别")) != category:
            continue
        peer_name = normalize_key_text(peer.get("名称"))
        if not peer_name or peer_name == name:
            continue
        if is_broad_summary_property(peer):
            continue
        return True
    return False


def should_drop_property_entry(entry: dict[str, Any], all_entries: list[dict[str, Any]]) -> bool:
    value = entry.get("值") or {}
    if is_failed_measurement_property(entry):
        return True
    if (
        is_broad_summary_property(entry)
        and not has_structured_numeric_value(value)
        and has_more_specific_peer(entry=entry, all_entries=all_entries)
    ):
        return True
    return False


def merge_property_entries(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    merged = {
        "类别": choose_scalar_value(left.get("类别"), right.get("类别")),
        "名称": choose_scalar_value(left.get("名称"), right.get("名称")),
        "缩写": choose_scalar_value(left.get("缩写"), right.get("缩写")),
        "值": merge_values(left.get("值") or {}, right.get("值") or {}),
        "测试条件": merge_values(left.get("测试条件") or {}, right.get("测试条件") or {}),
    }
    return prune_empty_values(merged)


def merge_property_lists(left: list[dict[str, Any]], right: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged_map: dict[tuple[str, str, str], dict[str, Any]] = {}
    ordered_keys: list[tuple[str, str, str]] = []

    for entry in list(left) + list(right):
        if not isinstance(entry, dict):
            continue
        key = property_entry_key(entry)
        if key not in merged_map:
            merged_map[key] = prune_empty_values(deepcopy(entry))
            ordered_keys.append(key)
        else:
            merged_map[key] = merge_property_entries(merged_map[key], entry)

    ordered_entries = [
        merged_map[key]
        for key in ordered_keys
    ]
    return [
        entry
        for entry in ordered_entries
        if not is_empty_value(entry) and not should_drop_property_entry(entry, ordered_entries)
    ]


def merge_parse_records(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    left_payload = dict(left or {})
    right_payload = dict(right or {})
    left_props = left_payload.get("性质") or []
    right_props = right_payload.get("性质") or []
    merged_props = merge_property_lists(left_props, right_props)
    merged = {"性质": merged_props}
    validated = PropertyResult.model_validate(merged).model_dump(mode="json", exclude_none=True)
    return {"性质": prune_empty_values(validated.get("性质", []))}


def build_output_record(task: dict[str, Any], merged_parse: dict[str, Any]) -> dict[str, Any]:
    return {
        "run_id": task["run_id"],
        "doc_id": task["doc_id"],
        "sample_id": task["sample_id"],
        "task_id": task["task_id"],
        "性质": prune_empty_values(merged_parse["性质"]),
    }
