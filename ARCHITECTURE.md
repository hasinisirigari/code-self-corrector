# System Architecture

## High-Level Overview
```mermaid
flowchart TB
    UI[User Input<br>Function + Tests] --> ORCH
    
    subgraph ORCH[Orchestrator]
        A1[Attempt 1<br>Generate] --> A2[Attempt 2<br>Repair]
        A2 --> A3[Attempt 3<br>Repair]
    end
    
    ORCH --> LLM[LLM Client<br>Codellama-7B / Llama-70B]
    ORCH --> SANDBOX[Docker Sandbox<br>Isolated Execution]
    
    SANDBOX --> PARSER[Error Parser<br>Classify & Extract]
    PARSER --> PATCH[Patch Builder<br>Repair Prompt]
    PATCH --> LLM
```

## Data Flow
```mermaid
flowchart LR
    A[User Request] --> B[Generate Code]
    B --> C[Test in Sandbox]
    C --> D{Passed?}
    D -->|Yes| E[SUCCESS]
    D -->|No| F[Parse Error]
    F --> G[Build Repair Prompt]
    G --> B
```

## Safety Architecture
```mermaid
flowchart TB
    subgraph SAFETY[Safety Layers]
        L1[1. Pre-execution<br>Block dangerous patterns]
        L2[2. Container Isolation<br>No network, memory limit]
        L3[3. Post-execution<br>Cleanup temp files]
    end
    
    L1 --> L2 --> L3
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

## Sandbox Security

| Layer | Protection |
|-------|------------|
| Pre-execution | Block os.system, eval, exec, file ops, network |
| Container | --network=none, --memory=512m, --timeout=15s |
| User | Non-root testrunner user |
| Cleanup | Remove temp files, kill container |