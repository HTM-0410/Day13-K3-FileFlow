# Validation results

Thời điểm chạy: 2026-08-11 12:06 (Asia/Bangkok).

## Automated tests

```text
22 passed, 2 warnings in 2.49s
```

Hai warning là deprecation warning của FastAPI `on_event`; không có test failure.

## Log validator

```text
Total log records analyzed: 13
Records with missing required fields: 0
Records with missing enrichment (context): 0
Unique correlation IDs found: 3
Potential PII leaks detected: 0
Estimated Score: 100/100
```

## Dashboard validator

```text
HỢP LỆ: 6/6 panel có trong dashboard contract.
```
