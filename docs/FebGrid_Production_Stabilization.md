# FebGrid Production Stabilization

FebGrid includes lightweight, dependency-free request timing for the temporary
public beta. It is designed to distinguish free-tier wake latency from warm
application, database, and provider latency without logging tenant data.

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

## Free Render behavior

Controlled public health measurements on July 11, 2026 showed:

| Service | First request | Warm request |
| --- | ---: | ---: |
| FastAPI | 22,212 ms | 263-281 ms |
| Java validator | 53,999 ms | 262 ms |

These measurements demonstrate platform wake time, not a warm application
regression. After six seconds, the frontend displays a non-blocking service-wake
message. Safe GET requests receive at most one controlled retry for network or
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
