# Logging and PII evidence

Request kiểm tra: `req-6463eb74` / trace `56039a54ffd95fc95ae9a5f21fbdda6f`.

Log đã lưu:

```json
{"service":"api","session_id":"pii-evidence","feature":"security","model":"mock-llm-v1","payload":{"message_preview":"Contact [REDACTED_EMAIL] or [REDACTED_PHONE_VN], card [REDACTED_CREDIT_CARD]"},"event":"request_received","correlation_id":"req-6463eb74","level":"info"}
```

Kiểm tra toàn bộ `data/logs.jsonl`:

```text
Raw email present: false
Raw phone present: false
Raw card present: false
Potential PII leaks detected: 0
```

`user_id` không được ghi nguyên văn; log chỉ lưu SHA-256 rút gọn trong `user_id_hash`.
