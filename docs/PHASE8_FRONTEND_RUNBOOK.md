# Phase 8 Frontend Runbook

## 1. Goal

This runbook covers the minimum local startup path for the new `Report Center + LLM Wiki` frontend workspace and the expected integration flow with the `openclaw` Skill.

## 2. Local Startup

### 2.1 Backend

Run the FastAPI service from the project root:

```powershell
python -m uvicorn backend.app.main:app --reload
```

### 2.2 Frontend Entry

The frontend is served by FastAPI as static files, so no separate Node process is required.

Open:

```text
http://127.0.0.1:8000/app/
```

Useful endpoints:

- `http://127.0.0.1:8000/docs`
- `http://127.0.0.1:8000/api/health`

## 3. Available Views

- `#/reports`
- `#/reports/{report_id}`
- `#/wiki`
- `#/wiki/{slug}`
- `#/ask`
- `#/tasks`
- `#/conflicts`
- `#/admin`

## 4. Admin Actions

The `/admin` view can directly trigger:

- `POST /api/sync`
- `POST /api/wiki/compile`
- `POST /api/wiki/lint`

This is the recommended local validation path after a new report is generated.

## 5. openclaw Skill Integration

Recommended Level 2 flow:

1. Skill writes raw capture files into `raw/`.
2. Skill writes normalized report markdown into `reports/YYYY/MM/`.
3. Trigger `POST /api/sync` to load reports into SQLite and FTS.
4. Trigger `POST /api/wiki/compile` with `mode=propose` or `mode=apply_safe`.
5. Review results in `/app/#/wiki`, `/app/#/tasks`, and `/app/#/conflicts`.

## 6. Delivery Notes

- The frontend is dependency-free and intentionally served from the backend to avoid CORS and extra dev orchestration.
- Search, query, writeback, task, and conflict views are all wired to the backend APIs implemented in earlier phases.
- The UI is intended as an MVP operations console, not a finalized design system.
