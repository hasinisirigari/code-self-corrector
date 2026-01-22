# Ollama Client - Communicates with local Ollama server to generate code.

import requests
import re
from typing import Optional
from pydantic import BaseModel


class GenerationResult(BaseModel):
    # Result from a code generation request.
    code: str
    raw_response: str
    generation_time: float
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None


class OllamaClient:
    # Client for interacting with Ollama API.
    
    def __init__(
        self, 
        model: str = "codellama:7b",
        base_url: str = "http://localhost:11434",
        temperature: float = 0.2,
        top_p: float = 0.9,
        max_tokens: int = 512
    ):
        self.model = model
        self.base_url = base_url
        self.temperature = temperature
        self.top_p = top_p
        self.max_tokens = max_tokens
    
    def generate(self, prompt: str) -> GenerationResult:
        """
        Generate code from a prompt.
        
        Args:
            prompt: The prompt to send to the model
            
        Returns:
            GenerationResult with extracted code and metadata
        """
        import time
        
        url = f"{self.base_url}/api/generate"
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": self.temperature,
                "top_p": self.top_p,
                "num_predict": self.max_tokens
            }
        }
        
        start_time = time.time()
        
        response = requests.post(url, json=payload)
        response.raise_for_status()
        
        generation_time = time.time() - start_time
        
        data = response.json()
        raw_response = data.get("response", "")
        
        # Extract code from response
        code = self._extract_code(raw_response)
        
        return GenerationResult(
            code=code,
            raw_response=raw_response,
            generation_time=generation_time,
            prompt_tokens=data.get("prompt_eval_count"),
            completion_tokens=data.get("eval_count")
        )
    
    def _extract_code(self, response: str) -> str:
        """
        Extract Python code from the model's response.
        Handles various formats: markdown blocks, [PYTHON] tags, or raw code.
        """
        # Try to extract from markdown code blocks
        markdown_pattern = r"```(?:python)?\n(.*?)```"
        matches = re.findall(markdown_pattern, response, re.DOTALL)
        if matches:
            return matches[0].strip()
        
        # Try to extract from [PYTHON] tags (Codellama format)
        python_tag_pattern = r"\[PYTHON\]\n?(.*?)\[/PYTHON\]"
        matches = re.findall(python_tag_pattern, response, re.DOTALL)
        if matches:
            return matches[0].strip()
        
        # If no special formatting, return the response as-is
        # but try to clean it up
        lines = response.strip().split('\n')
        code_lines = []
        in_code = False
        
        for line in lines:
            # Skip obvious non-code lines
            if line.strip().startswith(('#', 'def ', 'class ', 'import ', 'from ', 'return ', 'if ', 'for ', 'while ')):
                in_code = True
            if in_code or line.strip().startswith(('def ', 'class ', 'import ', 'from ')):
                code_lines.append(line)
                in_code = True
        
        if code_lines:
            return '\n'.join(code_lines).strip()
        
        return response.strip()
    
    def is_available(self) -> bool:
        """Check if Ollama server is running and model is available."""
        try:
            response = requests.get(f"{self.base_url}/api/tags")
            if response.status_code == 200:
                models = response.json().get("models", [])
                model_names = [m.get("name", "") for m in models]
                return self.model in model_names
            return False
        except requests.exceptions.ConnectionError:
            return False


# Simple test when running this file directly
if __name__ == "__main__":
    from rich.console import Console
    from rich.syntax import Syntax
    
    console = Console()
    
    console.print("\n[bold blue]Testing Ollama Client[/bold blue]\n")
    
    client = OllamaClient()
    
    # Check if Ollama is available
    console.print("Checking Ollama availability...", end=" ")
    if client.is_available():
        console.print("[green]✓ Available[/green]")
    else:
        console.print("[red]✗ Not available[/red]")
        console.print("[yellow]Make sure Ollama is running: ollama serve[/yellow]")
        exit(1)
    
    # Test generation
    console.print("\nGenerating code for: [italic]'Write a function to calculate factorial'[/italic]\n")
    
    prompt = """Complete the following Python function. Return only the code, no explanations.

def factorial(n):
    \"\"\"Calculate the factorial of n.\"\"\"
"""
    
    result = client.generate(prompt)
    
    console.print(f"[dim]Generation time: {result.generation_time:.2f}s[/dim]")
    console.print(f"[dim]Tokens: {result.prompt_tokens} prompt, {result.completion_tokens} completion[/dim]\n")
    
    console.print("[bold]Extracted Code:[/bold]")
    syntax = Syntax(result.code, "python", theme="monokai", line_numbers=True)
    console.print(syntax)