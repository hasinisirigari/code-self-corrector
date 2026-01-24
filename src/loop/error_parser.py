"""
Error Parser - Analyzes pytest output and classifies errors.
"""

import re
from typing import List, Optional
from pydantic import BaseModel
from enum import Enum


class ErrorCategory(str, Enum):
    """Categories for classifying errors."""
    SYNTAX = "SYNTAX"           # SyntaxError, IndentationError
    NAME = "NAME"               # NameError, ImportError
    TYPE = "TYPE"               #TypeError, AttributeError
    LOGIC = "LOGIC"             # AssertionError (wrong output)
    RUNTIME = "RUNTIME"         # IndexError, KeyError, ZeroDivisionError, ValueError
    TIMEOUT = "TIMEOUT"         # Execution timeout
    OTHER = "OTHER"             # Unclassified errors


class ErrorInfo(BaseModel):
    """Structured information about an error."""
    category: ErrorCategory
    error_type: str                          # e.g., "SyntaxError", "AssertionError"
    message: str                             # The error message
    line_number: Optional[int] = None        # Line where error occurred
    failing_tests: List[str] = []            # Names of failing tests
    traceback: str = ""                      # Full traceback
    fixable_probability: float = 0.5         # Estimated probability of fixing
    expected_vs_actual: Optional[dict] = None # Expected vs actual values

    @property
    def signature(self) -> str:
        """Unique signature for detecting repeated errors."""
        return f"{self.category}:{self.error_type}:{self.line_number}"


# Mapping of Python exceptions to our categories
ERROR_CATEGORY_MAP = {
    # Syntax errors
    "SyntaxError": ErrorCategory.SYNTAX,
    "IndentationError": ErrorCategory.SYNTAX,
    "TabError": ErrorCategory.SYNTAX,
    
    # Name resolution errors
    "NameError": ErrorCategory.NAME,
    "ImportError": ErrorCategory.NAME,
    "ModuleNotFoundError": ErrorCategory.NAME,
    "UnboundLocalError": ErrorCategory.NAME,
    
    # Type errors
    "TypeError": ErrorCategory.TYPE,
    "AttributeError": ErrorCategory.TYPE,
    
    # Logic errors (test failures)
    "AssertionError": ErrorCategory.LOGIC,
    
    # Runtime errors
    "IndexError": ErrorCategory.RUNTIME,
    "KeyError": ErrorCategory.RUNTIME,
    "ValueError": ErrorCategory.RUNTIME,
    "ZeroDivisionError": ErrorCategory.RUNTIME,
    "RecursionError": ErrorCategory.RUNTIME,
    "MemoryError": ErrorCategory.RUNTIME,
    "OverflowError": ErrorCategory.RUNTIME,
    "StopIteration": ErrorCategory.RUNTIME,
}

# Fixability probabilities by category
FIXABILITY_RATES = {
    ErrorCategory.SYNTAX: 0.85,
    ErrorCategory.NAME: 0.75,
    ErrorCategory.TYPE: 0.65,
    ErrorCategory.LOGIC: 0.45,
    ErrorCategory.RUNTIME: 0.55,
    ErrorCategory.TIMEOUT: 0.20,
    ErrorCategory.OTHER: 0.40,
}


def parse_pytest_output(stdout: str, stderr: str, timeout_occurred: bool = False) -> ErrorInfo:
    """
    Parse pytest output and extract structured error information.
    
    Args:
        stdout: Standard output from pytest
        stderr: Standard error from pytest
        timeout_occurred: Whether execution timed out
        
    Returns:
        ErrorInfo with classified error details
    """
    combined = stdout + "\n" + stderr
    
    # Handle timeout
    if timeout_occurred:
        return ErrorInfo(
            category=ErrorCategory.TIMEOUT,
            error_type="Timeout",
            message="Execution timed out. Check for infinite loops or excessive recursion.",
            fixable_probability=FIXABILITY_RATES[ErrorCategory.TIMEOUT]
        )
    
    # Extract error type from traceback
    error_type = _extract_error_type(combined)
    category = ERROR_CATEGORY_MAP.get(error_type, ErrorCategory.OTHER)
    
    # Extract line number
    line_number = _extract_line_number(combined)
    
    # Extract error message
    message = _extract_error_message(combined, error_type)
    
    # Extract failing test names
    failing_tests = _extract_failing_tests(combined)
    
    # Get fixability probability
    fixable_probability = FIXABILITY_RATES.get(category, 0.4)
    
    return ErrorInfo(
        category=category,
        error_type=error_type,
        message=message,
        line_number=line_number,
        failing_tests=failing_tests,
        traceback=combined,
        fixable_probability=fixable_probability,
        expected_vs_actual=_get_expected_actual(combined)
    )


def _extract_error_type(output: str) -> str:
    """Extract the Python exception type from output."""
    # Pattern: "ErrorType: message" or "E   ErrorType: message"
    patterns = [
        r"E\s+(\w+Error):",
        r"E\s+(\w+Exception):",
        r"^(\w+Error):",
        r"^(\w+Exception):",
        r"(\w+Error): ",
        r"(\w+Exception): ",
    ]
    
    for pattern in patterns:
        match = re.search(pattern, output, re.MULTILINE)
        if match:
            return match.group(1)
    
    # Check for assertion failures specifically
    if "assert " in output.lower() and ("AssertionError" in output or "assert" in output):
        return "AssertionError"
    
    return "UnknownError"


def _extract_line_number(output: str) -> Optional[int]:
    """Extract the line number where error occurred."""
    # Pattern: "solution.py:123" or "line 123"
    patterns = [
        r"solution\.py[\"']?,\s*line\s*(\d+)",
        r"solution\.py:(\d+)",
        r"line\s+(\d+)",
        r"File.*line\s+(\d+)",
    ]
    
    for pattern in patterns:
        match = re.search(pattern, output, re.IGNORECASE)
        if match:
            return int(match.group(1))
    
    return None


def _extract_error_message(output: str, error_type: str) -> str:
    """Extract the error message."""
    # Try to find the line with the error type and message
    pattern = rf"{error_type}:\s*(.+)"
    match = re.search(pattern, output)
    if match:
        return match.group(1).strip()[:200]  # Limit length
    
    # For assertion errors, try to extract the assertion details
    if error_type == "AssertionError":
        # Look for "assert X == Y" patterns
        assert_pattern = r"assert\s+(.+)"
        match = re.search(assert_pattern, output)
        if match:
            return f"Assertion failed: {match.group(1)[:150]}"
        
        # Look for "E       assert" pytest format
        e_assert_pattern = r"E\s+assert\s+(.+)"
        match = re.search(e_assert_pattern, output)
        if match:
            return f"Assertion failed: {match.group(1)[:150]}"
    
    return "Unknown error occurred"


def _extract_failing_tests(output: str) -> List[str]:
    """Extract names of failing tests from pytest output."""
    failing_tests = []
    
    # Pattern: "FAILED test_solution.py::test_name"
    pattern = r"FAILED\s+\S+::(\w+)"
    matches = re.findall(pattern, output)
    failing_tests.extend(matches)
    
    # Pattern: "test_name FAILED" or "______ test_name ______"
    pattern2 = r"_{3,}\s*(\w+)\s*_{3,}"
    matches2 = re.findall(pattern2, output)
    for match in matches2:
        if match.startswith("test_") and match not in failing_tests:
            failing_tests.append(match)
    
    return failing_tests

def _get_expected_actual(output: str) -> Optional[dict]:
    result = {}
    
    m = re.search(r"assert\s+(.+?)\s*==\s*(.+?)(?:\n|$)", output)
    if m:
        result["actual"] = m.group(1).strip()[:100]
        result["expected"] = m.group(2).strip()[:100]
    
    m = re.search(r"where\s+.+?=\s*\w+\((.+?)\)", output)
    if m:
        result["input"] = m.group(1).strip()[:100]
    
    return result if result else None


def summarize_error(error_info: ErrorInfo) -> str:
    """
    Create a concise, actionable error summary for the repair prompt.
    
    Args:
        error_info: The parsed error information
        
    Returns:
        A clear, concise summary string
    """
    if error_info.category == ErrorCategory.SYNTAX:
        line_info = f" at line {error_info.line_number}" if error_info.line_number else ""
        return f"SyntaxError{line_info}: {error_info.message}. Check parentheses, colons, and indentation."
    
    elif error_info.category == ErrorCategory.NAME:
        return f"{error_info.error_type}: {error_info.message}. Check variable/function names and imports."
    
    elif error_info.category == ErrorCategory.TYPE:
        return f"{error_info.error_type}: {error_info.message}. Check data types and method calls."
    
    elif error_info.category == ErrorCategory.LOGIC:
        tests = ", ".join(error_info.failing_tests) if error_info.failing_tests else "unknown tests"
        return f"Logic error: Wrong output. Failing tests: {tests}. Review the algorithm logic."
    
    elif error_info.category == ErrorCategory.RUNTIME:
        line_info = f" at line {error_info.line_number}" if error_info.line_number else ""
        return f"{error_info.error_type}{line_info}: {error_info.message}. Check boundary conditions and edge cases."
    
    elif error_info.category == ErrorCategory.TIMEOUT:
        return "Timeout: Code took too long. Check for infinite loops, excessive recursion, or inefficient algorithms."
    
    else:
        return f"Error: {error_info.error_type} - {error_info.message}"


# Test when running directly
if __name__ == "__main__":
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    
    console = Console()
    
    console.print("\n[bold blue]Testing Error Parser[/bold blue]\n")
    
    # Test cases with sample pytest outputs
    test_cases = [
        ("Syntax Error", """
ERRORS
_______________________ ERROR collecting test_solution.py _______________________
E   File "/work/solution.py", line 2
E     def add(a, b)
E                ^
E   SyntaxError: expected ':'
""", False),
        
        ("Name Error", """
FAILED test_solution.py::test_add
E       NameError: name 'undefined_var' is not defined
""", False),
        
        ("Type Error", """
FAILED test_solution.py::test_process
E       TypeError: unsupported operand type(s) for +: 'int' and 'str'
test_solution.py:10: TypeError
""", False),
        
        ("Assertion Error (Logic)", """
FAILED test_solution.py::test_add_positive
    def test_add_positive():
>       assert add(2, 3) == 5
E       assert -1 == 5
E        +  where -1 = add(2, 3)

test_solution.py:6: AssertionError
FAILED test_solution.py::test_add_negative - assert 2 == 0
""", False),
        
        ("Index Error", """
FAILED test_solution.py::test_get_element
E       IndexError: list index out of range
test_solution.py:15: IndexError
""", False),
        
        ("Timeout", "", True),
    ]
    
    # Create results table
    table = Table(title="Error Parser Results")
    table.add_column("Test Case", style="cyan", width=20)
    table.add_column("Category", style="yellow")
    table.add_column("Error Type", style="red")
    table.add_column("Line", style="green")
    table.add_column("Failing Tests", style="magenta")
    
    for name, output, is_timeout in test_cases:
        error_info = parse_pytest_output(output, "", is_timeout)
        
        table.add_row(
            name,
            error_info.category.value,
            error_info.error_type,
            str(error_info.line_number) if error_info.line_number else "-",
            ", ".join(error_info.failing_tests) if error_info.failing_tests else "-"
        )
    
    console.print(table)
    
    # Show summarized errors
    console.print("\n[bold]Error Summaries (for repair prompts):[/bold]\n")
    
    for name, output, is_timeout in test_cases:
        error_info = parse_pytest_output(output, "", is_timeout)
        summary = summarize_error(error_info)
        console.print(f"[cyan]{name}:[/cyan]")
        console.print(f"  {summary}\n")
    
    console.print("[bold green]Error parser test completed![/bold green]")