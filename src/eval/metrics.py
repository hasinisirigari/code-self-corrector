from collections import Counter
from typing import List, Dict
from ..loop.error_parser import ErrorCategory


def calculate_pass_at_k(results: List[dict], k: int) -> float:
    solved = sum(1 for r in results if r["solved"] and r["attempts"] <= k)
    return solved / len(results) if results else 0


def calculate_error_distribution(results: List[dict]) -> Dict[str, int]:
    errors = []
    for r in results:
        if "error_types" in r:
            errors.extend(r["error_types"])
    return dict(Counter(errors))


def calculate_fixability(results: List[dict]) -> Dict[str, dict]:
    # group by first error type
    by_error = {}
    
    for r in results:
        if not r.get("error_types") or r["attempts"] < 1:
            continue
        
        first_err = r["error_types"][0] if r["error_types"] else "UNKNOWN"
        
        if first_err not in by_error:
            by_error[first_err] = {"total": 0, "fixed_1": 0, "fixed_2": 0}
        
        by_error[first_err]["total"] += 1
        
        if r["solved"]:
            if r["attempts"] <= 2:
                by_error[first_err]["fixed_1"] += 1
            if r["attempts"] <= 3:
                by_error[first_err]["fixed_2"] += 1
    
    # calc rates
    for err, data in by_error.items():
        t = data["total"]
        data["fix_rate_1"] = round(data["fixed_1"] / t * 100, 1) if t > 0 else 0
        data["fix_rate_2"] = round(data["fixed_2"] / t * 100, 1) if t > 0 else 0
    
    return by_error


def summary_stats(results: List[dict]) -> dict:
    total = len(results)
    solved = sum(1 for r in results if r["solved"])
    
    times = [r["time"] for r in results]
    attempts = [r["attempts"] for r in results]
    
    return {
        "total": total,
        "solved": solved,
        "solve_rate": round(solved / total * 100, 1) if total > 0 else 0,
        "avg_time": round(sum(times) / total, 2) if total > 0 else 0,
        "avg_attempts": round(sum(attempts) / total, 2) if total > 0 else 0,
        "pass_at_1": round(calculate_pass_at_k(results, 1) * 100, 1),
        "pass_at_2": round(calculate_pass_at_k(results, 2) * 100, 1),
        "pass_at_3": round(calculate_pass_at_k(results, 3) * 100, 1),
    }


if __name__ == "__main__":
    # test with fake data
    fake_results = [
        {"solved": True, "attempts": 1, "time": 10, "error_types": []},
        {"solved": True, "attempts": 2, "time": 25, "error_types": ["LOGIC"]},
        {"solved": True, "attempts": 3, "time": 40, "error_types": ["SYNTAX", "LOGIC"]},
        {"solved": False, "attempts": 3, "time": 50, "error_types": ["LOGIC", "LOGIC", "LOGIC"]},
        {"solved": False, "attempts": 3, "time": 45, "error_types": ["TIMEOUT"]},
    ]
    
    print("Summary:", summary_stats(fake_results))
    print("Error dist:", calculate_error_distribution(fake_results))
    print("Fixability:", calculate_fixability(fake_results))
