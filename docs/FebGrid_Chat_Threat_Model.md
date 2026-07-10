# FebGrid Chat Threat Model

## Overview

This document is the Phase 4.5 threat model for the proposed FebGrid Chat
communication layer. It covers planned Chat surfaces only. Chat is not yet
implemented in the production backend, database, routing, sidebar, or UI.

FebGrid is a multi-company business operating system. Its current application
patterns already make company ownership, role checks, Events, Notifications,
and attachment permissions first-class concerns. Chat must preserve those
properties while adding two intentionally different communication modes:

- `private_e2ee`: direct messages and private groups. The server persists
  ciphertext and operating metadata only; participants decrypt locally.
- `managed_secure`: company, department, team, and project channels. The
  service can read content for the explicitly documented managed-channel
  features, but remains tenant and membership scoped.

This is not a production E2EE security claim. The cryptographic-library
decision is recorded separately in `docs/FebGrid_Chat_Crypto_ADR.md`.

## Threat Model, Trust Boundaries, and Assumptions

### Assets and security objectives

The most important assets are:

1. Private E2EE plaintext, message keys, identity keys, group state, and
   encrypted attachment keys.
2. Company boundaries, conversation membership, and employee discovery
   privacy.
3. Managed-channel messages, attachments, reports, and retention data.
4. Chat metadata: participant identities, timestamps, membership changes,
   delivery state, device state, and ciphertext sizes.
5. Chat connect codes, authenticated sessions, realtime authorization tokens,
   rate-limit state, and audit records.

The primary invariants are:

- Every Chat record has exactly one `company_id`; a valid identifier from
  another company reveals neither data nor existence.
- A conversation member may receive or submit only data for an active
  membership in that exact company and conversation.
- Private keys and per-file keys remain client-side. They are never sent to
  FastAPI, PostgreSQL, Supabase, storage, Events, Notifications, search, AI,
  Company Memory, Company Pulse, Work DNA, or Digital Twin.
- Conversation security mode is visible and immutable. A new conversation is
  required to change modes.
- Chat references do not grant permission to the referenced FebGrid entity.
- A deactivated employee, revoked device, or removed member loses future
  command, history, attachment, and realtime access promptly.

### Trust boundaries

| Boundary | Trusted responsibilities | Must not be trusted with |
| --- | --- | --- |
| Browser device | Local plaintext, private keys, E2EE state, local search | Other users, other companies, arbitrary page scripts |
| FastAPI command and history API | Authentication, company/membership authorization, idempotency, rate limits, ciphertext persistence | Private E2EE plaintext or keys |
| PostgreSQL/Supabase | Tenant-scoped records, ciphertext, managed-channel content, RLS enforcement | E2EE decryption or chat authorization by identifier alone |
| Realtime transport | Minimal authorized events, presence, typing, reconnect signalling | Authorization inferred only from a topic name |
| Object storage | Ciphertext/private attachment blobs or authorized managed attachments | Private file keys or local paths |
| Existing FebGrid intelligence systems | Explicitly approved operational data | Any private Chat content, metadata analytics, or plaintext |
| Owner/admin | Company policy and managed-channel administration | E2EE keys or E2EE plaintext |

### Actors and assumptions

- A normal employee may control browser input, identifiers, API payloads,
  websocket/realtime topics, retries, and local storage on their own device.
- A malicious employee may be a former member, have a stale session, or try
  to enumerate company employees or brute-force discovery codes.
- A malicious company administrator is trusted to manage policy but is not a
  private-conversation participant by default.
- A network attacker can observe or modify traffic outside TLS but cannot
  break modern TLS. E2EE additionally protects private content from the
  application server.
- A compromised browser, malicious extension, or XSS can access plaintext
  while it is displayed. E2EE does not protect a compromised endpoint.
- Platform operators and database administrators are outside the private E2EE
  trust boundary and must not have a decryption path.

## Attack Surface, Mitigations, and Attacker Stories

### Company and object authorization

Existing FebGrid service patterns use `ensure_company_access`, company-scoped
queries, and role checks. Chat must use the same backend-enforced pattern on
every command, list, history, attachment, device, invitation, and source-link
operation. Database RLS is defense in depth, not a replacement for FastAPI
authorization.

| Threat | Attack story | Required control |
| --- | --- | --- |
| Cross-company IDOR | Change conversation, message, attachment, invitation, device, or employee UUID | `company_id` plus active membership predicate on every query; generic 404/403 without existence leakage |
| Membership bypass | Removed member fetches history, sends a receipt, opens an attachment, or remains subscribed | Active membership check at command, history, download, and subscription time; revoke sessions and realtime state on removal |
| Realtime topic forgery | Client subscribes to a guessed topic or retains a stale token after a company switch | Private topics only, RLS authorization against membership, short-lived token/session version, explicit disconnect/revoke on removal |
| Replay/duplicate messages | Re-submit a captured envelope or retry after a timeout | Client UUID plus idempotency key unique per company/conversation; protocol replay protection and server sequence assignment |
| Stale employee/device | Deactivated employee or revoked device submits commands | Auth active-state check, device status check, membership sync, key-package revocation, and group rekey workflow |

### Privacy and cryptography

| Threat | Attack story | Required control |
| --- | --- | --- |
| Server plaintext exposure | Private message or attachment arrives unencrypted at API/storage | Browser-only encryption with a reviewed protocol library; accept E2EE envelopes/ciphertext only; redaction tests for DB, logs, Events, notifications, AI, and search |
| Mode confusion | UI labels a managed channel as E2EE or silently downgrades mode | Immutable `security_mode`, distinct visual indicators, server validation, and no conversion endpoint |
| Malicious admin access | Owner/admin joins or exports an employee DM | No admin membership bypass, no key escrow, no private plaintext search/export, and metadata minimization |
| Lost/stolen device | Stolen browser keeps reading future messages | Device revocation, expiration of public bundles, security notices, group rekey, and honest UI warning that past plaintext cannot be remotely erased |
| Key backup abuse | Backup becomes company escrow | Initial policy is no backup; any later encrypted backup requires a user-held recovery secret and separate review |

### Discovery, abuse, and availability

| Threat | Attack story | Required control |
| --- | --- | --- |
| Employee enumeration | Search names/handles or connect codes across companies | Company-scoped directory, discovery modes, generic errors, no cross-company result, and hidden profiles excluded |
| Connect-code brute force | Guess a code for an exact handle | Rotatable slow-hashed code, per-requester/IP/target limits, exponential cooldown, lockout, generic failure, and abuse audit without code values |
| Spam and resource exhaustion | Flood messages, typing, receipts, key bundle requests, or uploads | Rate limits, quotas, payload limits, cursor pagination, bounded connection limits, and backpressure |
| Attachment abuse | Upload executable, oversized, or malicious content | Mode-specific type/size controls, attachment downloads, isolated previews, content-disposition attachment, and no automatic execution |

### Browser, supply chain, and integrations

| Threat | Attack story | Required control |
| --- | --- | --- |
| XSS steals displayed plaintext | Untrusted managed content or dependency injects script | Strict CSP, no unsafe HTML rendering, safe text rendering/sanitization, dependency pinning, lockfile review, no dynamic code execution |
| Dependency compromise | Crypto or frontend package is replaced | Exact version pinning, integrity lockfile, dependency review, source provenance, vulnerability monitoring, and focused crypto review |
| AI/intelligence leakage | Private content reaches Groq, search, Pulse, Memory, Work DNA, or Twin | Explicit deny-by-default data contracts and tests; no private-Chat adapter in intelligence services |
| Entity reference escalation | Chat link lets recipient open a work object/file they cannot access | Reference carries only safe label/type/ID; normal target API rechecks permission |

### Required data minimization

Private E2EE metadata is limited to the operational minimum: company,
conversation, participant and sender-device IDs, timestamps, ciphertext size,
delivery state, encrypted attachment metadata, and membership/security events.
It excludes plaintext, message/file keys, safety numbers, connect codes, private
report evidence, raw ciphertext in routine Events, detailed presence history,
and private keyword analytics.

Managed channels may store readable content only for their documented
company-managed features. They still must not automatically feed AI, Company
Memory, Company Pulse, Work DNA, Digital Twin, or employee-performance
analytics.

## Severity Calibration

### Critical

- Cross-company history, attachment, device, or realtime subscription access.
- A server, owner/admin, or AI service can recover E2EE plaintext or private
  keys.
- A security-mode downgrade exposes E2EE content as managed content.

### High

- A removed member receives new private-group messages because rekey/realtime
  revocation failed.
- XSS or a compromised dependency can access active private plaintext.
- Connect-code brute force permits targeted employee discovery at scale.
- Replay/idempotency failures create materially different private messages.

### Medium

- Excess metadata retention exposes communication patterns beyond operating
  necessity.
- Managed-content sanitization allows non-executable but misleading entity
  references.
- Rate-limit gaps let a company member create local availability degradation.

### Low

- A safe error message is not sufficiently descriptive for a permitted user.
- A non-sensitive timestamp or generic conversation label is displayed with an
  inconsistent UI state but does not cross a tenant or membership boundary.

## Step 0 Security Gates

Before any Step 1 schema implementation, the following gates must be approved:

1. Select a browser-ready, maintained, reviewed protocol library with an
   acceptable license and documented multi-device/group lifecycle API.
2. Run official/basic vectors plus browser tests for device registration,
   asynchronous session setup, out-of-order handling, add/remove/rekey, and
   private-key non-transmission.
3. Review the FastAPI, RLS, realtime, storage, CSP, and incident-response
   designs against this document.
4. Confirm no production page claims E2EE until an independent focused crypto
   review is complete.

Repository: FebGrid
Version: 887aec6766ba409e7c04778b286a5354e401746d
