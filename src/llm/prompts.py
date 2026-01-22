"""
Prompts for code gen and repair.
"""


GENERATION_PROMPT = """Write a Python function to solve this problem. Return ONLY the code.

{problem_description}

Rules:
- Complete the function
- No print statements
- No test code
- Just the function, nothing else
"""


def build_generation_prompt(problem_desc: str) -> str:
    return GENERATION_PROMPT.format(problem_description=problem_desc)