from __future__ import annotations

from app import agent as agent_module


class ManagedPrompt:
    version = 3

    def compile(self, **variables: str) -> str:
        return (
            f"Feature={variables['feature']}\n"
            f"Docs={variables['docs']}\n"
            f"Question={variables['message']}"
        )


class RecordingLangfuseClient:
    def __init__(self) -> None:
        self.prompt = ManagedPrompt()
        self.trace_updates: list[dict] = []
        self.generation_updates: list[dict] = []

    def get_prompt(self, name: str, **kwargs):
        return self.prompt

    def update_current_trace(self, **kwargs) -> None:
        self.trace_updates.append(kwargs)

    def update_current_generation(self, **kwargs) -> None:
        self.generation_updates.append(kwargs)

    def update_current_span(self, **kwargs) -> None:
        return None

    def get_current_trace_id(self) -> str:
        return "trace-test-001"


def test_agent_links_prompt_version_to_trace_and_generation(monkeypatch) -> None:
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "test-public-key")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "test-secret-key")
    monkeypatch.setenv("LANGFUSE_PROMPT_NAME", "day13-chat")
    monkeypatch.setenv("LANGFUSE_PROMPT_LABEL", "production")
    client = RecordingLangfuseClient()
    monkeypatch.setattr(agent_module, "get_langfuse_client", lambda: client)

    agent = agent_module.LabAgent()
    agent_module.LabAgent.run.__wrapped__(
        agent,
        user_id="student-01",
        feature="qa",
        session_id="session-01",
        message="Explain traces",
        correlation_id="req-test-001",
    )

    trace_metadata = client.trace_updates[-1]["metadata"]
    generation_update = client.generation_updates[-1]
    assert trace_metadata["prompt_name"] == "day13-chat"
    assert trace_metadata["prompt_label"] == "production"
    assert trace_metadata["prompt_version"] == "3"
    assert trace_metadata["prompt_source"] == "langfuse"
    assert trace_metadata["correlation_id"] == "req-test-001"
    assert trace_metadata["rag_latency_ms"] >= 0
    assert trace_metadata["llm_latency_ms"] >= 100
    assert generation_update["prompt"] is client.prompt
    assert generation_update["metadata"]["prompt_version"] == "3"
    assert generation_update["metadata"]["component"] == "llm"
