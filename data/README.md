# SurveyReview Data

This directory contains the `v1.0-paper` data release.

## v1.0-paper

`v1.0-paper` is the paper-aligned version of SurveyReview .

The review-level data counts reported in the paper correspond to the files under:

```text
data/v1.0-paper/raw/
```

The `raw/` directory stores the original train/test review samples used for the paper data statistics.

## Reproducing Paper Results

To reproduce the paper setting, use the following directories:

```text
data/v1.0-paper/articles/
data/v1.0-paper/prompt/
data/v1.0-paper/train/
data/v1.0-paper/test/
```

Their roles are:

| Directory | Description |
| --- | --- |
| `articles/` | Article full texts used in the paper experiments, split into `articles_part1.json` and `articles_part2.json` for GitHub file-size limits |
| `prompt/` | Prompts used in the paper experiments |
| `train/` | Train data grouped by survey |
| `test/` | Test data grouped by survey |

The files under `train/` and `test/` have already been grouped by survey, so they are the directly usable version for training and evaluation.
