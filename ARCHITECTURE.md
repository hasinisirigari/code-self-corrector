# System Architecture

## High-Level Overview
```
┌─────────────────────────────────────────────────────────────────┐
│                        USER INPUT                                │
│              (Function description + Test cases)                 │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      ORCHESTRATOR                                │
│                   (src/loop/orchestrator.py)                     │
│                                                                  │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐         │
│  │  Attempt 1  │───▶│  Attempt 2  │───▶│  Attempt 3  │         │
│  └─────────────┘    └─────────────┘    └─────────────┘         │
│         │                  │                  │                  │
│         ▼                  ▼                  ▼                  │
│    [Generate]         [Repair]          [Repair]                │
└─────────────────────────────────────────────────────────────────┘
                                │
                ┌───────────────┴───────────────┐
                ▼                               ▼
┌───────────────────────────┐   ┌───────────────────────────────┐
│        LLM CLIENT         │   │       DOCKER SANDBOX          │
│   (src/llm/ollama_client) │   │  (src/sandbox/docker_runner)  │
│   (src/llm/groq_client)   │   │                               │
│                           │   │  ┌─────────────────────────┐  │
│  • Codellama-7B (local)   │   │  │   Isolated Container    │  │
│  • Llama-70B (Groq API)   │   │  │   • No network          │  │
│  • Code extraction        │   │  │   • 512MB memory        │  │
│  • Prompt formatting      │   │  │   • 15s timeout         │  │
│                           │   │  │   • Non-root user       │  │
└───────────────────────────┘   │  └─────────────────────────┘  │
                                │                               │
                                │  • Runs pytest                │
                                │  • Captures stdout/stderr     │
                                │  • Returns pass/fail          │
                                └───────────────────────────────┘
                                                │
                                                ▼
                                ┌───────────────────────────────┐
                                │       ERROR PARSER            │
                                │  (src/loop/error_parser.py)   │
                                │                               │
                                │  • Classifies error type      │
                                │  • Extracts line number       │
                                │  • Identifies failing tests   │
                                │  • Calculates fixability      │
                                └───────────────────────────────┘
                                                │
                                                ▼
                                ┌───────────────────────────────┐
                                │       PATCH BUILDER           │
                                │  (src/loop/patch_builder.py)  │
                                │                               │
                                │  • Builds repair prompt       │
                                │  • Includes test assertions   │
                                │  • Step-by-step reasoning     │
                                └───────────────────────────────┘
                                                │
                                                ▼
                                        [Back to LLM]

## Data Flow
```
User Request
     │
     ▼
┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐
│ Generate │────▶│  Test   │────▶│  Parse  │────▶│ Repair  │
│  Code   │     │  Code   │     │  Error  │     │ Prompt  │
└─────────┘     └─────────┘     └─────────┘     └─────────┘
                     │                               │
                     ▼                               │
                [SUCCESS]◀───────────────────────────┘
                    or
              [MAX_ATTEMPTS]
```

## Component Responsibilities

| Component | File | Purpose |
|-----------|------|---------|
| Orchestrator | `src/loop/orchestrator.py` | Controls retry loop, tracks attempts |
| Ollama Client | `src/llm/ollama_client.py` | Local LLM inference |
| Groq Client | `src/llm/groq_client.py` | Cloud LLM inference |
| Docker Runner | `src/sandbox/docker_runner.py` | Safe code execution |
| Guardrails | `src/sandbox/guardrails.py` | Malicious code detection |
| Error Parser | `src/loop/error_parser.py` | Error classification |
| Patch Builder | `src/loop/patch_builder.py` | Repair prompt construction |
| Benchmarks | `src/eval/benchmarks.py` | HumanEval/MBPP loading |
| Runner | `src/eval/runner.py` | Evaluation CLI |
| Metrics | `src/eval/metrics.py` | Pass@k calculation |

## Safety Architecture
```
┌─────────────────────────────────────────┐
│            SAFETY LAYERS                │
├─────────────────────────────────────────┤
│ 1. Pre-execution: Guardrails check      │
│    • Block os.system, eval, exec        │
│    • Block file operations              │
│    • Block network calls                │
├─────────────────────────────────────────┤
│ 2. Container isolation:                 │
│    • --network=none                     │
│    • --memory=512m                      │
│    • --timeout=15s                      │
│    • --user=testrunner (non-root)       │
├─────────────────────────────────────────┤
│ 3. Post-execution: Cleanup              │
│    • Remove temp files                  │
│    • Kill container                     │
└─────────────────────────────────────────┘
```

## Evaluation Pipeline
```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Load       │────▶│    Run       │────▶│   Generate   │
│  Benchmark   │     │  Evaluation  │     │   Reports    │
│  (HumanEval/ │     │  (n problems)│     │   & Charts   │
│   MBPP)      │     │              │     │              │
└──────────────┘     └──────────────┘     └──────────────┘
                            │
                            ▼
                     ┌──────────────┐
                     │   Metrics    │
                     │  • Pass@1    │
                     │  • Pass@3    │
                     │  • Error dist│
                     │  • Fixability│
                     └──────────────┘