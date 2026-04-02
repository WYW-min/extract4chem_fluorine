from __future__ import annotations

import argparse
import json
import re
import shutil
import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path


CONTENT_SUFFIX = "_content_list"


@dataclass(frozen=True)
class FileItem:
    path: Path
    stem: str
    normalized: str
    token_sorted: str


def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).lower().strip()
    text = text.replace("_", " ").replace("-", " ")
    text = re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def token_sort_text(text: str) -> str:
    tokens = [token for token in normalize_text(text).split() if token]
    return " ".join(sorted(tokens))


def md_item(path: Path) -> FileItem:
    stem = path.stem
    return FileItem(
        path=path,
        stem=stem,
        normalized=normalize_text(stem),
        token_sorted=token_sort_text(stem),
    )


def content_item(path: Path) -> FileItem:
    stem = path.stem
    if stem.endswith(CONTENT_SUFFIX):
        stem = stem[: -len(CONTENT_SUFFIX)]
    return FileItem(
        path=path,
        stem=stem,
        normalized=normalize_text(stem),
        token_sorted=token_sort_text(stem),
    )


def similarity(left: FileItem, right: FileItem) -> float:
    raw_ratio = SequenceMatcher(None, left.normalized, right.normalized).ratio()
    token_ratio = SequenceMatcher(None, left.token_sorted, right.token_sorted).ratio()
    return max(raw_ratio, token_ratio)


def unique_index(items: list[FileItem]) -> dict[str, FileItem]:
    counts: dict[str, int] = {}
    for item in items:
        counts[item.normalized] = counts.get(item.normalized, 0) + 1
    return {item.normalized: item for item in items if counts[item.normalized] == 1}


def pair_items(
    md_items: list[FileItem],
    content_items: list[FileItem],
    *,
    min_score: float,
) -> list[dict]:
    md_exact = unique_index(md_items)
    content_exact = unique_index(content_items)

    pairs: list[dict] = []
    matched_md: set[Path] = set()
    matched_content: set[Path] = set()

    for key in sorted(set(md_exact) & set(content_exact)):
        md = md_exact[key]
        content = content_exact[key]
        matched_md.add(md.path)
        matched_content.add(content.path)
        pairs.append(
            {
                "md_name": md.path.name,
                "content_name": content.path.name,
                "match_type": "exact_normalized",
                "score": 1.0,
            }
        )

    md_unmatched = [item for item in md_items if item.path not in matched_md]
    content_unmatched = [item for item in content_items if item.path not in matched_content]

    scored_candidates: list[tuple[float, FileItem, FileItem]] = []
    for md in md_unmatched:
        for content in content_unmatched:
            score = similarity(md, content)
            if score >= min_score:
                scored_candidates.append((score, md, content))

    scored_candidates.sort(
        key=lambda item: (
            -item[0],
            item[1].path.name,
            item[2].path.name,
        )
    )

    for score, md, content in scored_candidates:
        if md.path in matched_md or content.path in matched_content:
            continue
        matched_md.add(md.path)
        matched_content.add(content.path)
        pairs.append(
            {
                "md_name": md.path.name,
                "content_name": content.path.name,
                "match_type": "fuzzy",
                "score": round(score, 6),
            }
        )

    for md in md_items:
        if md.path in matched_md:
            continue
        pairs.append(
            {
                "md_name": md.path.name,
                "content_name": None,
                "match_type": "unmatched_md",
                "score": None,
            }
        )

    for content in content_items:
        if content.path in matched_content:
            continue
        pairs.append(
            {
                "md_name": None,
                "content_name": content.path.name,
                "match_type": "unmatched_content",
                "score": None,
            }
        )

    def sort_key(item: dict) -> tuple[str, str]:
        return (item.get("md_name") or "", item.get("content_name") or "")

    return sorted(pairs, key=sort_key)


def export_renamed_content(
    *,
    md_dir: Path,
    content_dir: Path,
    pairs: list[dict],
    output_dir: Path,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    md_map = {path.name: path for path in md_dir.glob("*.md")}
    content_map = {path.name: path for path in content_dir.glob("*.json")}

    for pair in pairs:
        md_name = pair.get("md_name")
        content_name = pair.get("content_name")
        if not md_name or not content_name:
            continue
        md_path = md_map[md_name]
        content_path = content_map[content_name]
        target = output_dir / f"{md_path.stem}{CONTENT_SUFFIX}.json"
        shutil.copy2(content_path, target)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Pair md_enhance files with content_list files by normalized exact "
            "match first, then one-to-one fuzzy similarity. The md_enhance stem "
            "is treated as the canonical final name."
        )
    )
    parser.add_argument("-m", "--md-dir", required=True, help="md_enhance directory")
    parser.add_argument("-c", "--content-dir", required=True, help="content_list directory")
    parser.add_argument(
        "-o",
        "--output-json",
        default=None,
        help="Optional path to write pairing result json.",
    )
    parser.add_argument(
        "-r",
        "--renamed-content-dir",
        default=None,
        help="Optional output dir to export matched content_list files using md_enhance names.",
    )
    parser.add_argument(
        "--min-score",
        type=float,
        default=0.85,
        help="Minimum fuzzy similarity score for one-to-one pairing (default: 0.85).",
    )
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    md_dir = Path(args.md_dir)
    content_dir = Path(args.content_dir)
    if not md_dir.exists():
        raise FileNotFoundError(f"md_dir not found: {md_dir}")
    if not content_dir.exists():
        raise FileNotFoundError(f"content_dir not found: {content_dir}")

    md_items = [md_item(path) for path in sorted(md_dir.glob("*.md"))]
    content_items = [content_item(path) for path in sorted(content_dir.glob("*.json"))]
    pairs = pair_items(md_items, content_items, min_score=args.min_score)

    summary = {
        "md_count": len(md_items),
        "content_count": len(content_items),
        "paired_count": sum(1 for item in pairs if item["md_name"] and item["content_name"]),
        "exact_normalized_count": sum(1 for item in pairs if item["match_type"] == "exact_normalized"),
        "fuzzy_count": sum(1 for item in pairs if item["match_type"] == "fuzzy"),
        "unmatched_md_count": sum(1 for item in pairs if item["match_type"] == "unmatched_md"),
        "unmatched_content_count": sum(1 for item in pairs if item["match_type"] == "unmatched_content"),
        "pairs": pairs,
    }

    if args.output_json:
        output_json = Path(args.output_json)
        output_json.parent.mkdir(parents=True, exist_ok=True)
        output_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.renamed_content_dir:
        export_renamed_content(
            md_dir=md_dir,
            content_dir=content_dir,
            pairs=pairs,
            output_dir=Path(args.renamed_content_dir),
        )

    print(json.dumps({k: v for k, v in summary.items() if k != "pairs"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
