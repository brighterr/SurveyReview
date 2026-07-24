# SurveyReview

This repository keeps SurveyReview releases side by side.

## Versions

- `v1.0/`: the original SurveyReview code, data, prompts, and training scripts.
- `v1.1/`: the updated release using cleaned article texts and XML-like rationale prompts.

## Run Evaluation

For the original release:

```bash
cd v1.0
python src/api_base_evaluate.py
```

For the updated release:

```bash
cd v1.1
python src/api_base_evaluate.py
```

`v1.1` keeps the SurveyReview evaluation style: MSE, MAE, parse statistics, and optional RQS. It does not use the RL reward calculation from `/zyh/RL/test`.
