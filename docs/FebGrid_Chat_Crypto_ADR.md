# ADR: FebGrid Secure Chat Architecture and Cryptography Feasibility

- Status: CONDITIONAL GO with Matrix for feasibility; NO-GO for Step 1 pending integration and review gates
- Date: 2026-07-10
- Scope: Phase 4.5 Steps 0, 0.1, and 0.2 only
- Decision owner: FebGrid engineering and security review

## Context

FebGrid requires company-scoped realtime communication with two materially
different security modes:

| Mode | Intended use | Server content access | Search and AI policy |
| --- | --- | --- | --- |
| `private_e2ee` | DMs and private groups | Ciphertext and operating metadata only | Local search only; excluded from AI, Memory, Pulse, Work DNA, and Twin |
| `managed_secure` | Company, department, team, and project channels | Authorized server-readable content | Permission-scoped managed search may be added later; AI remains opt-in and out of scope |

The mode is immutable. Moving between modes creates a new conversation with a
visible transition notice. No company administrator, manager, HR user, or
FebGrid operator receives a private-conversation decryption path.

## Architecture Decision

The original MLS-library direction remains a **NO-GO**: no browser MLS binding
evaluated in Step 0 satisfied FebGrid's maintenance, lifecycle, and review
requirements. Step 0.1 changes the candidate, not that conclusion.

The leading architecture is now Matrix E2EE using the maintained
`matrix-js-sdk` browser client and its official Matrix Rust/WASM crypto stack.
This is a provider architecture decision only. It does not authorize production
Chat schema, routes, or UI yet, and FebGrid will not implement or modify
cryptographic algorithms itself.

The current decision is **CONDITIONAL GO with Matrix**. Matrix meets the
browser bundling, maintained-library, local crypto-storage, and licensing
feasibility checks in this spike. Step 1 remains blocked until the explicit
homeserver, identity, lifecycle, isolation, and review gates in this ADR pass.

The managed-channel architecture is still viable, but it must not be separated
from the final tenant, realtime, and security-mode data contract without those
gates.

## Company Control Policy

Company owner/admin users may enable or disable Chat and its managed feature
flags: direct requests, private groups, organizational channels, attachments,
presence, receipts, editing, deletion, discovery, retention, and rollout.
They may delegate `manage_chat_settings` explicitly. Managers, HR users, and
employees are blocked by default unless that explicit delegation exists.

No company policy may provide a private key, private attachment key, E2EE
plaintext export, private plaintext search, silent private-group membership, or
security-mode conversion. Disabling Chat stops new Chat commands and realtime
subscriptions but cannot promise remote deletion of plaintext already stored on
an offline participant device.

## Candidate Evaluation

| Candidate | Evidence | Feasibility result | Decision |
| --- | --- | --- | --- |
| `@signalapp/libsignal-client@0.96.4` | Official Signal package; native Node bindings; AGPL-3.0-only | Imports in Node. It is not a browser/WASM package, Signal states external use is unsupported, and its license requires legal review. | Reject for FebGrid browser Chat. |
| `openmls-wasm@0.1.0` | Published by the OpenMLS project under MIT | Isolated test created a group, added/joined a member, and encrypted/decrypted a message in 71.48 ms. Package README calls it an experiment; no member removal/out-of-order API was exposed; Node warns WASM import is experimental. | Reject for production; useful only as spike evidence. |
| OpenMLS `v0.8.1` | Maintained Rust MLS implementation under MIT | The upstream project has a WASM build feature, but its official support table lists WASM as built but not tested. This workstation lacks Rust/wasm-pack. | Candidate for a future dedicated browser/WASM evaluation only. |
| AWS `mls-rs` | Maintained Rust MLS implementation under Apache-2.0 or MIT | Supports WASM builds and RFC 9420 test vectors, but its own security notice says it has not had a full third-party audit; its Web Crypto provider is not a supported path. | Not approved for browser deployment. |

Primary sources reviewed:

- Signal libsignal: https://github.com/signalapp/libsignal
- OpenMLS: https://github.com/openmls/openmls
- AWS mls-rs: https://github.com/awslabs/mls-rs
- MLS protocol: https://www.rfc-editor.org/rfc/rfc9420.html
- MLS architecture: https://www.rfc-editor.org/rfc/rfc9750.html
- Supabase Realtime authorization: https://supabase.com/docs/guides/realtime/authorization

## Matrix E2EE Feasibility Spike (Step 0.1)

### Candidate and browser prototype

The isolated prototype lives in `prototypes/matrix-e2ee-spike/`. It is not
imported by the FebGrid frontend or backend, contains no FebGrid credentials,
and uses the reserved `matrix.invalid` domain only. Its final browser run makes
no homeserver request, device-registration request, or key export.

| Component | Version evaluated | Evidence | Result |
| --- | --- | --- | --- |
| `matrix-js-sdk` | `41.9.0` | Element-maintained Matrix JavaScript SDK, Apache-2.0 | Vite production build and browser construction passed. |
| `@matrix-org/matrix-sdk-crypto-wasm` | `18.3.1` | Official Matrix Rust/WASM crypto package, Apache-2.0 | WASM initialized in a browser and reopened an explicit IndexedDB store after refresh. |
| Matrix Rust SDK | upstream maintained SDK | Official Rust implementation used by Matrix clients | Viable maintained crypto implementation; no custom protocol code is proposed. |
| Synapse homeserver | current supported Linux deployment | Official Matrix homeserver | Not run locally: this workstation has no Docker/WSL and Python 3.14 is outside Synapse's documented Python range. |

The Vite production build completed with the Rust/WASM asset at 5,573,870
bytes (about 5.31 MiB, 1.77 MiB gzip). The Matrix JavaScript chunks totalled
about 1.09 MiB before gzip. This is material initial-load cost and must be
lazy-loaded only after a user opens Chat; it must never be included in the
normal FebGrid dashboard bundle.

The prototype deliberately uses `OlmMachine.initialize` with a named store for
the no-homeserver browser check. The official `MatrixClient.initRustCrypto`
path also uses IndexedDB, but it performs a server key-backup check during
initialization, so it is only appropriate once a real homeserver exists. A
production integration must use `MatrixClient.initRustCrypto` and must not
copy the prototype's direct-machine wiring into application code.

### Required test matrix

| Required Step 0.1 check | Result | Evidence or blocker |
| --- | --- | --- |
| Vite/browser build | Passed | Production Vite build completed and loaded the official Rust/WASM asset. |
| Browser IndexedDB crypto storage | Passed locally | Explicit named Matrix crypto store opened and reopened after browser refresh. |
| Two synthetic users | Blocked | Requires a supported local homeserver. |
| Encrypted room creation | Blocked | Requires a homeserver and authenticated Matrix accounts. |
| Encrypted send/decrypt | Blocked | Requires encrypted-room lifecycle and sync events. |
| Invite/join | Blocked | Requires server-side room membership operations. |
| Device registration | Blocked | Requires the final FebGrid-to-Matrix account/login bridge. |
| Refresh and encrypted-state recovery | Partial | IndexedDB store reopen passed; recovery of real Megolm sessions still needs the live room test. |
| Second-device feasibility | Design feasible, unverified | Matrix supports multi-device/cross-signing flows; verify real device verification and key sharing. |
| Member removal/future-message denial | Blocked | Must verify room membership enforcement and outbound-session rotation after removal. |
| Attachment encryption | Protocol-supported, unverified | Matrix encrypted attachments store ciphertext in media and the file key inside encrypted event content; live upload/download test is required. |
| Room/company isolation | Design only | Requires the tenancy topology and negative tests below. |
| Bundle and operational requirements | Measured/documented | See the bundle measurement and server architecture below. |

No claim is made that an encrypted Matrix message, attachment, invitation,
device registration, membership removal, or second device succeeded in this
spike. Those tests are mandatory conditional-go gates, not deferred polish.

### Required server architecture

The first production-safe topology is a **dedicated, federation-disabled
Matrix homeserver deployment per FebGrid company**. Each tenant deployment
needs its own Synapse process/configuration, PostgreSQL database, media store,
signing-key lifecycle, backup policy, client API hostname, and operational
monitoring. This is deliberately more expensive than a shared homeserver but
gives a hard tenant boundary that the Matrix room model alone does not provide.

Synapse must run on a supported Linux host or container with PostgreSQL. The
deployment must expose only the Matrix client API through the reverse proxy,
not a federation listener, and use inbound and outbound firewall rules to
prevent federation traffic. The exact listener/resource configuration must be
verified against the pinned Synapse version during the live spike; do not treat
a single configuration flag as proof that federation is disabled.

Do not use Supabase Realtime or FastAPI as a parallel plaintext-message path
for `private_e2ee`. Matrix becomes the encrypted event transport and ciphertext
store. FastAPI remains the FebGrid policy and account-provisioning boundary:
it authorizes whether Chat is enabled, maps a FebGrid identity to a Matrix
identity, drives deactivation/revocation requests, and links a Matrix room to
FebGrid scope without receiving private plaintext or private keys.

### FebGrid identity and company isolation

Matrix accounts must use opaque stable IDs such as a UUID-derived localpart,
not a work email or employee name. The binding must be one-to-one with an
active FebGrid user/employee and company, recorded by a future reviewed
provisioning integration. It must not replicate FebGrid passwords, derive a
Matrix password from a FebGrid secret, or expose a homeserver administrator
token to the browser.

The preferred sign-in design is standards-based SSO/OIDC between FebGrid and
the tenant's homeserver. If the current FebGrid authentication system cannot
act as a suitable OIDC provider, the alternative one-time Matrix login-token
flow must be separately designed, reviewed, and tested before Step 1. It is a
blocker, not a reason to ship a password bridge.

Dedicated homeservers make company isolation an infrastructure boundary. A
future shared-homeserver design is out of scope until it proves that account
provisioning, room aliases, discovery, invitations, media, admin APIs, and
metadata queries cannot cross company boundaries. Neither a room prefix nor a
client-side `company_id` is a tenancy boundary.

### Server-visible metadata and security limitations

Private Matrix E2EE protects event content from the homeserver, not metadata.
The homeserver and its operator can observe Matrix user/device IDs, room IDs,
membership and invitations, event type, sender, timestamps, ciphertext size,
delivery/sync activity, encrypted attachment ciphertext and size, IP/log data,
and retention/backups of that metadata. It cannot be represented as anonymous
or metadata-free chat.

Matrix group encryption uses Olm/Megolm session mechanics rather than MLS.
Member removal must be coupled to room authorization changes and mandatory
outbound session rotation before any claim that the removed member is denied
future content. It cannot retract keys or plaintext that a former member
already received. Key backup, cross-signing, device verification, lost-device
recovery, session sharing, room-history visibility, and attachment key
lifecycle require an explicit product policy and focused cryptographic review.

Matrix room encryption is not a substitute for FebGrid authorization. Before
any room creation, the integration must ensure that the scope, participant
list, company, and mode are permitted. The private/managed mode remains
immutable at the FebGrid product layer; a new Matrix room is required for a
mode change. Direct client state-event changes that would weaken this policy
must be constrained by the homeserver/integration design.

### Licensing, operations, and review requirements

`matrix-js-sdk` and `matrix-sdk-crypto-wasm` are Apache-2.0. Synapse is
AGPL-3.0-only and must receive legal review before deployment, especially if
FebGrid modifies or distributes it. The Matrix protocol itself is an open
standard; protocol use does not remove the obligations of the deployed
implementation's license.

Operating a homeserver adds recurring cost and responsibility: Linux/container
patching, PostgreSQL and media backups, encrypted-media storage growth,
TLS/domain management, client API rate limiting, monitoring/alerting, incident
runbooks, signing-key protection and rotation, abuse reporting, account
deactivation, data retention/deletion policy, and periodic Matrix/Synapse and
SDK security updates. Per-company homeservers multiply this overhead.

Before implementation, obtain a focused review of: identity/SSO bridging,
client token handling, device verification/recovery, membership removal and
rekey behavior, federation isolation, metadata/privacy notices, attachment
encryption, server/admin access, incident response, licensing, and browser
IndexedDB compromise/loss assumptions.

Primary sources reviewed for Matrix:

- Matrix JavaScript SDK: https://github.com/matrix-org/matrix-js-sdk
- Matrix Rust SDK: https://github.com/matrix-org/matrix-rust-sdk
- Matrix Rust/WASM package: https://www.npmjs.com/package/@matrix-org/matrix-sdk-crypto-wasm
- Matrix E2EE attachment specification: https://spec.matrix.org/latest/client-server-api/#extensions-to-mroommessage-msgtypes
- Matrix end-to-end encryption concepts: https://matrix.org/docs/matrix-concepts/end-to-end-encryption/
- Synapse deployment documentation: https://element-hq.github.io/synapse/latest/setup/installation.html
- Synapse Docker documentation: https://element-hq.github.io/synapse/latest/setup/installation.html#docker

## Matrix Homeserver and Lifecycle Validation (Step 0.2)

### Isolated environment and lifecycle result

Step 0.2 ran on 2026-07-10 in the disposable
`prototypes/matrix-synapse-lifecycle-spike/` environment. It used two separate
Synapse 1.156.0 containers and two PostgreSQL 16 containers; it did not use
FebGrid services, databases, accounts, `.env`, or credentials. The tested
Synapse image digest was
`matrixdotorg/synapse@sha256:6882d26594b87171e0fe807ac6bd7f0000665cd70e73fb88c58ec9bff14c19ce`.
All client listeners were bound to `127.0.0.1`, with client-only listeners and
separate Docker networks for the two synthetic companies.

| Lifecycle check | Result | Evidence / limitation |
| --- | --- | --- |
| Synthetic user/device registration | Passed | Two users and a second device were registered only in the disposable homeserver. |
| Encrypted private room create, invite, join, send, decrypt | Passed | `matrix-js-sdk` with its Rust/WASM crypto stack sent and decrypted a real `m.megolm.v1.aes-sha2` message. |
| Browser refresh and encrypted-state recovery | Passed | A real browser test used IndexedDB crypto storage, refreshed, and read the prior encrypted event on the same device/session. |
| Second-device feasibility | Passed with limitation | The second device decrypted the test room. Cross-signing, user verification, device-loss recovery, and trust UX were not validated. |
| Member removal and future-message denial | Passed with limitation | A removed user was denied a future send. The test explicitly discarded the outbound session before the post-removal message; production must enforce an equivalent rekey/session-rotation workflow. Historic content already decrypted by the removed user cannot be revoked. |
| Encrypted attachment lifecycle | Passed | The official Matrix attachment helper encrypted before upload; the recipient downloaded ciphertext and decrypted it client-side. |
| Federation-disabled client surface | Passed for the test | The federation endpoint was absent from the client-only listener. This is not a substitute for a production inbound/egress firewall validation. |
| Company isolation | Passed for the test | Each company used a separate homeserver and PostgreSQL service on a distinct Docker network. A company-B access token was rejected by company-A. |
| FebGrid authentication and lifecycle integration | Not implemented | Matrix registration/login was tested only with synthetic Matrix credentials. FebGrid SSO/OIDC, deactivation, role changes, and logout/device revocation remain blockers. |

The browser harness used `matrix-js-sdk`, Vite, and IndexedDB-backed Rust/WASM
crypto. The Node lifecycle probe used the same official Matrix client stack in
an isolated runtime. Prototype logs deliberately omit access tokens, passwords,
room identifiers, plaintext, signing keys, and attachment bytes.

### Deployment and security implications

This result validates a self-hosted, per-company homeserver option. A production
deployment should use a pinned Synapse image, PostgreSQL, a client-only reverse
proxy, separate company homeserver/database/network boundaries, and explicit
inbound and outbound federation denial at the platform firewall layer. The
test's Docker networks were intentionally separate, but not marked `internal`:
Docker Desktop would not forward the loopback client ports with that setting.
That operational constraint must be resolved with the production network design
rather than treated as federation protection.

Matrix homeservers necessarily see routing metadata such as Matrix account,
room, device, membership, timestamp, ciphertext size, and ciphertext media
metadata. They do not receive private plaintext or attachment keys when the
browser uses the Matrix E2EE client correctly. Synapse is AGPL-3.0-only; legal
review and a focused independent security review are required before any
production use.

No production Chat model, migration, API, sidebar entry, or message UI was
created during this spike. The isolated test data, signing keys, media, browser
crypto store, containers, and volumes are destroyed after the validation run.

## Isolated Prototype Results

The prototype lives in `prototypes/secure-chat-crypto-spike/`. It has no
imports from the FebGrid frontend or backend and makes no network calls.

| Check | Result |
| --- | --- |
| Pinned candidate import | Signal client and OpenMLS WASM import in isolated Node runtime |
| OpenMLS group creation | Passed |
| Identity and key-package creation | Passed in the library's in-memory provider |
| Add member and join from welcome/ratchet tree | Passed |
| Encrypt/decrypt test message | Passed |
| Runtime | 71.48 ms for the in-memory exercise on this workstation |
| WASM payload | 1,402,409 bytes before compression (about 1.34 MiB) |
| Out-of-order message API | Not exposed by the published WASM package |
| Member removal/rekey API | Not exposed by the published WASM package |
| Browser bundle test | Failed safely: Vite 6 rejects the package's direct WASM ESM integration and requires an extra community WASM plugin or custom loader |
| Official vector execution | Not completed; the published experimental package does not provide a supported vector harness here |
| Backend private-key registration | Not attempted; zero FebGrid backend calls |

The probe demonstrates a cryptographic-library experiment, not a production
E2EE capability. No private or production key was generated or sent to FebGrid.
The browser build failure is an additional rejection signal: adding a loader or
rewriting bindings to force the experimental package into Vite would be custom
cryptography integration risk, not an acceptable production decision.

## Conditional Matrix Realtime and Authorization Topology

If the conditional gates pass, use this topology for `private_e2ee` only:

1. The React browser owns private plaintext, Matrix Rust/WASM crypto state,
   browser IndexedDB state, and encrypted attachment keys.
2. The tenant's Matrix homeserver owns encrypted event synchronization,
   ciphertext history, room membership protocol, and ciphertext media.
3. FastAPI remains the FebGrid policy/integration service: it validates
   company status and authorization before provisioning/removing an opaque
   Matrix identity or requesting a room-scope change. It never receives
   private plaintext, private identity keys, encrypted attachment keys, or
   browser Matrix access tokens.
4. FebGrid PostgreSQL records only a future reviewed mapping of company,
   FebGrid identity, Matrix identity, and permitted source scope. It does not
   become a duplicate private-message store.
5. Supabase Realtime is not used for private message contents, room state, or
   private presence. Existing FebGrid notifications can carry only a generic
   "new encrypted message" signal after a future permission review.
6. Private attachment bytes are encrypted by the Matrix client before upload;
   the homeserver stores ciphertext media. A managed-channel attachment flow,
   if added later, remains a separate server-readable feature.

### FebGrid policy and Matrix authorization proposal

- FebGrid sessions must authorize the identity-to-Matrix login bridge using a
  user identity, company identity, and revocable Chat authorization version.
  They must not contain Matrix key material or homeserver administrator tokens.
- Provisioning must ensure both company equality and active FebGrid membership
  before creating/re-enabling an opaque Matrix identity or issuing a login
  hand-off.
- A membership removal, device revocation, employee deactivation, or company
  switch must disable the Matrix account/room access and rotate future outbound
  room sessions. The live spike must prove prompt client disconnect and future
  event denial.
- In a future shared-server design, database/RLS checks would be only defense
  in depth. They cannot replace a verified Matrix tenant isolation model.

## Multi-Device and Key Lifecycle Decision

- One `ChatDevice` represents one browser/device registration for one active
  company employee/user.
- Device private identity material and group/session state stay local. Prefer
  non-extractable Web Crypto keys where the approved library allows it, with
  protocol state stored in IndexedDB only after a dedicated browser review.
- New devices require account reauthentication and, where supported, approval
  from an existing trusted device plus a visible security-change notice.
- Device revoke, employee deactivation, logout-all, and suspected compromise
  revoke device authorization, expire public bundles, block future commands,
  and require future group epoch changes.
- Initial release policy: **no key backup or escrow**. Device loss can mean
  unrecoverable private history. Any later backup needs user-held recovery
  material and a separate zero-knowledge design review.

## Metadata Exposure Inventory

| Data | Private E2EE server visibility | Managed channel server visibility |
| --- | --- | --- |
| Company, conversation, member, sender device IDs | Required operating metadata | Required operating metadata |
| Timestamps, ciphertext size, delivery state | Required operating metadata | Required operating metadata |
| Message plaintext | Never | Authorized managed-channel content |
| Private file key / identity private key | Never | Not applicable |
| Attachment bytes | Ciphertext only | Authorized managed attachment |
| Presence and typing | Ephemeral, scoped; no long-term surveillance | Same |
| Notification preview | `New encrypted message`, no plaintext by default | Policy-controlled safe preview |
| Events/Audit | Major security/admin actions only | Major security/admin actions only |
| AI, Company Memory, Pulse, Work DNA, Twin | Never | Disabled by default and out of scope |
| Retention | Ciphertext policy only; no claim of remote plaintext erasure | Explicit company retention policy may apply |
| Server-side search | Metadata only | Membership-scoped content search may be added later |

## Proposed Data and API Boundaries

This is a proposal only. No models, routes, migrations, or sidebar items are
created by Step 0.

Data records will include company-scoped settings, profiles, hashed connect
codes, devices/public bundles, conversations, members, invitations, direct
requests, envelopes, receipts, reactions, attachments, blocks, and reports.
They use UUID primary keys, timestamps, and company/status/created indexes.

API families will be `/api/v1/chat/settings`, profile/discovery, devices/key
bundles, direct requests, conversations, membership/invitations, messages,
attachments, and block/report controls. The backend accepts E2EE envelopes, not
plaintext, and a referenced FebGrid entity is opened through its own existing
permission check.

## Performance Limits for the First Beta

These are initial defaults, not final product guarantees:

| Control | Initial limit |
| --- | --- |
| Plaintext composer validation | 4,000 characters before encryption |
| E2EE envelope | 64 KiB maximum |
| Managed message body | 16 KiB maximum |
| Message send rate | 30 per minute per sender/conversation |
| Typing updates | 2 per second per member/conversation |
| Presence updates | 30 per minute per device |
| Key-bundle fetch | 20 per minute per requester/target pair |
| Conversation history page | 50 messages with opaque cursor |
| Private group size | 50 members until Matrix encrypted-room lifecycle is measured |
| Attachment policy | Disabled for private E2EE until Matrix encrypted-media/key lifecycle passes review |

## Rollout and Incident Position

The rollout remains developer-mode managed channels, private beta, general
beta, then production. E2EE remains experimental until browser tests, lifecycle
tests, independent security review, incident runbooks, RLS review, and rollback
controls pass. A protocol vulnerability response must be able to stop new E2EE
sends, revoke unsafe versions, preserve ciphertext safely, and notify users.

## Final Decision and Next Step

**CONDITIONAL GO with Matrix for the feasibility work; NO-GO for Step 1.** The
isolated supported Synapse plus PostgreSQL lifecycle spike passed the required
two-user encrypted room, refresh, second-device, removal/rekey, attachment,
client-only federation, and two-company isolation tests. Matrix remains the
only evaluated option that clears the maintained browser Rust/WASM crypto and
IndexedDB feasibility bar without custom cryptography.

This is not a production approval and does not start Step 1. Step 1 is safe to
begin only after all remaining gates are closed and independently reviewed:

1. Design, implement, and test a standards-based FebGrid-to-Matrix SSO/OIDC or
   narrowly scoped login-handoff bridge. It must not duplicate passwords or put
   homeserver administrator credentials, Matrix access tokens, or key material
   in a FebGrid browser/session.
2. Prove FebGrid-driven employee deactivation, company changes, room/member
   removal, device revoke, logout-all, and outbound-session rotation. The
   removal test forced session discard; production requires a reviewed automatic
   rekey policy and a clear statement that old decrypted history cannot be
   retroactively revoked.
3. Validate production federation controls with real reverse-proxy/firewall
   rules, including inbound and outbound federation denial, DNS restrictions,
   media egress policy, monitoring, backups, retention, and incident runbooks.
4. Complete cross-signing, trusted-device, verification, device-loss, and
   browser IndexedDB lifecycle UX/security review; the spike established
   feasibility only, not a complete end-user trust model.
5. Obtain legal review for Synapse AGPL-3.0-only use and an independent focused
   security review for identity/device lifecycle, metadata/privacy, retention,
   incident response, attachments, and browser storage.

<!-- Historical pre-validation footer retained for context:
The next correct roadmap action remains **Phase 4.5 Step 0.2 — Matrix
homeserver and lifecycle validation spike** in a disposable supported Linux or
container environment, still without production Chat models, migrations,
routes, sidebar items, or message UI. Step 1 must not begin until the Step 0.2
gates convert this decision to an unqualified GO.
-->

The next correct roadmap action is **Phase 4.5 Step 0.3 - FebGrid identity,
lifecycle, deployment-controls, and independent security-review design**. It
remains an architecture/security gate, with no production Chat models,
migrations, routes, sidebar items, or message UI. Step 1 must not begin until
the listed gates convert this conditional result to an unqualified GO.
