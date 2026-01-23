"""
Builds repair prompts from errors.
"""

from .error_parser import ErrorInfo, ErrorCategory


def build_adaptive_repair_prompt(code: str, error: ErrorInfo, problem_desc: str = "", tests: str = "") -> str:
    """Pick the right repair strategy based on error type."""
    
    if error.category == ErrorCategory.SYNTAX:
        return _syntax_prompt(code, error)
    elif error.category == ErrorCategory.LOGIC:
        return _logic_prompt(code, error, tests)
    else:
        return _generic_prompt(code, error)


def _syntax_prompt(code: str, error: ErrorInfo) -> str:
    return f"""This code has a syntax error. Fix it.
```python
{code}
```

Error: {error.message}
Line: {error.line_number or 'unknown'}

Return ONLY the fixed code, no explanation."""


def _logic_prompt(code: str, error: ErrorInfo, tests: str) -> str:
    test_hints = ""
    if tests:
        lines = [l.strip() for l in tests.split('\n') if 'assert' in l]
        if lines:
            test_hints = "\n\nThese are the expected behaviors:\n" + "\n".join(lines[:5])
    
    failing = ", ".join(error.failing_tests) if error.failing_tests else "unknown"
    
    return f"""This code returns wrong output. The logic is incorrect.
```python
{code}
```

Failing tests: {failing}
{test_hints}

The assertions show what the function SHOULD return. Study them carefully.
Fix the logic to match the expected output.
Return ONLY the fixed code, no explanation."""


def _generic_prompt(code: str, error: ErrorInfo) -> str:
    return f"""This code has an error. Fix it.
```python
{code}
```

Error type: {error.error_type}
Message: {error.message}

Return ONLY the fixed code, no explanation."""


# test it
if __name__ == "__main__":
    from .error_parser import parse_pytest_output
    
    err = parse_pytest_output("FAILED test_x - assert 1 == 2", "", False)
    code = "def foo():\n    return 1"
    tests = "def test_x():\n    assert foo() == 2"
    
    print(_logic_prompt(code, err, tests))