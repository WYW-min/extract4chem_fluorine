from __future__ import annotations

import re
import tomllib
from pathlib import Path
from typing import Any

CONFIG_PATH = Path(__file__).resolve().parents[3] / "configs" / "property.toml"


def _load_route_config() -> tuple[
    tuple[str, ...],
    tuple[str, ...],
    tuple[str, ...],
    tuple[tuple[str, re.Pattern[str]], ...],
    tuple[re.Pattern[str], ...],
    dict[str, tuple[str, ...]],
]:
    with CONFIG_PATH.open("rb") as fin:
        config = tomllib.load(fin)

    title_cfg = config.get("section_titles", {})
    method_titles = tuple(str(item).upper() for item in title_cfg.get("method", []))
    result_titles = tuple(str(item).upper() for item in title_cfg.get("result", []))
    ignore_titles = tuple(str(item).upper() for item in title_cfg.get("ignore", []))

    keyword_patterns: list[tuple[str, re.Pattern[str]]] = []
    for label, patterns in config.get("keywords", {}).items():
        for pattern in patterns:
            keyword_patterns.append((str(label), re.compile(str(pattern), re.IGNORECASE)))

    exclude_patterns: list[re.Pattern[str]] = []
    for patterns in config.get("exclude_keywords", {}).values():
        for pattern in patterns:
            exclude_patterns.append(re.compile(str(pattern), re.IGNORECASE))

    form_group_preferences = {
        str(group): tuple(str(label) for label in labels)
        for group, labels in config.get("form_group_property_preferences", {}).items()
    }

    return (
        method_titles,
        result_titles,
        ignore_titles,
        tuple(keyword_patterns),
        tuple(exclude_patterns),
        form_group_preferences,
    )


(
    METHOD_TITLE_PATTERNS,
    RESULT_TITLE_PATTERNS,
    IGNORE_TITLE_PATTERNS,
    PROPERTY_KEYWORD_PATTERNS,
    EXCLUDE_WINDOW_PATTERNS,
    FORM_GROUP_PROPERTY_PREFERENCES,
) = _load_route_config()

GENERIC_CATEGORY_NAMES = {
    "polyimide",
    "polyamic acid",
    "polyamic acid ammonium salt",
    "cellulose nanocrystal",
    "cellulose nanocrystals",
}
FORM_PATTERNS = {
    "Aerogel": ("aerogel",),
    "Film": ("film",),
    "Membrane": ("membrane",),
    "Ink": ("ink",),
    "Solution": ("solution",),
    "Gel": ("gel",),
    "Powder": ("powder",),
    "Foam": ("foam",),
    "Fiber": ("fiber", "fibre"),
    "Coating": ("coating",),
    "Solid": ("solid",),
}
FORM_GROUPS = {
    "Aerogel": "PorousBody",
    "Foam": "PorousBody",
    "Film": "ThinLayer",
    "Membrane": "ThinLayer",
    "Coating": "ThinLayer",
    "Ink": "PrecursorFluid",
    "Solution": "PrecursorFluid",
    "Gel": "PrecursorFluid",
    "Powder": "Powder",
    "Fiber": "Fiber",
    "Solid": "Solid",
}
PRECURSOR_FLUID_FORMS = {"Ink", "Solution", "Gel"}
VARIANT_MARKER_PATTERNS = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\b[A-Z][A-Za-z0-9+-]*\s*/\s*[A-Z][A-Za-z0-9+-]*\b",
        r"\bcomposite\b",
        r"\bdoped\b",
        r"\bloaded\b",
        r"\bfilled\b",
        r"\breinforced\b",
        r"\bblend\b",
        r"\bnanocomposite\b",
        r"\bnanoparticle",
        r"\bhybrid\b",
        r"\bwith\b.+\b(nano\w*|particle\w*|fiber\w*|filler\w*|tube\w*|sheet\w*|flake\w*|wire\w*)\b",
    )
)
RATIO_PATTERN = re.compile(r"\b\d+(?:\.\d+)?\s*wt\s*%\b", re.IGNORECASE)
CAPTION_LINE_PATTERN = re.compile(r"^\s*(figure|fig\.?|table|scheme)\b", re.IGNORECASE)
PROCESS_TRANSITION_PATTERNS = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"prepared\s+from",
        r"derived\s+from",
        r"converted\s+to",
        r"after\s+(thermal\s+)?imidization",
        r"after\s+freeze[-\s]?drying",
        r"freeze[-\s]?dried",
        r"3d\s+printed",
        r"direct\s+ink\s+writing",
        r"after\s+printing",
        r"printed\s+.*?(aerogel|film|membrane|foam|fiber|coating)",
    )
)
VARIANT_TAIL_PATTERN = re.compile(
    r"^\s*(?:[-,/()]|\b)*(?:doped\b|loaded\b|filled\b|reinforced\b|blend(?:ed)?\b|"
    r"composite\b|nanocomposite\b|hybrid\b|with\b)",
    re.IGNORECASE,
)


def normalize_title(title: str) -> str:
    return re.sub(r"\s+", " ", title).strip().upper()


def normalize_text(text: Any) -> str | None:
    if text is None:
        return None
    normalized = re.sub(r"\s+", " ", str(text).strip())
    return normalized or None


def normalize_text_list(value: Any) -> list[str]:
    if not value:
        return []
    raw_items = value if isinstance(value, list) else [value]
    items: list[str] = []
    seen: set[str] = set()
    for item in raw_items:
        text = normalize_text(item)
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        items.append(text)
    return items


def is_ignored_section(section: dict[str, Any]) -> bool:
    title = normalize_title(section["section_title"])
    return any(pattern in title for pattern in IGNORE_TITLE_PATTERNS)


def is_method_section(section: dict[str, Any]) -> bool:
    title = normalize_title(section["section_title"])
    return any(pattern in title for pattern in METHOD_TITLE_PATTERNS)


def is_results_section(section: dict[str, Any]) -> bool:
    title = normalize_title(section["section_title"])
    return any(pattern in title for pattern in RESULT_TITLE_PATTERNS)


def has_property_title(section: dict[str, Any]) -> bool:
    title = normalize_title(section["section_title"])
    if is_ignored_section(section):
        return False
    return any(pattern.search(title) for _, pattern in PROPERTY_KEYWORD_PATTERNS)


def is_front_matter_section(section: dict[str, Any]) -> bool:
    return int(section.get("chunk_index", 0)) == 0 and not is_method_section(section) and not is_results_section(section)


def collect_property_labels(text: str) -> list[str]:
    labels: list[str] = []
    for label, pattern in PROPERTY_KEYWORD_PATTERNS:
        if pattern.search(text):
            labels.append(label)
    return labels


def build_polymer_anchor(polymer: dict[str, Any]) -> dict[str, Any]:
    return {
        "身份标识": normalize_text(polymer.get("身份标识")),
        "名称": normalize_text(polymer.get("名称")),
        "别名": normalize_text_list(polymer.get("别名")),
        "聚合物分类编码": normalize_text(polymer.get("聚合物分类编码")),
        "聚合物分类名称": normalize_text(polymer.get("聚合物分类名称")),
        "样本形态": normalize_text(polymer.get("样本形态")),
    }


def _make_regex_term(term: str) -> tuple[str, re.Pattern[str]] | None:
    clean = normalize_text(term)
    if not clean:
        return None
    if len(clean) <= 6 and clean.upper() == clean and re.fullmatch(r"[A-Z0-9/+-]+", clean):
        pattern = re.compile(rf"(?<![A-Za-z0-9/+-]){re.escape(clean)}(?:s)?(?![A-Za-z0-9/+-])")
    else:
        pattern = re.compile(re.escape(clean), re.IGNORECASE)
    return clean, pattern


def build_anchor_patterns(anchor: dict[str, Any]) -> list[tuple[str, re.Pattern[str]]]:
    terms: list[str] = []
    name = anchor.get("名称")
    has_descriptive_name = bool(isinstance(name, str) and normalize_text(name))
    if isinstance(name, str) and name:
        terms.append(name)
    aliases = anchor.get("别名") or []
    if isinstance(aliases, list):
        terms.extend(str(item) for item in aliases if normalize_text(item))

    category_code = anchor.get("聚合物分类编码")
    if isinstance(category_code, str) and category_code:
        normalized_code = normalize_text(category_code) or ""
        is_short_base_code = bool(
            normalized_code
            and len(normalized_code) <= 6
            and normalized_code.upper() == normalized_code
            and re.fullmatch(r"[A-Z0-9+-]+", normalized_code)
            and "/" not in normalized_code
            and has_descriptive_name
        )
        if not is_short_base_code:
            terms.append(category_code)
        if "/" in category_code:
            terms.append(category_code.replace("/", "-"))
            terms.append(category_code.replace("/", " / "))

    category_name = anchor.get("聚合物分类名称")
    if isinstance(category_name, str) and category_name and category_name.lower() not in GENERIC_CATEGORY_NAMES:
        terms.append(category_name)

    patterns: list[tuple[str, re.Pattern[str]]] = []
    seen: set[str] = set()
    for term in terms:
        normalized = normalize_text(term)
        if not normalized:
            continue
        key = normalized.lower()
        if key in seen:
            continue
        seen.add(key)
        regex_term = _make_regex_term(normalized)
        if regex_term is not None:
            patterns.append(regex_term)
    return patterns


def build_family_patterns(anchor: dict[str, Any]) -> list[tuple[str, re.Pattern[str]]]:
    terms: list[str] = []

    category_code = anchor.get("聚合物分类编码")
    if isinstance(category_code, str) and category_code:
        terms.append(category_code)
        if "/" in category_code:
            terms.append(category_code.replace("/", "-"))
            terms.append(category_code.replace("/", " / "))

    category_name = anchor.get("聚合物分类名称")
    if isinstance(category_name, str) and category_name:
        terms.append(category_name)

    name = anchor.get("名称")
    if isinstance(name, str) and name:
        stripped = RATIO_PATTERN.sub("", name)
        stripped = normalize_text(stripped)
        if stripped:
            terms.append(stripped)

    patterns: list[tuple[str, re.Pattern[str]]] = []
    seen: set[str] = set()
    for term in terms:
        normalized = normalize_text(term)
        if not normalized:
            continue
        candidates = [normalized]
        candidates.extend(
            token
            for token in re.findall(r"\b[A-Z][A-Z0-9/+-]{1,}\b", normalized)
            if len(token) >= 2
        )
        for candidate in candidates:
            candidate_normalized = normalize_text(candidate)
            if not candidate_normalized:
                continue
            key = candidate_normalized.lower()
            if key in seen:
                continue
            seen.add(key)
            regex_term = _make_regex_term(candidate_normalized)
            if regex_term is not None:
                patterns.append(regex_term)
    return patterns


def anchor_has_variant_markers(anchor: dict[str, Any]) -> bool:
    texts = [
        anchor.get("名称"),
        anchor.get("聚合物分类编码"),
        anchor.get("聚合物分类名称"),
    ]
    joined = " ".join(text for text in texts if isinstance(text, str) and text)
    if not joined:
        return False
    return any(pattern.search(joined) for pattern in VARIANT_MARKER_PATTERNS)


def mentions_modified_variant_of_anchor(
    *,
    anchor: dict[str, Any],
    text: str,
    family_matches: list[str],
) -> bool:
    if not family_matches:
        return False
    if anchor_has_variant_markers(anchor):
        return False
    return any(pattern.search(text) for pattern in VARIANT_MARKER_PATTERNS)


def collect_anchor_matches(text: str, anchor_patterns: list[tuple[str, re.Pattern[str]]]) -> list[str]:
    matches: list[str] = []
    for label, pattern in anchor_patterns:
        if pattern.search(text):
            matches.append(label)
    return matches


def has_strong_direct_anchor_match(
    *,
    anchor: dict[str, Any],
    text: str,
    anchor_matches: list[str],
) -> bool:
    if not anchor_matches:
        return False
    if anchor_has_variant_markers(anchor):
        return True
    for label in anchor_matches:
        regex_term = _make_regex_term(label)
        if regex_term is None:
            continue
        _, pattern = regex_term
        for match in pattern.finditer(text):
            tail = text[match.end():]
            if VARIANT_TAIL_PATTERN.match(tail):
                continue
            return True
    return False


def collect_family_matches(text: str, family_patterns: list[tuple[str, re.Pattern[str]]]) -> list[str]:
    matches: list[str] = []
    for label, pattern in family_patterns:
        if pattern.search(text):
            matches.append(label)
    return matches


def collect_form_mentions(text: str) -> set[str]:
    lowered = text.lower()
    found: set[str] = set()
    for canonical, patterns in FORM_PATTERNS.items():
        if any(
            re.search(rf"(?<![a-z]){re.escape(pattern.lower())}(?![a-z])", lowered)
            for pattern in patterns
        ):
            found.add(canonical)
    return found


def expand_form_groups(forms: set[str]) -> set[str]:
    expanded = set(forms)
    expanded.update(FORM_GROUPS.get(form, form) for form in forms)
    return expanded


def is_precursor_fluid_anchor(anchor: dict[str, Any]) -> bool:
    anchor_form = normalize_text(anchor.get("样本形态"))
    if not anchor_form:
        return False
    return bool(collect_form_mentions(anchor_form).intersection(PRECURSOR_FLUID_FORMS))


def is_porous_body_anchor(anchor: dict[str, Any]) -> bool:
    return "PorousBody" in get_anchor_form_groups(anchor)


def get_anchor_form_groups(anchor: dict[str, Any]) -> set[str]:
    anchor_form = normalize_text(anchor.get("样本形态"))
    if not anchor_form:
        return set()
    return expand_form_groups(collect_form_mentions(anchor_form))


def extract_ratio_markers(text: str) -> set[str]:
    return {
        re.sub(r"\s+", "", match.group(0).lower())
        for match in RATIO_PATTERN.finditer(text)
    }


def has_excluded_result_signal(text: str) -> bool:
    return any(pattern.search(text) for pattern in EXCLUDE_WINDOW_PATTERNS)


def mentions_derived_other_form(anchor: dict[str, Any], text: str) -> bool:
    anchor_form = normalize_text(anchor.get("样本形态"))
    if not anchor_form:
        return False
    anchor_forms = collect_form_mentions(anchor_form)
    if not anchor_forms.intersection({"Ink", "Solution", "Gel"}):
        return False

    text_forms = collect_form_mentions(text)
    if not text_forms:
        return False
    if expand_form_groups(text_forms).issubset(expand_form_groups(anchor_forms)):
        return False
    if not any(pattern.search(text) for pattern in PROCESS_TRANSITION_PATTERNS):
        return False
    return True


def is_same_product_node_family_window(
    *,
    anchor: dict[str, Any],
    window_text: str,
    family_matches: list[str],
) -> bool:
    if not family_matches:
        return False
    anchor_form = normalize_text(anchor.get("样本形态"))
    if not anchor_form:
        return False
    anchor_forms = collect_form_mentions(anchor_form)
    if not anchor_forms:
        return False
    text_forms = collect_form_mentions(window_text)
    if not expand_form_groups(text_forms).intersection(expand_form_groups(anchor_forms)):
        return False
    return True


def is_same_precursor_family_property_window(
    *,
    anchor: dict[str, Any],
    window_text: str,
    family_matches: list[str],
) -> bool:
    if not family_matches:
        return False
    anchor_form = normalize_text(anchor.get("样本形态"))
    if not anchor_form:
        return False
    anchor_forms = collect_form_mentions(anchor_form)
    if not anchor_forms.intersection(PRECURSOR_FLUID_FORMS):
        return False
    labels = set(collect_property_labels(window_text))
    precursor_allowed_labels = set(FORM_GROUP_PROPERTY_PREFERENCES.get("PrecursorFluid", ()))
    if not labels.intersection(precursor_allowed_labels):
        return False
    return True


def is_relevant_same_family_window(
    *,
    anchor: dict[str, Any],
    window_text: str,
    family_matches: list[str],
) -> bool:
    return is_same_product_node_family_window(
        anchor=anchor,
        window_text=window_text,
        family_matches=family_matches,
    ) or is_same_precursor_family_property_window(
        anchor=anchor,
        window_text=window_text,
        family_matches=family_matches,
    )


def has_conflicting_ratio(anchor: dict[str, Any], window_text: str) -> bool:
    anchor_name = normalize_text(anchor.get("名称")) or ""
    anchor_ratios = extract_ratio_markers(anchor_name)
    window_ratios = extract_ratio_markers(window_text)
    if not anchor_ratios or not window_ratios:
        return False
    return not bool(anchor_ratios.intersection(window_ratios))


def has_conflicting_product_form(anchor: dict[str, Any], text: str) -> bool:
    anchor_form = normalize_text(anchor.get("样本形态"))
    if not anchor_form:
        return False
    anchor_forms = collect_form_mentions(anchor_form)
    if not anchor_forms:
        return False
    text_forms = collect_form_mentions(text)
    if not text_forms:
        return False
    return not bool(expand_form_groups(text_forms).intersection(expand_form_groups(anchor_forms)))


def should_exclude_result_window(*, anchor: dict[str, Any], window_text: str) -> bool:
    if mentions_derived_other_form(anchor, window_text):
        return True
    return has_excluded_result_signal(window_text)


def merge_ranges(ranges: list[tuple[int, int]]) -> list[tuple[int, int]]:
    if not ranges:
        return []
    sorted_ranges = sorted(ranges)
    merged: list[tuple[int, int]] = [sorted_ranges[0]]
    for start, end in sorted_ranges[1:]:
        last_start, last_end = merged[-1]
        if start <= last_end + 1:
            merged[-1] = (last_start, max(last_end, end))
        else:
            merged.append((start, end))
    return merged


def split_into_heading_segments(lines: list[str]) -> list[tuple[int, int]]:
    if not lines:
        return []
    heading_indices = [
        idx for idx, line in enumerate(lines)
        if idx > 0 and line.lstrip().startswith("#")
    ]
    if not heading_indices:
        return [(0, len(lines) - 1)]

    segments: list[tuple[int, int]] = []
    start_idx = 0
    for heading_idx in heading_indices:
        segments.append((start_idx, heading_idx - 1))
        start_idx = heading_idx
    segments.append((start_idx, len(lines) - 1))
    return segments


def extract_windows(
    *,
    section: dict[str, Any],
    route_role: str,
    anchor_patterns: list[tuple[str, re.Pattern[str]]],
    family_patterns: list[tuple[str, re.Pattern[str]]],
    radius: int,
    anchor: dict[str, Any],
    apply_result_filters: bool = True,
) -> list[dict[str, Any]]:
    lines = section["content"].splitlines()
    if not lines:
        return []

    line_infos: list[dict[str, Any]] = []
    seed_indices: list[int] = []
    for idx, line in enumerate(lines):
        keyword_labels = collect_property_labels(line)
        anchor_labels = collect_anchor_matches(line, anchor_patterns)
        strong_anchor = has_strong_direct_anchor_match(
            anchor=anchor,
            text=line,
            anchor_matches=anchor_labels,
        )
        line_infos.append(
            {
                "keyword_labels": keyword_labels,
                "anchor_labels": anchor_labels,
                "strong_anchor": strong_anchor,
            }
        )
        if route_role == "prop_methods":
            if keyword_labels:
                seed_indices.append(idx)
        elif keyword_labels:
            seed_indices.append(idx)

    if not seed_indices:
        return []

    if route_role != "prop_methods":
        focused_seed_indices: list[int] = []
        for idx in seed_indices:
            line = lines[idx]
            info = line_infos[idx]
            if info["anchor_labels"]:
                if not info["strong_anchor"] and mentions_modified_variant_of_anchor(
                    anchor=anchor,
                    text=line,
                    family_matches=collect_family_matches(line, family_patterns),
                ):
                    continue
                if has_conflicting_product_form(anchor, line):
                    continue
                focused_seed_indices.append(idx)
                continue

            family_matches = collect_family_matches(line, family_patterns)
            if (
                not mentions_modified_variant_of_anchor(
                    anchor=anchor,
                    text=line,
                    family_matches=family_matches,
                )
                and (
                    not has_conflicting_ratio(anchor, line)
                    or is_same_precursor_family_property_window(
                        anchor=anchor,
                        window_text=line,
                        family_matches=family_matches,
                    )
                )
                and is_relevant_same_family_window(
                    anchor=anchor,
                    window_text=line,
                    family_matches=family_matches,
                )
            ):
                focused_seed_indices.append(idx)

        if focused_seed_indices:
            seed_indices = focused_seed_indices

        if is_porous_body_anchor(anchor) and not anchor_has_variant_markers(anchor):
            anchor_seed_indices = [idx for idx in seed_indices if line_infos[idx]["strong_anchor"]]
            if anchor_seed_indices:
                seed_indices = anchor_seed_indices

    merged_ranges: list[tuple[int, int]] = []
    for segment_start, segment_end in split_into_heading_segments(lines):
        segment_seed_indices = [
            idx for idx in seed_indices
            if segment_start <= idx <= segment_end
        ]
        if not segment_seed_indices:
            continue
        ranges = []
        keep_independent_ranges = (
            route_role != "prop_methods"
            and is_porous_body_anchor(anchor)
            and not anchor_has_variant_markers(anchor)
            and all(line_infos[idx]["strong_anchor"] for idx in segment_seed_indices)
        )
        for idx in segment_seed_indices:
            effective_radius = radius
            if (
                route_role != "prop_methods"
                and line_infos[idx]["strong_anchor"]
                and not anchor_has_variant_markers(anchor)
            ):
                # For base objects, keep anchor-centered result windows tighter so nearby
                # composite/modified discussions in the same subsection do not dominate.
                effective_radius = min(effective_radius, 1)
            if route_role != "prop_methods" and is_precursor_fluid_anchor(anchor):
                line_labels = set(line_infos[idx]["keyword_labels"])
                precursor_allowed_labels = set(FORM_GROUP_PROPERTY_PREFERENCES.get("PrecursorFluid", ()))
                if line_labels.intersection(precursor_allowed_labels):
                    effective_radius = min(radius, 1)
            ranges.append(
                (max(segment_start, idx - effective_radius), min(segment_end, idx + effective_radius))
            )
        if keep_independent_ranges:
            merged_ranges.extend(ranges)
        else:
            merged_ranges.extend(merge_ranges(ranges))

    section_start_line = int(section["line_span"][0])
    windows: list[dict[str, Any]] = []
    for window_index, (start_idx, end_idx) in enumerate(merged_ranges, start=1):
        info_slice = line_infos[start_idx : end_idx + 1]
        matched_keywords = sorted(
            {label for info in info_slice for label in info["keyword_labels"]}
        )
        matched_anchors = sorted(
            {label for info in info_slice for label in info["anchor_labels"]}
        )
        if route_role != "prop_methods" and not matched_keywords:
            continue

        excerpt_lines = [
            f"{section_start_line + idx}: {lines[idx]}"
            for idx in range(start_idx, end_idx + 1)
        ]
        window_text = "\n".join(excerpt_lines).strip()
        matched_family = collect_family_matches(window_text, family_patterns)
        conflicting_ratio = has_conflicting_ratio(anchor, window_text)
        strong_anchor_window = has_strong_direct_anchor_match(
            anchor=anchor,
            text=window_text,
            anchor_matches=matched_anchors,
        )
        if route_role != "prop_methods" and apply_result_filters:
            if should_exclude_result_window(anchor=anchor, window_text=window_text):
                continue
        if (
            route_role != "prop_methods"
            and not strong_anchor_window
            and mentions_modified_variant_of_anchor(
                anchor=anchor,
                text=window_text,
                family_matches=matched_family,
            )
        ):
            continue
        windows.append(
            {
                "block_id": section["block_id"],
                "chunk_index": section["chunk_index"],
                "section_title": section["section_title"],
                "route_role": route_role,
                "window_index": window_index,
                "line_span": [section_start_line + start_idx, section_start_line + end_idx],
                "matched_keywords": matched_keywords,
                "matched_anchors": matched_anchors,
                "matched_family": matched_family,
                "conflicting_ratio": conflicting_ratio,
                "text": window_text,
            }
        )
    return windows


def collect_section_labels(section: dict[str, Any]) -> list[str]:
    labels: set[str] = set()
    title = section.get("section_title") or ""
    labels.update(collect_property_labels(title))
    for line in section["content"].splitlines():
        labels.update(collect_property_labels(line))
    return sorted(labels)


def make_full_section_excerpt(
    *,
    section: dict[str, Any],
    route_role: str,
    anchor_patterns: list[tuple[str, re.Pattern[str]]],
    section_index: int,
) -> dict[str, Any]:
    lines = section["content"].splitlines()
    section_start_line = int(section["line_span"][0])
    matched_anchors = sorted(
        {
            label
            for line in lines
            for label in collect_anchor_matches(line, anchor_patterns)
        }
    )
    excerpt_lines = [f"{section_start_line + idx}: {line}" for idx, line in enumerate(lines)]
    return {
        "block_id": section["block_id"],
        "chunk_index": section["chunk_index"],
        "section_title": section["section_title"],
        "route_role": route_role,
        "window_index": section_index,
        "line_span": list(section["line_span"]),
        "matched_keywords": collect_section_labels(section),
        "matched_anchors": matched_anchors,
        "text": "\n".join(excerpt_lines).strip(),
    }


def build_full_section_excerpts(
    *,
    sections: list[dict[str, Any]],
    route_role: str,
    anchor_patterns: list[tuple[str, re.Pattern[str]]],
) -> list[dict[str, Any]]:
    excerpts: list[dict[str, Any]] = []
    for idx, section in enumerate(sections, start=1):
        excerpts.append(
            make_full_section_excerpt(
                section=section,
                route_role=route_role,
                anchor_patterns=anchor_patterns,
                section_index=idx,
            )
        )
    return excerpts


def filter_windows_by_allowed_labels(
    windows: list[dict[str, Any]],
    allowed_labels: set[str],
) -> list[dict[str, Any]]:
    if not allowed_labels:
        return []
    filtered: list[dict[str, Any]] = []
    for window in windows:
        matched = [label for label in window["matched_keywords"] if label in allowed_labels]
        if not matched:
            continue
        window_copy = dict(window)
        window_copy["matched_keywords"] = matched
        filtered.append(window_copy)
    return filtered


def filter_method_windows_by_section_title(
    windows: list[dict[str, Any]],
    allowed_labels: set[str],
) -> list[dict[str, Any]]:
    if not allowed_labels:
        return []
    filtered: list[dict[str, Any]] = []
    for window in windows:
        title_labels = set(collect_property_labels(window.get("section_title", "")))
        if title_labels and not title_labels.intersection(allowed_labels):
            continue
        filtered.append(window)
    return filtered


def collect_result_property_hints(
    *,
    result_sections: list[dict[str, Any]],
    anchor_patterns: list[tuple[str, re.Pattern[str]]],
    family_patterns: list[tuple[str, re.Pattern[str]]],
    anchor: dict[str, Any],
) -> list[str]:
    hints: set[str] = set()
    for section in result_sections:
        full_text = section["content"]
        family_matches = collect_family_matches(full_text, family_patterns)
        relevant = bool(collect_anchor_matches(full_text, anchor_patterns))
        if not relevant:
            relevant = (
                not has_conflicting_ratio(anchor, full_text)
                and is_same_product_node_family_window(
                    anchor=anchor,
                    window_text=full_text,
                    family_matches=family_matches,
                )
            )
        if not relevant:
            continue
        if mentions_derived_other_form(anchor, full_text):
            continue
        hints.update(collect_property_labels(section.get("section_title", "")))
    return sorted(hints)


def strip_excerpt_prefix(line: str) -> str:
    return re.sub(r"^\d+:\s*", "", line).strip()


def collect_window_property_hints(
    *,
    result_windows: list[dict[str, Any]],
    anchor_patterns: list[tuple[str, re.Pattern[str]]],
    family_patterns: list[tuple[str, re.Pattern[str]]],
    anchor: dict[str, Any],
) -> list[str]:
    hints: set[str] = set()
    for window in result_windows:
        for raw_line in window["text"].splitlines():
            line = strip_excerpt_prefix(raw_line)
            if not line:
                continue
            labels = collect_property_labels(line)
            if not labels:
                continue

            anchor_matches = collect_anchor_matches(line, anchor_patterns)
            family_matches = collect_family_matches(line, family_patterns)
            same_family = (
                not mentions_modified_variant_of_anchor(
                    anchor=anchor,
                    text=line,
                    family_matches=family_matches,
                )
                and (
                    not has_conflicting_ratio(anchor, line)
                    or is_same_precursor_family_property_window(
                        anchor=anchor,
                        window_text=line,
                        family_matches=family_matches,
                    )
                )
                and is_relevant_same_family_window(
                    anchor=anchor,
                    window_text=line,
                    family_matches=family_matches,
                )
            )

            if anchor_matches or same_family:
                hints.update(labels)
                continue
            if CAPTION_LINE_PATTERN.match(line) or line.lstrip().startswith("#"):
                if same_family:
                    hints.update(labels)
    return sorted(hints)


def build_method_excerpts(
    *,
    method_sections: list[dict[str, Any]],
    anchor_patterns: list[tuple[str, re.Pattern[str]]],
    family_patterns: list[tuple[str, re.Pattern[str]]],
    anchor: dict[str, Any],
    allowed_property_labels: list[str],
    method_window_lines: int = 4,
) -> list[dict[str, Any]]:
    allowed_set = set(allowed_property_labels)
    if not method_sections or not allowed_set:
        return []

    windows: list[dict[str, Any]] = []
    for section in method_sections:
        section_windows = extract_windows(
            section=section,
            route_role="prop_methods",
            anchor_patterns=anchor_patterns,
            family_patterns=family_patterns,
            radius=method_window_lines,
            anchor=anchor,
            apply_result_filters=False,
        )
        windows.extend(
            filter_method_windows_by_section_title(
                filter_windows_by_allowed_labels(section_windows, allowed_set),
                allowed_set,
            )
        )
    if windows:
        windows.sort(key=lambda item: (item["chunk_index"], item["line_span"][0], item["window_index"]))
        return windows

    narrowed_sections = [
        section
        for section in method_sections
        if allowed_set.intersection(collect_property_labels(section.get("section_title", "")))
    ]
    if narrowed_sections:
        return build_full_section_excerpts(
            sections=sorted(narrowed_sections, key=lambda item: item["chunk_index"]),
            route_role="prop_methods_full",
            anchor_patterns=anchor_patterns,
        )

    return []


def build_porous_body_result_fallback(
    *,
    result_candidate_sections: list[dict[str, Any]],
    anchor_patterns: list[tuple[str, re.Pattern[str]]],
    family_patterns: list[tuple[str, re.Pattern[str]]],
    anchor: dict[str, Any],
    radius: int,
) -> list[dict[str, Any]]:
    allowed_labels = set(FORM_GROUP_PROPERTY_PREFERENCES.get("PorousBody", ()))
    if not result_candidate_sections or not allowed_labels:
        return []

    windows: list[dict[str, Any]] = []
    fallback_radius = min(radius, 2)
    for section in result_candidate_sections:
        section_windows = extract_windows(
            section=section,
            route_role="prop_results",
            anchor_patterns=anchor_patterns,
            family_patterns=family_patterns,
            radius=fallback_radius,
            anchor=anchor,
            apply_result_filters=True,
        )
        windows.extend(filter_windows_by_allowed_labels(section_windows, allowed_labels))

    windows.sort(key=lambda item: (item["chunk_index"], item["line_span"][0], item["window_index"]))
    return windows


def build_source_refs(
    *,
    method_windows: list[dict[str, Any]],
    result_windows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for window in [*method_windows, *result_windows]:
        refs.append(
            {
                "block_id": window["block_id"],
                "chunk_index": window["chunk_index"],
                "section_title": window["section_title"],
                "route_role": window["route_role"],
                "window_index": window["window_index"],
                "line_span": window["line_span"],
                "matched_keywords": window["matched_keywords"],
                "matched_anchors": window["matched_anchors"],
                "matched_family": window.get("matched_family", []),
            }
        )
    return refs


def render_polymer_anchor_text(anchor: dict[str, Any]) -> str:
    lines = [
        f"身份标识: {anchor.get('身份标识') or ''}",
        f"名称: {anchor.get('名称') or ''}",
        f"别名: {', '.join(anchor.get('别名') or [])}",
        f"聚合物分类编码: {anchor.get('聚合物分类编码') or ''}",
        f"聚合物分类名称: {anchor.get('聚合物分类名称') or ''}",
        f"样本形态: {anchor.get('样本形态') or ''}",
    ]
    return "\n".join(lines).strip()


def render_windows(tag: str, windows: list[dict[str, Any]]) -> str:
    if not windows:
        return f"[{tag}]\n"

    items: list[str] = []
    for idx, window in enumerate(windows, start=1):
        line_start, line_end = window["line_span"]
        keywords = ", ".join(window["matched_keywords"])
        anchors = ", ".join(window["matched_anchors"])
        family = ", ".join(window.get("matched_family", []))
        header = (
            f"## excerpt {idx} | block={window['block_id']} | "
            f"section={window['section_title']} | lines={line_start}-{line_end}"
        )
        details = []
        if keywords:
            details.append(f"keywords={keywords}")
        if anchors:
            details.append(f"anchors={anchors}")
        if family:
            details.append(f"family={family}")
        if details:
            header = f"{header} | {'; '.join(details)}"
        items.append(f"{header}\n{window['text']}")
    return f"[{tag}]\n" + "\n\n".join(items).strip()


def render_result_property_hints(result_property_hints: list[str]) -> str:
    if not result_property_hints:
        return "[RESULT_PROPERTY_HINTS]\n"
    return "[RESULT_PROPERTY_HINTS]\n" + ", ".join(result_property_hints)


def render_property_text(
    *,
    anchor: dict[str, Any],
    method_windows: list[dict[str, Any]],
    result_windows: list[dict[str, Any]],
    result_property_hints: list[str],
) -> str:
    parts = [f"[POLYMER_ANCHOR]\n{render_polymer_anchor_text(anchor)}"]
    parts.append(render_result_property_hints(result_property_hints))
    parts.append(render_windows("PROPERTY_METHODS", method_windows))
    parts.append(render_windows("PROPERTY_RESULTS", result_windows))
    return "\n\n".join(part.strip() for part in parts if part.strip()).strip()


def select_property_hints_for_anchor(
    *,
    anchor: dict[str, Any],
    result_property_hints: list[str],
) -> list[str]:
    if not result_property_hints:
        return []
    allowed: set[str] = set()
    for group in get_anchor_form_groups(anchor):
        allowed.update(FORM_GROUP_PROPERTY_PREFERENCES.get(group, ()))
    if not allowed:
        return result_property_hints
    narrowed = [label for label in result_property_hints if label in allowed]
    return narrowed or result_property_hints


def route_property_context(
    *,
    sections: list[dict[str, Any]],
    anchor: dict[str, Any],
    result_window_lines: int,
) -> dict[str, Any]:
    anchor_patterns = build_anchor_patterns(anchor)
    family_patterns = build_family_patterns(anchor)
    method_sections: list[dict[str, Any]] = []
    result_candidate_sections: list[dict[str, Any]] = []
    property_title_sections: list[dict[str, Any]] = []
    result_windows: list[dict[str, Any]] = []
    raw_result_window_count = 0

    for section in sections:
        if is_ignored_section(section):
            continue
        if is_method_section(section):
            method_sections.append(section)
            continue
        if is_front_matter_section(section):
            continue
        if is_results_section(section) or has_property_title(section):
            result_candidate_sections.append(section)
            if has_property_title(section):
                property_title_sections.append(section)
            raw_windows = extract_windows(
                section=section,
                route_role="prop_results",
                anchor_patterns=anchor_patterns,
                family_patterns=family_patterns,
                radius=result_window_lines,
                anchor=anchor,
                apply_result_filters=False,
            )
            raw_result_window_count += len(raw_windows)
            result_windows.extend(
                extract_windows(
                    section=section,
                    route_role="prop_results",
                    anchor_patterns=anchor_patterns,
                    family_patterns=family_patterns,
                    radius=result_window_lines,
                    anchor=anchor,
                    apply_result_filters=True,
                )
            )

    if any(window["matched_anchors"] for window in result_windows):
        strong_anchor_windows = [window for window in result_windows if window["matched_anchors"]]
        same_family_general_windows = [
            window
            for window in result_windows
            if not window["matched_anchors"]
            and (
                not window.get("conflicting_ratio", False)
                or is_same_precursor_family_property_window(
                    anchor=anchor,
                    window_text=window["text"],
                    family_matches=window.get("matched_family", []),
                )
            )
            and not mentions_modified_variant_of_anchor(
                anchor=anchor,
                text=window["text"],
                family_matches=window.get("matched_family", []),
            )
            and is_relevant_same_family_window(
                anchor=anchor,
                window_text=window["text"],
                family_matches=window.get("matched_family", []),
            )
        ]
        result_windows = strong_anchor_windows + same_family_general_windows

    result_windows.sort(key=lambda item: (item["chunk_index"], item["line_span"][0], item["window_index"]))
    used_result_fallback = False
    result_excerpts = result_windows
    if not result_excerpts and raw_result_window_count > 0 and is_porous_body_anchor(anchor):
        fallback_windows = build_porous_body_result_fallback(
            result_candidate_sections=result_candidate_sections,
            anchor_patterns=anchor_patterns,
            family_patterns=family_patterns,
            anchor=anchor,
            radius=result_window_lines,
        )
        if fallback_windows:
            used_result_fallback = True
            result_excerpts = fallback_windows
    if not result_excerpts and property_title_sections and raw_result_window_count == 0:
        used_result_fallback = True
        result_excerpts = build_full_section_excerpts(
            sections=sorted(property_title_sections, key=lambda item: item["chunk_index"]),
            route_role="prop_results_full",
            anchor_patterns=anchor_patterns,
        )

    result_property_hints = collect_window_property_hints(
        result_windows=result_excerpts,
        anchor_patterns=anchor_patterns,
        family_patterns=family_patterns,
        anchor=anchor,
    )
    selected_property_hints = select_property_hints_for_anchor(
        anchor=anchor,
        result_property_hints=result_property_hints,
    )
    if selected_property_hints:
        result_excerpts = filter_windows_by_allowed_labels(result_excerpts, set(selected_property_hints))
    result_property_hints = selected_property_hints
    method_excerpts = build_method_excerpts(
        method_sections=method_sections,
        anchor_patterns=anchor_patterns,
        family_patterns=family_patterns,
        anchor=anchor,
        allowed_property_labels=result_property_hints,
    )

    return {
        "method_excerpts": method_excerpts,
        "result_excerpts": result_excerpts,
        "result_property_hints": result_property_hints,
        "used_result_fallback": used_result_fallback,
        "source_refs": build_source_refs(
            method_windows=method_excerpts,
            result_windows=result_excerpts,
        ),
    }


def build_property_task(
    *,
    run_id: str,
    doc_id: str,
    file_name: str,
    polymer: dict[str, Any],
    polymer_index: int,
    sections: list[dict[str, Any]],
    result_window_lines: int,
) -> dict[str, Any]:
    anchor = build_polymer_anchor(polymer)
    route = route_property_context(
        sections=sections,
        anchor=anchor,
        result_window_lines=result_window_lines,
    )
    return {
        "run_id": run_id,
        "doc_id": doc_id,
        "sample_id": anchor.get("身份标识"),
        "task_id": f"{run_id}__{doc_id}__{polymer_index:03d}__property",
        "file_name": file_name,
        "polymer_anchor": anchor,
        "source_refs": route["source_refs"],
        "chain_input": {
            "text": render_property_text(
                anchor=anchor,
                method_windows=route["method_excerpts"],
                result_windows=route["result_excerpts"],
                result_property_hints=route["result_property_hints"],
            )
        },
        "route_stats": {
            "method_window_count": len(route["method_excerpts"]),
            "result_window_count": len(route["result_excerpts"]),
            "used_result_fallback": route["used_result_fallback"],
        },
    }
