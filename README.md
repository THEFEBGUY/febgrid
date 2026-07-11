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
- Sprint 9 Basic Dashboard polish with a tenant-safe live operational summary for employees, work, projects, leave, files, notifications, announcements, and recent events
- Health check, universal timeline, and basic operational search
- Sprint 10 AI foundation with tenant-safe AI job storage, provider-agnostic mock/Groq-ready mode, status lifecycle, events, and requester notifications
- Phase 2 Step 3 configuration foundation for company settings, industry templates v1, configurable work object types, and custom fields

Not included in Phase 1: billing, WhatsApp/SMS, advanced AI, MCP servers, enterprise dashboards, or production FebGuyAI.

## Stack

Frontend: React + Vite + TypeScript + Tailwind CSS  
Backend: Python + FastAPI  
Database: PostgreSQL / Supabase  
ORM: SQLAlchemy  
Migrations: Alembic  
Validation: Pydantic  
AI Layer: `ai_service.py` provider abstraction with mock mode by default and Groq as the first real provider option

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

AI provider configuration is optional for local development. Keep `AI_PROVIDER_MODE=mock` to avoid external calls. To test Groq later, set `AI_PROVIDER_MODE=groq`, configure `GROQ_API_KEY` locally, keep secrets out of source control, and enable external AI processing from the owner/admin Settings UI.

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

For a temporary Vercel + Render + Supabase college-demo deployment, follow
[College Demo Deployment](docs/College_Demo_Deployment.md). It preserves the
existing localhost flow, keeps the public demo Java validation endpoint behind
its server-only service key, and documents the optional exact-email Supabase
magic-link onboarding path.

Public-beta timing, safe request correlation, free-tier wake behavior, and the
small Supabase connection-pool defaults are documented in
[Production Stabilization](docs/FebGrid_Production_Stabilization.md).

The Phase 1 frontend includes the main dashboard shell, sidebar navigation, reusable table/card/badge UI, and pages for Dashboard, Companies, Employees, Teams, Projects, Work Objects, Leaves, Events, Announcements, and Notifications. Sprint 3 adds authenticated employee directory management, employee profile modals, status controls, department creation, and team creation. The project foundation adds create/edit project workflows, status and priority controls, project members, detail view, timeline, and linked work object readiness. Sprint 4 adds real work object CRUD, assignment, status and priority controls, project linkage, and detail timeline. Sprint 5 adds real leave submission, pending edits, approval/rejection/cancel decisions, and leave detail timeline. Sprint 6 adds work-object attachment upload, attachment list/download/delete actions, description edits, and file activity events. Notification v1 adds unread counts, mark read/unread, mark all read, dismiss, action links, and event timeline filtering. The Phase 1 communication layer adds comments to work-object/project detail views, simple employee mentions, internal announcements, communication events, and communication notifications. Sprint 9 turns the Dashboard into a real operational overview backed by `/api/v1/dashboard/summary`, with live cards, priority work, project health, leave attention, recent events, unread notifications, announcements, and quick actions.

Phase 2 begins with operational search/filtering and the configuration foundation. The Settings page lets owner/admin users update company settings, apply built-in industry templates, manage company-specific work object types, define simple custom fields for work object forms, review billing/file foundations, and run tenant-safe AI foundation jobs. AI defaults to mock mode; Groq can be enabled only with local environment configuration plus explicit company-level external-processing consent. Existing work objects keep their string `object_type`, while new configurable type records provide company-specific labels and defaults.

Layer 2 starts with rule-based operational intelligence. Company Pulse gives owner/admin users an explainable company health snapshot. Employee Digital Twin v1 gives permitted users a privacy-safe operational work profile for one employee at a time. It summarizes assigned work, project involvement, safe availability context, skills/tags, attention areas, risks, and recommended planning actions for 7, 30, or 90 day periods. Work DNA v1 analyzes company/project/team/department work-system patterns: work type mix, recurring work, overdue and blocked patterns, deadline pressure, workflow bottlenecks, metadata coverage, template candidates, and advisory process improvements. Work DNA is not an employee ranking, productivity score, surveillance tool, personality profile, or employment-decision system. Owner/admin users can generate company-wide Work DNA, project members/owners can access permitted project scope where backend rules allow it, and department scope is owner/admin-only until a safe manager mapping exists. The core is deterministic and rule-based; no Groq key or external AI call is required. Work DNA snapshots can be suggested into Company Memory through the existing suggested-to-approved review workflow and never create autonomous work changes. The owner/admin Dashboard includes a compact Layer 2 readiness section that links Company Pulse, Work DNA, Employee Digital Twin coverage, AI queue state, and Company Memory review counts without exposing those admin-level intelligence surfaces to employee POV.

Local uploaded files are stored under `backend/storage/uploads/` for development. That folder is ignored by Git and should not be committed.

## Alembic

Run migrations from the `backend` directory:

```powershell
python -m alembic upgrade head
```

## Bulk Employee Invite CSV

Bulk employee invitations keep FebGrid's Python backend as the authority for
company access, invitation creation, onboarding links, delivery preparation,
events, and notifications. The isolated Java service only parses and validates
CSV files during preview.

The flow is intentionally split:

```text
Employees page -> Python FastAPI (auth, tenant checks, invitation service)
               -> Java validator (CSV parsing and structural validation only)
```

For local development, start `java-bulk-invite-service` with a development-only
internal service key, then configure the matching runtime values described in
`.env.example` without committing them. The Employees page supports template
download, drag-and-drop CSV preview, explicit confirmation, partial outcomes,
formula-safe result export, and idempotency-safe retry. Existing single-invite
and manual activation flows remain unchanged.

For normal production deployment, keep the Java validator on an internal Docker
or private service network. The temporary free college-demo setup documented in
[College Demo Deployment](docs/College_Demo_Deployment.md) uses a public Render
web service instead, protected by the same dedicated service key. In either
case, it has no database, token, email, or FebGrid-user access. The Python
service calls it through `JAVA_BULK_INVITE_BASE_URL` with a matching
`JAVA_BULK_INVITE_SERVICE_KEY`. Local loopback exposure is suitable for
development only.

CSV limits are 2 MiB and 500 data rows. Required columns are `email`,
`full_name`, `job_title`, and `role`; the supported optional columns are
`department`, `team`, `manager_email`, `employment_type`, `phone`, and
`employee_code`. Download the current template from the Employees page rather
than maintaining a copied template.

College explanation: FebGrid is a polyglot application. Python FastAPI owns
authentication, permissions, tenant-aware employee data, invitation tokens,
email preparation, events, notifications, and transactions. The Java Spring
Boot service has one isolated responsibility: normalize and validate CSV rows
before Python rechecks live company data and invokes the same invitation service
used for an individual employee.

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
- `/dashboard/summary`
- `/departments`
- `/employees`
- `/employees/{employee_id}/digital-twin`
- `/invitations`
- `/companies/{company_id}/bulk-invites/template`
- `/companies/{company_id}/bulk-invites/preview`
- `/companies/{company_id}/bulk-invites/confirm`
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
- `/company-settings`
- `/industry-templates`
- `/work-object-types`
- `/custom-fields`
- `/ai/capabilities`
- `/ai/provider-status`
- `/ai/safety-settings`
- `/ai/jobs`
- `/ai-jobs` legacy compatibility surface
- `/company-pulse`
- `/work-dna`
- `/search`

Major create/update/status/approval/upload/comment/announcement actions record events for the universal timeline. Employee invitation and manual activation APIs store only token hashes, expose raw activation links only in one-time action responses, and use the email placeholder service rather than real provider delivery. Notification creation also records a `notification.sent` event and in-app notifications remain scoped to the current company and recipient. Phase 2 notification preferences include an email-alert placeholder in `backend/app/services/email_service.py`; real email provider delivery is intentionally not implemented yet.
