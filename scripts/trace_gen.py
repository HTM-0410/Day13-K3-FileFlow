import httpx, json, time

BASE_URL = "http://127.0.0.1:8000"

payloads = [
    {"user_id": f"u{i}@test.com", "session_id": f"sess{i:02d}", "feature": "qa", "message": f"What is the capital of country {i}?"}
    for i in range(1, 16)
]

client = httpx.Client(timeout=15.0)
print(f"Sending {len(payloads)} requests to {BASE_URL}/chat...")
for i, p in enumerate(payloads, 1):
    try:
        r = client.post(f"{BASE_URL}/chat", json=p)
        data = r.json()
        print(f"[{i:02d}] [{r.status_code}] cid={data.get('correlation_id')} | {p['session_id']}")
    except Exception as e:
        print(f"[{i:02d}] Error: {e}")
client.close()
print("\nDone. Waiting 5s for traces to flush...")
time.sleep(5)
