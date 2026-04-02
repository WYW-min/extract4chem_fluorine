from __future__ import annotations

import re
from bisect import bisect_right
from typing import Any


HEADER_RE = re.compile(r"^(#{1,6})[ \t]+(.+?)\s*$", re.MULTILINE)
OUTLINE_RE = re.compile(r"^(?P<number>\d+(?:\.\d+)*)(?:\.(?=[^\d]|$)|\s+|$)")


def build_line_offsets(text: str) -> list[int]:
    return [idx for idx, ch in enumerate(text) if ch == "\n"]


def char_to_line(line_offsets: list[int], char_pos: int) -> int:
    return bisect_right(line_offsets, char_pos) + 1


def non_empty_lines(text: str) -> int:
    return sum(1 for line in text.splitlines() if line.strip())


def effective_body_non_empty_lines(text: str) -> int:
    count = 0
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if HEADER_RE.match(stripped):
            continue
        count += 1
    return count


def parse_outline_title(title: str) -> tuple[str | None, int | None]:
    match = OUTLINE_RE.match(title.strip())
    if not match:
        return None, None
    number = match.group("number")
    return number, len(number.split("."))


def rebuild_section(
    *,
    line_offsets: list[int],
    block_idx: int,
    base_section: dict[str, Any],
    start_char: int,
    end_char: int,
    content: str,
) -> dict[str, Any]:
    clean_text = content.strip()
    safe_end = max(start_char, end_char - 1)
    return {
        "block_id": f"b{block_idx:04d}",
        "section_index": block_idx,
        "header_level": base_section["header_level"],
        "title_level": base_section["title_level"],
        "outline_level": base_section["outline_level"],
        "section_number": base_section["section_number"],
        "section_title": base_section["section_title"],
        "line_span": [
            char_to_line(line_offsets, start_char),
            char_to_line(line_offsets, safe_end),
        ],
        "char_span": [start_char, end_char],
        "content": clean_text,
        "content_char_len": len(clean_text),
        "content_non_empty_lines": non_empty_lines(clean_text),
        "effective_body_non_empty_lines": effective_body_non_empty_lines(clean_text),
    }


def collapse_heading_only_sections(
    sections: list[dict[str, Any]],
    content: str,
    line_offsets: list[int],
) -> list[dict[str, Any]]:
    collapsed: list[dict[str, Any]] = []
    idx = 0

    while idx < len(sections):
        section = sections[idx]
        start_char = section["char_span"][0]
        end_char = section["char_span"][1]
        merge_until = idx

        if section["effective_body_non_empty_lines"] == 0:
            probe = idx + 1
            while probe < len(sections):
                end_char = sections[probe]["char_span"][1]
                merge_until = probe
                if sections[probe]["effective_body_non_empty_lines"] > 0:
                    break
                probe += 1

        merged_content = content[start_char:end_char]
        collapsed.append(
            rebuild_section(
                line_offsets=line_offsets,
                block_idx=len(collapsed) + 1,
                base_section=section,
                start_char=start_char,
                end_char=end_char,
                content=merged_content,
            )
        )
        idx = merge_until + 1

    return collapsed


def split_markdown(content: str) -> list[dict[str, Any]]:
    matches = list(HEADER_RE.finditer(content))
    line_offsets = build_line_offsets(content)
    sections: list[dict[str, Any]] = []
    block_idx = 0

    def add_section(
        *,
        header_level: int,
        title_level: int,
        outline_level: int,
        section_title: str,
        start_char: int,
        end_char: int,
        text: str,
        section_number: str | None,
    ) -> None:
        nonlocal block_idx
        clean_text = text.strip()
        if not clean_text:
            return
        block_idx += 1
        safe_end = max(start_char, end_char - 1)
        sections.append(
            {
                "block_id": f"b{block_idx:04d}",
                "section_index": block_idx,
                "header_level": header_level,
                "title_level": title_level,
                "outline_level": outline_level,
                "section_number": section_number,
                "section_title": section_title.strip() or "__UNTITLED__",
                "line_span": [
                    char_to_line(line_offsets, start_char),
                    char_to_line(line_offsets, safe_end),
                ],
                "char_span": [start_char, end_char],
                "content": clean_text,
                "content_char_len": len(clean_text),
                "content_non_empty_lines": non_empty_lines(clean_text),
                "effective_body_non_empty_lines": effective_body_non_empty_lines(clean_text),
            }
        )

    if not matches:
        add_section(
            header_level=0,
            title_level=0,
            outline_level=0,
            section_title="__FULL_TEXT__",
            start_char=0,
            end_char=len(content),
            text=content,
            section_number=None,
        )
        return collapse_heading_only_sections(sections, content, line_offsets)

    headings: list[dict[str, Any]] = []
    for match in matches:
        section_title = match.group(2).strip()
        section_number, outline_level = parse_outline_title(section_title)
        headings.append(
            {
                "header_level": len(match.group(1)),
                "section_title": section_title,
                "section_number": section_number,
                "outline_level": outline_level,
                "start_char": match.start(),
            }
        )

    split_headings = [
        heading
        for heading in headings
        if heading["outline_level"] == 1 or heading["outline_level"] is None
    ]
    if split_headings:
        for idx, heading in enumerate(split_headings):
            start_char = 0 if idx == 0 else heading["start_char"]
            end_char = (
                split_headings[idx + 1]["start_char"]
                if idx + 1 < len(split_headings)
                else len(content)
            )
            add_section(
                header_level=heading["header_level"],
                title_level=1,
                outline_level=1,
                section_title=heading["section_title"],
                start_char=start_char,
                end_char=end_char,
                text=content[start_char:end_char],
                section_number=heading["section_number"],
            )
        return collapse_heading_only_sections(sections, content, line_offsets)

    if matches[0].start() > 0:
        add_section(
            header_level=0,
            title_level=0,
            outline_level=0,
            section_title="__PREFACE__",
            start_char=0,
            end_char=matches[0].start(),
            text=content[: matches[0].start()],
            section_number=None,
        )

    for idx, match in enumerate(matches):
        header_level = len(match.group(1))
        section_title = match.group(2).strip()
        section_number, outline_level = parse_outline_title(section_title)
        block_start = match.start()
        next_start = matches[idx + 1].start() if idx + 1 < len(matches) else len(content)
        add_section(
            header_level=header_level,
            title_level=outline_level or header_level,
            outline_level=outline_level or header_level,
            section_title=section_title,
            start_char=block_start,
            end_char=next_start,
            text=content[block_start:next_start],
            section_number=section_number,
        )

    return collapse_heading_only_sections(sections, content, line_offsets)

