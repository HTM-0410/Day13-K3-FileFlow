# Trace evidence

Các trace dưới đây được sinh từ bản code có waterfall `agent_run → rag_retrieval → llm_generation`.

| Mục đích | Prompt label | Trace ID | Correlation ID |
|---|---|---|---|
| Prompt baseline | `baseline` | `8945c972856f954b9a295e7667dbf50c` | `req-208f6f7d` |
| Prompt candidate | `candidate` | `c88a1d2ba1b2c36ebace05897ac89509` | `req-30dc07be` |
| Incident chậm 1 | `production` | `24a058d82e78170c490f7e98da443b24` | `req-e4597bb8` |
| Incident chậm 2 | `production` | `b2c9ed564622731a3957c095fbf4b5f9` | `req-43d8bae9` |
| Incident chậm 3 | `production` | `0b2410dc4aecce190e173ee13bfd31a3` | `req-afa876e7` |
| Incident chậm 4 | `production` | `aad01642542e120f99e5fee5754fe276` | `req-c28aafff` |
| Incident chậm 5 | `production` | `88a808e61731eaee52d1a15c788ea38e` | `req-c1bf8b92` |
| Sau mitigation 1 | `production` | `6c753428f51d5a206e52fd5a0a145d0d` | `req-79f133ed` |
| Sau mitigation 2 | `production` | `6a309d1a86deec65d3710316a49c7ac4` | `req-b2c8d33f` |
| Sau mitigation 3 | `production` | `50452adcc9ca9e61231b3ccba7d5dc47` | `req-35da192b` |
| Sau mitigation 4 | `production` | `1d7fcbc27fdb59c78d39280483d586da` | `req-38521b31` |
| Sau mitigation 5 | `production` | `9c7ac2aaf9fa4889ac8950daea229e42` | `req-105a6c09` |
| PII redaction | `production` | `56039a54ffd95fc95ae9a5f21fbdda6f` | `req-6463eb74` |
| Production sau rollback | `production` (v2) | `3cf28c3a7c93e08111316ffb36f79842` | `req-ea341701` |

Trace metadata chứa `correlation_id`, `prompt_name`, `prompt_label`, `prompt_version`, `prompt_source`, `rag_latency_ms` và `llm_latency_ms`. Log `response_sent` chứa cùng `trace_id` và `correlation_id` để điều tra hai chiều.

Ảnh metadata: `trace_baseline_v2_metadata.png` và `trace_candidate_v3_metadata.png`. Waterfall incident: `trace_waterfall.png`. Ảnh rollback: `prompt_rollback_v3_to_v2.png`.
