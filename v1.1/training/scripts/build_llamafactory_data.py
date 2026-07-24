#!/usr/bin/env python3

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA_ROOT = PROJECT_ROOT / "data" / "v1.1-paper"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "training" / "generated-v1.1"

DIMENSIONS = {
    "Readability": "surveyreview_readability",
    "Criticalness": "surveyreview_criticalness",
    "Comprehensiveness": "surveyreview_comprehensiveness",
    "Structure": "surveyreview_structure",
}

VALID_SCORES = {-2, -1, 1, 2}


def read_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def normalize_text(value: object) -> str:
    text = "" if value is None else str(value)
    return re.sub(r"\s+", " ", text).strip()


def score_to_int(value: object) -> int:
    return int(float(value))


def split_path(data_root: Path, split: str, source: str) -> Path:
    if source == "grouped":
        return data_root / split / f"grouped_{split}set.json"
    return data_root / "raw" / f"{split}_samples.json"


def load_articles(data_root: Path) -> Dict[str, str]:
    articles_dir = data_root / "articles"
    articles: Dict[str, str] = {}
    part_files = sorted(articles_dir.glob("articles_part*.json"))
    if not part_files:
        raise FileNotFoundError(f"No article shards found in {articles_dir}")

    for part_file in part_files:
        part = read_json(part_file)
        overlap = set(articles).intersection(part)
        if overlap:
            examples = ", ".join(sorted(overlap)[:5])
            raise ValueError(f"Duplicate article ids in {part_file}: {examples}")
        articles.update(part)

    return articles


def iter_dimension_results(rows: Iterable[dict]) -> Iterable[Tuple[dict, dict]]:
    for row in rows:
        for result in row.get("result", []):
            yield row, result


def format_output(reasons: List[str], score: int) -> str:
    reason_text = " ".join(normalize_text(reason) for reason in reasons if normalize_text(reason))
    return f"<reason>{reason_text}</reason> <score>{score}</score>"


def build_examples(data_root: Path, split: str, source: str) -> Tuple[Dict[str, List[dict]], dict]:
    prompt_path = data_root / "prompt" / "eval-prompt.json"
    prompts = read_json(prompt_path)

    rows_path = split_path(data_root, split, source)
    rows = read_json(rows_path)
    articles = load_articles(data_root)

    examples = {dataset_name: [] for dataset_name in DIMENSIONS.values()}
    stats = {
        "data_root": str(data_root),
        "split": split,
        "source": source,
        "rows_path": str(rows_path),
        "article_count": len(articles),
        "top_level_rows": len(rows),
        "written": Counter(),
        "skipped_invalid_score": Counter(),
        "skipped_missing_article": Counter(),
        "skipped_unknown_dimension": Counter(),
    }

    for row, result in iter_dimension_results(rows):
        dimension = result.get("dimension", "")
        if dimension not in DIMENSIONS:
            stats["skipped_unknown_dimension"][dimension] += 1
            continue

        score = score_to_int(result.get("score", 0))
        if score not in VALID_SCORES:
            stats["skipped_invalid_score"][dimension] += 1
            continue

        uid = row.get("uid", "")
        article = articles.get(uid)
        if not article:
            stats["skipped_missing_article"][dimension] += 1
            continue

        dataset_name = DIMENSIONS[dimension]
        examples[dataset_name].append({
            "instruction": prompts[dimension],
            "input": article,
            "output": format_output(result.get("reasons", []), score),
        })
        stats["written"][dimension] += 1

    stats = {
        key: dict(value) if isinstance(value, Counter) else value
        for key, value in stats.items()
    }
    return examples, stats


def write_dataset_info(output_dir: Path) -> None:
    dataset_info = {
        dataset_name: {"file_name": f"{dataset_name}.json"}
        for dataset_name in DIMENSIONS.values()
    }
    write_json(output_dir / "dataset_info.json", dataset_info)


def write_examples(output_dir: Path, examples: Dict[str, List[dict]], stats: dict) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    for dataset_name, rows in examples.items():
        write_json(output_dir / f"{dataset_name}.json", rows)

    write_dataset_info(output_dir)
    write_json(output_dir / "build_stats.json", stats)


def print_summary(output_dir: Path, examples: Dict[str, List[dict]], stats: dict) -> None:
    print(f"Output: {output_dir}")
    for dimension, dataset_name in DIMENSIONS.items():
        print(f"{dimension}: {len(examples[dataset_name])} examples -> {dataset_name}.json")

    skipped = defaultdict(int)
    for key in ["skipped_invalid_score", "skipped_missing_article", "skipped_unknown_dimension"]:
        for dimension, count in stats.get(key, {}).items():
            skipped[key] += count

    if skipped:
        print("Skipped:")
        for key, count in sorted(skipped.items()):
            print(f"  {key}: {count}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build LLaMA-Factory Alpaca-format SFT data for SurveyReview."
    )
    parser.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--split", choices=["train", "test"], default="train")
    parser.add_argument("--source", choices=["grouped", "raw"], default="grouped")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    examples, stats = build_examples(args.data_root, args.split, args.source)
    write_examples(args.output_dir, examples, stats)
    print_summary(args.output_dir, examples, stats)


if __name__ == "__main__":
    main()
