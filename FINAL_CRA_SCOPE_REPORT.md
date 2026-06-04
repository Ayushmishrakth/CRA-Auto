# Final CRA Scope Report

Generated: 2026-06-02

## Final Scope

| Metric | Count |
|---|---:|
| Approved Parameters | 64 |
| Real Collectors | 48 |
| Placeholder Collectors | 16 |
| Unsupported Controls | 16 |
| Coverage % | 75.0% |

Coverage formula:

```text
Real Collectors / Approved Parameters = 48 / 64 = 75.0%
```

## Governance Decision

`unused_licenses_count` is not part of the final approved CRA scope and has been removed from active inventory and runtime execution.

## Production Meaning

The platform now has a single authoritative parameter count of 64. Coverage is no longer reported as registered collectors divided by approved parameters. It is now real tenant-evidence collectors divided by approved parameters, so unsupported and licensing-limited controls do not inflate readiness coverage.
