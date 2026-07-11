# College Demo Deployment

This guide prepares a short-lived FebGrid demo without changing local runtime
behavior. It does not deploy anything automatically.

## Architecture

```text
Browser -> Vercel (React/Vite) -> Render web service (FastAPI) -> Supabase
                                      |
                                      +-> Render private service (Java CSV validator)
```

The Java service has no public URL. Keep the FastAPI and Java Render services
in the same workspace and region, then use the Java service's **Internal**
address from Render's Connect panel for `JAVA_BULK_INVITE_BASE_URL`.

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
JWT_SECRET_KEY=<new random server-only value>
PUBLIC_APP_URL=https://<your-vercel-production-domain>
CORS_ORIGINS=https://<your-vercel-production-domain>,http://localhost:5173
SUPABASE_URL=https://<your-project-ref>.supabase.co
SUPABASE_ANON_KEY=<Supabase publishable/anon key>
SUPABASE_AUTH_TIMEOUT_SECONDS=10
JAVA_BULK_INVITE_BASE_URL=http://<Render Java Internal address>
JAVA_BULK_INVITE_SERVICE_KEY=<random value shared only with Java>
JAVA_BULK_INVITE_TIMEOUT_SECONDS=20
BULK_INVITE_MAX_ROWS=500
BULK_INVITE_MAX_FILE_BYTES=2097152
AI_PROVIDER_MODE=mock
AI_EXTERNAL_PROCESSING_ENABLED=false
```

`PUBLIC_APP_URL` is the sole source of generated acceptance links. Its local
default remains `http://localhost:5173`, so local invite links keep working.

### Render Java private service

```text
FEBGRID_INTERNAL_SERVICE_KEY=<same random value as FastAPI>
BULK_INVITE_MAX_ROWS=500
BULK_INVITE_MAX_FILE_BYTES=2097152
```

Render injects `PORT`; the Java service now respects it. Do not publish the
Java validator as a public web service.

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
2. Set the FastAPI environment values above. The included Blueprint uses
   `backend` as its root directory and runs `python -m alembic upgrade head`
   as its pre-deploy command. Render documents pre-deploy commands as the
   supported migration path for paid web/private services.
3. **Java validator**: deploy as a Docker **Private Service** using
   `java-bulk-invite-service/Dockerfile`. Set its service key, then copy the
   private HTTP address into the FastAPI environment.
4. Verify FastAPI `GET /api/v1/health` and Java
   `GET /internal/v1/health` from the FastAPI private network only.

Render private services require a paid instance type. If the demo budget cannot
use one, do not expose the Java validator publicly; leave bulk invite disabled
and use existing single employee invitations instead.

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

1. Run migrations against the existing Supabase database from the FastAPI
   deployment configuration.
2. Deploy the Java private validator and copy its internal address to FastAPI.
3. Deploy FastAPI, verify health and CORS from the Vercel domain.
4. Configure Supabase Site URL/redirect URLs.
5. Set Vercel public variables and deploy frontend.
6. Create one owner-authorized test invitation; verify copy link, password
   onboarding, and magic-link onboarding with the exact invited email.

## Readiness checklist

- `PUBLIC_APP_URL` is the Vercel production URL, not the Render API URL.
- `CORS_ORIGINS` includes only intended frontend origins.
- The Java service has an Internal address and no public endpoint.
- Supabase redirect URLs include the exact invite path.
- The backend and Java service keys are distinct random values and are set only
  in Render.
- The frontend contains only `VITE_*` public configuration.
- Local `.env` has not been changed and localhost flow is still verified.
