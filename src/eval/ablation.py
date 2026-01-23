import time
import json
from pathlib import Path
from rich.console import Console
from rich.table import Table

from .benchmarks import load_mbpp
from ..loop.orchestrator import Orchestrator
from ..llm.ollama_client import OllamaClient
from ..sandbox.docker_runner import DockerSandbox
from ..loop.error_parser import ErrorInfo, ErrorCategory

console = Console()


def basic_repair(code: str, error: ErrorInfo, tests: str) -> str:
    return f"""Fix this code:
```python
{code}
```

Error: {error.error_type}: {error.message}

Return ONLY the fixed code."""


def with_tests_repair(code: str, error: ErrorInfo, tests: str) -> str:
    test_lines = [l.strip() for l in tests.split('\n') if 'assert' in l]
    test_str = "\n".join(test_lines[:5])
    
    return f"""Fix this code:
```python
{code}
```

Error: {error.error_type}

Expected behavior:
{test_str}

Return ONLY the fixed code."""


def stepbystep_repair(code: str, error: ErrorInfo, tests: str) -> str:
    test_lines = [l.strip() for l in tests.split('\n') if 'assert' in l]
    test_str = "\n  ".join(test_lines[:5])
    
    return f"""The code below produces WRONG OUTPUT.
```python
{code}
```

Expected behavior from tests:
  {test_str}

Think step by step:
1. What does each test expect?
2. What is the current code actually doing?
3. How should the logic change?

Return ONLY the fixed code, no explanation."""


class AblationOrchestrator(Orchestrator):
    def __init__(self, repair_fn, **kwargs):
        super().__init__(**kwargs)
        self.repair_fn = repair_fn
    
    def _build_repair(self, code, error, problem_desc, tests):
        return self.repair_fn(code, error, tests)


def run_ablation(limit: int = 15):
    console.print("\n[bold]Ablation Study: Prompt Strategies[/bold]\n")
    
    problems = load_mbpp(limit=limit)
    console.print(f"Running on {len(problems)} MBPP problems\n")
    
    sandbox = DockerSandbox()
    llm = OllamaClient()
    
    strategies = [
        ("basic", basic_repair),
        ("with_tests", with_tests_repair),
        ("step_by_step", stepbystep_repair),
    ]
    
    results = {}
    
    for name, repair_fn in strategies:
        console.print(f"[cyan]Testing: {name}[/cyan]")
        
        # monkey-patch the repair function
        from ..loop import patch_builder
        original = patch_builder.build_adaptive_repair_prompt
        patch_builder.build_adaptive_repair_prompt = lambda c, e, p, t, fn=repair_fn: fn(c, e, t)
        
        orch = Orchestrator(llm=llm, sandbox=sandbox, max_attempts=3)
        
        pass1 = 0
        pass3 = 0
        
        for p in problems:
            r = orch.solve(p.prompt, p.tests)
            if r.solved:
                pass3 += 1
                if len(r.attempts) == 1:
                    pass1 += 1
            console.print(f"  {p.task_id}: {'✓' if r.solved else '✗'}")
        
        # restore
        patch_builder.build_adaptive_repair_prompt = original
        
        n = len(problems)
        p1_pct = round(pass1 / n * 100, 1)
        p3_pct = round(pass3 / n * 100, 1)
        imp = round((p3_pct - p1_pct) / p1_pct * 100, 1) if p1_pct > 0 else 0
        
        results[name] = {
            "pass_at_1": p1_pct,
            "pass_at_3": p3_pct,
            "improvement": imp
        }
        console.print(f"  Pass@1: {p1_pct}%, Pass@3: {p3_pct}%, Improvement: {imp}%\n")
    
    # summary table
    table = Table(title="Ablation Results: Prompt Strategies")
    table.add_column("Strategy")
    table.add_column("Pass@1")
    table.add_column("Pass@3")
    table.add_column("Improvement")
    
    for name, data in results.items():
        table.add_row(
            name,
            f"{data['pass_at_1']}%",
            f"{data['pass_at_3']}%",
            f"{data['improvement']}%"
        )
    
    console.print(table)
    
    # save
    Path("runs").mkdir(exist_ok=True)
    with open("runs/ablation_results.json", "w") as f:
        json.dump(results, f, indent=2)
    console.print("\n[green]Saved to runs/ablation_results.json[/green]")
    
    return results


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=15)
    args = parser.parse_args()
    run_ablation(limit=args.limit)
