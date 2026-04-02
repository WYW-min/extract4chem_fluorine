from __future__ import annotations

import re
from collections import OrderedDict
from typing import Any


INTRO_PATTERNS = (
    "INTRODUCT",
    "引言",
    "绪论",
)
EXPERIMENT_PATTERNS = (
    "MATERIALS AND METHODS",
    "MATERIALS & METHODS",
    "MATERIALS AND METHOD",
    "EXPERIMENTAL",
    "EXPERIMENT",
    "METHODS",
    "METHODOLOGY",
)
RESULTS_PATTERNS = (
    "RESULTS AND DISCUSSION",
    "RESULTS",
    "DISCUSSION",
)
BODY_PATTERNS = (
    *INTRO_PATTERNS,
    *EXPERIMENT_PATTERNS,
    *RESULTS_PATTERNS,
    "CONCLUSION",
    "CONCLUSIONS",
)


def normalize_title(title: str) -> str:
    return re.sub(r"\s+", " ", title).strip().upper()


def is_experiment_section(section: dict[str, Any]) -> bool:
    title = normalize_title(section["section_title"])
    return any(pattern in title for pattern in EXPERIMENT_PATTERNS) or title == "MATERIALS"


def is_body_section(section: dict[str, Any]) -> bool:
    if section.get("section_number") is not None:
        return True
    title = normalize_title(section["section_title"])
    return any(pattern in title for pattern in BODY_PATTERNS)


def is_results_section(section: dict[str, Any]) -> bool:
    title = normalize_title(section["section_title"])
    return any(pattern in title for pattern in RESULTS_PATTERNS)


def select_front_matter_sections(sections: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not sections:
        return []

    for idx, section in enumerate(sections[1:], start=1):
        if is_body_section(section):
            return sections[:idx]
    return sections[:1]


def render_block_text(section: dict[str, Any]) -> str:
    return section["content"].strip()


def render_tagged_text(
    *,
    front_matter_sections: list[dict[str, Any]],
    experiment_section: dict[str, Any] | None,
    results_section: dict[str, Any] | None,
) -> str:
    parts: list[str] = []

    if front_matter_sections:
        front_text = "\n\n".join(
            render_block_text(section) for section in front_matter_sections if render_block_text(section)
        ).strip()
        if front_text:
            parts.append(f"[FRONT_MATTER]\n{front_text}")

    if experiment_section is not None:
        experiment_text = render_block_text(experiment_section)
        if experiment_text:
            parts.append(f"[EXPERIMENT]\n{experiment_text}")

    if results_section is not None:
        results_text = render_block_text(results_section)
        if results_text:
            parts.append(f"[RESULTS]\n{results_text}")

    return "\n\n".join(parts).strip()


def build_source_refs(
    *,
    title_section: dict[str, Any],
    front_matter_sections: list[dict[str, Any]],
    experiment_section: dict[str, Any] | None,
    results_section: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    refs: "OrderedDict[str, dict[str, Any]]" = OrderedDict()

    def upsert(section: dict[str, Any], role: str) -> None:
        block_id = section["block_id"]
        if block_id not in refs:
            refs[block_id] = {
                "block_id": block_id,
                "chunk_index": section["chunk_index"],
                "section_title": section["section_title"],
                "line_span": section["line_span"],
                "roles": [],
            }
        if role not in refs[block_id]["roles"]:
            refs[block_id]["roles"].append(role)

    upsert(title_section, "title")
    for section in front_matter_sections:
        upsert(section, "front_matter")
    if experiment_section is not None:
        upsert(experiment_section, "experimental")
    if results_section is not None:
        upsert(results_section, "results")

    return sorted(refs.values(), key=lambda item: item["chunk_index"])


def build_main_signal_task(
    *,
    run_id: str,
    doc_id: str,
    file_name: str,
    sections: list[dict[str, Any]],
) -> dict[str, Any]:
    ordered_sections = sorted(sections, key=lambda item: item["chunk_index"])
    title_section = ordered_sections[0]
    front_matter_sections = select_front_matter_sections(ordered_sections)
    experiment_section = next(
        (section for section in ordered_sections if is_experiment_section(section)),
        None,
    )
    results_section = next(
        (section for section in ordered_sections if is_results_section(section)),
        None,
    )

    chain_input = {
        "text": render_tagged_text(
            front_matter_sections=front_matter_sections,
            experiment_section=experiment_section,
            results_section=results_section,
        )
    }
    return {
        "run_id": run_id,
        "doc_id": doc_id,
        "task_id": f"{run_id}__{doc_id}__main_signal",
        "file_name": file_name,
        "source_refs": build_source_refs(
            title_section=title_section,
            front_matter_sections=front_matter_sections,
            experiment_section=experiment_section,
            results_section=results_section,
        ),
        "chain_input": chain_input,
    }
