# Self-Correcting Code Generator - Evaluation Report

## Executive Summary

This system generates Python code using local LLMs, executes it in Docker sandboxes, and automatically fixes errors through iterative feedback. Evaluated on HumanEval and MBPP benchmarks with cross-model comparison.

## Key Results

| Dataset | Model | Pass@1 | Pass@3 | Improvement |
|---------|-------|--------|--------|-------------|
| HumanEval (30) | Codellama-7B | 66.7% | 70.0% | 5.0% |
| MBPP (10) | Codellama-7B | 30.0% | 40.0% | 33.3% |
| HumanEval (10) | Codellama-7B | 60.0% | 70.0% | 16.7% |
| HumanEval (10) | Llama-70B | 90.0% | 90.0% | 0.0% |

## Key Finding: Self-Correction Benefits Weaker Models More

| Model | Pass@1 | Pass@3 | Improvement | Avg Time |
|-------|--------|--------|-------------|----------|
| Codellama-7B (local) | 60% | 70% | 16.7% | 27.3s |
| Llama-70B (Groq) | 90% | 90% | 0% | 1.7s |

The 70B model achieves 90% on first attempt, leaving no room for improvement. The 7B model benefits significantly from self-correction, improving by 16.7%.

**Implication:** Self-correction is most valuable for resource-constrained deployments using smaller models.

## Error Analysis

### Error Distribution (HumanEval 30)

| Error Type | Count | Percentage |
|------------|-------|------------|
| LOGIC | 17 | 85% |
| SYNTAX | 2 | 10% |
| TYPE | 1 | 5% |

### Fixability by Error Type

| Error Type | Fix Rate |
|------------|----------|
| LOGIC | 12.5% |
| SYNTAX | 0% |
| TYPE | 0% |

Logic errors dominate but are hardest to fix. Improved prompts with step-by-step reasoning increased fix rates on MBPP from 0% to 33%.

## Architecture
```
User Request → LLM Generation → Docker Sandbox → Test Execution
                    ↑                                  ↓
                    └──── Error Parsing ← Failed Tests ┘
```

## Prompt Engineering Impact

Initial MBPP results: 6.7% Pass@1
After adding function signatures: 36.7% Pass@1
After improved repair prompts: 33% improvement from self-correction

Prompt engineering had massive impact on baseline performance.

## Safety Measures

- Docker containers with no network access
- 512MB memory limit, 15s timeout
- Malicious code detection before execution
- Non-root user in container

## Conclusions

1. **Self-correction works best for weaker models** - 16.7% improvement for 7B vs 0% for 70B
2. **Logic errors are hardest to fix** - only 12.5% fix rate
3. **Prompt engineering matters** - 5x improvement on MBPP from better prompts
4. **Step-by-step reasoning helps** - improved MBPP fix rate from 0% to 33%

## Future Work

- Include expected outputs in repair prompts
- Adaptive strategies based on error type
- Fine-tuning on self-correction data