from __future__ import annotations

import os
import time
from dataclasses import dataclass

from . import metrics
from .openai_client import get_llm, FakeResponse, USE_REAL_API
from .mock_rag import retrieve
from .pii import hash_user_id, summarize_text
from .prompt_management import ResolvedPrompt, resolve_prompt
from .tracing import get_langfuse_client, observe, tracing_enabled


@dataclass
class AgentResult:
    answer: str
    latency_ms: int
    tokens_in: int
    tokens_out: int
    cost_usd: float
    quality_score: float
    trace_id: str | None = None
    rag_latency_ms: int = 0
    llm_latency_ms: int = 0


class LabAgent:
    def __init__(self, model: str | None = None) -> None:
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self._llm = None  # Lazy initialization

    @property
    def llm(self):
        """Lazy-load the LLM client based on configuration."""
        if self._llm is None:
            self._llm = get_llm(model=self.model)
        return self._llm

    @observe(name="agent_run", as_type="span", capture_input=False, capture_output=False)
    def run(
        self,
        user_id: str,
        feature: str,
        session_id: str,
        message: str,
        correlation_id: str | None = None,
    ) -> AgentResult:
        started = time.perf_counter()
        langfuse_client = get_langfuse_client()

        rag_started = time.perf_counter()
        docs = self._retrieve(message)
        rag_latency_ms = int((time.perf_counter() - rag_started) * 1000)

        prompt = resolve_prompt(
            langfuse_client,
            feature=feature,
            docs=docs,
            message=message,
            enabled=tracing_enabled(),
        )

        llm_started = time.perf_counter()
        response = self._generate(prompt)
        llm_latency_ms = int((time.perf_counter() - llm_started) * 1000)
        quality_score = self._heuristic_quality(message, response.text, docs)
        latency_ms = int((time.perf_counter() - started) * 1000)
        cost_usd = self._estimate_cost(response.usage.input_tokens, response.usage.output_tokens)

        try:
            update_trace = getattr(langfuse_client, "update_current_trace", None)
            update_v3 = getattr(langfuse_client, "update", None)
            if callable(update_trace):
                update_trace(
                    user_id=hash_user_id(user_id),
                    session_id=session_id,
                    tags=["lab", feature, self.model],
                    metadata={
                        "correlation_id": correlation_id,
                        "prompt_name": prompt.name,
                        "prompt_label": prompt.label,
                        "prompt_version": prompt.version,
                        "prompt_source": prompt.source,
                        "rag_latency_ms": rag_latency_ms,
                        "llm_latency_ms": llm_latency_ms,
                    },
                )
            elif callable(update_v3):
                trace_id_val = getattr(langfuse_client, "get_current_trace_id", lambda: None)()
                if trace_id_val:
                    langfuse_client.update(
                        id=trace_id_val,
                        user_id=hash_user_id(user_id),
                        session_id=session_id,
                        tags=["lab", feature, self.model],
                        metadata={
                            "correlation_id": correlation_id,
                            "prompt_name": prompt.name,
                            "prompt_label": prompt.label,
                            "prompt_version": prompt.version,
                            "prompt_source": prompt.source,
                            "rag_latency_ms": rag_latency_ms,
                            "llm_latency_ms": llm_latency_ms,
                        },
                    )
        except Exception:
            pass

        get_trace_id = getattr(langfuse_client, "get_current_trace_id", None)
        trace_id = get_trace_id() if callable(get_trace_id) else None

        metrics.record_request(
            latency_ms=latency_ms,
            cost_usd=cost_usd,
            tokens_in=response.usage.input_tokens,
            tokens_out=response.usage.output_tokens,
            quality_score=quality_score,
        )

        return AgentResult(
            answer=response.text,
            latency_ms=latency_ms,
            tokens_in=response.usage.input_tokens,
            tokens_out=response.usage.output_tokens,
            cost_usd=cost_usd,
            quality_score=quality_score,
            trace_id=trace_id,
            rag_latency_ms=rag_latency_ms,
            llm_latency_ms=llm_latency_ms,
        )

    @observe(name="rag_retrieval", as_type="span", capture_input=False, capture_output=False)
    def _retrieve(self, message: str) -> list[str]:
        client = get_langfuse_client()
        update_span = getattr(client, "update_current_span", None)
        if callable(update_span):
            update_span(metadata={"component": "rag", "query_preview": summarize_text(message)})
        return retrieve(message)

    @observe(name="llm_generation", as_type="generation", capture_input=False, capture_output=False)
    def _generate(self, prompt: ResolvedPrompt) -> FakeResponse:
        response = self.llm.generate(prompt.text)
        cost_usd = self._estimate_cost(response.usage.input_tokens, response.usage.output_tokens)
        get_langfuse_client().update_current_generation(
            model=self.model,
            metadata={
                "component": "llm",
                "prompt_name": prompt.name,
                "prompt_label": prompt.label,
                "prompt_version": prompt.version,
                "prompt_source": prompt.source,
                "prompt_fetch_error": prompt.fetch_error,
            },
            usage_details={
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens,
            },
            cost_details={"total": cost_usd},
            prompt=prompt.managed_prompt,
        )
        return response

    def _estimate_cost(self, tokens_in: int, tokens_out: int) -> float:
        input_rate = float(os.getenv("INPUT_COST_PER_MILLION_USD", "3"))
        output_rate = float(os.getenv("OUTPUT_COST_PER_MILLION_USD", "15"))
        input_cost = (tokens_in / 1_000_000) * input_rate
        output_cost = (tokens_out / 1_000_000) * output_rate
        return round(input_cost + output_cost, 6)

    def _heuristic_quality(self, question: str, answer: str, docs: list[str]) -> float:
        score = 0.5
        if docs:
            score += 0.2
        if len(answer) > 40:
            score += 0.1
        if question.lower().split()[0:1] and any(token in answer.lower() for token in question.lower().split()[:3]):
            score += 0.1
        if "[REDACTED" in answer:
            score -= 0.2
        return round(max(0.0, min(1.0, score)), 2)
