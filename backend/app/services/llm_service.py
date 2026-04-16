from __future__ import annotations

import os

from ..config import settings
from ..resources import get_prompts_root


PROMPTS_ROOT = get_prompts_root()


class LLMUnavailableError(RuntimeError):
    """Raised when the configured LLM provider is not available."""


class LLMService:
    def __init__(self) -> None:
        self.model = settings.llm_model
        self.api_key = os.getenv("ANTHROPIC_API_KEY")

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    def load_prompt(self, prompt_key: str) -> str:
        if PROMPTS_ROOT is None:
            raise FileNotFoundError("prompt template root not found")
        prompt_path = PROMPTS_ROOT / f"{prompt_key}.md"
        if not prompt_path.exists():
            raise FileNotFoundError(f"prompt template not found: {prompt_key}")
        return prompt_path.read_text(encoding="utf-8")

    def render_prompt(self, prompt_key: str, variables: dict[str, str]) -> str:
        template = self.load_prompt(prompt_key)
        rendered = template
        for key, value in variables.items():
            rendered = rendered.replace(f"{{{{{key}}}}}", value)
        return rendered

    def complete(self, prompt_key: str, variables: dict[str, str]) -> str:
        if not self.available:
            raise LLMUnavailableError("ANTHROPIC_API_KEY is not configured")
        raise LLMUnavailableError(
            "LLM provider integration is not wired yet; current compile flow uses deterministic fallback"
        )


llm_service = LLMService()
