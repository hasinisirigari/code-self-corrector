import time
import json
from pathlib import Path
from typing import List, Optional
from dataclasses import asdict

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table

from .benchmarks import Problem, load_humaneval, load_mbpp, load_all
from ..loop.orchestrator import Orchestrator, SolutionResult


console = Console()


def run_evaluation(
    problems: List[Problem],
    max_attempts: int = 3,
    save_path: Optional[str] = None
) -> dict:
    
    orch = Orchestrator(max_attempts=max_attempts)
    results = []
    
    pass_at_1 = 0
    pass_at_2 = 0
    pass_at_3 = 0
    total_time = 0
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console
    ) as progress:
        
        task = progress.add_task("Running evaluation...", total=len(problems))
        
        for p in problems:
            progress.update(task, description=f"[cyan]{p.task_id}[/cyan]")
            
            t0 = time.time()
            result = orch.solve(p.prompt, p.tests)
            elapsed = time.time() - t0
            total_time += elapsed
            
            # track pass@k
            if result.solved:
                n = len(result.attempts)
                if n <= 1:
                    pass_at_1 += 1
                if n <= 2:
                    pass_at_2 += 1
                if n <= 3:
                    pass_at_3 += 1
            

            error_types = []
            for att in result.attempts:
                if att.error:
                    error_types.append(att.error.category.value)
                
            results.append({
                "task_id": p.task_id,
                "source": p.source,
                "status": result.status,
                "attempts": len(result.attempts),
                "time": elapsed,
                "solved": result.solved,
                "error_types": error_types
            })
            
            progress.advance(task)
    
    n = len(problems)
    metrics = {
        "total": n,
        "pass_at_1": pass_at_1,
        "pass_at_2": pass_at_2,
        "pass_at_3": pass_at_3,
        "pass_at_1_pct": round(pass_at_1 / n * 100, 1),
        "pass_at_2_pct": round(pass_at_2 / n * 100, 1),
        "pass_at_3_pct": round(pass_at_3 / n * 100, 1),
        "total_time": round(total_time, 1),
        "avg_time": round(total_time / n, 1)
    }
    
    output = {"metrics": metrics, "results": results}
    
    if save_path:
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        with open(save_path, "w") as f:
            json.dump(output, f, indent=2)
        console.print(f"\n[green]Results saved to {save_path}[/green]")
    
    return output


def print_summary(data: dict):
    m = data["metrics"]
    
    table = Table(title="Evaluation Results")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Total problems", str(m["total"]))
    table.add_row("Pass@1", f"{m['pass_at_1']} ({m['pass_at_1_pct']}%)")
    table.add_row("Pass@2", f"{m['pass_at_2']} ({m['pass_at_2_pct']}%)")
    table.add_row("Pass@3", f"{m['pass_at_3']} ({m['pass_at_3_pct']}%)")
    table.add_row("Total time", f"{m['total_time']}s")
    table.add_row("Avg time/problem", f"{m['avg_time']}s")
    
    console.print(table)
    
    # improvement calc
    if m["pass_at_1"] > 0:
        improvement = ((m["pass_at_3"] - m["pass_at_1"]) / m["pass_at_1"]) * 100
        console.print(f"\n[bold]Improvement from self-correction: {improvement:.1f}%[/bold]")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Run code generation evaluation")
    parser.add_argument("--dataset", choices=["humaneval", "mbpp", "all"], default="humaneval")
    parser.add_argument("--limit", type=int, default=None, help="limit problems to run")
    parser.add_argument("--attempts", type=int, default=3)
    parser.add_argument("--output", type=str, default=None, help="save results to json")
    
    args = parser.parse_args()
    
    console.print(f"\n[bold]Loading {args.dataset}...[/bold]")
    
    if args.dataset == "humaneval":
        problems = load_humaneval(args.limit)
    elif args.dataset == "mbpp":
        problems = load_mbpp(args.limit)
    else:
        problems = load_all(args.limit)
    
    console.print(f"Loaded {len(problems)} problems\n")
    
    data = run_evaluation(problems, args.attempts, args.output)
    print_summary(data)