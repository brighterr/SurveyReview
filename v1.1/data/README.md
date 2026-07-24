# SurveyReview v1.1 Data

This directory contains the `v1.1-paper` data release.

## v1.1-paper

`v1.1-paper` keeps the original SurveyReview train/test labels and uses cleaned article texts.

The review-level data counts reported in the paper correspond to the files under:

```text
data/v1.1-paper/raw/
```

The `raw/` directory stores the original train/test review samples used for the paper data statistics.

## Reproducing Paper Results

To reproduce the paper setting, use the following directories:

```text
data/v1.1-paper/articles/
data/v1.1-paper/prompt/
data/v1.1-paper/train/
data/v1.1-paper/test/
```

Their roles are:

| Directory | Description |
| --- | --- |
| `articles/` | Cleaned article full texts split into `articles_part1.json` and `articles_part2.json` for GitHub file-size limits |
| `prompt/` | v1.1 prompts using `<reason>...</reason> <score>X</score>` output format |
| `train/` | Train data grouped by survey |
| `test/` | Test data grouped by survey |

The files under `train/` and `test/` have already been grouped by survey, so they are the directly usable version for training and evaluation.
