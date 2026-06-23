# FebGrid

FebGrid is a Business Operating System built around Work Objects, Events, Company Memory, searchable operations, and an AI-readable foundation.

## Core Philosophy

- Everything is a Work Object.
- Everything generates an Event.
- Everything is searchable.
- Everything is AI-readable.
- Everything contributes to Company Memory.

## Phase 1 Scope

Phase 1 focuses on the backend foundation:

- FastAPI application setup
- PostgreSQL / Supabase database connection
- SQLAlchemy models with UUID primary keys and `company_id` tenant separation
- Alembic migrations
- CRUD APIs for companies, employees, teams, projects, work objects, leave requests, attachments, notifications, events, and AI jobs
- Sprint 3 employee management foundation for departments, teams, employee profiles, employee status, and tenant-aware people operations
- Phase 1 project management foundation for project ownership, members, status, priority, progress, timeline, and linked work object lists
- Sprint 4 Work Object Engine v1 for tenant-safe work creation, assignment, status/priority tracking, project linkage, detail timeline, and dashboard work counts
- Sprint 5 Leave Management v1 for tenant-safe leave requests, pending review, approval/rejection/cancel flows, leave events, and dashboard leave counts
- Sprint 6 File Upload v1 for tenant-safe work-object attachments, local development storage, download/delete flow, file events, and attachment search metadata
- Notification v1 and Event Stream Polish for tenant-safe in-app notifications, unread/read/dismiss actions, unread counts, and a reliable universal timeline
- Phase 1 Communication Layer foundation for tenant-safe work-object/project comments, simple employee mentions, internal announcements, communication events, and in-app notifications
- Health check, universal timeline, and basic operational search
- Mock-only AI boundary in `backend/app/services/ai_service.py`

Not included in Phase 1: billing, WhatsApp/SMS, advanced AI, MCP servers, enterprise dashboards, or production FebGuyAI.

## Stack

Frontend: React + Vite + TypeScript + Tailwind CSS  
Backend: Python + FastAPI  
Database: PostgreSQL / Supabase  
ORM: SQLAlchemy  
Migrations: Alembic  
Validation: Pydantic  
AI Layer: `ai_service.py` mock abstraction

## Backend Setup

Create your local environment file from the documented template:

```powershell
Copy-Item .env.example .env
```

Fill in `DATABASE_URL` and other local values in `.env`. Do not commit `.env`.

Install and run the backend:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m alembic upgrade head
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The API will be available at:

- Health: `GET http://127.0.0.1:8000/api/v1/health`
- Docs: `http://127.0.0.1:8000/docs`

`DATABASE_URL` may use either `postgresql://...` or `postgresql+psycopg://...`; the backend normalizes plain PostgreSQL URLs to the psycopg v3 SQLAlchemy driver internally.

For local auth, set a development value for `JWT_SECRET_KEY`. If it is omitted, the backend uses a process-local development signing key and existing sessions are invalidated when the server restarts.

## Frontend Setup

Install and run the React dashboard from the `frontend` directory:

```powershell
cd frontend
npm install
npm run dev
```

The frontend reads the backend URL from `VITE_API_BASE_URL`. The documented default in `.env.example` is:

```text
VITE_API_BASE_URL=http://localhost:8000
```

The Phase 1 frontend includes the main dashboard shell, sidebar navigation, reusable table/card/badge UI, and pages for Dashboard, Companies, Employees, Teams, Projects, Work Objects, Leaves, Events, Announcements, and Notifications. Sprint 3 adds authenticated employee directory management, employee profile modals, status controls, department creation, and team creation. The project foundation adds create/edit project workflows, status and priority controls, project members, detail view, timeline, and linked work object readiness. Sprint 4 adds real work object CRUD, assignment, status and priority controls, project linkage, detail timeline, and light dashboard work metrics. Sprint 5 adds real leave submission, pending edits, approval/rejection/cancel decisions, leave detail timeline, and light dashboard leave metrics. Sprint 6 adds work-object attachment upload, attachment list/download/delete actions, description edits, and file activity events. Notification v1 adds unread counts, mark read/unread, mark all read, dismiss, action links, and event timeline filtering. The Phase 1 communication layer adds comments to work-object/project detail views, simple employee mentions, internal announcements, communication events, and communication notifications.

Local uploaded files are stored under `backend/storage/uploads/` for development. That folder is ignored by Git and should not be committed.

## Alembic

Run migrations from the `backend` directory:

```powershell
python -m alembic upgrade head
```

Create future migrations after model changes:

```powershell
python -m alembic revision --autogenerate -m "describe change"
```

## API Surface

All Phase 1 endpoints are mounted under `/api/v1`.

- `/auth/register`
- `/auth/login`
- `/auth/logout`
- `/auth/me`
- `/companies`
- `/departments`
- `/employees`
- `/teams`
- `/projects`
- `/work-objects`
- `/leaves`
- `/attachments`
- `/uploads`
- `/files`
- `/events`
- `/timeline`
- `/notifications`
- `/comments`
- `/announcements`
- `/ai-jobs`
- `/search`

Major create/update/status/approval/upload/comment/announcement actions record events for the universal timeline. Notification creation also records a `notification.sent` event and in-app notifications remain scoped to the current company and recipient.
