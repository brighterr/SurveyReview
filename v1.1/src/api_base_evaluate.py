#!/usr/bin/env python3

import os
import json
import re
import time
import csv
import numpy as np
from pathlib import Path
from typing import List, Dict, Optional
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv
from model_client import ModelClient
from reason_evaluator import evaluate_reasons_from_results

load_dotenv(Path(__file__).parent.parent / ".env")

PROJECT_ROOT = Path(__file__).parent.parent

DIMENSIONS = ["readability", "criticalness", "comprehensiveness", "structure"]
VALID_SCORES = {-2, -1, 1, 2}

DATA_VERSION = os.getenv("DATA_VERSION", "v1.1-paper")
DATA_ROOT = Path(os.getenv("DATA_ROOT", PROJECT_ROOT / "data" / DATA_VERSION)).expanduser()
ARTICLES_DIR = DATA_ROOT / "articles"
PROMPT_DIR = DATA_ROOT / "prompt"
PROMPT_FILE = PROMPT_DIR / "eval-prompt.json"
DEFINITION_FILE = PROMPT_DIR / "Definition.json"
JUDGE_PROMPT_FILE = PROMPT_DIR / "reason_quality_judge.json"
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", PROJECT_ROOT / "result" / DATA_VERSION)).expanduser()

MODEL_NAME = os.getenv("MODEL_NAME", "gpt-5.2")
JUDGE_MODEL = os.getenv("JUDGE_MODEL", "gpt-5.2")
MAX_WORKERS = int(os.getenv("MAX_WORKERS", "64"))
JUDGE_MAX_WORKERS = int(os.getenv("JUDGE_MAX_WORKERS", "32"))
EVALUATE_REASONS = os.getenv("EVALUATE_REASONS", "True").lower() == "true"
EVAL_SPLIT = os.getenv("EVAL_SPLIT", "test").lower()

REASON_RE = re.compile(r"<reason>(.*?)</reason>", re.DOTALL | re.IGNORECASE)
SCORE_RE = re.compile(r"<score>\s*(-?\d+(?:\.\d+)?)\s*</score>", re.IGNORECASE)
LEGACY_SCORE_RE = re.compile(r"\$\$\$\s*(-?\d+(?:\.\d+)?)\s*\$\$\$")


def parse_score_value(raw: str) -> Optional[int]:
    try:
        value = float(raw.strip())
        score = int(value)
        if value != score:
            return None
        return score if score in VALID_SCORES else None
    except (TypeError, ValueError):
        return None


def parse_prediction(text: str) -> Dict:
    text = text or ""
    reason_match = REASON_RE.search(text)
    score_match = SCORE_RE.search(text)

    score = parse_score_value(score_match.group(1)) if score_match else None
    reasoning = reason_match.group(1).strip() if reason_match else ""
    output_format = "xml" if reason_match or score_match else "legacy"

    if not reasoning:
        legacy_cleaned = LEGACY_SCORE_RE.sub("", text).strip()
        reasoning = re.sub(r"<score>.*?</score>", "", legacy_cleaned, flags=re.DOTALL | re.IGNORECASE).strip()

    if score is None and not score_match:
        legacy_match = LEGACY_SCORE_RE.search(text)
        if legacy_match:
            score = parse_score_value(legacy_match.group(1))

    return {
        "reasoning": reasoning,
        "score": score,
        "output_format": output_format,
    }


def extract_score(text: str) -> Optional[int]:
    parsed = parse_prediction(text)
    return parsed["score"]
    return None


def split_file(split: str) -> Path:
    filename = f"grouped_{split}set.json"
    path = DATA_ROOT / split / filename
    if not path.exists():
        raise FileNotFoundError(f"Split file not found: {path}")
    return path


def load_split_rows(split: str) -> List[Dict]:
    with open(split_file(split), "r", encoding="utf-8") as f:
        return json.load(f)


def load_articles() -> Dict:
    articles = {}
    part_files = sorted(ARTICLES_DIR.glob("articles_part*.json"))
    if not part_files:
        raise FileNotFoundError(f"No article shards found in {ARTICLES_DIR}")

    for part_file in part_files:
        with open(part_file, "r", encoding="utf-8") as f:
            part = json.load(f)
        overlap = set(articles).intersection(part)
        if overlap:
            raise ValueError(f"Duplicate article ids in {part_file}: {sorted(overlap)[:5]}")
        articles.update(part)
    return articles


def normalize_dimension(name: str) -> str:
    return (name or "").strip().lower()


def load_samples(dimension: str, rows: List[Dict]) -> List[Dict]:
    target_dimension = normalize_dimension(dimension)
    samples = []

    for row in rows:
        for item in row.get("result", []):
            if normalize_dimension(item.get("dimension")) != target_dimension:
                continue

            score = int(float(item.get("score", 0)))
            if score in [0, -3]:
                continue

            samples.append({
                "uid": row["uid"],
                "paper_title": row.get("paper_title", ""),
                "paper_abstract": row.get("paper_abstract", ""),
                "review_content": row.get("review_content", ""),
                "source": row.get("source", ""),
                "dimension": target_dimension,
                "score": score,
                "reasons": item.get("reasons", [])
            })

    return samples


def summarize_split(rows: List[Dict]) -> Dict:
    dimension_counts = {dim: 0 for dim in DIMENSIONS}
    zero_counts = {dim: 0 for dim in DIMENSIONS}
    uids_with_nonzero = set()
    all_zero_uids = []

    for row in rows:
        row_has_nonzero = False
        for item in row.get("result", []):
            dimension = normalize_dimension(item.get("dimension"))
            if dimension not in dimension_counts:
                continue

            score = int(float(item.get("score", 0)))
            if score in [0, -3]:
                zero_counts[dimension] += 1
                continue

            row_has_nonzero = True
            dimension_counts[dimension] += 1

        if row_has_nonzero:
            uids_with_nonzero.add(row.get("uid"))
        else:
            all_zero_uids.append(row.get("uid"))

    return {
        "data_root": str(DATA_ROOT),
        "eval_split": EVAL_SPLIT,
        "top_level_samples": len(rows),
        "unique_uids": len({row.get("uid") for row in rows}),
        "uids_with_nonzero": len(uids_with_nonzero),
        "all_zero_uid_count": len(all_zero_uids),
        "all_zero_uids": all_zero_uids,
        "dimension_nonzero_counts": dimension_counts,
        "dimension_zero_counts": zero_counts,
        "dimension_nonzero_total": sum(dimension_counts.values()),
        "dimension_zero_total": sum(zero_counts.values())
    }


def write_jsonl(path: Path, rows: List[Dict]):
    with open(path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def evaluate_sample(idx: int, sample: Dict, articles: Dict, instruction: str, client: ModelClient) -> Dict:
    uid = sample['uid']
    true_score = sample['score']
    reasons = sample['reasons']
    base_result = {
        'index': idx,
        'uid': uid,
        'paper_title': sample.get('paper_title', ''),
        'source': sample.get('source', ''),
        'dimension': sample.get('dimension', ''),
        'true_score': true_score,
        'true_reasons': " ".join(reasons)
    }
    
    paper = articles.get(uid)
    if not paper:
        return {**base_result, 'pred_output': "Paper not found", 'pred_score': 0, 'error': abs(true_score), 'status': 'not_found'}
    
    try:
        output = client.call(user_text=f"{instruction}\n\n{paper}")
        parsed = parse_prediction(output)
        extracted_score = parsed["score"]
        pred_score = extracted_score if extracted_score is not None else 0
        status = 'success' if extracted_score is not None else 'parse_failed'
        return {
            **base_result,
            'pred_output': output,
            'pred_reasoning': parsed["reasoning"],
            'pred_score': pred_score,
            'output_format': parsed["output_format"],
            'error': abs(true_score - pred_score),
            'status': status
        }
    except Exception as e:
        return {**base_result, 'pred_output': str(e), 'pred_score': 0, 'error': abs(true_score), 'status': 'error'}


def evaluate(client: ModelClient, samples: List[Dict], articles: Dict, instruction: str, dimension: str) -> Dict:
    predictions = []
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(evaluate_sample, i, s, articles, instruction, client): i
            for i, s in enumerate(samples)
        }
        
        with tqdm(total=len(samples), desc=f"{dimension}", ncols=80) as pbar:
            for future in as_completed(futures):
                predictions.append(future.result())
                pbar.update(1)
    
    predictions.sort(key=lambda x: x['index'])
    
    valid = [p for p in predictions if p.get('status') in ['success', 'parse_failed']]
    success = [p for p in predictions if p.get('status') == 'success']

    if valid:
        true_scores = np.array([p['true_score'] for p in valid])
        pred_scores = np.array([p['pred_score'] for p in valid])
        mse = float(np.mean((true_scores - pred_scores) ** 2))
        mae = float(np.mean(np.abs(true_scores - pred_scores)))
    else:
        mse = None
        mae = None
    
    return {
        'dimension': dimension,
        'mse': mse,
        'mae': mae,
        'sample_count': len(samples),
        'valid_count': len(valid),
        'success_count': len(success),
        'parse_failed_count': sum(1 for p in predictions if p.get('status') == 'parse_failed'),
        'not_found_count': sum(1 for p in predictions if p.get('status') == 'not_found'),
        'error_count': sum(1 for p in predictions if p.get('status') == 'error'),
        'predictions': predictions
    }


def format_metric(value: Optional[float]) -> str:
    return f"{value:.4f}" if value is not None else "N/A"


def main():
    ts = time.strftime("%Y%m%d-%H%M%S")
    output_dir = OUTPUT_DIR / ts
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if EVAL_SPLIT not in ["train", "test"]:
        raise ValueError("EVAL_SPLIT must be 'train' or 'test'")

    print(f"Model: {MODEL_NAME}")
    print(f"Data: {DATA_ROOT}")
    print(f"Split: {EVAL_SPLIT}")
    print(f"Output: {output_dir}\n")
    
    client = ModelClient(model=MODEL_NAME)
    
    rows = load_split_rows(EVAL_SPLIT)
    split_summary = summarize_split(rows)
    articles = load_articles()

    with open(PROMPT_FILE, 'r', encoding='utf-8') as f:
        prompts = json.load(f)

    run_config = {
        "model": MODEL_NAME,
        "judge_model": JUDGE_MODEL,
        "evaluate_reasons": EVALUATE_REASONS,
        "max_workers": MAX_WORKERS,
        "judge_max_workers": JUDGE_MAX_WORKERS,
        "data_version": DATA_VERSION,
        "data_root": str(DATA_ROOT),
        "articles_dir": str(ARTICLES_DIR),
        "prompt_file": str(PROMPT_FILE),
        "definition_file": str(DEFINITION_FILE),
        "judge_prompt_file": str(JUDGE_PROMPT_FILE),
        "supported_prediction_formats": ["xml_reason_score", "legacy_dollar_score"],
        "split_summary": split_summary,
        "article_count": len(articles)
    }
    with open(output_dir / "run_config.json", "w", encoding="utf-8") as f:
        json.dump(run_config, f, ensure_ascii=False, indent=2)
    
    results = []
    
    for dim in DIMENSIONS:
        samples = load_samples(dim, rows)
        instruction = prompts[dim.capitalize()]
        
        result = evaluate(client, samples, articles, instruction, dim)
        write_jsonl(output_dir / f"predictions_{dim}.jsonl", result['predictions'])
        
        if EVALUATE_REASONS:
            try:
                reason_eval = evaluate_reasons_from_results(
                    predictions=result['predictions'],
                    dimension=dim,
                    judge_model=JUDGE_MODEL,
                    max_workers=JUDGE_MAX_WORKERS,
                    show_progress=True,
                    definition_file=DEFINITION_FILE,
                    judge_prompt_file=JUDGE_PROMPT_FILE
                )
                result['rqs'] = reason_eval['statistics']['mean_score']
                with open(output_dir / f"rqs_{dim}.json", "w", encoding="utf-8") as f:
                    json.dump(reason_eval, f, ensure_ascii=False, indent=2)
            except:
                result['rqs'] = None
        
        results.append(result)
        print(f"{dim}: samples={result['sample_count']}, MSE={format_metric(result['mse'])}, MAE={format_metric(result['mae'])}", end="")
        if result.get('rqs'):
            print(f", RQ_{dim}: {result['rqs']:.4f}")
        else:
            print()
    
    with open(output_dir / "results.csv", 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        headers = ['Dimension', 'Samples', 'Valid', 'Success', 'ParseFailed', 'NotFound', 'Errors', 'MSE', 'MAE']
        if EVALUATE_REASONS:
            headers.append('RQS')
        writer.writerow(headers)
        
        rqs_values = []
        for r in results:
            row = [
                r['dimension'],
                r['sample_count'],
                r['valid_count'],
                r['success_count'],
                r['parse_failed_count'],
                r['not_found_count'],
                r['error_count'],
                format_metric(r['mse']),
                format_metric(r['mae'])
            ]
            if EVALUATE_REASONS:
                rqs = r.get('rqs')
                row.append(f"{rqs:.4f}" if rqs else "N/A")
                if rqs:
                    rqs_values.append(rqs)
            writer.writerow(row)
        
        if EVALUATE_REASONS and rqs_values:
            writer.writerow(['RQS_Mean', '', '', '', '', '', '', '', '', f"{np.mean(rqs_values):.4f}"])
    
    print(f"\n✅ Done: {output_dir / 'results.csv'}")


if __name__ == "__main__":
    main()
