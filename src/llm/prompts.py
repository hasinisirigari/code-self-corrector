"""
Prompt templates for code generation and repair.
"""


GENERATION_PROMPT = """Complete the following Python function. Return only the code, no explanations.

{problem_description}

Constraints:
- Keep the exact function signature
- No print statements or debug output
- Deterministic output only
- Use efficient algorithms
- Return ONLY the code, nothing else
"""


REPAIR_PROMPT = """The following code failed tests. Fix the function based on the error.

Previous code:
```python
{code}
```

Error: {error_type} at line {line_number}
{error_message}

Failing tests:
{failing_tests}

Instructions:
- Fix ONLY the function logic
- Keep the function signature unchanged
- Do NOT modify the test cases
- Return ONLY the corrected code with no explanation
"""


REPAIR_PROMPT_WITH_TESTS = """The following code failed tests. Fix the function based on the error.

Previous code:
```python
{code}
```

Error: {error_type}
{error_message}

The following test assertions failed:
{test_assertions}

Instructions:
- Fix ONLY the function logic to pass all tests
- Keep the function signature unchanged
- Return ONLY the corrected code with no explanation
"""


def build_generation_prompt(problem_description: str) -> str:
    """Build a prompt for initial code generation."""
    return GENERATION_PROMPT.format(problem_description=problem_description)


def build_repair_prompt(
    code: str,
    error_type: str,
    error_message: str,
    line_number: int = None,
    failing_tests: str = ""
) -> str:
    """Build a prompt for code repair."""
    line_info = line_number if line_number else "unknown"
    
    return REPAIR_PROMPT.format(
        code=code,
        error_type=error_type,
        line_number=line_info,
        error_message=error_message,
        failing_tests=failing_tests
    )


def build_repair_prompt_with_assertions(
    code: str,
    error_type: str,
    error_message: str,
    test_assertions: str
) -> str:
    """Build a repair prompt that includes the actual test assertions."""
    return REPAIR_PROMPT_WITH_TESTS.format(
        code=code,
        error_type=error_type,
        error_message=error_message,
        test_assertions=test_assertions
    )


# Test the prompts
if __name__ == "__main__":
    from rich.console import Console
    from rich.panel import Panel
    
    console = Console()
    
    # Test generation prompt
    problem = """def is_palindrome(s: str) -> bool:
    \"\"\"Check if a string is a palindrome.\"\"\"
"""
    
    gen_prompt = build_generation_prompt(problem)
    console.print(Panel(gen_prompt, title="Generation Prompt", border_style="blue"))
    
    # Test repair prompt
    repair = build_repair_prompt(
        code="def is_palindrome(s):\n    return s == s.reverse()",
        error_type="AttributeError",
        error_message="'str' object has no attribute 'reverse'",
        line_number=2,
        failing_tests="test_palindrome_basic, test_palindrome_empty"
    )
    console.print(Panel(repair, title="Repair Prompt", border_style="yellow"))