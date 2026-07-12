# FebGrid Production Stabilization

FebGrid includes lightweight, dependency-free request timing for the public
application. It distinguishes network latency from warm application, database,
and provider latency without logging tenant data.

## Safe observability

FastAPI responses include:

- `X-Request-ID`, accepted from a safe client value or generated server-side.
- `Server-Timing`, with total application time and aggregate SQL query count/time.

The `febgrid.performance` logger emits one structured completion record with
method, route template, status, total duration, query count/time, and aggregate
durations for Groq, Supabase Auth, and the Java validator. It intentionally
excludes URLs, query strings, request/response bodies, identities, tokens,
headers, prompts, filenames, and provider payloads.

The frontend keeps the latest 100 safe endpoint timing records in memory and
emits `febgrid:api-timing` browser events. `getApiTimingSnapshot()` is available
for an authenticated browser QA session. Records contain endpoint paths without
query values, durations, response status, retry state, duplicate-in-flight state,
correlation ID, and the safe `Server-Timing` value. Nothing is sent to analytics.

## Hosting latency

Controlled public health measurements on July 11, 2026 showed:

| Service | First request | Warm request |
| --- | ---: | ---: |
| FastAPI | 22,212 ms | 263-281 ms |
| Java validator | 53,999 ms | 262 ms |

These measurements demonstrate hosting-platform startup time, not a warm
application regression. The frontend does not show hosting-plan or startup
notices. Safe GET requests receive at most one controlled retry for network or
502/503/504 failures. Mutations are never automatically retried.

The Java service is called only for bulk CSV preview. Normal login, dashboard,
single invitation, onboarding, and AI flows do not wake Java.

## Database pool controls

Optional server-only settings:

```text
DATABASE_POOL_SIZE=5
DATABASE_MAX_OVERFLOW=5
DATABASE_POOL_TIMEOUT_SECONDS=10
DATABASE_POOL_RECYCLE_SECONDS=300
```

Defaults are intentionally small for Render/Supabase. `pool_pre_ping` remains
enabled and sessions remain request-scoped. Do not place these variables in the
frontend and do not change the Supabase connection URL automatically.

## Invitation responsiveness

Single invite and resend responses are committed before FastAPI returns. The
frontend applies the returned invitation immediately, so the authorized dev/demo
acceptance link is available without waiting for a full admin workspace refresh.
Email delivery preparation remains a separate status in the response. Password
and Supabase exact-email magic-link acceptance continue to use the same server
invitation validation and tenant checks.

## Page-scoped loading and mutation updates

The public-beta frontend uses a route-specific data plan instead of loading the
entire company workspace on every page. The critical request sets are bounded:

| Page | Initial company-scoped requests |
| --- | --- |
| Dashboard | dashboard summary and unread count; employee labels and intelligence widgets load independently |
| Employees | employees, invitations, departments, teams, unread count |
| Teams | teams, departments, eligible employees, unread count |
| Projects | projects, employees, departments, teams, unread count |
| Work Objects | work objects and only the lookup data used by its form, plus unread count |
| Leaves | leaves, employees, unread count |

Independent requests in one plan run concurrently and optional failures are
reported per module. Settings, billing, file-pipeline, and AI-foundation data do
not load on ordinary operational pages.

Successful CRUD responses update only their affected local collection. Team,
department, project, work-object, leave, announcement, invitation, and employee
mutations do not trigger a full workspace refresh. Notification read state is
optimistic and rolls back on failure. Identical in-flight GETs share one network
request, and company/auth changes abort stale GETs without retrying the abort.

The frontend does not run a health polling interval. The `/api/v1/health`
traffic visible at a fixed cadence in hosting logs comes from the configured
deployment health check.

An isolated July 12, 2026 FastAPI + SQLite route probe used synthetic data and
the production request middleware to separate application and SQL time. These
numbers are local warm-path diagnostics, not claims about Render network time:

| Operation | Client ms | App ms | DB ms | Queries |
| --- | ---: | ---: | ---: | ---: |
| Create department | 13.17 | 11.36 | 0.28 | 5 |
| Create team | 46.49 | 44.98 | 0.29 | 6 |
| Create project | 40.73 | 38.93 | 0.41 | 8 |
| Create work object | 50.31 | 48.57 | 0.52 | 9 |
| Create leave | 55.25 | 53.87 | 0.79 | 12 |
| Create announcement | 14.43 | 13.03 | 0.53 | 11 |
| Deactivate employee | 8.22 | 6.69 | 0.19 | 4 |
| Read notification | 11.68 | 10.33 | 0.38 | 8 |
| Create invitation | 16.14 | 14.87 | 0.64 | 11 |
| Regenerate invitation link | 10.27 | 9.00 | 0.29 | 6 |

The probe also measured individual list endpoints at 7-8 ms and the dashboard
summary at 58.50 ms (54 aggregate queries). The dashboard route has since been
reworked to aggregate related counters once per domain instead of issuing one
query per counter. The route probe was deleted after
execution and left no synthetic database or upload artifact in the repository.

## July 12 focused stabilization

Production observations before this pass were approximately 10 seconds for the
warm dashboard, 4-5 seconds for standard mutations, and 25 seconds for the
Universal Timeline. The root causes found in code were remote-database
round-trip amplification:

- dashboard counters were each queried separately;
- create/update routes flushed the entity, flushed every Event, committed, and
  then refreshed an unexpired entity;
- the Events page blocked on timeline, audit, employees, and projects together;
- audit serialization performed actor, employee, and company lookups per row;
- the public invitation preview shared the active-workspace cancellation map.

The stabilization changes consolidate dashboard counts by domain, batch Event
writes into the owning transaction, remove unnecessary post-commit refreshes,
load 50 timeline events with stable keyset pagination, join audit enrichment,
and give invitation previews a page-owned public request scope. Company Pulse,
the AI executive brief, audit entries, and label lookups use widget-level or
section-level loading and cannot hold the critical dashboard/timeline shell.

Deployment verification must use `Server-Timing` and `X-Request-ID` to record
the actual Vercel-to-Render-to-Supabase result. Local checks prove query shape
and correctness but do not prove the production latency targets.

An isolated in-memory route-core probe after this pass measured:

| Operation | Route-core ms | SQL ms | Queries |
| --- | ---: | ---: | ---: |
| Create department | 2.90 | 0.13 | 2 |
| Create team (no optional references) | 1.71 | 0.09 | 2 |
| Dashboard summary | 69.57 | 2.76 | 18 |
| Timeline first 50 | 2.70 | 0.20 | 1 |
| Timeline next 50 | 2.66 | 0.15 | 1 |

The two timeline pages were newest-first, bounded, non-overlapping, and stable
for equal timestamps. These route-core numbers exclude authentication/network
latency. The temporary probe and synthetic database were removed immediately.
