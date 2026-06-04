# CRA Audit Rules

- Do not re-route PowerShell-required Teams and Exchange controls back through Graph limitation shims.
- Do not classify Custom Banned Password List as PASS or FAIL unless Microsoft exposes enabled state and custom word count from tenant evidence.
- Client-facing APIs must not expose secret IDs, encrypted secrets, deployment diagnostics, raw Graph responses, raw PowerShell stdout/stderr, collector names, script paths, or internal artifact IDs.
- Redis/WebSocket fanout failures must be logged. Persisted assessment events are authoritative, but silent fanout failures make runtime debugging unreliable.
- JSON serialization of external/runtime data must use a guarded stringify helper in frontend rendering paths.
- Browser-only APIs must be guarded so components and utilities remain test-safe outside the browser.
- Uploaded workbook filenames must be normalized before storage, and workbook size must be bounded before parsing.
- Database exception responses must be structured and generic; raw database messages stay in server logs only.
