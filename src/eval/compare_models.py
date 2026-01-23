import json
import time
from pathlib import Path
from rich.console import Console
from rich.table import Table

from .benchmarks import load_humaneval
from ..loop.orchestrator import Orchestrator
from ..llm.ollama_client import OllamaClient
from ..llm.groq_client import GroqClient
from ..sandbox.docker_runner import DockerSandbox

console = Console()


def run_comparison(limit: int = 20, output_dir: str = "runs"):
    console.print("\n[bold]Model Comparison: Ollama vs Groq[/bold]\n")
    
    problems = load_humaneval(limit=limit)
    console.print(f"Loaded {len(problems)} problems\n")
    
    sandbox = DockerSandbox()
    
    results = {"ollama": [], "groq": []}
    
    # run ollama
    console.print("[cyan]Running Ollama (codellama:7b)...[/cyan]")
    ollama = OllamaClient()
    orch_ollama = Orchestrator(llm=ollama, sandbox=sandbox, max_attempts=3)
    
    for p in problems:
        t0 = time.time()
        r = orch_ollama.solve(p.prompt, p.tests)
        elapsed = time.time() - t0
        
        results["ollama"].append({
            "task_id": p.task_id,
            "solved": r.solved,
            "attempts": len(r.attempts),
            "time": elapsed
        })
        status = "✓" if r.solved else "✗"
        console.print(f"  {p.task_id}: {status} ({len(r.attempts)} attempts)")
    
    # run groq
    console.print("\n[cyan]Running Groq (llama-3.3-70b)...[/cyan]")
    groq = GroqClient()
    orch_groq = Orchestrator(llm=groq, sandbox=sandbox, max_attempts=3)
    
    for p in problems:
        t0 = time.time()
        r = orch_groq.solve(p.prompt, p.tests)
        elapsed = time.time() - t0
        
        results["groq"].append({
            "task_id": p.task_id,
            "solved": r.solved,
            "attempts": len(r.attempts),
            "time": elapsed
        })
        status = "✓" if r.solved else "✗"
        console.print(f"  {p.task_id}: {status} ({len(r.attempts)} attempts)")
        
        time.sleep(2)  # rate limit
    
    # calc stats
    def calc_stats(data):
        n = len(data)
        solved = sum(1 for d in data if d["solved"])
        pass1 = sum(1 for d in data if d["solved"] and d["attempts"] == 1)
        return {
            "total": n,
            "solved": solved,
            "pass_at_1": round(pass1 / n * 100, 1),
            "pass_at_3": round(solved / n * 100, 1),
            "avg_time": round(sum(d["time"] for d in data) / n, 1)
        }
    
    ollama_stats = calc_stats(results["ollama"])
    groq_stats = calc_stats(results["groq"])
    
    # print comparison
    console.print("\n")
    table = Table(title="Model Comparison Results")
    table.add_column("Metric")
    table.add_column("Ollama (7B)", style="cyan")
    table.add_column("Groq (70B)", style="green")
    
    table.add_row("Pass@1", f"{ollama_stats['pass_at_1']}%", f"{groq_stats['pass_at_1']}%")
    table.add_row("Pass@3", f"{ollama_stats['pass_at_3']}%", f"{groq_stats['pass_at_3']}%")
    table.add_row("Avg Time", f"{ollama_stats['avg_time']}s", f"{groq_stats['avg_time']}s")
    
    o_imp = round((ollama_stats['pass_at_3'] - ollama_stats['pass_at_1']) / ollama_stats['pass_at_1'] * 100, 1) if ollama_stats['pass_at_1'] > 0 else 0
    g_imp = round((groq_stats['pass_at_3'] - groq_stats['pass_at_1']) / groq_stats['pass_at_1'] * 100, 1) if groq_stats['pass_at_1'] > 0 else 0
    table.add_row("Improvement", f"{o_imp}%", f"{g_imp}%")
    
    console.print(table)
    
    # save
    Path(output_dir).mkdir(exist_ok=True)
    out_path = f"{output_dir}/model_comparison.json"
    with open(out_path, "w") as f:
        json.dump({"ollama": ollama_stats, "groq": groq_stats, "results": results}, f, indent=2)
    console.print(f"\n[green]Saved to {out_path}[/green]")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()
    run_comparison(limit=args.limit)