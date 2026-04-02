from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from src.extract_chem_2.entities.process import ProcessResult
from src.extract_chem_2.process_predict.helpers import is_valid_predict_result

SUPPORTED_NODE_PATTERNS: tuple[tuple[str, str], ...] = (
    ("sensor substrate", "sensor substrate"),
    ("sensing substrate", "sensing substrate"),
    ("coated substrate", "coated substrate"),
    ("substrate", "substrate"),
    ("electrode", "electrode"),
    ("sensor", "sensor device"),
    ("device", "device"),
)
SUPPORTED_NODE_FORM_HINTS = {"film", "membrane", "coating", "coated", "thin layer"}


def is_good_predict_record(record: dict[str, Any]) -> bool:
    return is_valid_predict_result(record.get("result"))


def recover_parse_from_raw_text(record: dict[str, Any]) -> dict[str, Any] | None:
    result = record.get("result")
    if not isinstance(result, dict):
        return None
    raw_text = result.get("raw_text")
    if not isinstance(raw_text, str) or not raw_text.strip():
        return None
    try:
        payload = json.loads(raw_text)
        validated = ProcessResult.model_validate(payload).model_dump(mode="json", exclude_none=True)
        return {"工艺流程": prune_empty_values(validated.get("工艺流程", []))}
    except Exception:
        return None


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


def material_key(entry: dict[str, Any]) -> tuple[str, str, str, str]:
    return (
        normalize_key_text(entry.get("原料名称")),
        normalize_key_text(entry.get("原料类别")),
        normalize_key_text(entry.get("原料类型")),
        normalize_key_text(entry.get("缩写")),
    )


def condition_key(entry: dict[str, Any]) -> tuple[str, str, str]:
    return (
        normalize_key_text(entry.get("反应装置")),
        normalize_key_text(entry.get("制备过程")),
        normalize_key_text(entry.get("反应条件")),
    )


def merge_materials(left: list[dict[str, Any]], right: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged_map: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    ordered_keys: list[tuple[str, str, str, str]] = []
    for entry in list(left) + list(right):
        if not isinstance(entry, dict):
            continue
        key = material_key(entry)
        if key not in merged_map:
            merged_map[key] = prune_empty_values(deepcopy(entry))
            ordered_keys.append(key)
        else:
            merged_map[key] = prune_empty_values(merge_values(merged_map[key], entry))
    return [merged_map[key] for key in ordered_keys if not is_empty_value(merged_map[key])]


def merge_conditions(left: list[dict[str, Any]], right: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged_map: dict[tuple[str, str, str], dict[str, Any]] = {}
    ordered_keys: list[tuple[str, str, str]] = []
    for entry in list(left) + list(right):
        if not isinstance(entry, dict):
            continue
        key = condition_key(entry)
        if key not in merged_map:
            merged_map[key] = prune_empty_values(deepcopy(entry))
            ordered_keys.append(key)
        else:
            merged_map[key] = prune_empty_values(merge_values(merged_map[key], entry))
    return [merged_map[key] for key in ordered_keys if not is_empty_value(merged_map[key])]


def normalize_postprocess(value: Any) -> list[str]:
    if is_empty_value(value):
        return []
    raw_items = value if isinstance(value, list) else [value]
    items: list[str] = []
    seen: set[str] = set()
    for item in raw_items:
        text = str(item).strip()
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        items.append(text)
    return items


def process_step_key(step: dict[str, Any]) -> tuple[str]:
    return (normalize_key_text(step.get("产物名称")),)


def merge_process_step(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    merged = {
        "产物名称": choose_scalar_value(left.get("产物名称"), right.get("产物名称")),
        "产物质量": choose_scalar_value(left.get("产物质量"), right.get("产物质量")),
        "产物单位": choose_scalar_value(left.get("产物单位"), right.get("产物单位")),
        "产物收率百分比": choose_scalar_value(left.get("产物收率百分比"), right.get("产物收率百分比")),
        "原料": merge_materials(left.get("原料") or [], right.get("原料") or []),
        "反应条件": merge_conditions(left.get("反应条件") or [], right.get("反应条件") or []),
        "位置索引": merge_values(left.get("位置索引") or {}, right.get("位置索引") or {}),
    }
    postprocess = merge_list_values(
        normalize_postprocess(left.get("后处理步骤")),
        normalize_postprocess(right.get("后处理步骤")),
    )
    if postprocess:
        merged["后处理步骤"] = postprocess[0] if len(postprocess) == 1 else postprocess
    return prune_empty_values(merged)


def merge_process_lists(left: list[dict[str, Any]], right: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged_map: dict[tuple[str], dict[str, Any]] = {}
    ordered_keys: list[tuple[str]] = []
    for step in list(left) + list(right):
        if not isinstance(step, dict):
            continue
        key = process_step_key(step)
        if key not in merged_map:
            merged_map[key] = prune_empty_values(deepcopy(step))
            ordered_keys.append(key)
        else:
            merged_map[key] = merge_process_step(merged_map[key], step)
    return [merged_map[key] for key in ordered_keys if not is_empty_value(merged_map[key])]


def merge_parse_records(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    left_payload = dict(left or {})
    right_payload = dict(right or {})
    left_steps = left_payload.get("工艺流程") or []
    right_steps = right_payload.get("工艺流程") or []
    merged_steps = merge_process_lists(left_steps, right_steps)
    validated = ProcessResult.model_validate({"工艺流程": merged_steps}).model_dump(mode="json", exclude_none=True)
    return {"工艺流程": prune_empty_values(validated.get("工艺流程", []))}


def is_thin_or_supported_anchor(task: dict[str, Any]) -> bool:
    anchor = task.get("polymer_anchor") or {}
    sample_form = normalize_key_text(anchor.get("样本形态"))
    return any(hint in sample_form for hint in SUPPORTED_NODE_FORM_HINTS)


def extract_supported_node_text(task: dict[str, Any]) -> str | None:
    for ref in task.get("source_refs") or []:
        if not isinstance(ref, dict):
            continue
        if ref.get("route_role") != "process_support":
            continue
        segment_title = normalize_key_text(ref.get("segment_title"))
        section_title = normalize_key_text(ref.get("section_title"))
        text = " ".join(part for part in (segment_title, section_title) if part)
        for pattern, label in SUPPORTED_NODE_PATTERNS:
            if pattern in text:
                return label
    text = normalize_key_text(((task.get("chain_input") or {}).get("text")))
    for pattern, label in SUPPORTED_NODE_PATTERNS:
        if pattern in text:
            return label
    return None


def has_supported_node_step(steps: list[dict[str, Any]]) -> bool:
    for step in steps:
        name = normalize_key_text(step.get("产物名称"))
        if any(pattern in name for pattern, _ in SUPPORTED_NODE_PATTERNS):
            return True
    return False


def has_current_object_step(task: dict[str, Any], steps: list[dict[str, Any]]) -> bool:
    anchor = task.get("polymer_anchor") or {}
    terms = [
        normalize_key_text(anchor.get("名称")),
        normalize_key_text(anchor.get("聚合物分类编码")),
        normalize_key_text(anchor.get("聚合物分类名称")),
    ]
    for step in steps:
        name = normalize_key_text(step.get("产物名称"))
        if any(term and term in name for term in terms):
            return True
    return False


def supplement_supported_node(task: dict[str, Any], steps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not is_thin_or_supported_anchor(task):
        return steps
    if not has_current_object_step(task, steps):
        return steps
    if has_supported_node_step(steps):
        return steps

    node_name = extract_supported_node_text(task)
    if not node_name:
        return steps

    anchor = task.get("polymer_anchor") or {}
    support_source = None
    for ref in task.get("source_refs") or []:
        if not isinstance(ref, dict):
            continue
        if ref.get("route_role") != "process_support":
            continue
        segment_title = normalize_key_text(ref.get("segment_title"))
        if node_name in segment_title or any(pattern in segment_title for pattern, _ in SUPPORTED_NODE_PATTERNS):
            support_source = ref
            break

    minimal_step: dict[str, Any] = {
        "产物名称": node_name,
        "原料": [],
        "反应条件": [],
    }
    if support_source:
        original_text = support_source.get("original_text") or support_source.get("原文")
        line_span = support_source.get("line_span")
        md_range = None
        if isinstance(line_span, list) and len(line_span) == 2:
            md_range = f"line {line_span[0]}-{line_span[1]}"
        minimal_step["位置索引"] = prune_empty_values(
            {
                "block_id": support_source.get("block_id"),
                "md_range": md_range,
                "原文": original_text,
            }
        )
    return steps + [prune_empty_values(minimal_step)]


def build_output_record(task: dict[str, Any], merged_parse: dict[str, Any]) -> dict[str, Any]:
    process_steps = supplement_supported_node(task, deepcopy(merged_parse["工艺流程"]))
    return {
        "run_id": task["run_id"],
        "doc_id": task["doc_id"],
        "sample_id": task["sample_id"],
        "task_id": task["task_id"],
        "工艺流程": prune_empty_values(process_steps),
    }
