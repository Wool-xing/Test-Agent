# API Overview

Test-Agent V2 exposes a FastAPI backend with bearer authentication, RBAC, and CORS-restricted access. The API server runs on `http://localhost:8000` by default.

## Authentication

Set `TAGENT_API_AUTH_TOKEN` in your `.env` to enable bearer auth:

```bash
TAGENT_API_AUTH_TOKEN=your-secret-token

```text

All endpoints (except `/health`) require `Authorization: Bearer <token>`.

## Core Endpoints

### Health Check

```text

GET /health

```text

Returns 200 when the server is running. No auth required.

### Catalog

```text

GET /catalog
Authorization: Bearer <token>

```text

Returns the full expert agent and skill catalog:

```json

{
  "experts": [...],
  "skills": [...],
  "counts": { "experts": 16, "skills": 32 }
}

```text

### Plan

```text

POST /plan
Authorization: Bearer <token>
Content-Type: application/json

{
  "prd_path": "path/to/prd.md",
  "options": { "mode": "comprehensive" }
}

```text

Returns a test plan with task list and DAG structure.

### Run

```text

POST /run
Authorization: Bearer <token>
Content-Type: application/json

{
  "prd_path": "path/to/prd.md"
}

```text

Executes the full pipeline and returns a run ID for status polling.

### Status

```text

GET /status/{run_id}
Authorization: Bearer <token>

```text

Returns execution status, progress, and any failures.

### Dashboard

```text

GET /dashboard
Authorization: Bearer <token>

```text

Returns the observability dashboard with three sections:

-**Decision**: Pass rate, trends, MTTD/MTTR
-**Diagnostic**: Expert heatmap, flaky candidates, environment health
-**Actions**: P0/P1 action items

### Report

```text

GET /report/{run_id}
Authorization: Bearer <token>

```text

Returns the full test report in JSON format.

## RBAC

When `TAGENT_RBAC_ENABLED=1`, endpoints are gated by role:

| Role | Permissions |
| ------ | ------------- |
| `admin` | Full access to all endpoints |
| `leader` | Plan, run, status, report, dashboard |
| `tester` | Run, status, report |
| `viewer` | Status, report, catalog |

Configure role tokens via `TAGENT_ADMIN_TOKENS`, `TAGENT_LEAD_TOKENS`, etc.

## Error Format

All errors return a consistent envelope:

```json

{
  "success": false,
  "data": null,
  "error": {
    "code": "AUTH_REQUIRED",
    "message": "Missing or invalid bearer token",
    "run_id": null
  }
}

```text

For execution errors, the message includes the `run_id` and log path for debugging:

```text

Internal error — run_id: abc123, logs: workspace/logs/abc123.log
Use --debug for verbose output.

```text
