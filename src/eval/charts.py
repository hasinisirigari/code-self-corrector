import json
from pathlib import Path
import matplotlib.pyplot as plt
from .metrics import summary_stats, calculate_error_distribution, calculate_fixability


def generate_all_charts(results_path: str, output_dir: str = "reports"):
    with open(results_path) as f:
        data = json.load(f)
    
    results = data["results"]
    Path(output_dir).mkdir(exist_ok=True)
    
    stats = summary_stats(results)
    errors = calculate_error_distribution(results)
    fixability = calculate_fixability(results)
    
    _chart_pass_at_k(stats, output_dir)
    if errors:
        _chart_error_distribution(errors, output_dir)
    if fixability:
        _chart_fixability(fixability, output_dir)
    
    print(f"Charts saved to {output_dir}/")


def _chart_pass_at_k(stats: dict, output_dir: str):
    fig, ax = plt.subplots(figsize=(8, 5))
    
    labels = ["Pass@1", "Pass@2", "Pass@3"]
    values = [stats["pass_at_1"], stats["pass_at_2"], stats["pass_at_3"]]
    colors = ["#ff6b6b", "#feca57", "#48dbfb"]
    
    bars = ax.bar(labels, values, color=colors, edgecolor="black")
    
    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                f"{val}%", ha="center", fontsize=12, fontweight="bold")
    
    ax.set_ylabel("Success Rate (%)")
    ax.set_title("Pass@k Performance")
    ax.set_ylim(0, 100)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    
    plt.tight_layout()
    plt.savefig(f"{output_dir}/pass_rate_comparison.png", dpi=150)
    plt.close()


def _chart_error_distribution(errors: dict, output_dir: str):
    fig, ax = plt.subplots(figsize=(8, 6))
    
    labels = list(errors.keys())
    sizes = list(errors.values())
    colors = ["#ff6b6b", "#feca57", "#48dbfb", "#ff9ff3", "#54a0ff", "#5f27cd"]
    
    wedges, texts, autotexts = ax.pie(
        sizes, labels=labels, autopct="%1.0f%%",
        colors=colors[:len(labels)], startangle=90
    )
    
    for autotext in autotexts:
        autotext.set_fontsize(10)
        autotext.set_fontweight("bold")
    
    ax.set_title("Error Type Distribution")
    
    plt.tight_layout()
    plt.savefig(f"{output_dir}/error_taxonomy.png", dpi=150)
    plt.close()


def _chart_fixability(fixability: dict, output_dir: str):
    fig, ax = plt.subplots(figsize=(10, 6))
    
    errors = list(fixability.keys())
    fix_1 = [fixability[e]["fix_rate_1"] for e in errors]
    fix_2 = [fixability[e]["fix_rate_2"] for e in errors]
    
    x = range(len(errors))
    width = 0.35
    
    bars1 = ax.bar([i - width/2 for i in x], fix_1, width, label="1 retry", color="#48dbfb")
    bars2 = ax.bar([i + width/2 for i in x], fix_2, width, label="2 retries", color="#ff6b6b")
    
    ax.set_ylabel("Fix Rate (%)")
    ax.set_title("Error Fixability by Type")
    ax.set_xticks(x)
    ax.set_xticklabels(errors)
    ax.legend()
    ax.set_ylim(0, 100)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    
    plt.tight_layout()
    plt.savefig(f"{output_dir}/error_fixability.png", dpi=150)
    plt.close()


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        generate_all_charts(sys.argv[1])
    else:
        print("Usage: py -m src.eval.charts <results.json>")
