import json
from pathlib import Path
from rich.console import Console
from rich.table import Table
from .metrics import summary_stats, calculate_error_distribution, calculate_fixability


console = Console()


def generate_report(results_path: str, output_dir: str = "reports"):
    with open(results_path) as f:
        data = json.load(f)
    
    results = data["results"]
    
    Path(output_dir).mkdir(exist_ok=True)
    
    stats = summary_stats(results)
    errors = calculate_error_distribution(results)
    fixability = calculate_fixability(results)
    
    # print to console
    console.print("\n[bold]== Evaluation Report ==[/bold]\n")
    
    # summary table
    t1 = Table(title="Summary")
    t1.add_column("Metric")
    t1.add_column("Value")
    for k, v in stats.items():
        t1.add_row(k, str(v))
    console.print(t1)
    
    # error distribution
    if errors:
        console.print("\n")
        t2 = Table(title="Error Distribution")
        t2.add_column("Error Type")
        t2.add_column("Count")
        for err, count in sorted(errors.items(), key=lambda x: -x[1]):
            t2.add_row(err, str(count))
        console.print(t2)
    
    # fixability
    if fixability:
        console.print("\n")
        t3 = Table(title="Fixability by Error Type")
        t3.add_column("Error Type")
        t3.add_column("Total")
        t3.add_column("Fixed (1 retry)")
        t3.add_column("Fixed (2 retries)")
        for err, d in fixability.items():
            t3.add_row(err, str(d["total"]), f"{d['fix_rate_1']}%", f"{d['fix_rate_2']}%")
        console.print(t3)
    
    # save markdown report
    md_path = Path(output_dir) / "report.md"
    with open(md_path, "w") as f:
        f.write("# Evaluation Report\n\n")
        f.write("## Summary\n\n")
        f.write(f"- Total problems: {stats['total']}\n")
        f.write(f"- Solved: {stats['solved']} ({stats['solve_rate']}%)\n")
        f.write(f"- Pass@1: {stats['pass_at_1']}%\n")
        f.write(f"- Pass@2: {stats['pass_at_2']}%\n")
        f.write(f"- Pass@3: {stats['pass_at_3']}%\n")
        f.write(f"- Avg time: {stats['avg_time']}s\n\n")
        
        if stats['pass_at_1'] > 0:
            imp = ((stats['pass_at_3'] - stats['pass_at_1']) / stats['pass_at_1']) * 100
            f.write(f"**Improvement from self-correction: {imp:.1f}%**\n\n")
        
        if errors:
            f.write("## Error Distribution\n\n")
            f.write("| Error Type | Count |\n")
            f.write("|------------|-------|\n")
            for err, count in sorted(errors.items(), key=lambda x: -x[1]):
                f.write(f"| {err} | {count} |\n")
            f.write("\n")
        
        if fixability:
            f.write("## Fixability Analysis\n\n")
            f.write("| Error Type | Total | Fixed (1 retry) | Fixed (2 retries) |\n")
            f.write("|------------|-------|-----------------|-------------------|\n")
            for err, d in fixability.items():
                f.write(f"| {err} | {d['total']} | {d['fix_rate_1']}% | {d['fix_rate_2']}% |\n")
    
    console.print(f"\n[green]Report saved to {md_path}[/green]")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        generate_report(sys.argv[1])
    else:
        print("Usage: py -m src.eval.reports <results.json>")