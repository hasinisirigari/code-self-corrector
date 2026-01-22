"""
Docker Sandbox Runner - Executes code safely in isolated containers.
"""

import os
import uuid
import tempfile
import subprocess
from pathlib import Path
from typing import Optional
from pydantic import BaseModel


class ExecutionResult(BaseModel):
    """Result from executing code in the sandbox."""
    passed: bool
    exit_code: int
    stdout: str
    stderr: str
    execution_time: float
    timeout_occurred: bool = False


class DockerSandbox:
    """Executes Python code safely in Docker containers."""
    
    def __init__(
        self,
        image: str = "code-runner:latest",
        timeout: int = 15,
        memory_limit: str = "512m",
        cpu_limit: float = 1.0
    ):
        self.image = image
        self.timeout = timeout
        self.memory_limit = memory_limit
        self.cpu_limit = cpu_limit
    
    def run(self, code: str, tests: str) -> ExecutionResult:
        """
        Execute code with tests in a Docker container.
        
        Args:
            code: The Python code to test
            tests: The pytest test code
            
        Returns:
            ExecutionResult with pass/fail status and output
        """
        import time
        
        # Create temporary directory for code files
        # Use project directory for Windows Docker compatibility
        project_root = Path(__file__).parent.parent.parent
        temp_base = project_root / "temp"
        temp_base.mkdir(exist_ok=True)
        temp_dir = str(temp_base / f"code_exec_{uuid.uuid4().hex[:8]}")
        os.makedirs(temp_dir)
        
        try:
            # Write solution file
            solution_path = Path(temp_dir) / "solution.py"
            solution_path.write_text(code, encoding="utf-8")
            
            # Write test file that imports the solution
            test_content = f"""# Auto-generated test file
from solution import *

{tests}
"""
            test_path = Path(temp_dir) / "test_solution.py"
            test_path.write_text(test_content, encoding="utf-8")
            
            # Build docker command
            # Convert Windows path to Docker-compatible path
            docker_temp_dir = temp_dir.replace("\\", "/")
            
            cmd = [
                "docker", "run",
                "--rm",                              # Remove container after exit
                "--network=none",                    # No network access
                f"--memory={self.memory_limit}",    # Memory limit
                f"--cpus={self.cpu_limit}",         # CPU limit
                "--pids-limit=50",                   # Limit processes
                "-v", f"{docker_temp_dir}:/work:ro", # Mount code read-only
                "-w", "/work",                       # Set working directory
                self.image,
                "pytest", "-q", "test_solution.py", "-x"  # Run tests, stop on first failure
            ]
            
            # Execute
            start_time = time.time()
            
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout
                )
                execution_time = time.time() - start_time
                timeout_occurred = False
                
            except subprocess.TimeoutExpired:
                execution_time = self.timeout
                timeout_occurred = True
                
                # Kill the container if still running
                return ExecutionResult(
                    passed=False,
                    exit_code=-1,
                    stdout="",
                    stderr="Execution timed out",
                    execution_time=execution_time,
                    timeout_occurred=True
                )
            
            # Parse result
            passed = result.returncode == 0
            
            return ExecutionResult(
                passed=passed,
                exit_code=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                execution_time=execution_time,
                timeout_occurred=timeout_occurred
            )
            
        finally:
            # Cleanup temporary directory
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def is_available(self) -> bool:
        """Check if Docker is available and the image exists."""
        try:
            # Check if Docker is running
            result = subprocess.run(
                ["docker", "info"],
                capture_output=True,
                timeout=5
            )
            if result.returncode != 0:
                return False
            
            # Check if our image exists
            result = subprocess.run(
                ["docker", "images", "-q", self.image],
                capture_output=True,
                text=True,
                timeout=5
            )
            return len(result.stdout.strip()) > 0
            
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False


# Test when running directly
if __name__ == "__main__":
    from rich.console import Console
    from rich.panel import Panel
    
    console = Console()
    
    console.print("\n[bold blue]Testing Docker Sandbox[/bold blue]\n")
    
    sandbox = DockerSandbox()
    
    # Check availability
    console.print("Checking Docker availability...", end=" ")
    if sandbox.is_available():
        console.print("[green]✓ Available[/green]")
    else:
        console.print("[red]✗ Not available[/red]")
        console.print("[yellow]Make sure Docker is running and code-runner image is built[/yellow]")
        exit(1)
    
    # Test 1: Passing code
    console.print("\n[bold]Test 1: Code that should PASS[/bold]")
    
    passing_code = """
def add(a, b):
    return a + b
"""
    
    passing_tests = """
def test_add_positive():
    assert add(2, 3) == 5

def test_add_negative():
    assert add(-1, 1) == 0

def test_add_zero():
    assert add(0, 0) == 0
"""
    
    result = sandbox.run(passing_code, passing_tests)
    
    if result.passed:
        console.print("[green]✓ Tests passed as expected[/green]")
    else:
        console.print("[red]✗ Tests failed unexpectedly[/red]")
    
    console.print(f"[dim]Execution time: {result.execution_time:.2f}s[/dim]")
    
    # Test 2: Failing code
    console.print("\n[bold]Test 2: Code that should FAIL[/bold]")
    
    failing_code = """
def add(a, b):
    return a - b  # Bug: subtracting instead of adding
"""
    
    result = sandbox.run(failing_code, passing_tests)
    
    if not result.passed:
        console.print("[green]✓ Tests failed as expected[/green]")
    else:
        console.print("[red]✗ Tests passed unexpectedly[/red]")
    
    console.print(f"[dim]Exit code: {result.exit_code}[/dim]")
    console.print(Panel(result.stdout + result.stderr, title="Output", border_style="yellow"))
    
    # Test 3: Syntax error
    console.print("\n[bold]Test 3: Code with syntax error[/bold]")
    
    syntax_error_code = """
def add(a, b)
    return a + b
"""
    
    result = sandbox.run(syntax_error_code, passing_tests)
    
    combined_output = result.stdout + result.stderr
    if not result.passed and "SyntaxError" in combined_output:
        console.print("[green]✓ Syntax error detected as expected[/green]")
    else:
        console.print("[red]✗ Syntax error not detected[/red]")
    
    console.print(Panel(combined_output, title="Error Output", border_style="red"))
    
    console.print("\n[bold green]All sandbox tests completed![/bold green]")