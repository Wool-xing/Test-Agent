# API Overview

Test-Agent V2 exposes a FastAPI backend with bearer authentication, RBAC, and CORS-restricted access. The API server runs on `http://localhost:8000` by default.

## Authentication

Set `TAGENT_API_AUTH_TOKEN` in your `.env` to enable bearer auth:

```bash
TAGENT_API_AUTH_TOKEN=your-secret-token
```

All endpoints (except `/health`) require `Authorization: Bearer <token>`.

## Core Endpoints

### Health Check

```
GET /health
```

Returns 200 when the server is running. No auth required.

### Catalog

```
GET /catalog
Authorization: Bearer <token>
```

Returns the full expert agent and skill catalog:

```json
{
  "experts": [...],
  "skills": [...],
  "counts": { "experts": 16, "skills": 32 }
}
```

### Plan

```
POST /plan
Authorization: Bearer <token>
Content-Type: application/json

{
  "prd_path": "path/to/prd.md",
  "options": { "mode": "comprehensive" }
}
```

Returns a test plan with task list and DAG structure.

### Run

```
POST /run
Authorization: Bearer <token>
Content-Type: application/json

{
  "prd_path": "path/to/prd.md"
}
```

Executes the full pipeline and returns a run ID for status polling.

### Status

```
GET /status/{run_id}
Authorization: Bearer <token>
```

Returns execution status, progress, and any failures.

### Dashboard

```
GET /dashboard
Authorization: Bearer <token>
```

Returns the observability dashboard with three sections:

- **Decision**: Pass rate, trends, MTTD/MTTR
- **Diagnostic**: Expert heatmap, flaky candidates, environment health
- **Actions**: P0/P1 action items

### Report

```
GET /report/{run_id}
Authorization: Bearer <token>
```

Returns the full test report in JSON format.

## RBAC

When `TAGENT_RBAC_ENABLED=1`, endpoints are gated by role:

| Role | Permissions |
|------|-------------|
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
```

For execution errors, the message includes the `run_id` and log path for debugging:

```
Internal error — run_id: abc123, logs: workspace/logs/abc123.log
Use --debug for verbose output.
```
