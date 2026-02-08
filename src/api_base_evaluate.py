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

TESTSET_DIR = PROJECT_ROOT / "data" / "testset"
ARTICLES_FILE = PROJECT_ROOT / "data" / "articles" / "articles4test.json"
PROMPT_FILE = PROJECT_ROOT / "data" / "prompt" / "eval-prompt.json"
OUTPUT_DIR = PROJECT_ROOT / "result"

MODEL_NAME = os.getenv("MODEL_NAME", "gpt-5.2")
JUDGE_MODEL = os.getenv("JUDGE_MODEL", "gpt-5.2")
MAX_WORKERS = int(os.getenv("MAX_WORKERS", "64"))
JUDGE_MAX_WORKERS = int(os.getenv("JUDGE_MAX_WORKERS", "32"))
EVALUATE_REASONS = os.getenv("EVALUATE_REASONS", "True").lower() == "true"


def extract_score(text: str) -> Optional[int]:
    match = re.search(r'\$\$\$\s*(-?\d+(?:\.\d+)?)\s*\$\$\$', text or "")
    if match:
        try:
            score = int(float(match.group(1)))
            return score if score in [-2, -1, 1, 2] else None
        except:
            return None
    return None


def load_samples(dimension: str) -> List[Dict]:
    with open(TESTSET_DIR / f"{dimension}.json", 'r', encoding='utf-8') as f:
        data = json.load(f)
    return [
        {"uid": item["uid"], "score": int(item["score"]), "reasons": item.get("reasons", [])}
        for item in data if item.get("score", 0) != 0
    ]


def evaluate_sample(idx: int, sample: Dict, articles: Dict, instruction: str, client: ModelClient) -> Dict:
    uid = sample['uid']
    true_score = sample['score']
    reasons = sample['reasons']
    
    paper = articles.get(uid)
    if not paper:
        return {
            'index': idx, 'uid': uid, 'true_score': true_score,
            'true_reasons': " ".join(reasons), 'pred_output': "Paper not found",
            'pred_score': 0, 'error': abs(true_score), 'status': 'not_found'
        }
    
    try:
        output = client.call(user_text=f"{instruction}\n\n{paper}")
        pred_score = extract_score(output) or 0
        return {
            'index': idx, 'uid': uid, 'true_score': true_score,
            'true_reasons': " ".join(reasons), 'pred_output': output,
            'pred_score': pred_score, 'error': abs(true_score - pred_score), 'status': 'success'
        }
    except Exception as e:
        return {
            'index': idx, 'uid': uid, 'true_score': true_score,
            'true_reasons': " ".join(reasons), 'pred_output': str(e),
            'pred_score': 0, 'error': abs(true_score), 'status': 'error'
        }


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
    
    valid = [p for p in predictions if p.get('status') == 'success']
    true_scores = np.array([p['true_score'] for p in valid])
    pred_scores = np.array([p['pred_score'] for p in valid])
    
    return {
        'dimension': dimension,
        'mse': float(np.mean((true_scores - pred_scores) ** 2)),
        'mae': float(np.mean(np.abs(true_scores - pred_scores))),
        'predictions': predictions
    }


def main():
    ts = time.strftime("%Y%m%d-%H%M%S")
    output_dir = OUTPUT_DIR / ts
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Model: {MODEL_NAME}\nOutput: {output_dir}\n")
    
    client = ModelClient(model=MODEL_NAME)
    
    with open(ARTICLES_FILE, 'r', encoding='utf-8') as f:
        articles = json.load(f)
    with open(PROMPT_FILE, 'r', encoding='utf-8') as f:
        prompts = json.load(f)
    
    results = []
    
    for dim in DIMENSIONS:
        samples = load_samples(dim)
        instruction = prompts[dim.capitalize()]
        
        result = evaluate(client, samples, articles, instruction, dim)
        
        if EVALUATE_REASONS:
            try:
                reason_eval = evaluate_reasons_from_results(
                    predictions=result['predictions'],
                    dimension=dim,
                    judge_model=JUDGE_MODEL,
                    max_workers=JUDGE_MAX_WORKERS,
                    show_progress=True
                )
                result['rqs'] = reason_eval['statistics']['mean_score']
            except:
                result['rqs'] = None
        
        results.append(result)
        print(f"MSE: {result['mse']:.4f}, MAE: {result['mae']:.4f}", end="")
        if result.get('rqs'):
            print(f", RQ_{dim}: {result['rqs']:.4f}")
        else:
            print()
    
    with open(output_dir / "results.csv", 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        headers = ['Dimension', 'MSE', 'MAE']
        if EVALUATE_REASONS:
            headers.append('RQS')
        writer.writerow(headers)
        
        rqs_values = []
        for r in results:
            row = [r['dimension'], f"{r['mse']:.4f}", f"{r['mae']:.4f}"]
            if EVALUATE_REASONS:
                rqs = r.get('rqs')
                row.append(f"{rqs:.4f}" if rqs else "N/A")
                if rqs:
                    rqs_values.append(rqs)
            writer.writerow(row)
        
        if EVALUATE_REASONS and rqs_values:
            writer.writerow(['RQS_Mean', '', '', f"{np.mean(rqs_values):.4f}"])
    
    print(f"\n✅ Done: {output_dir / 'results.csv'}")


if __name__ == "__main__":
    main()
