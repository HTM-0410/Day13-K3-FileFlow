# Demo Q&A theo vai trò

Tài liệu này là dàn ý vấn đáp; mỗi thành viên cần tự giải thích bằng lời và mở đúng evidence khi demo.

## Đỗ Nhật Minh — Logging & PII

**Correlation ID dùng để làm gì?**
Nó định danh một HTTP request xuyên suốt middleware và các log `request_received`/`response_sent`. Trace ID định danh distributed trace; bản triển khai ghi cả hai để nối log với Langfuse.

**Vì sao không log `user_id` trực tiếp?**
`user_id` có thể là PII. Hệ thống lưu SHA-256 rút gọn 16 ký tự và chỉ log preview đã scrub. Email, số điện thoại VN, CCCD, thẻ và passport đều được redact trước JSON rendering.

**Vì sao scrub processor phải chạy trước JSON renderer?**
Sau khi render thành chuỗi JSON, việc scrub theo field khó kiểm soát và có thể bỏ sót nested payload. Processor hiện scrub event/payload trước khi ghi file.

Evidence mở khi trả lời: `evidence/logging_and_pii.md`, correlation `req-6463eb74`.

## Trần Đức Thiện — Tracing & Prompt Version

**Trace khác log như thế nào?**
Trace thể hiện cấu trúc và duration của từng component; log giải thích dữ liệu/request cụ thể. Waterfall hiện có `agent_run`, `rag_retrieval`, `llm_generation`.

**Version và label prompt khác nhau thế nào?**
Version là bản nội dung bất biến. Label (`baseline`, `candidate`, `production`) là con trỏ có thể chuyển giữa các version. Rollback là chuyển `production` về version ổn định trước đó, không sửa giả metadata trong code.

**Làm sao biết request dùng prompt nào?**
Mở trace Data/metadata và kiểm tra `prompt_name`, `prompt_label`, `prompt_version`, `prompt_source`. Baseline evidence là trace `8945...` version 2; candidate là `c88a...` version 3.

Evidence mở khi trả lời: `evidence/trace_waterfall.png`, `evidence/trace_baseline_v2_metadata.png`, `evidence/trace_candidate_v3_metadata.png`.

## Trương Minh Hoàng — Dashboard, SLO, Alert & Incident

**P95 latency nghĩa là gì?**
95% request có latency nhỏ hơn hoặc bằng giá trị P95; 5% request chậm hơn. P95 phù hợp theo dõi tail latency hơn mean vì không che khuất nhóm request chậm.

**Vì sao điều tra theo Metrics → Traces → Logs?**
Metrics cho biết thời điểm và mức độ bất thường; trace chỉ ra component chậm; log dùng trace/correlation ID để xác nhận request và root cause cụ thể.

**Incident này được chứng minh thế nào?**
Dashboard cho thấy P95 2653ms. Trace `24a058...` cho thấy RAG 2501ms, LLM 151ms. Log correlation `req-e4597bb8` ghi cùng các giá trị. Sau mitigation, request tương đương còn 152ms.

**Alert tốt cần những gì?**
Có SLI, threshold, window/consecutive condition, severity, owner và runbook. `RagRetrievalSlow` cảnh báo RAG >2000ms trong 3 request liên tiếp.

Evidence mở khi trả lời: `evidence/dashboard_latency_traffic.png`, `evidence/incident_investigation.md`, `../docs/alerts.md`.
