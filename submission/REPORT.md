# Báo cáo Day 13 Observability

## 1. Thông tin nhóm

- **Tên nhóm:** FileFlow
- **Repository URL:** https://github.com/HTM-0410/Day13-K3-FileFlow
- **Commit SHA source/evidence dùng để chấm:** `829d23a`
- **Thành viên và vai trò:**

| Thành viên | MSSV | Email | Vai trò |
|------------|------|-------|---------|
| Đỗ Nhật Minh | 2A202601085 | minhblcute26102004@gmail.com | Logging & PII |
| Trần Đức Thiện | 2A202602032 | 23521488@gm.uit.edu.vn | Tracing & Prompt Version |
| Trương Minh Hoàng | 2A202602004 | hoangtruongminh22@gmail.com | Dashboard, SLO & Alert |

---

## 2. Kết quả kỹ thuật

| Metric | Giá trị |
|--------|---------|
| Điểm `validate_logs.py` | **100/100** |
| Tổng số traces (Langfuse) | **20+; 13 trace ID mới được liệt kê trong evidence** |
| Số PII leak còn lại | **0** |
| Kết quả `validate_dashboard.py` | **6/6 panels** |
| Test suite | **22/22 passed** |
| Dashboard URL | `streamlit run scripts/dashboard.py` |

---

## 3. Logging và PII (Checkpoint 1)

### 3.1 Correlation ID
- Mỗi request được gán correlation ID tự động (format: `req-xxxxxxxx`)
- Correlation ID được bind vào context và xuất hiện trong tất cả log entries

### 3.2 Metadata log
- Log có đầy đủ: `user_id_hash`, `session_id`, `feature`, `model`, `env`
- Format: JSON với timestamp RFC3339

### 3.3 PII Redaction
- **Email:** thay bằng `[REDACTED_EMAIL]`
- **Số điện thoại VN:** thay bằng `[REDACTED_PHONE_VN]`
- **Số thẻ:** thay bằng `[REDACTED_CREDIT_CARD]`

**Evidence:**
- `submission/evidence/logging_and_pii.md`
- `submission/evidence/validation_results.md`
- Request mẫu: correlation ID `req-6463eb74`, trace ID `56039a54ffd95fc95ae9a5f21fbdda6f`
- Validator cuối: 13 records, 3 correlation IDs, 0 PII leak

---

## 4. Tracing và Prompt Versioning (Checkpoint 2)

### 4.1 Tracing
- Waterfall được tách thành `agent_run → rag_retrieval → llm_generation`.
- Trace và generation ghi đầy đủ metadata:
  - `prompt_name`
  - `prompt_label`
  - `prompt_version`
  - `prompt_source`
  - `correlation_id`
  - `rag_latency_ms`
  - `llm_latency_ms`
- Log `response_sent` ghi cùng `trace_id` và `correlation_id`, cho phép đi từ trace sang log và ngược lại.

### 4.2 Prompt Versioning
| Prompt Name | Label | Version | Mô tả |
|-------------|-------|---------|--------|
| `day13-chat` | `baseline` | v2 | Prompt baseline |
| `day13-chat` | `candidate` | v3 | Prompt cải tiến |
| `day13-chat` | `production` | v2 | Đã rollback về baseline |

### 4.3 Evidence
- **Danh sách 13 trace ID:** `submission/evidence/trace_ids.md`
- **Baseline trace:** `8945c972856f954b9a295e7667dbf50c` — label `baseline`, version 2
- **Candidate trace:** `c88a1d2ba1b2c36ebace05897ac89509` — label `candidate`, version 3
- **Metadata screenshots:** `submission/evidence/trace_baseline_v2_metadata.png`, `submission/evidence/trace_candidate_v3_metadata.png`
- **Screenshot prompt versions:** `submission/evidence/2promt.png`
- **Screenshot production promotion:** `submission/evidence/sau_rollback.png`
- **Screenshot waterfall:** `submission/evidence/trace_waterfall.png`
- **Screenshot rollback thật:** `submission/evidence/prompt_rollback_v3_to_v2.png`
- **Production trace sau rollback:** `3cf28c3a7c93e08111316ffb36f79842` — label `production`, version 2

---

## 5. Dashboard, SLO và Alerts (Checkpoint 2)

### 5.1 Dashboard Panels (6/6)
| # | Panel | Metric | SLO Threshold |
|---|-------|--------|--------------|
| 1 | Latency | P50/P95/P99 | P95 ≤ 3000ms |
| 2 | Traffic | req/min | ≥ 1 req/min |
| 3 | Error Rate | % errors | ≤ 2% |
| 4 | Token Usage | In/Out/Total | Total ≤ 50,000 |
| 5 | Cost | Daily $ | ≤ $2.5 |
| 6 | Quality | Mean score | ≥ 0.75 |

### 5.2 SLO Objectives
| SLI | Target | Current | Status |
|-----|--------|---------|--------|
| Latency P95 | ≤ 3000ms | 2653ms | OK |
| Error Rate | ≤ 2% | 0% | OK |
| Daily Cost | ≤ $2.5 | $0.0976 | OK |
| Mean Quality | ≥ 0.75 | 0.8792 | OK |

### 5.3 Alert Rules
- `config/alert_rules.yaml` - 6 alert rules, gồm:
  1. Latency P95 > 3000ms
  2. Error Rate > 2%
  3. Daily Cost > $2.5
  4. Mean Quality < 0.75
  5. No Traffic
  6. RAG Retrieval > 2000ms trong 3 request liên tiếp
- Runbook: `docs/alerts.md`
- Dashboard evidence: `submission/evidence/dashboard_latency_traffic.png` và `submission/evidence/dashboard_panels_detail.png`

---

## 6. Điều tra Challenge (nếu có)

### Challenge: `rag_slow` (day13-k3-observability-v1)

| Bước | Hành động | Kết quả |
|------|-----------|---------|
| 1 — Metrics | Dashboard latency | P95 = 2653ms; 5 challenge requests đều > 2.6s |
| 2 — Traces | Trace `24a058...` | `rag_retrieval` = 2501ms, `llm_generation` = 151ms |
| 3 — Logs | Correlation `req-e4597bb8` | total = 3105ms, RAG = 2501ms, LLM = 151ms |
| 4 — Root cause | `app/mock_rag.py` | `time.sleep(2.5)` khi `STATE["rag_slow"]` bật |
| 5 — Fix | Disable `rag_slow` | Request tương đương còn 152ms; RAG = 0ms |

**Root cause:** Incident `rag_slow` bật thêm 2.5s delay vào RAG retrieval.

**Fix:** Disable incident `rag_slow`.

**Trace trước/sau:** `24a058d82e78170c490f7e98da443b24` / `6c753428f51d5a206e52fd5a0a145d0d`.

**Preventive measure đã triển khai:** child span riêng cho RAG/LLM, log liên kết trace/correlation, alert `RagRetrievalSlow` và runbook Metrics → Traces → Logs. Chi tiết: `submission/evidence/incident_investigation.md`.

---

## 7. Đóng góp cá nhân

| Thành viên | Phần việc | Commit | Chi tiết |
|------------|-----------|--------|----------|
| **A — Đỗ Nhật Minh** | Logging & PII | `2fcad82` | Correlation ID middleware, PII scrubbing, log enrichment và trace-linked schema |
| **B — Trần Đức Thiện** | Tracing & Prompt | `1243125` | Prompt v2/v3, rollback, waterfall, trace/log linking và OpenAI adapter |
| **C — Trương Minh Hoàng** | Dashboard & Alerts | `829d23a` | Dashboard 6 panels, SLO, alert rules, runbook và incident evidence |

### 7.1 Đỗ Nhật Minh (Logging & PII)
- **Phần việc:** Triển khai correlation ID middleware, PII detection & redaction, log enrichment
- **Commit:** `2fcad82`
- **Đã học:** Contextvars cho async tracing, regex patterns cho PII (email, VN phone, credit card)

### 7.2 Trần Đức Thiện (Tracing & Prompt Version)
- **Phần việc:** Prompt versioning workflow, rollback evidence, waterfall, trace/log linking và OpenAI adapter
- **Commit:** `1243125`
- **Đã học:** Langfuse SDK `@observe` decorator, prompt label/version metadata, rollback workflow

### 7.3 Trương Minh Hoàng (Dashboard, SLO & Alert)
- **Phần việc:** Dashboard 6 panels (Streamlit), SLO configuration, alert rules, runbook và incident evidence
- **Commit:** `829d23a`
- **Đã học:** Streamlit layout, metric panels, SLO/SLI definition, alerting thresholds

---

## 8. Checklist hoàn tất

- [x] `validate_logs.py` ≥ 80/100 (đạt 100/100)
- [x] `validate_dashboard.py` 6/6 panels
- [x] ≥ 10 trace IDs
- [x] Prompt v1/v2 với label & version metadata
- [x] Rollback thật từ production v3 về v2, có screenshot và trace production v2
- [x] Dashboard có time range + SLO threshold
- [x] Alert rules và runbook
- [x] Report đầy đủ 7 mục
- [x] Không có .env/secret/PII trong Git
- [x] Chuỗi điều tra Metrics → Traces → Logs có trace ID và correlation ID chung
- [x] Có dàn ý vấn đáp theo vai trò tại `submission/DEMO_QA.md`
- [x] Commit đúng tác giả, email và vai trò; SHA được ghi rõ trong mục đóng góp cá nhân
