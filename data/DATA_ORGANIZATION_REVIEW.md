# Data Organization Review for Open Source LLM Evaluation Project

## 📊 Current Structure Overview

```
/zyh/Data/Final/data/
├── articles/
│   └── articles4test.json          (18MB, 164 lines)
├── prompt/
│   ├── prompt.json                 (4 evaluation dimension prompts)
│   └── reason_quality_judge.json   (Quality assessment rubric)
└── testset/
    ├── readability.json            (120 samples)
    ├── criticalness.json           (112 samples)
    ├── comprehensiveness.json      (106 samples)
    └── structure.json              (110 samples)
```

## ✅ Strengths

### 1. **Clear Separation of Concerns**
- ✓ Articles (input data) separated from test sets (ground truth)
- ✓ Prompts isolated in dedicated directory
- ✓ Each evaluation dimension has its own test file

### 2. **Structured Data Format**
- ✓ Consistent JSON format across all files
- ✓ Well-defined schema for test samples:
  ```json
  {
    "uid": "unique-identifier",
    "score": -2.0 | -1.0 | 1.0 | 2.0,
    "reasons": ["reason1", "reason2", ...]
  }
  ```

### 3. **Comprehensive Evaluation Framework**
- ✓ Four key dimensions: Readability, Criticalness, Comprehensiveness, Structure
- ✓ Clear scoring rubric (-2, -1, 1, 2)
- ✓ Detailed prompts with examples
- ✓ Quality assessment framework for predicted reasoning

### 4. **Good Sample Size**
- ✓ ~110 samples per dimension
- ✓ Reasonable score distribution (balanced negative/positive)

## ⚠️ Issues & Concerns

### 🔴 **CRITICAL: UID Inconsistency**

**Problem:** Only **41 UIDs** are common across all four dimensions!

```
Total UIDs per dimension:
- Readability:        120 UIDs (79 unique)
- Criticalness:       112 UIDs (71 unique)
- Comprehensiveness:  106 UIDs (65 unique)
- Structure:          110 UIDs (69 unique)
Common across all:     41 UIDs
```

**Impact:**
- Cannot perform multi-dimensional evaluation on most samples
- Difficult to analyze correlation between dimensions
- Incomplete evaluation for ~70% of samples

**Recommendation:**
```
Option 1 (Recommended): Create a CORE test set
- Select the 41 common UIDs as the primary benchmark
- Add supplementary dimension-specific tests

Option 2: Expand coverage
- Annotate missing dimensions for all UIDs
- Achieve 120+ samples across all dimensions
```

### 🟡 **Missing Documentation**

**Problem:** No README, schema documentation, or data card

**Needed:**
1. **README.md** - Project overview, usage instructions
2. **SCHEMA.md** - Data format specification
3. **DATACARD.md** - Dataset statistics, provenance, limitations
4. **CHANGELOG.md** - Version history

### 🟡 **Missing Metadata**

**Problem:** No dataset-level metadata file

**Recommendation:** Add `metadata.json`:
```json
{
  "dataset_name": "Academic Paper Review Quality Benchmark",
  "version": "1.0.0",
  "created_date": "2026-02-08",
  "description": "Multi-dimensional evaluation benchmark for LLM-generated academic paper reviews",
  "dimensions": ["readability", "criticalness", "comprehensiveness", "structure"],
  "total_samples": 120,
  "common_samples": 41,
  "score_scale": [-2, -1, 1, 2],
  "languages": ["en"],
  "domain": "academic_peer_review",
  "license": "TBD"
}
```

### 🟡 **Score Distribution Imbalance**

**Current distribution:**
```
Readability:        -2(8%) -1(60%) 1(24%) 2(8%)
Criticalness:       -2(13%) -1(52%) 1(29%) 2(7%)
Comprehensiveness:  -2(9%) -1(70%) 1(13%) 2(8%)
Structure:          -2(6%) -1(70%) 1(22%) 2(3%)
```

**Issue:** Heavy skew toward -1 score (52-70%)

**Recommendation:**
- Consider whether this reflects real data distribution
- If not, balance the dataset for better evaluation coverage

### 🟡 **Missing Examples/Cases**

**Problem:** No curated example cases for demonstration

**Recommendation:** Add `examples/` directory:
```
examples/
├── excellent_predictions/      # High-quality model outputs
├── poor_predictions/           # Common failure cases
├── edge_cases/                 # Challenging examples
└── multilingual/ (optional)    # Non-English examples
```

### 🟡 **No Test/Validation Split**

**Problem:** All data in single test set

**Recommendation:**
```
testset/
├── dev/           # Development set (20%) - for prompt tuning
├── test/          # Test set (80%) - for final evaluation
└── challenge/     # Hard cases - for advanced evaluation
```

### 🟡 **Articles File Too Large**

**Problem:** `articles4test.json` is 18MB (single file)

**Recommendation:**
```
articles/
├── index.json                    # Metadata index
└── papers/
    ├── openreview/              # By source
    ├── f1000/
    ├── moprd/
    └── [uid].json               # Individual paper files
```

## 📋 Recommended New Structure

```
/zyh/Data/Final/data/
├── README.md                          # Project overview
├── SCHEMA.md                          # Data format specification
├── DATACARD.md                        # Dataset card
├── metadata.json                      # Dataset metadata
├── LICENSE                            # License information
│
├── articles/
│   ├── index.json                     # Article index with metadata
│   └── papers/                        # Individual paper files
│       ├── [uid].json
│       └── ...
│
├── testset/
│   ├── core/                          # 41 common UIDs across all dimensions
│   │   ├── readability.json
│   │   ├── criticalness.json
│   │   ├── comprehensiveness.json
│   │   └── structure.json
│   │
│   ├── supplementary/                 # Dimension-specific samples
│   │   ├── readability_extra.json
│   │   ├── criticalness_extra.json
│   │   └── ...
│   │
│   └── splits/                        # Optional dev/test splits
│       ├── dev/
│       └── test/
│
├── prompts/
│   ├── evaluation_prompts.json        # Dimension-specific prompts
│   └── quality_judge_prompt.json      # Quality assessment prompt
│
├── examples/
│   ├── excellent_predictions/         # Example high-quality outputs
│   ├── poor_predictions/              # Example poor outputs
│   └── edge_cases/                    # Challenging cases
│
├── scripts/                           # Utility scripts
│   ├── validate_data.py               # Data validation
│   ├── compute_metrics.py             # Evaluation metrics
│   └── visualize_results.py           # Result visualization
│
└── baselines/                         # Baseline model results
    ├── gpt4/
    ├── claude/
    └── ...
```

## 🎯 Priority Action Items

### 🔥 High Priority
1. ✅ **Resolve UID inconsistency**
   - Create core test set (41 common UIDs)
   - Document dimension-specific samples

2. ✅ **Add documentation**
   - README.md with usage instructions
   - SCHEMA.md with data format
   - DATACARD.md with dataset statistics

3. ✅ **Add metadata.json**
   - Version, provenance, statistics
   - License information

### 🟠 Medium Priority
4. **Reorganize articles directory**
   - Split large JSON into individual files
   - Add index file

5. **Add example cases**
   - Curate 5-10 excellent predictions
   - Document common failure patterns

6. **Add validation scripts**
   - Data format validation
   - UID consistency checker
   - Score distribution analyzer

### 🟢 Low Priority
7. **Create dev/test splits**
   - Enable systematic prompt tuning

8. **Add baseline results**
   - Document commercial LLM performance
   - Enable comparison

9. **Internationalization**
   - Consider multilingual support (if applicable)

## 🔧 Quick Wins

### Immediate improvements (< 1 hour):
```bash
# 1. Add README.md
# 2. Add metadata.json
# 3. Add LICENSE file
# 4. Create validation script
```

### Short-term improvements (< 1 day):
```bash
# 1. Resolve UID inconsistency → create core + supplementary split
# 2. Add SCHEMA.md and DATACARD.md
# 3. Reorganize articles directory
# 4. Add example cases
```

## 📝 Additional Recommendations

### For Open Source Release:

1. **Add Citation Information**
   ```bibtex
   @dataset{your_dataset_2026,
     title={Academic Paper Review Quality Benchmark},
     author={...},
     year={2026},
     url={...}
   }
   ```

2. **Add Contribution Guidelines**
   - How to report issues
   - How to submit new test cases
   - Code of conduct

3. **Add Evaluation Metrics**
   - Define exact metric computation
   - Provide reference implementation
   - Document expected performance ranges

4. **Add Leaderboard Format**
   - Standard result reporting format
   - Submission guidelines

5. **Consider Data Versioning**
   - Use semantic versioning (v1.0.0)
   - Track changes in CHANGELOG.md

## Summary

**Current State:** ⚠️ Functional but needs refinement

**Strengths:**
- Good conceptual organization
- Clear evaluation framework
- Reasonable sample size

**Main Issues:**
- UID inconsistency across dimensions (CRITICAL)
- Missing documentation
- No metadata/versioning
- Large monolithic files

**Recommendation:** The data organization is **usable** for an open source project, but requires **refinement** before public release. Focus on resolving the UID inconsistency and adding proper documentation first.

**Estimated effort to production-ready:** 2-3 days of focused work

---

*Generated: 2026-02-08*
*Reviewer: AI Assistant*
