"""
Langfuse Prompt Versioning — Evidence Script

Kiểm tra traces và prompt versions.
Sau khi chạy script này, user thực hiện thao tác đổi label trên dashboard.
"""

from dotenv import load_dotenv
import os; load_dotenv('.env')
import langfuse, time

lf = langfuse.Langfuse()
PROMPT_NAME = "day13-chat"

def get_traces(n=20):
    traces = lf.api.trace.list(limit=n)
    return traces.data

def show_traces(traces):
    print(f"\n{'='*60}")
    print(f"Traces ({len(traces)} total):")
    print(f"{'='*60}")
    for t in traces:
        meta = getattr(t, 'metadata', {}) or {}
        pn = meta.get('prompt_name', 'N/A')
        pl = meta.get('prompt_label', 'N/A')
        pv = meta.get('prompt_version', 'N/A')
        ps = meta.get('prompt_source', 'N/A')
        print(f"  [{t.id}] label={pl} version={pv} source={ps}")

def show_prompt_versions():
    print(f"\n{'='*60}")
    print(f"Prompt versions for '{PROMPT_NAME}':")
    print(f"{'='*60}")
    for label in ["production", "baseline", "candidate"]:
        try:
            p = lf.api.prompts.get(PROMPT_NAME, label=label)
            print(f"  Label '{label}': version={p.version}, labels={p.labels}")
        except Exception as e:
            print(f"  Label '{label}': ERROR - {type(e).__name__}")

def send_one_request(label_override=None):
    """Send one request and return trace info."""
    import httpx
    # Temporarily override env for label
    old_label = os.environ.get("LANGFUSE_PROMPT_LABEL")
    if label_override:
        os.environ["LANGFUSE_PROMPT_LABEL"] = label_override
        # Need to restart app or it won't pick up change...
        # Instead, we'll just record which label we tried with
    client = httpx.Client(timeout=15.0)
    r = client.post("http://127.0.0.1:8000/chat", json={
        "user_id": "evidence@test.com",
        "session_id": "sess_evidence",
        "feature": "qa",
        "message": "What is AI observability?",
    })
    client.close()
    data = r.json()
    if label_override:
        if old_label:
            os.environ["LANGFUSE_PROMPT_LABEL"] = old_label
        else:
            os.environ.pop("LANGFUSE_PROMPT_LABEL", None)
    return {
        "cid": data.get("correlation_id"),
        "status": r.status_code,
        "label_used": label_override or old_label or "production"
    }

def main():
    print("=" * 60)
    print("LANGFUSE PROMPT VERSIONING — EVIDENCE COLLECTION")
    print("=" * 60)
    
    # Show prompt versions
    show_prompt_versions()
    
    # Show current traces
    traces = get_traces()
    show_traces(traces)
    
    print(f"\n{'='*60}")
    print("SUMMARY:")
    print(f"  - Total traces: {len(traces)}")
    print(f"  - Prompt: {PROMPT_NAME}")
    print(f"  - v2 labels: baseline, production")
    print(f"  - v3 labels: candidate")
    print(f"{'='*60}")
    print("\nNEXT STEPS (manual on Langfuse dashboard):")
    print("  1. Go to https://jp.cloud.langfuse.com")
    print("  2. Navigate to Prompts > day13-chat")
    print("  3. Note: To change 'production' label from v2 -> v3,")
    print("     you must do this via the Langfuse dashboard UI.")
    print("     (SDK only supports create/get/list, not update labels)")
    print("  4. After changing label in dashboard, run:")
    print("       python scripts/send_with_labels.py")
    print("     to capture a trace with the new version")
    print("  5. Use the Langfuse UI to take screenshots for evidence")

if __name__ == "__main__":
    main()
