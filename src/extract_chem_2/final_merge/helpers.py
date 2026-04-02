from __future__ import annotations

from copy import deepcopy
from typing import Any

from src.extract_chem_2.characterization_after.helpers import (
    merge_parse_records as merge_characterization_parse_records,
)
from src.extract_chem_2.property_after.helpers import (
    merge_parse_records as merge_property_parse_records,
)
from src.extract_chem_2.process_after.helpers import (
    merge_parse_records as merge_process_parse_records,
)


def merge_characterization_payloads(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    return merge_characterization_parse_records({"表征": left or {}}, {"表征": right or {}})["表征"]


def merge_property_payloads(left: list[dict[str, Any]], right: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return merge_property_parse_records({"性质": left or []}, {"性质": right or []})["性质"]


def merge_process_payloads(left: list[dict[str, Any]], right: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return merge_process_parse_records({"工艺流程": left or []}, {"工艺流程": right or []})["工艺流程"]


def merge_doc_record(
    record: dict[str, Any],
    *,
    characterization_map: dict[tuple[str, str], dict[str, Any]],
    property_map: dict[tuple[str, str], list[dict[str, Any]]],
    process_map: dict[tuple[str, str], list[dict[str, Any]]],
) -> tuple[dict[str, Any], int, int, int, int]:
    output = deepcopy(record)
    result = output.get("result") or {}
    polymers = result.get("聚合物") or []

    polymer_count = 0
    matched_char_count = 0
    matched_prop_count = 0
    matched_proc_count = 0

    doc_id = str(output.get("doc_id") or "")

    for polymer in polymers:
        if not isinstance(polymer, dict):
            continue
        polymer_count += 1
        sample_id = str(polymer.get("身份标识") or "").strip()
        if not sample_id:
            continue
        key = (doc_id, sample_id)

        char_payload = characterization_map.get(key)
        if char_payload is not None:
            polymer["表征"] = deepcopy(char_payload)
            matched_char_count += 1

        prop_payload = property_map.get(key)
        if prop_payload is not None:
            polymer["性质"] = deepcopy(prop_payload)
            matched_prop_count += 1

        proc_payload = process_map.get(key)
        if proc_payload is not None:
            polymer["工艺流程"] = deepcopy(proc_payload)
            matched_proc_count += 1

    output["result"] = result
    return output, polymer_count, matched_char_count, matched_prop_count, matched_proc_count

