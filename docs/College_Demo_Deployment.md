# College Demo Deployment

This guide prepares a short-lived FebGrid demo without changing local runtime
behavior. It does not deploy anything automatically.

## Architecture

```text
Browser -> Vercel (React/Vite) -> Render web service (FastAPI) -> Supabase
                                      |
                                      +-> Render public web service (Java CSV validator)
```

For this temporary free demo, the Java validator is a public Render web
service. Its validation endpoint remains protected by the required
`X-FebGrid-Service-Key`; do not publish the service key, and do not put it in
Vercel. FastAPI calls the validator over its HTTPS `onrender.com` URL.

## Environment variables

### Vercel frontend

Only browser-safe values belong here:

```text
VITE_API_BASE_URL=https://<your-fastapi-service>.onrender.com
VITE_SUPABASE_URL=https://<your-project-ref>.supabase.co
VITE_SUPABASE_ANON_KEY=<Supabase publishable/anon key>
```

Do not add `DATABASE_URL`, `JWT_SECRET_KEY`, Java service keys, Supabase
service-role keys, Groq keys, or any other backend secret to Vercel.

### Render FastAPI web service

```text
ENVIRONMENT=production
DATABASE_URL=<existing Supabase Postgres connection string>
DATABASE_POOL_SIZE=5
DATABASE_MAX_OVERFLOW=5
DATABASE_POOL_TIMEOUT_SECONDS=10
DATABASE_POOL_RECYCLE_SECONDS=300
JWT_SECRET_KEY=<new random server-only value>
PUBLIC_APP_URL=https://<your-vercel-production-domain>
CORS_ORIGINS=https://<your-vercel-production-domain>,http://localhost:5173
SUPABASE_URL=https://<your-project-ref>.supabase.co
SUPABASE_ANON_KEY=<Supabase publishable/anon key>
SUPABASE_SERVICE_ROLE_KEY=<server-only Supabase service-role key>
SUPABASE_AUTH_TIMEOUT_SECONDS=10
SUPABASE_STORAGE_BUCKET=work-files
SUPABASE_STORAGE_TIMEOUT_SECONDS=30
JAVA_BULK_INVITE_BASE_URL=https://<your-java-validator-service>.onrender.com
JAVA_BULK_INVITE_SERVICE_KEY=<random value shared only with Java>
JAVA_BULK_INVITE_TIMEOUT_SECONDS=20
BULK_INVITE_MAX_ROWS=500
BULK_INVITE_MAX_FILE_BYTES=2097152
AI_PROVIDER_MODE=mock
AI_EXTERNAL_PROCESSING_ENABLED=false
AI_JOB_WORKER_ENABLED=true
AI_JOB_WORKER_POLL_SECONDS=2
AI_JOB_LEASE_SECONDS=600
```

`PUBLIC_APP_URL` is the sole source of generated acceptance links. Its local
default remains `http://localhost:5173`, so local invite links keep working.

The existing `work-files` Supabase Storage bucket must remain **private**. Set
`SUPABASE_SERVICE_ROLE_KEY` only on the FastAPI Render service; never add it to
Vercel or any `VITE_*` variable. FebGrid streams authorized file downloads and
previews through FastAPI, so it does not need public bucket access or persistent
local upload storage.

### Render Java validator web service

```text
FEBGRID_INTERNAL_SERVICE_KEY=<same random value as FastAPI>
BULK_INVITE_MAX_ROWS=500
BULK_INVITE_MAX_FILE_BYTES=2097152
```

Render injects `PORT`; the Java service respects it. The service key protects
the validation route, but this public-service arrangement is for a temporary
college demo only. Rotate the shared key after the demo and use a private
service for any paid or long-lived deployment.

## Vercel setup

1. Import the repository and set **Root Directory** to `frontend`.
2. Framework preset: Vite. Build command: `npm run build`. Output directory:
   `dist`.
3. Add the three frontend variables above for Production (and Preview only if
   a matching Supabase redirect URL is configured).
4. Keep `frontend/vercel.json`; it rewrites `/accept-invite/<token>` to the
   SPA so the existing onboarding route survives a direct magic-link redirect.
5. Copy the final production Vercel URL into Render as `PUBLIC_APP_URL` and
   into the Supabase URL configuration before inviting anyone.

## Render setup

The included `render.yaml` is intentionally inert (`autoDeployTrigger: off`)
and prompts for secret values. Create both services from the same repository,
workspace, and region:

1. **FastAPI**: deploy as a Docker **Web Service** using
   `backend/Dockerfile`; health path is `/api/v1/health`.
2. Set the FastAPI environment values above. Free web services cannot use a
   paid-only pre-deploy command or Render shell access, so run the migration
   manually from a secure local backend environment before this deploy:

   ```powershell
   cd backend
   # Provide the production DATABASE_URL only through your secure shell/session.
   python -m alembic upgrade head
   ```

   Do not add the production URL to `.env`, source control, or frontend
   variables.
3. **Java validator**: deploy as a Docker **Web Service** using
   `java-bulk-invite-service/Dockerfile`, choose the **Free** instance type,
   and set its service key. Copy its public HTTPS URL into
   `JAVA_BULK_INVITE_BASE_URL` on FastAPI.
4. Verify FastAPI `GET /api/v1/health` and Java
   `GET /internal/v1/health`. The Java health response must not reveal keys or
   configuration; the validation endpoint must reject a missing/wrong service
   key.

Both services use Render's Free web-service tier. They can spin down after
idle time and can take about a minute to wake, so the first bulk-preview or API
request may be slow. Free instances have no persistent disk or Render shell
access; FebGrid continues to use Supabase for persistent data.

FebGrid shows a non-blocking wake message when a request exceeds six seconds.
Safe GET requests may retry once after a transient network/502/503/504 response;
mutations are never retried automatically. Use the response `Server-Timing` and
`X-Request-ID` headers to separate Render wake time from application/database
time without exposing request data.

## Supabase magic-link configuration

In **Authentication -> URL Configuration**:

1. Set **Site URL** to `https://<your-vercel-production-domain>`.
2. Add exact Redirect URLs:
   - `http://localhost:5173/accept-invite/**`
   - `https://<your-vercel-production-domain>/accept-invite/**`
3. Add preview patterns only when necessary, for example
   `https://*-<your-vercel-team>.vercel.app/accept-invite/**`.
4. In **Authentication -> Providers -> Email**, keep passwordless email/magic
   links enabled for the demo and confirm the project email rate limit is
   suitable for the small invited test group.

The onboarding page sends a magic link only to the invitation's read-only
email. After redirect, FastAPI calls Supabase Auth's user endpoint with the
user access token and checks the verified email against the invitation before
accepting it. It also checks the token, invitation company, status, and expiry
through the existing invitation service. A Supabase session for any other email
cannot accept the invitation.

For the demo-only owner/admin workflow, the existing Employees page continues
to show the generated acceptance link only in the authorized invite action
result. It is never persisted in invitation metadata or returned by list APIs.

## Deployment order

1. Run the manual Alembic migration against the existing Supabase database
   from a secure local backend environment.
2. Deploy the Java validator as a free public web service and copy its HTTPS
   URL to FastAPI.
3. Deploy FastAPI, verify health and CORS from the Vercel domain.
4. Configure Supabase Site URL/redirect URLs.
5. Set Vercel public variables and deploy frontend.
6. Create one owner-authorized test invitation; verify copy link, password
   onboarding, and magic-link onboarding with the exact invited email.

## Readiness checklist

- `PUBLIC_APP_URL` is the Vercel production URL, not the Render API URL.
- `CORS_ORIGINS` includes only intended frontend origins.
- The Java public validator URL is configured only in FastAPI, never Vercel.
- A request without the Java service key is rejected before CSV validation.
- Supabase redirect URLs include the exact invite path.
- The backend and Java service keys are distinct random values and are set only
  in Render.
- The frontend contains only `VITE_*` public configuration.
- Local `.env` has not been changed and localhost flow is still verified.
