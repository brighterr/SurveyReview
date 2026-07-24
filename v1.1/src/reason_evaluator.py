#!/usr/bin/env python3

import json
import os
import re
from pathlib import Path
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
import numpy as np
from model_client import ModelClient


PROJECT_ROOT = Path(__file__).parent.parent

DEFAULT_DATA_VERSION = os.getenv("DATA_VERSION", "v1.1-paper")
DEFAULT_DATA_ROOT = Path(os.getenv("DATA_ROOT", PROJECT_ROOT / "data" / DEFAULT_DATA_VERSION)).expanduser()
DEFAULT_DEFINITION_FILE = DEFAULT_DATA_ROOT / "prompt" / "Definition.json"
DEFAULT_JUDGE_PROMPT_FILE = DEFAULT_DATA_ROOT / "prompt" / "reason_quality_judge.json"


class ReasonEvaluator:
    def __init__(
        self,
        judge_model: str = "gpt-5.2",
        temperature: float = 0.3,
        max_workers: int = 16,
        definition_file: Path = DEFAULT_DEFINITION_FILE,
        judge_prompt_file: Path = DEFAULT_JUDGE_PROMPT_FILE
    ):
        self.max_workers = max_workers
        self.definitions = self._load_json(definition_file)
        self.judge_prompt = self._load_judge_prompt(judge_prompt_file)
        self.client = ModelClient(model=judge_model, temperature=temperature)
    
    def _load_json(self, file_path: Path) -> Dict:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _load_judge_prompt(self, file_path: Path) -> str:
        data = self._load_json(file_path)
        if isinstance(data, str):
            return data
        return data.get("reason_quality_judge", data.get("prompt", ""))
    
    def _extract_reasoning(self, text: str) -> str:
        text = text or ""
        text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
        reason_match = re.search(r"<reason>(.*?)</reason>", text, flags=re.DOTALL | re.IGNORECASE)
        if reason_match:
            return reason_match.group(1).strip()

        text = re.sub(r"<score>.*?</score>", "", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'\$\$\$.*?\$\$\$', '', text)
        return text.strip()
    
    def _parse_score(self, response: str) -> Optional[float]:
        for pattern in [r'^(0\.0|0\.2|0\.4|0\.6|0\.8|1\.0)$', r'(0\.0|0\.2|0\.4|0\.6|0\.8|1\.0)']:
            match = re.search(pattern, response.strip(), re.IGNORECASE)
            if match:
                try:
                    score = float(match.group(1))
                    if score in [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]:
                        return score
                except:
                    continue
        return None
    
    def _format_input(self, dimension: str, definition: str, title: str, true_reasons: str, pred_output: str) -> str:
        pred_reasoning = self._extract_reasoning(pred_output)
        return f"""**Dimension**: {dimension}

**Dimension Definition**: {definition}

**Paper Title**: {title}

**Reference Reasoning**: {true_reasons}

**Predicted Output**: {pred_reasoning}

Please provide your quality score (0.0, 0.2, 0.4, 0.6, 0.8, or 1.0):"""
    
    def _judge_sample(self, idx: int, pred: Dict, dimension: str, definition: str) -> Dict:
        user_input = self._format_input(
            dimension, definition,
            pred.get('paper_title', ''),
            pred.get('true_reasons', ''),
            pred.get('pred_reasoning') or pred.get('pred_output', '')
        )
        
        try:
            response = self.client.call(user_text=user_input, system_prompt=self.judge_prompt)
            score = self._parse_score(response) or -1.0
            return {
                'index': idx, 'uid': pred.get('uid', ''), 'quality_score': score,
                'true_score': pred.get('true_score', 0), 'pred_score': pred.get('pred_score', 0)
            }
        except Exception as e:
            return {'index': idx, 'uid': pred.get('uid', ''), 'quality_score': -1.0, 'error': str(e)}
    
    def evaluate_reasons(self, predictions: List[Dict], dimension: str, show_progress: bool = True) -> Dict:
        dimension_key = dimension.capitalize()
        definition = self.definitions.get(dimension_key, "")
        if not definition:
            raise ValueError(f"Definition not found for '{dimension_key}'")
        
        results = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(self._judge_sample, i, p, dimension, definition): i
                for i, p in enumerate(predictions)
            }
            
            if show_progress:
                pbar = tqdm(total=len(predictions), desc=f"RQS {dimension}", ncols=80)
            
            for future in as_completed(futures):
                results.append(future.result())
                if show_progress:
                    pbar.update(1)
            
            if show_progress:
                pbar.close()
        
        results.sort(key=lambda x: x['index'])
        
        valid = [r['quality_score'] for r in results if r['quality_score'] >= 0]
        
        if not valid:
            stats = {
                'total_samples': len(results), 'valid_samples': 0, 'failed_samples': len(results),
                'mean_score': 0.0, 'median_score': 0.0, 'std_score': 0.0, 'score_distribution': {}
            }
        else:
            distribution = {}
            for s in [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]:
                count = sum(1 for v in valid if v == s)
                distribution[str(s)] = {'count': count, 'percentage': round(count / len(valid) * 100, 2)}
            
            stats = {
                'total_samples': len(results), 'valid_samples': len(valid),
                'failed_samples': len(results) - len(valid),
                'mean_score': round(float(np.mean(valid)), 4),
                'median_score': round(float(np.median(valid)), 4),
                'std_score': round(float(np.std(valid)), 4),
                'score_distribution': distribution
            }
        
        return {'dimension': dimension, 'scored_results': results, 'statistics': stats}


def evaluate_reasons_from_results(
    predictions: List[Dict],
    dimension: str,
    judge_model: str = "gpt-5.2",
    temperature: float = 0.3,
    max_workers: int = 16,
    show_progress: bool = True,
    definition_file: Path = DEFAULT_DEFINITION_FILE,
    judge_prompt_file: Path = DEFAULT_JUDGE_PROMPT_FILE
) -> Dict:
    evaluator = ReasonEvaluator(
        judge_model=judge_model,
        temperature=temperature,
        max_workers=max_workers,
        definition_file=definition_file,
        judge_prompt_file=judge_prompt_file
    )
    return evaluator.evaluate_reasons(predictions, dimension, show_progress)


def save_reason_evaluation(evaluation_result: Dict, output_dir: Path):
    return None, None
