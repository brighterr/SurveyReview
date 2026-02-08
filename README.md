# SurveyReview
SurveyReview: A Reviewer-Aligned Benchmark for Evaluating Survey Papers

## Environment

- **Python**: 3.9+
- **Install dependencies**:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

- **Configure `.env`** (copy from `.env.example` and fill in):
  - `API_KEY`: your API key
  - `BASE_URL`: OpenAI-compatible base URL (e.g. `https://api.openai.com/v1` or your local gateway)
  - `MODEL_NAME`: model used for evaluation (default `gpt-5.2`)
  - `JUDGE_MODEL`: model used for RQS judging (default `gpt-5.2`)
  - Optional: `MAX_WORKERS`, `JUDGE_MAX_WORKERS`, `TEMPERATURE`, `MAX_TOKENS`, `TIMEOUT`

## Run Evaluation

```bash
python src/api_base_evaluate.py
```

- Outputs are written to `result/<timestamp>/results.csv`.

## Leader Board


<table>
  <thead>
    <tr>
      <th rowspan="2">Rank</th>
      <th rowspan="2">Model</th>
      <th rowspan="2">SSR ↑</th>
      <th rowspan="2">RQS ↑</th>
      <th colspan="2">AVE</th>
      <th colspan="2">Read.</th>
      <th colspan="2">Crit.</th>
      <th colspan="2">Comp.</th>
      <th colspan="2">Stru.</th>
    </tr>
    <tr>
      <th>MSE</th><th>MAE</th>
      <th>MSE</th><th>MAE</th>
      <th>MSE</th><th>MAE</th>
      <th>MSE</th><th>MAE</th>
      <th>MSE</th><th>MAE</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>1</td>
      <td>SurveyReviewer</td>
      <td><b>0.74</b></td>
      <td>0.36</td>
      <td><b>1.38</b></td><td><b>0.69</b></td>
      <td><b>1.43</b></td><td><b>0.72</b></td>
      <td><b>1.52</b></td><td><b>0.82</b></td>
      <td><b>1.26</b></td><td><b>0.56</b></td>
      <td><b>1.29</b></td><td><b>0.65</b></td>
    </tr>
    <tr>
      <td>2</td>
      <td>GPT-5.2</td>
      <td>0.68</td>
      <td>0.42</td>
      <td>2.28</td><td>1.15</td>
      <td>2.13</td><td>1.07</td>
      <td>1.97</td><td>0.97</td>
      <td>2.04</td><td>1.08</td>
      <td>2.98</td><td>1.47</td>
    </tr>
    <tr>
      <td>3</td>
      <td>Claude-Opus-4.5</td>
      <td>0.68</td>
      <td><b>0.48</b></td>
      <td>2.77</td><td>1.25</td>
      <td>2.91</td><td>1.29</td>
      <td>1.88</td><td>0.88</td>
      <td>2.66</td><td>1.23</td>
      <td>3.65</td><td>1.58</td>
    </tr>
    <tr>
      <td>4</td>
      <td>Qwen3-32B</td>
      <td>0.61</td>
      <td>0.36</td>
      <td>3.21</td><td>1.51</td>
      <td>3.05</td><td>1.45</td>
      <td>3.24</td><td>1.51</td>
      <td>3.22</td><td>1.54</td>
      <td>3.35</td><td>1.53</td>
    </tr>
    <tr>
      <td>5</td>
      <td>GLM-4.7</td>
      <td>0.60</td>
      <td>0.37</td>
      <td>3.62</td><td>1.56</td>
      <td>3.43</td><td>1.50</td>
      <td>2.58</td><td>1.21</td>
      <td>3.66</td><td>1.57</td>
      <td>4.83</td><td>1.95</td>
    </tr>
    <tr>
      <td>6</td>
      <td>gemini-3-pro</td>
      <td>0.58</td>
      <td>0.29</td>
      <td>3.94</td><td>1.53</td>
      <td>3.84</td><td>1.52</td>
      <td>2.25</td><td>1.00</td>
      <td>3.91</td><td>1.49</td>
      <td>5.76</td><td>2.11</td>
    </tr>
    <tr>
      <td>7</td>
      <td>DeepSeek-v3.2</td>
      <td>0.58</td>
      <td>0.37</td>
      <td>3.97</td><td>1.65</td>
      <td>4.78</td><td>1.88</td>
      <td>2.49</td><td>1.15</td>
      <td>4.59</td><td>1.82</td>
      <td>4.02</td><td>1.76</td>
    </tr>
  </tbody>
</table>



## Data availability

Due to data redistribution restrictions, please contact `zhangyuheng@ruc.edu.cn` to request access to the original data.

