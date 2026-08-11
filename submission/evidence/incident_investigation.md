# Incident investigation: `rag_slow`

## 1. Metrics — phát hiện triệu chứng

Sau 5 request challenge, latency P95 tăng lên khoảng 2.65 giây. Dashboard thể hiện P50/P95/P99 và SLO 3,000 ms trong `dashboard_latency_traffic.png`.

## 2. Traces — khoanh vùng component

Trace mẫu `24a058d82e78170c490f7e98da443b24`, correlation ID `req-e4597bb8`:

```text
total latency     3105 ms
rag_retrieval     2501 ms
llm_generation     151 ms
```

Child span `rag_retrieval` chiếm phần lớn tổng thời gian; `llm_generation` vẫn bình thường.

## 3. Logs — xác nhận root cause và request cụ thể

```json
{"event":"response_sent","correlation_id":"req-e4597bb8","trace_id":"24a058d82e78170c490f7e98da443b24","latency_ms":3105,"rag_latency_ms":2501,"llm_latency_ms":151}
```

Root cause trong `app/mock_rag.py`: khi incident `rag_slow` bật, retrieval ngủ 2.5 giây.

## 4. Fix action và kết quả sau fix

Mitigation: gọi `POST /incidents/rag_slow/disable`.

Request tương đương sau mitigation, correlation ID `req-79f133ed`, trace `6c753428f51d5a206e52fd5a0a145d0d`:

```text
total latency      152 ms
rag_retrieval        0 ms
llm_generation     151 ms
```

Latency giảm 95.1% so với request chậm mẫu.

## 5. Preventive measures đã triển khai

- Child span riêng `rag_retrieval` và `llm_generation`.
- Ghi `trace_id`, `correlation_id`, `rag_latency_ms`, `llm_latency_ms` vào log/trace metadata.
- Alert `RagRetrievalSlow` khi retrieval > 2,000 ms trong 3 request liên tiếp.
- Runbook hướng dẫn điều tra đúng thứ tự Metrics → Traces → Logs.
