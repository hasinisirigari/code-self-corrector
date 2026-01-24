# Self-Correcting Code Generator - Evaluation Report

## Executive Summary

Self-correcting code generation system evaluated on 200 problems across HumanEval and MBPP benchmarks. Key finding: self-correction provides up to 32% improvement, with weaker models benefiting more.

## Results Summary

| Benchmark | Problems | Pass@1 | Pass@3 | Improvement |
|-----------|----------|--------|--------|-------------|
| HumanEval | 100 | 44.0% | 48.0% | 9.1% |
| MBPP | 100 | 28.0% | 37.0% | 32.1% |
| **Combined** | **200** | **36.0%** | **42.5%** | **18.1%** |

## Model Comparison (HumanEval n=10)

| Model | Pass@1 | Pass@3 | Improvement |
|-------|--------|--------|-------------|
| Codellama-7B | 60% | 70% | 16.7% |
| Llama-70B | 90% | 90% | 0% |

**Finding:** Weaker models benefit more from self-correction.

## Error Distribution

### HumanEval
| Error Type | Count | Percentage |
|------------|-------|------------|
| LOGIC | 77 | 69% |
| NAME | 15 | 13% |
| RUNTIME | 9 | 8% |
| TYPE | 7 | 6% |
| SYNTAX | 4 | 4% |

### MBPP
| Error Type | Count | Percentage |
|------------|-------|------------|
| LOGIC | 67 | 50% |
| NAME | 51 | 38% |
| TYPE | 8 | 6% |
| RUNTIME | 7 | 5% |
| SYNTAX | 2 | 1% |

## Fixability by Error Type

### HumanEval
| Error Type | Fix Rate |
|------------|----------|
| NAME | 33.3% |
| RUNTIME | 20.0% |
| LOGIC | 0% |

### MBPP
| Error Type | Fix Rate |
|------------|----------|
| LOGIC | 14.3% |
| NAME | 14.3% |
| TYPE | 0% |
| RUNTIME | 0% |

**Finding:** LOGIC errors are fixable on MBPP (14.3%) but not on HumanEval (0%), suggesting problem complexity affects fixability.

## Key Insights

1. **MBPP benefits more from self-correction (32.1%)** than HumanEval (9.1%)
2. **Lower baseline = more room to improve** - MBPP started at 28% vs HumanEval's 44%
3. **Weaker models benefit more** - 7B improved 16.7%, 70B improved 0%
4. **LOGIC errors dominate** both benchmarks but fixability varies
5. **NAME errors are consistently fixable** across both benchmarks

## Conclusions

Self-correction is most valuable when:
- Using smaller/weaker models
- Baseline performance is lower
- Error types are more mechanical (NAME, SYNTAX)

Self-correction is less effective when:
- Model already achieves high accuracy
- Errors require deep algorithmic understanding

## Future Work

- Include expected vs actual output in repair prompts
- Adaptive repair strategies based on error type
- Fine-tuning on self-correction data