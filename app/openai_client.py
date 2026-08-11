from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import openai

from .incidents import STATE

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
USE_REAL_API = bool(OPENAI_API_KEY)


@dataclass
class FakeUsage:
    input_tokens: int
    output_tokens: int


@dataclass
class FakeResponse:
    text: str
    usage: FakeUsage
    model: str


def _create_client() -> openai.OpenAI | None:
    if not USE_REAL_API:
        return None
    return openai.OpenAI(api_key=OPENAI_API_KEY)


class RealLLM:
    def __init__(self, model: str = "gpt-4o-mini") -> None:
        self.model = model
        self.client = _create_client()

    def generate(self, prompt: str) -> FakeResponse:
        if not self.client:
            raise RuntimeError("OpenAI API key not configured. Set OPENAI_API_KEY in .env")

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )

        choice = response.choices[0]
        text = choice.message.content or ""

        usage = response.usage
        input_tokens = usage.prompt_tokens if usage else 0
        output_tokens = usage.completion_tokens if usage else 0

        if STATE["cost_spike"]:
            output_tokens *= 4

        return FakeResponse(
            text=text,
            usage=FakeUsage(input_tokens, output_tokens),
            model=self.model,
        )


class FakeLLM:
    """Mock LLM for testing when no API key is available."""

    def __init__(self, model: str = "claude-sonnet-4-5") -> None:
        self.model = model

    def generate(self, prompt: str) -> FakeResponse:
        import random
        import time

        time.sleep(0.15)
        input_tokens = max(20, len(prompt) // 4)
        output_tokens = random.randint(80, 180)
        if STATE["cost_spike"]:
            output_tokens *= 4
        answer = (
            "Starter answer. Teams should improve this output logic and add better quality checks. "
            "Use retrieved context and keep responses concise."
        )
        return FakeResponse(text=answer, usage=FakeUsage(input_tokens, output_tokens), model=self.model)


def get_llm(model: str = "gpt-4o-mini") -> RealLLM | FakeLLM:
    """Factory function that returns real or fake LLM based on configuration."""
    if USE_REAL_API:
        return RealLLM(model=model)
    return FakeLLM(model=model)
