import os
import re
import time
from typing import Optional
from pydantic import BaseModel


class GenerationResult(BaseModel):
    code: str
    raw_response: str
    generation_time: float
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None


class GroqClient:
    
    def __init__(self, model: str = "llama-3.3-70b-versatile", api_key: str = None):
        from groq import Groq
        self.model = model
        self.client = Groq(api_key=api_key or os.environ.get("GROQ_API_KEY"))
    
    def generate(self, prompt: str) -> GenerationResult:
        t0 = time.time()
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=512
        )
        
        gen_time = time.time() - t0
        raw = response.choices[0].message.content
        code = self._extract_code(raw)
        
        return GenerationResult(
            code=code,
            raw_response=raw,
            generation_time=gen_time,
            prompt_tokens=response.usage.prompt_tokens,
            completion_tokens=response.usage.completion_tokens
        )
    
    def _extract_code(self, response: str) -> str:
        md = re.findall(r"```(?:python)?\n(.*?)```", response, re.DOTALL)
        if md:
            return md[0].strip()
        
        py = re.findall(r"\[PYTHON\]\n?(.*?)\[/PYTHON\]", response, re.DOTALL)
        if py:
            return py[0].strip()
        
        return response.strip()
    
    def is_available(self) -> bool:
        try:
            self.client.models.list()
            return True
        except:
            return False


if __name__ == "__main__":
    client = GroqClient()
    
    if not client.is_available():
        print("Groq not available. Set GROQ_API_KEY env variable.")
        exit(1)
    
    print("Testing Groq...")
    result = client.generate("Write a Python function to check if a number is prime. Return only code.")
    print(f"Time: {result.generation_time:.2f}s")
    print(result.code)
