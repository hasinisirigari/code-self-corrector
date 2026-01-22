"""
Patch Builder - Constructs repair prompts from error information.
"""

from typing import Optional
from .error_parser import ErrorInfo, ErrorCategory, summarize_error


def build_repair_prompt(
    code: str,
    error_info: ErrorInfo,
    problem_description: str = "",
    include_tests: bool = True
) -> str:
    """
    Build a repair prompt based on the error information.
    
    Args:
        code: The code that failed
        error_info: Parsed error information
        problem_description: Original problem description (optional)
        include_tests: Whether to include failing test names
        
    Returns:
        A prompt string for the LLM to fix the code
    """
    # Get summarized error message
    error_summary = summarize_error(error_info)
    
    # Build failing tests section
    tests_section = ""
    if include_tests and error_info.failing_tests:
        tests_section = f"\nFailing tests: {', '.join(error_info.failing_tests)}"
    
    # Build the prompt
    prompt = f"""The following Python code failed. Fix the code based on the error.

Previous code:
```python
{code.strip()}
```

Error: {error_summary}{tests_section}

Instructions:
- Fix ONLY the code logic
- Keep the function signature unchanged
- Do NOT add test functions
- Return ONLY the corrected code with no explanation
"""
    
    return prompt


def build_repair_prompt_with_context(
    code: str,
    error_info: ErrorInfo,
    problem_description: str,
    test_code: str = ""
) -> str:
    """
    Build a more detailed repair prompt with problem context.
    Used for logic errors where understanding the problem helps.
    
    Args:
        code: The code that failed
        error_info: Parsed error information
        problem_description: Original problem description
        test_code: The test code (to show expected behavior)
        
    Returns:
        A detailed prompt string
    """
    error_summary = summarize_error(error_info)
    
    # Extract relevant test assertions if available
    test_hints = ""
    if test_code and error_info.category == ErrorCategory.LOGIC:
        test_hints = _extract_test_hints(test_code, error_info.failing_tests)
    
    prompt = f"""The following Python code failed tests. Fix it to match the expected behavior.

Problem description:
{problem_description.strip()}

Previous code:
```python
{code.strip()}
```

Error: {error_summary}
{test_hints}
Instructions:
- Fix the code to pass all tests
- Keep the function signature unchanged
- Do NOT modify or add test functions
- Return ONLY the corrected code with no explanation
"""
    
    return prompt


def build_syntax_repair_prompt(code: str, error_info: ErrorInfo) -> str:
    """
    Build a specialized prompt for syntax errors.
    These are usually simple fixes.
    """
    line_info = ""
    if error_info.line_number:
        lines = code.split('\n')
        if 0 < error_info.line_number <= len(lines):
            problematic_line = lines[error_info.line_number - 1]
            line_info = f"\nProblematic line {error_info.line_number}: `{problematic_line.strip()}`"
    
    prompt = f"""Fix the syntax error in this Python code.

Code:
```python
{code.strip()}
```

Error: {error_info.message}{line_info}

Return ONLY the corrected code with no explanation.
"""
    
    return prompt


def build_type_repair_prompt(code: str, error_info: ErrorInfo) -> str:
    """
    Build a specialized prompt for type errors.
    """
    prompt = f"""Fix the type error in this Python code.

Code:
```python
{code.strip()}
```

Error: {error_info.error_type}: {error_info.message}

Common fixes for type errors:
- Check if you're using the right data type
- Ensure method calls are valid for the object type
- Convert types if necessary (int(), str(), list(), etc.)

Return ONLY the corrected code with no explanation.
"""
    
    return prompt


def build_adaptive_repair_prompt(
    code: str,
    error_info: ErrorInfo,
    problem_description: str = "",
    test_code: str = ""
) -> str:
    """
    Build a repair prompt adapted to the error category.
    This is the main entry point for building repair prompts.
    
    Args:
        code: The code that failed
        error_info: Parsed error information
        problem_description: Original problem description
        test_code: The test code
        
    Returns:
        An appropriate repair prompt based on error type
    """
    # Use specialized prompts for certain error types
    if error_info.category == ErrorCategory.SYNTAX:
        return build_syntax_repair_prompt(code, error_info)
    
    elif error_info.category == ErrorCategory.TYPE:
        return build_type_repair_prompt(code, error_info)
    
    elif error_info.category == ErrorCategory.LOGIC:
        # Logic errors benefit from more context
        return build_repair_prompt_with_context(
            code, error_info, problem_description, test_code
        )
    
    else:
        # Default repair prompt for other errors
        return build_repair_prompt(code, error_info, problem_description)


def _extract_test_hints(test_code: str, failing_tests: list) -> str:
    """
    Extract relevant assertions from test code to help with repairs.
    """
    if not failing_tests:
        return ""
    
    hints = []
    lines = test_code.split('\n')
    
    for test_name in failing_tests[:3]:  # Limit to first 3 tests
        in_test = False
        for line in lines:
            if f"def {test_name}" in line:
                in_test = True
                continue
            if in_test:
                if line.strip().startswith("def "):
                    break
                if "assert" in line:
                    hints.append(line.strip())
    
    if hints:
        return "\nExpected behavior from tests:\n" + "\n".join(f"  {h}" for h in hints[:5])
    
    return ""


# Test when running directly
if __name__ == "__main__":
    from rich.console import Console
    from rich.panel import Panel
    from .error_parser import parse_pytest_output
    
    console = Console()
    
    console.print("\n[bold blue]Testing Patch Builder[/bold blue]\n")
    
    # Sample code that failed
    failed_code = """
def add(a, b):
    return a - b  # Bug: should be +
"""
    
    # Sample error output
    error_output = """
FAILED test_solution.py::test_add_positive
    def test_add_positive():
>       assert add(2, 3) == 5
E       assert -1 == 5
E        +  where -1 = add(2, 3)
FAILED test_solution.py::test_add_zero - assert 0 == 0
"""
    
    # Parse the error
    error_info = parse_pytest_output(error_output, "", False)
    
    # Build different types of prompts
    console.print("[bold]1. Basic Repair Prompt:[/bold]")
    basic_prompt = build_repair_prompt(failed_code, error_info)
    console.print(Panel(basic_prompt, border_style="yellow"))
    
    console.print("\n[bold]2. Adaptive Repair Prompt (for LOGIC error):[/bold]")
    problem_desc = "def add(a, b):\n    '''Return the sum of a and b.'''"
    test_code = """
def test_add_positive():
    assert add(2, 3) == 5

def test_add_zero():
    assert add(0, 0) == 0
"""
    adaptive_prompt = build_adaptive_repair_prompt(
        failed_code, error_info, problem_desc, test_code
    )
    console.print(Panel(adaptive_prompt, border_style="green"))
    
    # Test syntax error prompt
    console.print("\n[bold]3. Syntax Error Prompt:[/bold]")
    syntax_error = parse_pytest_output(
        "SyntaxError: expected ':'", 
        "File 'solution.py', line 2\n  def add(a, b)\n             ^", 
        False
    )
    syntax_code = """
def add(a, b)
    return a + b
"""
    syntax_prompt = build_syntax_repair_prompt(syntax_code, syntax_error)
    console.print(Panel(syntax_prompt, border_style="red"))
    
    console.print("\n[bold green]Patch builder test completed![/bold green]")