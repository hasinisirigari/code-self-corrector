"""
Main loop - generate, test, fix, repeat.
"""

import time
from typing import Optional, List
from pydantic import BaseModel

from ..llm.ollama_client import OllamaClient
from ..llm.prompts import build_generation_prompt
from ..sandbox.docker_runner import DockerSandbox
from ..sandbox.guardrails import check_code_safety, check_test_integrity
from .error_parser import parse_pytest_output, ErrorInfo
from .patch_builder import build_adaptive_repair_prompt


class Attempt(BaseModel):
    number: int
    code: str
    status: str
    error: Optional[ErrorInfo] = None
    gen_time: float = 0.0
    exec_time: float = 0.0


class SolutionResult(BaseModel):
    status: str
    attempts: List[Attempt]
    final_code: Optional[str] = None
    total_time: float = 0.0
    
    @property
    def solved(self):
        return self.status == "SUCCESS"


class Orchestrator:
    
    def __init__(self, llm=None, sandbox=None, max_attempts=3):
        self.llm = llm or OllamaClient()
        self.sandbox = sandbox or DockerSandbox()
        self.max_attempts = max_attempts
    
    def solve(self, problem_desc: str, tests: str) -> SolutionResult:
        t0 = time.time()
        attempts = []
        prev_code = None
        prev_err = None
        prev_sig = None
        
        for n in range(1, self.max_attempts + 1):
            # first attempt = generate, rest = repair
            if n == 1:
                prompt = build_generation_prompt(problem_desc)
            else:
                prompt = build_adaptive_repair_prompt(
                    prev_code, prev_err, problem_desc, tests
                )
            
            t1 = time.time()
            res = self.llm.generate(prompt)
            gen_time = time.time() - t1
            code = res.code
            
            # safety checks
            safe, violations = check_code_safety(code)
            if not safe:
                attempts.append(Attempt(number=n, code=code, status="UNSAFE", gen_time=gen_time))
                return SolutionResult(status="UNSAFE", attempts=attempts, total_time=time.time()-t0)
            
            valid, _ = check_test_integrity(tests, code)
            if not valid:
                attempts.append(Attempt(number=n, code=code, status="TAMPERED", gen_time=gen_time))
                return SolutionResult(status="TAMPERED", attempts=attempts, total_time=time.time()-t0)
            
            # run it
            exec_res = self.sandbox.run(code, tests)
            
            if exec_res.passed:
                attempts.append(Attempt(
                    number=n, code=code, status="SUCCESS",
                    gen_time=gen_time, exec_time=exec_res.execution_time
                ))
                return SolutionResult(
                    status="SUCCESS", attempts=attempts,
                    final_code=code, total_time=time.time()-t0
                )
            
            # failed - parse what went wrong
            err = parse_pytest_output(exec_res.stdout, exec_res.stderr, exec_res.timeout_occurred)
            
            # same error twice? give up
            if prev_sig and err.signature == prev_sig:
                attempts.append(Attempt(
                    number=n, code=code, status="FAIL", error=err,
                    gen_time=gen_time, exec_time=exec_res.execution_time
                ))
                return SolutionResult(status="REPEATED_FAILURE", attempts=attempts, total_time=time.time()-t0)
            
            attempts.append(Attempt(
                number=n, code=code, status="FAIL", error=err,
                gen_time=gen_time, exec_time=exec_res.execution_time
            ))
            
            prev_code = code
            prev_err = err
            prev_sig = err.signature
        
        return SolutionResult(status="MAX_ATTEMPTS", attempts=attempts, total_time=time.time()-t0)


if __name__ == "__main__":
    from rich.console import Console
    from rich.panel import Panel
    from rich.syntax import Syntax
    
    console = Console()
    console.print("\n[bold]Testing the orchestrator[/bold]\n")
    
    llm = OllamaClient()
    if not llm.is_available():
        console.print("[red]Ollama not running[/red]")
        exit(1)
    
    sandbox = DockerSandbox()
    if not sandbox.is_available():
        console.print("[red]Docker not running[/red]")
        exit(1)
    
    console.print("Ollama: [green]ok[/green]")
    console.print("Docker: [green]ok[/green]\n")
    
    # test with palindrome problem
    problem = '''def is_palindrome(s: str) -> bool:
    """Return True if s is a palindrome. Ignore case and non-alphanumeric chars."""
'''
    
    tests = '''
def test_simple():
    assert is_palindrome("racecar") == True

def test_spaces():
    assert is_palindrome("A man a plan a canal Panama") == True

def test_nope():
    assert is_palindrome("hello") == False

def test_empty():
    assert is_palindrome("") == True
'''
    
    console.print("[yellow]Running...[/yellow]\n")
    
    orch = Orchestrator(max_attempts=3)
    result = orch.solve(problem, tests)
    
    for att in result.attempts:
        color = "green" if att.status == "SUCCESS" else "red"
        console.print(f"Attempt {att.number}: [{color}]{att.status}[/{color}] ({att.gen_time:.1f}s gen, {att.exec_time:.1f}s exec)")
        if att.error:
            console.print(f"  -> {att.error.category.value}: {att.error.error_type}")
        console.print(Syntax(att.code, "python", line_numbers=True))
        console.print()
    
    console.print(f"[bold]Result: {result.status}[/bold] ({result.total_time:.1f}s total)")