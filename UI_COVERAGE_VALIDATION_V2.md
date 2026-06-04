# UI Coverage Validation V2

Generated: 2026-06-02

## Finding

The Evidence page previously counted any finding row as collected. That inflated coverage because unsupported outcomes such as `NOT_SUPPORTED` and `LICENSING_LIMITATION` were included in the collected count.

## Validation Result

| UI/API Area | Result |
|---|---|
| Evidence API total parameters | Uses approved registry count: 64 |
| Evidence API collected count | Counts only real evidence statuses, excluding unsupported outcomes |
| Evidence API unsupported count | Added as separate `coverage.unsupported` value |
| Evidence API not collected count | Calculates `total - collected - unsupported` |
| Evidence page cards | Shows `Collected`, `Unsupported`, and `Not collected` separately |
| Evidence page status filter | Includes `NOT_SUPPORTED` and `LICENSING_LIMITATION` |
| Coverage percentage | Uses real collected controls only |

## Current Coverage Counts

| Metric | Count |
|---|---:|
| Approved parameters | 64 |
| Collected real evidence | 48 |
| Unsupported / placeholder | 16 |
| Not collected | 0 |
| Coverage percent | 75.0% |
