# loading HumanEval and MBPP datasets
from dataclasses import dataclass
from typing import List, Optional
from datasets import load_dataset


@dataclass
class Problem:
    task_id: str
    prompt: str          
    tests: str           
    entry_point: str     
    source: str          


def load_humaneval(limit: Optional[int] = None) -> List[Problem]:
    ds = load_dataset("openai_humaneval", split="test")
    
    problems = []
    for i, item in enumerate(ds):
        if limit and i >= limit:
            break
        
        # build pytest tests from the canonical solution test
        test_code = _convert_humaneval_tests(item["test"], item["entry_point"])
        
        problems.append(Problem(
            task_id=item["task_id"],
            prompt=item["prompt"],
            tests=test_code,
            entry_point=item["entry_point"],
            source="humaneval"
        ))
    
    return problems


def load_mbpp(limit: Optional[int] = None) -> List[Problem]:
    ds = load_dataset("mbpp", "sanitized", split="test")
    
    problems = []
    for i, item in enumerate(ds):
        if limit and i >= limit:
            break
        
        # mbpp has test_list with assert statements
        test_code = _convert_mbpp_tests(item["test_list"], item["task_id"])
        
        problems.append(Problem(
            task_id=f"MBPP/{item['task_id']}",
            prompt=item["prompt"] + "\n\n" + item["code"].split("def ")[0] if "def " in item["code"] else item["prompt"],
            tests=test_code,
            entry_point=_extract_function_name(item["code"]),
            source="mbpp"
        ))
    
    return problems


def load_all(limit_each: Optional[int] = None) -> List[Problem]:
    # combining both datasets
    he = load_humaneval(limit_each)
    mb = load_mbpp(limit_each)
    return he + mb


def _convert_humaneval_tests(test_code: str, entry_point: str) -> str:
    lines = test_code.strip().split('\n')
    
    result = []
    for line in lines:
        if 'assert' in line.lower():
            fixed = line.replace('candidate', entry_point)
            result.append(fixed)
    
    if not result:
        return f"def test_main():\n    {test_code}"
    
    out = "def test_main():\n"
    for line in result:
        stripped = line.strip()
        out += f"    {stripped}\n"
    
    return out


def _convert_mbpp_tests(test_list: List[str], task_id: int) -> str:
    # MBPP gives us a list of assert statements
    out = f"def test_mbpp_{task_id}():\n"
    for test in test_list:
        out += f"    {test.strip()}\n"
    return out


def _extract_function_name(code: str) -> str:
    import re
    match = re.search(r'def\s+(\w+)\s*\(', code)
    if match:
        return match.group(1)
    return "solution"


# quick test
if __name__ == "__main__":
    from rich.console import Console
    from rich.table import Table
    
    console = Console()
    console.print("\n[bold]Loading datasets...[/bold]\n")
    
    # loading just a few to test
    console.print("Loading HumanEval (first 3)...")
    he = load_humaneval(limit=3)
    console.print(f"Got {len(he)} problems\n")
    
    console.print("Loading MBPP (first 3)...")
    mb = load_mbpp(limit=3)
    console.print(f"Got {len(mb)} problems\n")
    
    # showing sample problems
    table = Table(title="Sample Problems")
    table.add_column("ID", style="cyan")
    table.add_column("Source")
    table.add_column("Entry Point", style="green")
    table.add_column("Prompt (truncated)")
    
    for p in he + mb:
        table.add_row(
            p.task_id,
            p.source,
            p.entry_point,
            p.prompt[:50] + "..."
        )
    
    console.print(table)
    
    # showing one problem in detail
    console.print("\n[bold]Sample HumanEval problem:[/bold]")
    console.print(f"[cyan]Prompt:[/cyan]\n{he[0].prompt}")
    console.print(f"\n[cyan]Tests:[/cyan]\n{he[0].tests}")