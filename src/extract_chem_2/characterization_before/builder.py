from __future__ import annotations

import re
import tomllib
from pathlib import Path
from typing import Any

CONFIG_PATH = Path(__file__).resolve().parents[3] / "configs" / "characterization.toml"


def _load_route_config() -> tuple[
    tuple[str, ...],
    tuple[str, ...],
    tuple[str, ...],
    tuple[tuple[str, re.Pattern[str]], ...],
    tuple[re.Pattern[str], ...],
    tuple[re.Pattern[str], ...],
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

    comparative_patterns: list[re.Pattern[str]] = []
    for pattern in config.get("comparative_patterns", {}).get("side_mention", []):
        comparative_patterns.append(re.compile(str(pattern), re.IGNORECASE))

    return (
        method_titles,
        result_titles,
        ignore_titles,
        tuple(keyword_patterns),
        tuple(exclude_patterns),
        tuple(comparative_patterns),
    )


(
    METHOD_TITLE_PATTERNS,
    RESULT_TITLE_PATTERNS,
    IGNORE_TITLE_PATTERNS,
    CHAR_KEYWORD_PATTERNS,
    EXCLUDE_WINDOW_PATTERNS,
    COMPARATIVE_SIDE_PATTERNS,
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
}
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


def has_characterization_title(section: dict[str, Any]) -> bool:
    title = normalize_title(section["section_title"])
    if is_ignored_section(section):
        return False
    if is_method_section(section) or is_results_section(section):
        return True
    return any(pattern.search(title) for _, pattern in CHAR_KEYWORD_PATTERNS)


def collect_characterization_labels(text: str) -> list[str]:
    labels: list[str] = []
    for label, pattern in CHAR_KEYWORD_PATTERNS:
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
        # Treat "/", "+", "-" as part of the token boundary so short codes like
        # "PI" do not spuriously match composite codes such as "PI/AuNPs".
        pattern = re.compile(rf"(?<![A-Za-z0-9/+-]){re.escape(clean)}(?![A-Za-z0-9/+-])")
    else:
        pattern = re.compile(re.escape(clean), re.IGNORECASE)
    return clean, pattern


def build_anchor_patterns(anchor: dict[str, Any]) -> list[tuple[str, re.Pattern[str]]]:
    terms: list[str] = []
    name = anchor.get("名称")
    if isinstance(name, str) and name:
        terms.append(name)
    aliases = anchor.get("别名") or []
    if isinstance(aliases, list):
        terms.extend(str(item) for item in aliases if normalize_text(item))

    category_code = anchor.get("聚合物分类编码")
    if isinstance(category_code, str) and category_code:
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


def collect_anchor_matches(text: str, anchor_patterns: list[tuple[str, re.Pattern[str]]]) -> list[str]:
    matches: list[str] = []
    for label, pattern in anchor_patterns:
        if pattern.search(text):
            matches.append(label)
    return matches


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
            re.search(rf"(?<![a-z]){re.escape(pattern.lower())}(?:s|es)?(?![a-z])", lowered)
            for pattern in patterns
        ):
            found.add(canonical)
    return found


def extract_ratio_markers(text: str) -> set[str]:
    return {
        re.sub(r"\s+", "", match.group(0).lower())
        for match in RATIO_PATTERN.finditer(text)
    }


def has_excluded_result_signal(text: str) -> bool:
    return any(pattern.search(text) for pattern in EXCLUDE_WINDOW_PATTERNS)


def has_comparative_side_signal(text: str) -> bool:
    return any(pattern.search(text) for pattern in COMPARATIVE_SIDE_PATTERNS)


def has_direct_characterization_anchor_support(
    *,
    anchor_patterns: list[tuple[str, re.Pattern[str]]],
    family_patterns: list[tuple[str, re.Pattern[str]]],
    anchor: dict[str, Any],
    matched_keywords: list[str],
    window_text: str,
) -> bool:
    matched_set = set(matched_keywords)
    for raw_line in window_text.splitlines():
        line = strip_excerpt_prefix(raw_line)
        if not line:
            continue
        line_labels = set(collect_characterization_labels(line))
        if not line_labels.intersection(matched_set):
            continue
        if has_excluded_result_signal(line) and has_comparative_side_signal(line):
            continue
        anchor_matches = collect_anchor_matches(line, anchor_patterns)
        family_matches = collect_family_matches(line, family_patterns)
        same_family = (
            not has_conflicting_ratio(anchor, line)
            and is_same_product_node_family_window(
                anchor=anchor,
                window_text=line,
                family_matches=family_matches,
            )
        )
        same_node_morphology = is_same_product_node_generic_morphology_window(
            anchor=anchor,
            window_text=line,
            matched_keywords=list(line_labels),
        )
        if not (anchor_matches or same_family or same_node_morphology):
            continue
        if CAPTION_LINE_PATTERN.match(line) or line.lstrip().startswith("#"):
            return True
        if not has_excluded_result_signal(line):
            return True
    return False


def is_comparative_side_characterization_window(
    *,
    anchor_patterns: list[tuple[str, re.Pattern[str]]],
    family_patterns: list[tuple[str, re.Pattern[str]]],
    anchor: dict[str, Any],
    matched_keywords: list[str],
    window_text: str,
) -> bool:
    target_labels = set(matched_keywords).intersection({"Morphology", "BET"})
    if not target_labels:
        return False
    if not has_excluded_result_signal(window_text):
        return False
    if not has_comparative_side_signal(window_text):
        return False
    if has_direct_characterization_anchor_support(
        anchor_patterns=anchor_patterns,
        family_patterns=family_patterns,
        anchor=anchor,
        matched_keywords=list(target_labels),
        window_text=window_text,
    ):
        return False
    return True


def should_exclude_result_window(
    *,
    anchor: dict[str, Any],
    anchor_patterns: list[tuple[str, re.Pattern[str]]],
    family_patterns: list[tuple[str, re.Pattern[str]]],
    matched_keywords: list[str],
    window_text: str,
) -> bool:
    if mentions_derived_other_form(anchor, window_text):
        return True
    if is_comparative_side_characterization_window(
        anchor_patterns=anchor_patterns,
        family_patterns=family_patterns,
        anchor=anchor,
        matched_keywords=matched_keywords,
        window_text=window_text,
    ):
        return True
    if not has_excluded_result_signal(window_text):
        return False

    # Morphology windows often co-occur with shrinkage/shape-fidelity discussion
    # for the same final product node. Keep them for final-form objects, but do
    # not relax this for precursor-like forms such as ink/solution/gel.
    anchor_form = normalize_text(anchor.get("样本形态")) or ""
    anchor_forms = collect_form_mentions(anchor_form)
    if "Morphology" in matched_keywords and not anchor_forms.intersection({"Ink", "Solution", "Gel"}):
        return False
    return True


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
    if text_forms.issubset(anchor_forms):
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
    if not text_forms.intersection(anchor_forms):
        return False
    return True


def is_same_product_node_generic_morphology_window(
    *,
    anchor: dict[str, Any],
    window_text: str,
    matched_keywords: list[str],
) -> bool:
    if "Morphology" not in matched_keywords:
        return False
    anchor_form = normalize_text(anchor.get("样本形态"))
    if not anchor_form:
        return False
    anchor_forms = collect_form_mentions(anchor_form)
    if not anchor_forms or anchor_forms.intersection({"Ink", "Solution", "Gel"}):
        return False
    text_forms = collect_form_mentions(window_text)
    return bool(text_forms.intersection(anchor_forms))


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
    return not bool(text_forms.intersection(anchor_forms))


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


def has_nearby_anchor_support(
    *,
    lines: list[str],
    seed_idx: int,
    segment_start: int,
    segment_end: int,
    anchor_patterns: list[tuple[str, re.Pattern[str]]],
    family_patterns: list[tuple[str, re.Pattern[str]]],
    anchor: dict[str, Any],
    radius: int,
) -> bool:
    start_idx = max(segment_start, seed_idx - radius)
    end_idx = min(segment_end, seed_idx + radius)
    window_lines = lines[start_idx : end_idx + 1]
    window_text = "\n".join(window_lines)
    if has_conflicting_product_form(anchor, window_text):
        return False
    if collect_anchor_matches(window_text, anchor_patterns):
        return True
    family_matches = collect_family_matches(window_text, family_patterns)
    if (
        not has_conflicting_ratio(anchor, window_text)
        and is_same_product_node_family_window(
            anchor=anchor,
            window_text=window_text,
            family_matches=family_matches,
        )
    ):
        return True
    return False


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
        keyword_labels = collect_characterization_labels(line)
        anchor_labels = collect_anchor_matches(line, anchor_patterns)
        line_infos.append(
            {
                "keyword_labels": keyword_labels,
                "anchor_labels": anchor_labels,
            }
        )
        if route_role == "char_methods":
            if keyword_labels:
                seed_indices.append(idx)
        elif keyword_labels:
            seed_indices.append(idx)

    if not seed_indices:
        return []

    if route_role != "char_methods":
        focused_seed_indices: list[int] = []
        for idx in seed_indices:
            line = lines[idx]
            info = line_infos[idx]
            if info["anchor_labels"]:
                if has_conflicting_product_form(anchor, line):
                    continue
                focused_seed_indices.append(idx)
                continue

            family_matches = collect_family_matches(line, family_patterns)
            if (
                not has_conflicting_ratio(anchor, line)
                and is_same_product_node_family_window(
                    anchor=anchor,
                    window_text=line,
                    family_matches=family_matches,
                )
            ):
                focused_seed_indices.append(idx)
                continue

            if is_same_product_node_generic_morphology_window(
                anchor=anchor,
                window_text=line,
                matched_keywords=info["keyword_labels"],
            ):
                focused_seed_indices.append(idx)
                continue

            if CAPTION_LINE_PATTERN.match(line) or line.lstrip().startswith("#"):
                for segment_start, segment_end in split_into_heading_segments(lines):
                    if not (segment_start <= idx <= segment_end):
                        continue
                    if has_nearby_anchor_support(
                        lines=lines,
                        seed_idx=idx,
                        segment_start=segment_start,
                        segment_end=segment_end,
                        anchor_patterns=anchor_patterns,
                        family_patterns=family_patterns,
                        anchor=anchor,
                        radius=radius,
                    ):
                        focused_seed_indices.append(idx)
                    break

        if focused_seed_indices:
            seed_indices = focused_seed_indices

    merged_ranges: list[tuple[int, int]] = []
    for segment_start, segment_end in split_into_heading_segments(lines):
        segment_seed_indices = [
            idx for idx in seed_indices
            if segment_start <= idx <= segment_end
        ]
        if not segment_seed_indices:
            continue
        ranges = [
            (max(segment_start, idx - radius), min(segment_end, idx + radius))
            for idx in segment_seed_indices
        ]
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
        if route_role != "char_methods" and not matched_keywords:
            continue

        excerpt_lines = [
            f"{section_start_line + idx}: {lines[idx]}"
            for idx in range(start_idx, end_idx + 1)
        ]
        window_text = "\n".join(excerpt_lines).strip()
        matched_family = collect_family_matches(window_text, family_patterns)
        conflicting_ratio = has_conflicting_ratio(anchor, window_text)
        if route_role != "char_methods" and apply_result_filters:
            if should_exclude_result_window(
                anchor=anchor,
                anchor_patterns=anchor_patterns,
                family_patterns=family_patterns,
                matched_keywords=matched_keywords,
                window_text=window_text,
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
    labels.update(collect_characterization_labels(title))
    for line in section["content"].splitlines():
        labels.update(collect_characterization_labels(line))
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
    excerpt_lines = [
        f"{section_start_line + idx}: {line}"
        for idx, line in enumerate(lines)
    ]
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


def collect_result_method_hints(
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
            relevant = is_same_product_node_family_window(
                anchor=anchor,
                window_text=full_text,
                family_matches=family_matches,
            )
        title_labels = collect_characterization_labels(section.get("section_title", ""))
        if not relevant:
            relevant = is_same_product_node_generic_morphology_window(
                anchor=anchor,
                window_text=full_text,
                matched_keywords=title_labels,
            )
        if not relevant:
            continue
        if mentions_derived_other_form(anchor, full_text):
            continue

        hints.update(title_labels)

    return sorted(hints)


def strip_excerpt_prefix(line: str) -> str:
    return re.sub(r"^\d+:\s*", "", line).strip()


def collect_window_method_hints(
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
            labels = collect_characterization_labels(line)
            if not labels:
                continue

            anchor_matches = collect_anchor_matches(line, anchor_patterns)
            family_matches = collect_family_matches(line, family_patterns)
            same_family = (
                not has_conflicting_ratio(anchor, line)
                and is_same_product_node_family_window(
                    anchor=anchor,
                    window_text=line,
                    family_matches=family_matches,
                )
            )
            same_node_morphology = is_same_product_node_generic_morphology_window(
                anchor=anchor,
                window_text=line,
                matched_keywords=labels,
            )

            if anchor_matches or same_family:
                hints.update(labels)
                continue
            if CAPTION_LINE_PATTERN.match(line) or line.lstrip().startswith("#"):
                if same_family or same_node_morphology:
                    hints.update(labels)
                continue
            if same_node_morphology:
                hints.update(label for label in labels if label == "Morphology")
    return sorted(hints)


def build_method_excerpts(
    *,
    method_sections: list[dict[str, Any]],
    anchor_patterns: list[tuple[str, re.Pattern[str]]],
    family_patterns: list[tuple[str, re.Pattern[str]]],
    anchor: dict[str, Any],
    allowed_method_labels: list[str],
    method_window_lines: int = 4,
) -> list[dict[str, Any]]:
    allowed_set = set(allowed_method_labels)
    if not method_sections:
        return []

    if not allowed_set:
        return []

    windows: list[dict[str, Any]] = []
    for section in method_sections:
        section_windows = extract_windows(
            section=section,
            route_role="char_methods",
            anchor_patterns=anchor_patterns,
            family_patterns=family_patterns,
            radius=method_window_lines,
            anchor=anchor,
            apply_result_filters=False,
        )
        windows.extend(filter_windows_by_allowed_labels(section_windows, allowed_set))
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


def render_result_method_hints(result_method_hints: list[str]) -> str:
    if not result_method_hints:
        return "[RESULT_METHOD_HINTS]\n"
    return "[RESULT_METHOD_HINTS]\n" + ", ".join(result_method_hints)


def render_characterization_text(
    *,
    anchor: dict[str, Any],
    method_windows: list[dict[str, Any]],
    result_windows: list[dict[str, Any]],
    result_method_hints: list[str],
) -> str:
    parts = [f"[POLYMER_ANCHOR]\n{render_polymer_anchor_text(anchor)}"]
    parts.append(render_result_method_hints(result_method_hints))
    parts.append(render_windows("CHAR_METHODS", method_windows))
    parts.append(render_windows("CHAR_RESULTS", result_windows))
    return "\n\n".join(part.strip() for part in parts if part.strip()).strip()


def route_characterization_context(
    *,
    sections: list[dict[str, Any]],
    anchor: dict[str, Any],
    result_window_lines: int,
) -> dict[str, Any]:
    anchor_patterns = build_anchor_patterns(anchor)
    family_patterns = build_family_patterns(anchor)
    method_sections: list[dict[str, Any]] = []
    result_candidate_sections: list[dict[str, Any]] = []
    result_windows: list[dict[str, Any]] = []
    raw_result_window_count = 0

    for section in sections:
        if is_ignored_section(section):
            continue
        if is_method_section(section):
            method_sections.append(section)
            continue
        if is_results_section(section) or has_characterization_title(section):
            result_candidate_sections.append(section)
            raw_windows = extract_windows(
                section=section,
                route_role="char_results",
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
                    route_role="char_results",
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
            and not window.get("conflicting_ratio", False)
            and (
                is_same_product_node_family_window(
                    anchor=anchor,
                    window_text=window["text"],
                    family_matches=window.get("matched_family", []),
                )
                or is_same_product_node_generic_morphology_window(
                    anchor=anchor,
                    window_text=window["text"],
                    matched_keywords=window.get("matched_keywords", []),
                )
            )
        ]
        result_windows = strong_anchor_windows + same_family_general_windows
    result_windows.sort(key=lambda item: (item["chunk_index"], item["line_span"][0], item["window_index"]))
    used_result_fallback = False
    result_excerpts = result_windows
    if not result_excerpts and result_candidate_sections and raw_result_window_count == 0:
        used_result_fallback = True
        result_excerpts = build_full_section_excerpts(
            sections=sorted(result_candidate_sections, key=lambda item: item["chunk_index"]),
            route_role="char_results_full",
            anchor_patterns=anchor_patterns,
        )

    result_method_hints = sorted(
        {
            *collect_result_method_hints(
                result_sections=result_candidate_sections,
                anchor_patterns=anchor_patterns,
                family_patterns=family_patterns,
                anchor=anchor,
            ),
            *collect_window_method_hints(
                result_windows=result_excerpts,
                anchor_patterns=anchor_patterns,
                family_patterns=family_patterns,
                anchor=anchor,
            ),
        }
    )
    method_excerpts = build_method_excerpts(
        method_sections=method_sections,
        anchor_patterns=anchor_patterns,
        family_patterns=family_patterns,
        anchor=anchor,
        allowed_method_labels=result_method_hints,
    )

    return {
        "method_excerpts": method_excerpts,
        "result_excerpts": result_excerpts,
        "result_method_hints": result_method_hints,
        "used_result_fallback": used_result_fallback,
        "source_refs": build_source_refs(
            method_windows=method_excerpts,
            result_windows=result_excerpts,
        ),
    }


def build_characterization_task(
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
    route = route_characterization_context(
        sections=sections,
        anchor=anchor,
        result_window_lines=result_window_lines,
    )
    return {
        "run_id": run_id,
        "doc_id": doc_id,
        "sample_id": anchor.get("身份标识"),
        "task_id": f"{run_id}__{doc_id}__{polymer_index:03d}__characterization",
        "file_name": file_name,
        "polymer_anchor": anchor,
        "source_refs": route["source_refs"],
        "chain_input": {
            "text": render_characterization_text(
                anchor=anchor,
                method_windows=route["method_excerpts"],
                result_windows=route["result_excerpts"],
                result_method_hints=route["result_method_hints"],
            )
        },
        "route_stats": {
            "method_window_count": len(route["method_excerpts"]),
            "result_window_count": len(route["result_excerpts"]),
            "used_result_fallback": route["used_result_fallback"],
        },
    }
