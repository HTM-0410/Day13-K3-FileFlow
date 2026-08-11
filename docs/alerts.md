# Alert Runbooks — Day 13 Observability

## Latency P95 Breach

- **Tên**: `LatencyP95Breach`
- **Severity**: Warning
- **SLI/SLO**: `latency_p95_ms` / SLO target 99.5%
- **Điều kiện**: P95 latency > 3000ms trong 5 phút liên tiếp
- **Ảnh hưởng**: Người dùng nhận câu trả lời chậm, trải nghiệm kém
- **Ba bước kiểm tra đầu tiên**:
  1. Kiểm tra dashboard panel `latency` — xem P95 có thực sự cao không
  2. Mở Langfuse trace gần nhất, xem span nào có duration lớn nhất
  3. Check `/incidents/rag_slow/enable` có đang active không
- **Mitigation tạm thời**: Disable incident `rag_slow`, restart RAG service
- **Owner**: backend-team

---

## High Error Rate

- **Tên**: `HighErrorRate`
- **Severity**: Critical
- **SLI/SLO**: `error_rate_pct` / SLO target 99%
- **Điều kiện**: Error rate > 2% trong 2 phút liên tiếp
- **Ảnh hưởng**: Nhiều user nhận HTTP 500, dịch vụ không khả dụng một phần
- **Ba bước kiểm tra đầu tiên**:
  1. Kiểm tra dashboard panel `errors` — xem số lượng `request_failed`
  2. Tra cứu log `data/logs.jsonl` filter `event=request_failed`, đọc `error_type`
  3. Mở trace có `event=request_failed`, xem stack trace trong metadata
- **Mitigation tạm thời**: Disable incident `tool_fail`; rollback prompt chỉ khi trace chứng minh lỗi bắt đầu sau khi đổi prompt
- **Owner**: backend-team

---

## Cost Spike

- **Tên**: `CostSpike`
- **Severity**: Warning
- **SLI/SLO**: `daily_cost_usd` / SLO target 100%
- **Điều kiện**: Cumulative cost > $2.5/ngày
- **Ảnh hưởng**: Chi phí vượt ngân sách, cần review token usage
- **Ba bước kiểm tra đầu tiên**:
  1. Kiểm tra dashboard panel `cost` — xem trend cost theo thời gian
  2. Kiểm tra dashboard panel `tokens` — xem token in/out
  3. Review traces gần đây, xem model và số tokens mỗi request
- **Mitigation tạm thời**: Giảm traffic, tối ưu prompt để giảm token
- **Owner**: platform-team

---

## Low Quality Score

- **Tên**: `LowQualityScore`
- **Severity**: Warning
- **SLI/SLO**: `quality_score_avg` / SLO target 95%
- **Điều kiện**: Mean quality < 0.75 trong 10 phút liên tiếp
- **Ảnh hưởng**: User nhận câu trả lời kém chất lượng
- **Ba bước kiểm tra đầu tiên**:
  1. Kiểm tra dashboard panel `quality` — xem trend quality theo thời gian
  2. Tra cứu traces với `quality_score` thấp, xem RAG docs và prompt
  3. So sánh prompt version và tài liệu RAG của các trace điểm thấp với trace bình thường
- **Mitigation tạm thời**: Rollback prompt về `baseline` nếu candidate làm giảm chất lượng; không bật incident khi xử lý sự cố
- **Owner**: ai-team

---

## No Traffic

- **Tên**: `NoTraffic`
- **Severity**: Warning
- **SLI/SLO**: `traffic` / SLO target 99%
- **Điều kiện**: 0 requests trong 5 phút liên tiếp
- **Ảnh hưởng**: Dịch vụ không nhận traffic, có thể là upstream issue hoặc service down
- **Ba bước kiểm tra đầu tiên**:
  1. Ping `/health` endpoint — xem service có alive không
  2. Check uvicorn logs — có request nhưng không đến `/chat` không
  3. Verify upstream load balancer hoặc API gateway có forward request không
- **Mitigation tạm thời**: Restart uvicorn, check network connectivity
- **Owner**: platform-team

---

## RAG Retrieval Slow

- **Tên**: `RagRetrievalSlow`
- **Severity**: Warning
- **SLI**: `rag_latency_ms`
- **Điều kiện**: RAG retrieval > 2000ms trong 3 request liên tiếp
- **Ảnh hưởng**: Tổng latency tăng dù thời gian LLM bình thường
- **Ba bước kiểm tra đầu tiên**:
  1. Mở panel latency và xác định khoảng thời gian P95 vượt SLO
  2. Mở trace trong khoảng đó, so sánh span `rag_retrieval` với `llm_generation`
  3. Dùng `correlation_id` hoặc `trace_id` trong metadata để mở đúng log `response_sent`
- **Mitigation tạm thời**: Tắt incident `rag_slow`; trong production, bypass nguồn RAG chậm hoặc dùng cache/fallback đã phê duyệt
- **Preventive measure**: Giữ child span RAG/LLM, alert riêng cho `rag_latency_ms`, và chạy synthetic check định kỳ
- **Owner**: backend-team
