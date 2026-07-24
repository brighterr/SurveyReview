# SurveyReview Training

This directory contains lightweight training recipes for reproducing the
SurveyReviewer SFT models with LLaMA-Factory.

## Layout

```text
training/
  llamafactory/
    configs/qwen3_32b/        # Main Qwen3-32B SFT configs
    dataset_info.example.json # LLaMA-Factory dataset registry example
  scripts/                    # Data conversion scripts will live here
```

The configs expect generated LLaMA-Factory-format data under:

```text
training/generated/
```

Training outputs should be written under:

```text
training/outputs/
```

These generated directories are intentionally not committed.

## Build LLaMA-Factory Data

Generate Alpaca-format SFT data from the paper reproduction split:

```bash
python training/scripts/build_llamafactory_data.py
```

This writes:

```text
training/generated/
  dataset_info.json
  surveyreview_readability.json
  surveyreview_criticalness.json
  surveyreview_comprehensiveness.json
  surveyreview_structure.json
  build_stats.json
```

By default, the script uses `data/v1.0-paper/train/grouped_trainset.json`
and skips labels with score `0` or `-3`, matching the evaluation pipeline.

