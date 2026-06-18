# FebGrid Agent Instructions

## Product Identity

FebGrid is a Business Operating System, not just an HRMS or task management tool.

Core philosophy:
- Everything is a Work Object.
- Everything generates an Event.
- Everything is searchable.
- Everything is AI-readable.
- Everything contributes to Company Memory.

## Stack

Frontend:
- React
- TypeScript
- Vite
- Tailwind CSS

Backend:
- Python
- FastAPI
- PostgreSQL
- SQLAlchemy
- Alembic
- Pydantic

Database:
- PostgreSQL / Supabase

## Coding Rules

- Build clean, scalable, production-style code.
- Keep multi-company support from day one.
- Every major action must generate an Event.
- Do not hardcode secrets.
- Do not put API keys in frontend code.
- Use `.env` for secrets.
- Use UUIDs for main database IDs.
- Use `company_id` for tenant separation.
- Keep AI logic behind `ai_service.py`.
- Do not build FebGuyAI deeply in Phase 1.
- Phase 1 focuses on companies, employees, teams, projects, work objects, events, leaves, files, and notifications.

## First Build Priority

1. Backend base setup
2. Database models
3. Alembic migrations
4. Core CRUD APIs
5. Frontend base dashboard
6. Authentication
7. Universal timeline
8. Employee management
9. Work object engine
10. Leave system