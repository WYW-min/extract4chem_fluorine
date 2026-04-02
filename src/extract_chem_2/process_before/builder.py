from __future__ import annotations

import re
import tomllib
from pathlib import Path
from typing import Any

CONFIG_PATH = Path(__file__).resolve().parents[3] / "configs" / "process.toml"


def _load_route_config() -> tuple[
    tuple[str, ...],
    tuple[str, ...],
    tuple[str, ...],
    tuple[str, ...],
    tuple[str, ...],
    tuple[re.Pattern[str], ...],
    tuple[re.Pattern[str], ...],
    tuple[re.Pattern[str], ...],
    tuple[re.Pattern[str], ...],
    dict[str, tuple[str, ...]],
]:
    with CONFIG_PATH.open("rb") as fin:
        config = tomllib.load(fin)

    title_cfg = config.get("section_titles", {})
    method_titles = tuple(str(item).upper() for item in title_cfg.get("method", []))
    support_titles = tuple(str(item).upper() for item in title_cfg.get("support", []))
    ignore_titles = tuple(str(item).upper() for item in title_cfg.get("ignore", []))

    title_pattern_cfg = config.get("segment_title_patterns", {})
    title_contains_cfg = config.get("segment_title_contains", {})
    include_title_patterns = tuple(
        re.compile(str(pattern), re.IGNORECASE)
        for pattern in title_pattern_cfg.get("include", [])
    )
    exclude_title_patterns = tuple(
        re.compile(str(pattern), re.IGNORECASE)
        for pattern in title_pattern_cfg.get("exclude", [])
    )
    include_title_contains = tuple(
        str(item).lower().strip()
        for item in title_contains_cfg.get("include", [])
        if str(item).strip()
    )
    exclude_title_contains = tuple(
        str(item).lower().strip()
        for item in title_contains_cfg.get("exclude", [])
        if str(item).strip()
    )

    keyword_cfg = config.get("keywords", {})
    action_patterns = tuple(
        re.compile(str(pattern), re.IGNORECASE)
        for pattern in keyword_cfg.get("actions", [])
    )
    material_patterns = tuple(
        re.compile(str(pattern), re.IGNORECASE)
        for pattern in keyword_cfg.get("materials", [])
    )
    support_patterns = tuple(
        re.compile(str(pattern), re.IGNORECASE)
        for pattern in keyword_cfg.get("support", [])
    )

    upstream_preferences = {
        str(group): tuple(str(item) for item in values)
        for group, values in config.get("form_group_upstream_preferences", {}).items()
    }

    return (
        method_titles,
        support_titles,
        ignore_titles,
        include_title_contains,
        exclude_title_contains,
        include_title_patterns,
        exclude_title_patterns,
        action_patterns,
        material_patterns,
        support_patterns,
        upstream_preferences,
    )


(
    METHOD_TITLE_PATTERNS,
    SUPPORT_TITLE_PATTERNS,
    IGNORE_TITLE_PATTERNS,
    INCLUDE_SEGMENT_TITLE_CONTAINS,
    EXCLUDE_SEGMENT_TITLE_CONTAINS,
    INCLUDE_SEGMENT_TITLE_PATTERNS,
    EXCLUDE_SEGMENT_TITLE_PATTERNS,
    PROCESS_ACTION_PATTERNS,
    MATERIAL_SEGMENT_PATTERNS,
    SUPPORT_SIGNAL_PATTERNS,
    FORM_GROUP_UPSTREAM_PREFERENCES,
) = _load_route_config()

FORM_PATTERNS = {
    "Aerogel": ("aerogel",),
    "Foam": ("foam",),
    "Film": ("film",),
    "Membrane": ("membrane",),
    "Coating": ("coating",),
    "Substrate": ("substrate",),
    "Electrode": ("electrode",),
    "Sensor": ("sensor",),
    "Device": ("device",),
    "Ink": ("ink",),
    "Solution": ("solution",),
    "Gel": ("gel",),
    "Powder": ("powder",),
    "Fiber": ("fiber", "fibre"),
    "Solid": ("solid",),
}
FORM_GROUPS = {
    "Aerogel": "PorousBody",
    "Foam": "PorousBody",
    "Film": "ThinLayer",
    "Membrane": "ThinLayer",
    "Coating": "ThinLayer",
    "Substrate": "SupportedNode",
    "Electrode": "SupportedNode",
    "Sensor": "SupportedNode",
    "Device": "SupportedNode",
    "Ink": "PrecursorFluid",
    "Solution": "PrecursorFluid",
    "Gel": "PrecursorFluid",
    "Powder": "Powder",
    "Fiber": "Fiber",
    "Solid": "Solid",
}
VARIANT_MARKER_PATTERNS = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\bcomposite\b",
        r"\bdoped\b",
        r"\bloaded\b",
        r"\bfilled\b",
        r"\breinforced\b",
        r"\bhybrid\b",
        r"\bnanocomposite\b",
        r"\bnanoparticle",
        r"\bparticle",
        r"\bfiber\b",
        r"\bfibre\b",
        r"\bfiller\b",
        r"\bdecorated\b",
    )
)
VARIANT_TAIL_PATTERN = re.compile(
    r"^\s*(?:[-,/()]|\b)*(?:doped\b|loaded\b|filled\b|reinforced\b|"
    r"composite\b|nanocomposite\b|hybrid\b|with\b|decorated\b)",
    re.IGNORECASE,
)
GENERIC_CATEGORY_NAMES = {
    "polyimide",
    "polyamic acid",
    "polyamic acid ammonium salt",
    "cellulose nanocrystal",
    "cellulose nanocrystals",
}
RATIO_PATTERN = re.compile(r"\b\d+(?:\.\d+)?\s*wt\s*%\b", re.IGNORECASE)
MARKDOWN_HEADING_PATTERN = re.compile(r"^\s*#{1,6}\s*(.+?)\s*$")
PSEUDO_HEADING_PATTERN = re.compile(
    r"^\s*[A-Z0-9][A-Za-z0-9\-\s/(),%μ\.]{2,80}\.\s*$"
)
INLINE_PSEUDO_HEADING_PATTERN = re.compile(
    r"^\s*([A-Z][A-Za-z0-9\-\s/(),%μ]{2,80})\.\s+\S.+$"
)
IMAGE_LINE_PATTERN = re.compile(r"^\s*!\[")
CAPTION_LINE_PATTERN = re.compile(r"^\s*(figure|fig\.?|scheme|table)\b", re.IGNORECASE)


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


def is_support_section(section: dict[str, Any]) -> bool:
    title = normalize_title(section["section_title"])
    return any(pattern in title for pattern in SUPPORT_TITLE_PATTERNS)


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


def collect_family_matches(text: str, family_patterns: list[tuple[str, re.Pattern[str]]]) -> list[str]:
    matches: list[str] = []
    for label, pattern in family_patterns:
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


def collect_form_mentions(text: str) -> set[str]:
    lowered = text.lower()
    found: set[str] = set()
    for canonical, patterns in FORM_PATTERNS.items():
        if any(
            re.search(rf"(?<![a-z]){re.escape(pattern.lower())}s?(?![a-z])", lowered)
            for pattern in patterns
        ):
            found.add(canonical)
    return found


def collect_routing_forms(title: str, text: str) -> set[str]:
    title_forms = expand_form_groups(collect_form_mentions(title))
    if title_forms:
        return title_forms
    return expand_form_groups(collect_form_mentions(" ".join([title, text])))


def expand_form_groups(forms: set[str]) -> set[str]:
    expanded = set(forms)
    expanded.update(FORM_GROUPS.get(form, form) for form in forms)
    return expanded


def get_anchor_form_groups(anchor: dict[str, Any]) -> set[str]:
    anchor_form = normalize_text(anchor.get("样本形态"))
    if not anchor_form:
        return set()
    return expand_form_groups(collect_form_mentions(anchor_form))


def get_allowed_upstream_groups(anchor: dict[str, Any]) -> set[str]:
    anchor_groups = get_anchor_form_groups(anchor)
    allowed = set(anchor_groups)
    for group in anchor_groups:
        allowed.update(FORM_GROUP_UPSTREAM_PREFERENCES.get(group, ()))
    return allowed


def segment_has_process_title(title: str) -> bool:
    lowered = title.lower()
    return (
        any(token in lowered for token in INCLUDE_SEGMENT_TITLE_CONTAINS)
        or any(pattern.search(title) for pattern in INCLUDE_SEGMENT_TITLE_PATTERNS)
    )


def segment_is_excluded(title: str) -> bool:
    if segment_has_process_title(title):
        return False
    lowered = title.lower()
    return (
        any(token in lowered for token in EXCLUDE_SEGMENT_TITLE_CONTAINS)
        or any(pattern.search(title) for pattern in EXCLUDE_SEGMENT_TITLE_PATTERNS)
    )


def has_process_action(text: str) -> bool:
    return any(pattern.search(text) for pattern in PROCESS_ACTION_PATTERNS)


def has_material_signal(text: str) -> bool:
    return any(pattern.search(text) for pattern in MATERIAL_SEGMENT_PATTERNS)


def has_support_signal(text: str) -> bool:
    return any(pattern.search(text) for pattern in SUPPORT_SIGNAL_PATTERNS)


def is_pseudo_heading(line: str) -> bool:
    stripped = line.strip()
    if not stripped or IMAGE_LINE_PATTERN.search(stripped) or CAPTION_LINE_PATTERN.search(stripped):
        return False
    return bool(PSEUDO_HEADING_PATTERN.match(stripped))


def split_into_segments(lines: list[str], parent_section_title: str) -> list[dict[str, Any]]:
    entries: list[tuple[int, str]] = []
    for index, line in enumerate(lines):
        md_match = MARKDOWN_HEADING_PATTERN.match(line)
        if md_match:
            entries.append((index, normalize_text(md_match.group(1)) or parent_section_title))
            continue
        if is_pseudo_heading(line):
            entries.append((index, normalize_text(line.rstrip(".")) or parent_section_title))
            continue
        inline_match = INLINE_PSEUDO_HEADING_PATTERN.match(line)
        if inline_match:
            entries.append((index, normalize_text(inline_match.group(1)) or parent_section_title))

    if not entries:
        return [{
            "segment_title": parent_section_title,
            "start": 0,
            "end": len(lines),
            "lines": list(lines),
        }]

    segments: list[dict[str, Any]] = []
    for i, (start, title) in enumerate(entries):
        end = entries[i + 1][0] if i + 1 < len(entries) else len(lines)
        segments.append({
            "segment_title": title,
            "start": start,
            "end": end,
            "lines": lines[start:end],
        })
    return segments


def make_excerpt(
    *,
    section: dict[str, Any],
    segment: dict[str, Any],
    route_role: str,
    matched_anchors: list[str],
    matched_families: list[str],
    text_forms: set[str],
) -> dict[str, Any]:
    section_line_start = int(section["line_span"][0])
    segment_line_start = section_line_start + int(segment["start"])
    segment_line_end = section_line_start + max(int(segment["end"]) - 1, int(segment["start"]))
    text = "\n".join(segment["lines"]).strip()
    return {
        "block_id": section["block_id"],
        "chunk_index": section["chunk_index"],
        "section_title": section["section_title"],
        "segment_title": segment["segment_title"],
        "route_role": route_role,
        "line_span": [segment_line_start, segment_line_end],
        "matched_anchors": matched_anchors,
        "matched_families": matched_families,
        "matched_forms": sorted(text_forms),
        "text": text,
    }


def dedupe_excerpts(excerpts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: list[dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()
    for excerpt in excerpts:
        key = (
            excerpt["block_id"],
            excerpt["segment_title"],
            excerpt["route_role"],
            tuple(excerpt["line_span"]),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(excerpt)
    return deduped


def build_method_excerpts(
    *,
    anchor: dict[str, Any],
    sections: list[dict[str, Any]],
    anchor_patterns: list[tuple[str, re.Pattern[str]]],
    family_patterns: list[tuple[str, re.Pattern[str]]],
) -> tuple[list[dict[str, Any]], bool]:
    anchor_groups = get_anchor_form_groups(anchor)
    allowed_upstream_groups = get_allowed_upstream_groups(anchor)
    excerpts: list[dict[str, Any]] = []
    fallback_candidates: list[dict[str, Any]] = []

    for section in sections:
        if is_ignored_section(section) or not is_method_section(section):
            continue
        lines = str(section["content"]).splitlines()
        for segment in split_into_segments(lines, str(section["section_title"])):
            title = str(segment["segment_title"])
            if segment_is_excluded(title):
                continue
            text = "\n".join(segment["lines"]).strip()
            if not text:
                continue
            matched_anchors = collect_anchor_matches(text, anchor_patterns)
            matched_families = collect_family_matches(text, family_patterns)
            strong_anchor = has_strong_direct_anchor_match(
                anchor=anchor,
                text=text,
                anchor_matches=matched_anchors,
            )
            forms = collect_routing_forms(title, text)
            material_signal = has_material_signal(title) or has_material_signal(text)
            process_signal = segment_has_process_title(title) or has_process_action(text)
            if material_signal:
                fallback_candidates.append(
                    make_excerpt(
                        section=section,
                        segment=segment,
                        route_role="process_methods",
                        matched_anchors=matched_anchors,
                        matched_families=matched_families,
                        text_forms=forms,
                    )
                )
            if not process_signal and not material_signal and not matched_anchors:
                continue

            if strong_anchor:
                excerpts.append(
                    make_excerpt(
                        section=section,
                        segment=segment,
                        route_role="process_methods",
                        matched_anchors=matched_anchors,
                        matched_families=matched_families,
                        text_forms=forms,
                    )
                )
                continue

            if mentions_modified_variant_of_anchor(
                anchor=anchor,
                text=text,
                family_matches=matched_families,
            ):
                continue

            if matched_families and forms and forms.intersection(allowed_upstream_groups):
                excerpts.append(
                    make_excerpt(
                        section=section,
                        segment=segment,
                        route_role="process_methods",
                        matched_anchors=matched_anchors,
                        matched_families=matched_families,
                        text_forms=forms,
                    )
                )
                continue

            if process_signal and allowed_upstream_groups and forms.intersection(allowed_upstream_groups):
                excerpts.append(
                    make_excerpt(
                        section=section,
                        segment=segment,
                        route_role="process_methods",
                        matched_anchors=matched_anchors,
                        matched_families=matched_families,
                        text_forms=forms,
                    )
                )

    excerpts = dedupe_excerpts(excerpts)
    used_fallback = False
    if not excerpts and fallback_candidates:
        excerpts = dedupe_excerpts(fallback_candidates)
        used_fallback = True
    return excerpts, used_fallback


def build_weak_frontmatter_excerpts(
    *,
    anchor: dict[str, Any],
    sections: list[dict[str, Any]],
    anchor_patterns: list[tuple[str, re.Pattern[str]]],
    family_patterns: list[tuple[str, re.Pattern[str]]],
) -> list[dict[str, Any]]:
    anchor_groups = get_anchor_form_groups(anchor)
    allowed_upstream_groups = get_allowed_upstream_groups(anchor)
    excerpts: list[dict[str, Any]] = []

    for section in sections:
        if is_ignored_section(section) or is_method_section(section) or is_support_section(section):
            continue
        if int(section.get("chunk_index", 0)) > 0:
            continue
        lines = str(section["content"]).splitlines()
        for segment in split_into_segments(lines, str(section["section_title"])):
            title = str(segment["segment_title"])
            text = "\n".join(segment["lines"]).strip()
            if not text:
                continue
            matched_anchors = collect_anchor_matches(text, anchor_patterns)
            matched_families = collect_family_matches(text, family_patterns)
            strong_anchor = has_strong_direct_anchor_match(
                anchor=anchor,
                text=text,
                anchor_matches=matched_anchors,
            )
            forms = collect_routing_forms(title, text)
            if not (matched_anchors or matched_families):
                continue
            if not (
                has_process_action(text)
                or has_support_signal(text)
                or (forms and forms.intersection(allowed_upstream_groups))
                or (not forms and anchor_groups)
            ):
                continue
            if not strong_anchor and mentions_modified_variant_of_anchor(
                anchor=anchor,
                text=text,
                family_matches=matched_families,
            ):
                continue
            excerpts.append(
                make_excerpt(
                    section=section,
                    segment=segment,
                    route_role="process_support",
                    matched_anchors=matched_anchors,
                    matched_families=matched_families,
                    text_forms=forms,
                )
            )
    return dedupe_excerpts(excerpts)


def build_support_excerpts(
    *,
    anchor: dict[str, Any],
    sections: list[dict[str, Any]],
    anchor_patterns: list[tuple[str, re.Pattern[str]]],
    family_patterns: list[tuple[str, re.Pattern[str]]],
) -> list[dict[str, Any]]:
    anchor_groups = get_anchor_form_groups(anchor)
    allowed_upstream_groups = get_allowed_upstream_groups(anchor)
    excerpts: list[dict[str, Any]] = []

    for section in sections:
        if is_ignored_section(section) or not is_support_section(section):
            continue
        lines = str(section["content"]).splitlines()
        for segment in split_into_segments(lines, str(section["section_title"])):
            title = str(segment["segment_title"])
            text = "\n".join(segment["lines"]).strip()
            if not text:
                continue
            matched_anchors = collect_anchor_matches(text, anchor_patterns)
            matched_families = collect_family_matches(text, family_patterns)
            strong_anchor = has_strong_direct_anchor_match(
                anchor=anchor,
                text=text,
                anchor_matches=matched_anchors,
            )
            forms = collect_routing_forms(title, text)
            weak_supported_node_signal = bool(
                forms.intersection({"SupportedNode"})
                and (strong_anchor or matched_families)
            )
            if segment_is_excluded(title) and not weak_supported_node_signal:
                continue
            if not (
                segment_has_process_title(title)
                or has_process_action(text)
                or has_support_signal(text)
                or weak_supported_node_signal
            ):
                continue
            if strong_anchor:
                excerpts.append(
                    make_excerpt(
                        section=section,
                        segment=segment,
                        route_role="process_support",
                        matched_anchors=matched_anchors,
                        matched_families=matched_families,
                        text_forms=forms,
                    )
                )
                continue
            if mentions_modified_variant_of_anchor(
                anchor=anchor,
                text=text,
                family_matches=matched_families,
            ):
                continue
            if matched_families and (
                (forms and forms.intersection(allowed_upstream_groups))
                or (not forms and anchor_groups)
            ):
                excerpts.append(
                    make_excerpt(
                        section=section,
                        segment=segment,
                        route_role="process_support",
                        matched_anchors=matched_anchors,
                        matched_families=matched_families,
                        text_forms=forms,
                    )
                )
    excerpts = dedupe_excerpts(excerpts)
    if excerpts:
        return excerpts
    return build_weak_frontmatter_excerpts(
        anchor=anchor,
        sections=sections,
        anchor_patterns=anchor_patterns,
        family_patterns=family_patterns,
    )


def build_source_refs(
    method_excerpts: list[dict[str, Any]],
    support_excerpts: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for excerpt in [*method_excerpts, *support_excerpts]:
        refs.append({
            "block_id": excerpt["block_id"],
            "chunk_index": excerpt["chunk_index"],
            "section_title": excerpt["section_title"],
            "segment_title": excerpt["segment_title"],
            "route_role": excerpt["route_role"],
            "line_span": excerpt["line_span"],
            "matched_anchors": excerpt["matched_anchors"],
            "matched_families": excerpt["matched_families"],
            "matched_forms": excerpt["matched_forms"],
        })
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
    return "[POLYMER_ANCHOR]\n" + "\n".join(lines).strip()


def render_excerpts(tag: str, excerpts: list[dict[str, Any]]) -> str:
    if not excerpts:
        return f"[{tag}]\n"
    blocks = [f"[{tag}]"]
    for idx, excerpt in enumerate(excerpts, start=1):
        blocks.append(
            "\n".join(
                [
                    f"## excerpt {idx}",
                    f"section_title: {excerpt['section_title']}",
                    f"segment_title: {excerpt['segment_title']}",
                    f"line_span: {excerpt['line_span'][0]}-{excerpt['line_span'][1]}",
                    excerpt["text"],
                ]
            ).strip()
        )
    return "\n\n".join(blocks)


def render_process_text(
    anchor: dict[str, Any],
    method_excerpts: list[dict[str, Any]],
    support_excerpts: list[dict[str, Any]],
) -> str:
    parts = [
        render_polymer_anchor_text(anchor),
        render_excerpts("PROCESS_METHODS", method_excerpts),
        render_excerpts("PROCESS_SUPPORT", support_excerpts),
    ]
    return "\n\n".join(part for part in parts if part.strip()).strip()


def route_process_context(
    *,
    anchor: dict[str, Any],
    sections: list[dict[str, Any]],
) -> dict[str, Any]:
    anchor_patterns = build_anchor_patterns(anchor)
    family_patterns = build_family_patterns(anchor)
    method_excerpts, used_method_fallback = build_method_excerpts(
        anchor=anchor,
        sections=sections,
        anchor_patterns=anchor_patterns,
        family_patterns=family_patterns,
    )
    support_excerpts = build_support_excerpts(
        anchor=anchor,
        sections=sections,
        anchor_patterns=anchor_patterns,
        family_patterns=family_patterns,
    )
    source_refs = build_source_refs(method_excerpts, support_excerpts)
    return {
        "method_excerpts": method_excerpts,
        "support_excerpts": support_excerpts,
        "source_refs": source_refs,
        "route_stats": {
            "method_excerpt_count": len(method_excerpts),
            "support_excerpt_count": len(support_excerpts),
            "used_method_fallback": used_method_fallback,
        },
    }


def build_process_task(
    *,
    run_id: str,
    doc_id: str,
    file_name: str,
    polymer: dict[str, Any],
    polymer_index: int,
    sections: list[dict[str, Any]],
) -> dict[str, Any]:
    anchor = build_polymer_anchor(polymer)
    sample_id = normalize_text(polymer.get("身份标识"))
    if not sample_id:
        raise ValueError(f"Missing 身份标识 in polymer record: doc_id={doc_id}, index={polymer_index}")

    routed = route_process_context(anchor=anchor, sections=sections)
    text = render_process_text(
        anchor=anchor,
        method_excerpts=routed["method_excerpts"],
        support_excerpts=routed["support_excerpts"],
    )
    task_id = f"{run_id}__{doc_id}__{polymer_index:03d}__process"
    return {
        "run_id": run_id,
        "doc_id": doc_id,
        "task_id": task_id,
        "file_name": file_name,
        "sample_id": sample_id,
        "polymer_anchor": anchor,
        "source_refs": routed["source_refs"],
        "chain_input": {
            "text": text,
        },
        "route_stats": routed["route_stats"],
    }
