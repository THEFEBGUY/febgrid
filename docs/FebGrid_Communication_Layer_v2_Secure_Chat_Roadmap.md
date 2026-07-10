# FebGrid Phase 4.5 — Communication Layer v2
## Secure Realtime Chat System Roadmap and Engineering Specification

**Product:** FebGrid — Business Operating System  
**Brand:** TheFebGuy  
**Phase:** 4.5  
**Layer:** Communication Layer v2  
**Document type:** Product roadmap, architecture specification, security contract, and Codex implementation guide  
**Status:** Approved for implementation after Layer 2 / Phase 4 Step 4 is manually verified and committed  
**Version:** 1.0  
**Date:** 10 July 2026  
**Primary repository location:** `docs/FebGrid_Communication_Layer_v2_Secure_Chat_Roadmap.md`

---

# 1. Purpose

This document defines the complete roadmap for building a secure, company-scoped, realtime chat system inside FebGrid.

The chat system must support:

- employee-to-employee direct messages
- private custom groups
- whole-company channels
- department channels
- team channels
- project channels
- group invitations and membership approval
- group owners and multiple group admins
- company-level enable/disable controls
- employee discovery controls
- secure connect codes
- encrypted private conversations
- realtime delivery, presence, typing indicators, receipts, attachments, reactions, replies, editing, deletion, blocking, reporting, and notification controls
- strict tenant isolation
- role-based access control
- safe integration with FebGrid employees, teams, departments, projects, files, events, notifications, and audit logs

The system must feel like a complete communication product inside FebGrid, not a basic comment box or notification stream.

The chat system is intentionally placed in **Phase 4.5**, after Layer 2 Operational Intelligence is stabilized and before Layer 3 Workflow Automation. Future automation features may later post safe system updates into managed channels, but automation must not read private end-to-end encrypted conversations.

---

# 2. Product Vision

FebGrid Chat should become the secure communication layer of the FebGrid Business Operating System.

A company that enables Chat should be able to communicate without leaving FebGrid:

- Employees can privately contact another employee.
- Teams can coordinate inside team channels.
- Departments can maintain department channels.
- Projects can have project-specific communication.
- The entire company can receive company-wide operational announcements.
- Employees can create private work groups and invite coworkers.
- Conversations can reference FebGrid projects, work objects, files, and approved company knowledge without exposing inaccessible data.

The experience should be familiar to users of modern chat products while remaining deeply connected to FebGrid’s company, employee, team, project, work, permission, event, and audit architecture.

---

# 3. Non-Negotiable Product Principles

## 3.1 Company boundary

Every chat identity, conversation, group, channel, invitation, message, receipt, attachment, device, and encryption key bundle must belong to exactly one FebGrid company.

A user in Company A must never:

- discover Company B employees
- send a request to Company B
- subscribe to Company B realtime channels
- fetch Company B conversation metadata
- receive Company B messages
- resolve Company B handles
- access Company B attachments
- reuse a Company B invitation
- receive Company B presence information

Cross-company access must be rejected by the backend and database policies even if a frontend bug supplies a valid identifier.

## 3.2 Private conversations remain private

For conversations marked **Private E2EE**:

- message content is encrypted on the sender’s device
- message content is decrypted only on authorized participant devices
- the server stores ciphertext, not plaintext
- company owners, managers, HR, database administrators, and FebGrid operators cannot read message content
- private attachment bytes are encrypted before upload
- notification previews do not expose plaintext by default
- private messages are excluded from Company Pulse, Work DNA, Employee Digital Twin, Company Memory, operational search, audit logs, and Groq processing

The server may still process limited metadata required to operate the system, such as:

- company ID
- conversation ID
- participant IDs
- sender device ID
- timestamps
- ciphertext size
- delivery status
- encrypted attachment metadata
- membership changes
- abuse-rate signals

The UI must explain this limitation honestly. E2EE protects content, not all metadata.

## 3.3 Do not invent cryptography

Codex must not design a custom cryptographic protocol.

The implementation must use:

- a mature, reviewed Signal-style protocol implementation for asynchronous one-to-one messaging, or
- a mature, reviewed Messaging Layer Security implementation for E2EE group messaging

The exact library must be selected during the cryptography feasibility spike. It must support the project’s browser/TypeScript environment and have an acceptable maintenance and security posture.

No production E2EE claim may be shown until:

- the selected library is integrated correctly
- test vectors pass
- key lifecycle tests pass
- multi-device behavior is verified
- a focused security review is completed

## 3.4 Security mode is visible and immutable

Every conversation has an explicit security mode:

- `private_e2ee`
- `managed_secure`

The mode must be visible in the conversation header.

A conversation must never silently change from E2EE to server-readable or from server-readable to E2EE.

If a different security mode is needed, create a new conversation and display a clear transition notice.

## 3.5 Company controls cannot break private encryption

Company administrators may control whether Chat, DMs, custom groups, organizational channels, attachments, presence, receipts, or retention features are available.

They may not:

- obtain private conversation keys
- silently add themselves to private conversations
- decrypt past private messages
- convert a private conversation into a managed conversation
- export private message plaintext
- search private message plaintext
- send private messages to AI without participant action

## 3.6 No automatic AI access

Groq and all FebGrid AI systems must be excluded from private E2EE chats by default.

Private chat content can be sent to AI only through a future, explicit, user-controlled action that:

- allows the user to select the exact messages
- shows what data will leave the device
- requests confirmation
- identifies the AI provider
- records consent
- does not silently enable future access

This AI sharing feature is out of scope for Chat v1.

## 3.7 Safe operational integration

Chat may integrate with FebGrid entities through secure references:

- work objects
- projects
- files
- employees
- teams
- departments
- approved Company Memory

A reference never grants access. The recipient must already have permission to open the referenced entity.

---

# 4. Conversation Security Model

FebGrid Chat will use two clearly separated communication modes.

## 4.1 Private E2EE conversations

Used for:

- employee-to-employee direct messages
- private custom groups

Properties:

- content encrypted on participant devices
- server stores ciphertext
- no server-side plaintext search
- no owner/admin plaintext access
- no server-side AI analysis
- no server-side content moderation
- no plaintext message previews in system notifications by default
- private attachment bytes encrypted client-side
- local search only
- participant-controlled disappearing messages where supported
- device verification and security-change notices

## 4.2 Managed secure channels

Used for:

- whole-company channels
- department channels
- team channels
- project channels
- future automation/system channels

Properties:

- TLS in transit
- database/storage encryption at rest
- strict company and membership authorization
- server-readable content
- company retention policy may apply
- server-side search may be supported
- moderation and organization controls may be supported
- audit may record management actions, but not unnecessarily duplicate message content
- future workflow automations may post into these channels
- AI access remains disabled unless a future company setting and separate consent design explicitly allows it

Managed channels must not display an E2EE badge.

## 4.3 Why two modes are required

True E2EE prevents the server and company administrators from reading content. Enterprise retention, centralized search, automated moderation, and server-side workflow integration require server access to content.

FebGrid must not falsely promise both at the same time.

The product therefore provides:

- private, participant-controlled E2EE conversations
- company-managed organizational channels with enterprise controls

---

# 5. Company Chat Controls

Create a company-scoped Chat Settings module.

## 5.1 Master setting

`chat_enabled`

When disabled:

- Chat disappears from the company sidebar
- new messages cannot be sent
- invitations cannot be created or accepted
- realtime subscriptions are denied
- existing server data is not automatically deleted
- existing local E2EE caches cannot be remotely guaranteed to disappear
- owner/admin can re-enable the feature later
- retention/deletion workflows remain available through authorized administration tools

## 5.2 Feature settings

Recommended company settings:

- `chat_enabled`
- `direct_messages_enabled`
- `private_groups_enabled`
- `company_channels_enabled`
- `department_channels_enabled`
- `team_channels_enabled`
- `project_channels_enabled`
- `managed_channel_creation_enabled`
- `employee_created_groups_enabled`
- `attachments_enabled`
- `voice_messages_enabled`
- `link_previews_enabled`
- `read_receipts_enabled`
- `typing_indicators_enabled`
- `presence_enabled`
- `message_editing_enabled`
- `message_deletion_enabled`
- `reactions_enabled`
- `thread_replies_enabled`
- `directory_discovery_enabled`
- `connect_code_discovery_enabled`
- `external_links_enabled`
- `managed_channel_retention_days`
- `private_group_default_disappearing_timer`
- `max_group_members`
- `max_attachment_size_bytes`
- `allowed_attachment_types`
- `chat_notification_previews`
- `chat_feature_rollout_percentage` or explicit beta allowlist if needed

## 5.3 Who can manage company Chat settings

Default:

- company owner: allowed
- company admin: allowed
- manager: blocked
- HR: blocked
- employee: blocked

The owner may delegate a dedicated permission:

`manage_chat_settings`

This permission may be assigned to selected managers or HR users.

This is safer than automatically allowing every manager or HR user to disable Chat for the whole company.

## 5.4 Settings audit

Every company Chat setting change must create a safe audit event containing:

- company ID
- actor user ID
- setting name
- previous boolean/value
- new boolean/value
- timestamp

Never include:

- message content
- encryption keys
- connect-code values
- raw private settings payloads containing secrets

---

# 6. Chat Identity and Discovery

## 6.1 Fixed display name

The visible Chat display name should use the existing employee name.

It remains controlled by the company’s employee profile rules.

Employees cannot independently rename themselves in Chat.

## 6.2 Immutable unique company handle

Employee names are not unique. FebGrid must create an immutable, unique, company-scoped handle.

Examples:

- `@pranav.amble-0142`
- `@rahul.sharma-0187`

Requirements:

- unique within the company
- generated by backend
- case-insensitive uniqueness
- stable even if display name changes
- not reused immediately after employee deactivation
- internal employee/user IDs remain the source of truth
- handle is never used as an authorization credential

## 6.3 Discovery modes

Each employee may choose one of these company-scoped discovery modes, subject to company policy:

### Directory mode

- visible in the company Chat directory
- searchable by display name and immutable handle
- coworkers may send a message request

### Connect-code mode

- hidden from normal directory results, or visible without a direct message action
- a coworker must enter the exact handle and a valid connect code
- recipient still receives an accept/reject request

### No-new-requests mode

- existing conversations continue
- new DM requests are blocked
- optionally group invitations remain independently configurable

## 6.4 Replace the four-digit PIN with a safer connect code

A four-digit PIN has only 10,000 combinations and is unsuitable as a persistent discovery secret.

FebGrid should use a **Chat Connect Code** with one of these policies:

Preferred:

- eight-character alphanumeric code
- generated securely by the backend
- rotatable at any time
- optionally expires
- stored only as a slow, salted hash
- displayed only when generated/reset
- never logged
- never returned in list/search APIs

Acceptable reduced-complexity option:

- six-digit numeric code
- strict rate limits
- short cooldowns
- lockout after repeated failures
- exact immutable handle required
- generic failure messages
- optional expiry

The connect code is not:

- an account password
- a login credential
- an encryption key
- an authorization token
- a recovery code

## 6.5 Connect-code validation safety

Required controls:

- rate limit per requester user
- rate limit per requester IP/device
- rate limit per target employee
- company-wide abuse threshold
- exponential cooldown
- temporary lock after repeated failures
- generic error: `Employee or connect code is incorrect`
- do not reveal whether the employee exists
- audit repeated abuse without storing the code
- allow target employee to rotate code instantly
- existing approved conversations remain active after rotation
- blocked users cannot validate the target’s code

---

# 7. Direct Message Flow

## 7.1 Directory discovery flow

1. User opens Chats.
2. User selects **New message**.
3. User searches company directory.
4. Backend returns only discoverable employees in the same company.
5. User selects an employee.
6. If an existing conversation exists, open it.
7. Otherwise create a message request.
8. Recipient receives a Chat request notification.
9. Recipient accepts, rejects, or blocks.
10. E2EE session setup completes before the first message is sent.

## 7.2 Connect-code flow

1. User opens **Connect with code**.
2. User enters immutable handle and connect code.
3. Backend validates company, status, blocks, rate limits, and hashed code.
4. On failure, return a generic message.
5. On success, create a pending DM request.
6. Recipient accepts or rejects.
7. On acceptance, device key negotiation begins.
8. Conversation becomes usable only when encryption setup succeeds.

## 7.3 DM request states

- `pending`
- `accepted`
- `rejected`
- `expired`
- `cancelled`
- `blocked`

Rules:

- pending requests expire
- requester can cancel
- recipient can block
- rejected requests have a cooldown before retry
- duplicate pending requests are prevented
- only one active one-to-one conversation exists per employee pair per company unless product explicitly supports separate contexts later

## 7.4 Direct message controls

- mute
- archive
- pin
- mark unread
- block
- report
- delete local history
- disappearing-message timer
- read receipt preference, subject to company policy
- presence preference, subject to company policy
- device verification
- security-change notice
- clear local cache

---

# 8. Custom Private Group Flow

## 8.1 Creation

1. Employee selects **New private group**.
2. Employee enters:
   - group name
   - optional image
   - optional description
   - disappearing-message setting
3. Creator becomes `group_owner`.
4. Creator invites company employees.
5. Group becomes active after creation even if invitations remain pending.

## 8.2 Group roles

- `group_owner`
- `group_admin`
- `member`
- optional `read_only_member`

## 8.3 Owner powers

- rename group
- update image and description
- add/remove admins
- transfer ownership
- remove members
- change selected group settings
- close/archive group
- invite members
- revoke invitations

## 8.4 Admin powers

Depending on group settings:

- rename group
- update image and description
- invite members
- remove normal members
- manage selected permissions
- revoke invitations

Admins cannot:

- remove the owner
- transfer ownership unless explicitly allowed
- access another company
- decrypt messages sent before they joined unless protocol/history policy explicitly supports secure history sharing

## 8.5 Invitation flow

1. Owner/admin searches by company name or immutable handle.
2. Backend verifies the employee exists in the same company.
3. If private discovery requires a code, the inviter must use the exact handle and connect code, unless existing conversation/trust policy allows an invite.
4. Backend creates a group invitation.
5. Invitee receives accept/reject options.
6. On acceptance:
   - membership is created
   - group encryption membership is updated
   - other members receive a membership-change system event
7. On rejection:
   - no membership is created
   - inviter sees a safe rejected state
8. Invitation expires after a configured period.

## 8.6 Incorrect employee entry

Return:

`Employee not found or unavailable in this company.`

Do not expose:

- employees in other companies
- hidden employees
- deactivated employees
- block relationships
- detailed discovery policy

## 8.7 Group membership changes and encryption

When a member joins or leaves:

- rotate group encryption state
- removed members cannot decrypt future messages
- new members do not automatically receive past plaintext
- show security membership change in the group timeline
- invalidate removed member realtime authorization immediately
- revoke attachment access for future requests where possible

The last owner cannot leave until ownership is transferred or the group is closed.

---

# 9. Organizational Channels

## 9.1 Channel types

- company channel
- department channel
- team channel
- project channel
- optional managed custom channel

## 9.2 System-managed membership

Membership should be synchronized from existing FebGrid data:

- Company channel → active company members
- Department channel → active employees assigned to department
- Team channel → active team members
- Project channel → active project members and permitted project owners/managers

Do not manually duplicate organizational membership when existing FebGrid models are the source of truth.

## 9.3 Membership synchronization events

Trigger sync on:

- employee activation
- employee deactivation
- employee company removal
- department change
- team assignment/removal
- project member add/remove
- project archive
- company Chat enable/disable
- role/permission change

Sync must be:

- idempotent
- retryable
- auditable
- company-scoped
- safe under concurrent updates

## 9.4 Managed channel roles

- channel owner/system
- channel admin
- moderator
- member
- read-only member

Organizational channels may use system ownership.

## 9.5 Whole-company channel

Recommended behavior:

- one default company channel
- active members synchronized automatically
- only allowed roles may post if configured as announcement-style
- optional reply permissions
- no employee can remove another company member from system membership
- deactivation removes access immediately

## 9.6 Department, team, and project channels

Channel lifecycle should follow the linked entity:

- creation may be automatic or manual based on company setting
- rename follows entity name unless overridden by a permitted admin
- archive when entity is archived
- membership follows entity membership
- source entity link is shown
- deleted/inaccessible entity produces a safe archived state

---

# 10. Realtime Architecture

## 10.1 Recommended components

- FastAPI for authoritative authorization, commands, persistence, invitations, membership, and history APIs
- PostgreSQL/Supabase for persistent metadata and ciphertext/message records
- Supabase Realtime Broadcast for low-latency delivery
- Supabase Presence for online state and typing indicators
- Row Level Security plus backend authorization
- Supabase Storage or existing FebGrid file abstraction for encrypted attachment bytes
- React frontend for local encryption/decryption, outbox, realtime state, and conversation UX

## 10.2 Private realtime channels only

All FebGrid Chat realtime topics must be private.

Never use public channels for company Chat.

Example topic patterns:

- `chat:company:{company_id}:conversation:{conversation_id}`
- `chat:company:{company_id}:presence:{conversation_id}`
- `chat:company:{company_id}:user:{user_id}`

Topic names must not be treated as authorization. Authorization must verify active membership.

## 10.3 Message delivery sequence

1. Client builds plaintext message locally.
2. Client validates local size/type rules.
3. For E2EE:
   - client encrypts content
   - client creates encrypted envelope per protocol
4. Client sends command to FastAPI with idempotency key.
5. Backend verifies:
   - authenticated user
   - active company membership
   - Chat enabled
   - conversation membership
   - sender permission
   - message rate limit
   - payload size
   - supported envelope version
6. Backend persists message envelope.
7. Transaction commits.
8. Backend/realtime trigger broadcasts a minimal event.
9. Authorized clients fetch/receive the envelope.
10. Recipient device decrypts locally.
11. Delivery/read receipts are sent separately.
12. Push/in-app notification is created using privacy-safe preview policy.

## 10.4 Do not rely only on realtime delivery

Persistent message storage is the source of truth.

Clients must recover missed messages through paginated history APIs after:

- reconnect
- browser refresh
- device wake
- temporary network failure
- realtime subscription loss

## 10.5 Ordering and idempotency

Every message command should include:

- client-generated message UUID
- idempotency key
- client timestamp
- conversation ID
- sender device ID
- envelope version

Server should assign:

- server sequence number per conversation, or a stable sortable identifier
- server received timestamp

Duplicate submissions must return the existing message rather than create duplicates.

## 10.6 Outbox

Frontend should maintain an outbox state:

- preparing
- encrypting
- sending
- sent
- delivered
- read
- failed
- retrying

Retries must reuse idempotency keys.

---

# 11. End-to-End Encryption Architecture

## 11.1 Mandatory feasibility spike

Before production implementation, Codex must complete a focused spike covering:

- supported browser environments
- TypeScript/WASM integration
- library maintenance status
- licensing
- test vectors
- multi-device support
- prekey/key-package management
- group membership changes
- storage of non-extractable keys where possible
- performance on low-end devices
- bundle size
- backup/recovery options
- security review requirements

The spike must end with an Architecture Decision Record.

## 11.2 One-to-one messaging target

Use an audited Signal-style design supporting:

- asynchronous initial key agreement
- identity keys
- signed prekeys
- one-time prekeys where supported
- Double Ratchet message-key evolution
- forward secrecy
- recovery after temporary compromise where protocol supports it
- multi-device session management
- out-of-order messages
- skipped message keys
- replay protection

Do not implement these primitives manually.

## 11.3 Group messaging target

Use a reviewed MLS implementation or another mature reviewed group-E2EE implementation.

Required properties:

- authenticated group membership
- forward secrecy
- post-compromise security where implementation supports it
- secure member add/remove
- epoch/key rotation
- asynchronous operation
- group state recovery
- multiple devices per employee

## 11.4 Device identity

Each Chat-capable device must have:

- device ID
- employee/user ID
- company ID
- device display name
- device public identity key
- protocol key package/prekey data
- created timestamp
- last seen timestamp
- revoked timestamp
- trust state

Private keys remain on the device.

## 11.5 Local key storage

Preferred browser storage:

- Web Crypto generated keys
- non-extractable keys where protocol/library permits
- IndexedDB for wrapped protocol state
- local database encrypted with a device-bound key where practical

Security requirements:

- strong Content Security Policy
- no unsafe inline scripts
- no untrusted script injection
- dependency review
- XSS prevention
- secure logout behavior
- device revoke support

E2EE cannot protect plaintext on a compromised device or in a page compromised by XSS.

## 11.6 New-device flow

Recommended:

1. User logs in normally.
2. Chat detects unregistered device.
3. Device generates local identity material.
4. Device registers public bundle.
5. Existing trusted device receives approval request where available.
6. User verifies device through QR/safety code or account reauthentication.
7. Conversations establish sessions for the new device.
8. Participants receive a security-change notice.
9. Past history availability follows the selected secure backup/history policy.

## 11.7 Device revocation

On:

- manual revoke
- logout-all
- employee deactivation
- suspected compromise
- account removal

The system must:

- mark device revoked
- deny realtime subscriptions
- deny message sending
- remove/expire public key packages
- rotate group membership state
- notify affected conversations of a security change
- prevent future message decryption by revoked device keys

Previously downloaded plaintext cannot be remotely guaranteed to disappear.

## 11.8 Safety numbers / verification

Private conversations should expose:

- participant identity verification status
- safety number or QR
- device list
- last security change
- unverified-device warning

## 11.9 Key backup and recovery

Do not silently escrow keys to the company.

Possible future-safe approach:

- user-generated recovery key
- client-side encrypted key backup
- passphrase-derived wrapping key
- zero-knowledge server storage of encrypted backup blob
- explicit recovery warning

For the initial release, key backup may be deferred if it cannot be implemented safely. The UI must clearly explain the consequence of device loss.

---

# 12. Message and Attachment Data Model

Suggested model names may be adjusted to existing FebGrid conventions.

## 12.1 Company settings

`ChatCompanySettings`

Important fields:

- id
- company_id
- settings flags
- retention policy
- limits
- created_by_user_id
- updated_by_user_id
- created_at
- updated_at

## 12.2 Chat profile

`ChatProfile`

- id
- company_id
- employee_id
- user_id
- immutable_handle
- discovery_mode
- allow_group_invites
- presence_visibility
- read_receipt_preference
- created_at
- updated_at

Unique constraints:

- company_id + employee_id
- company_id + lower(immutable_handle)

## 12.3 Connect code

`ChatConnectCode`

- id
- company_id
- employee_id
- code_hash
- code_version
- created_at
- expires_at nullable
- rotated_at
- failed_attempt_count or external rate-limit state
- locked_until nullable
- is_active

Never store plaintext code.

## 12.4 Device

`ChatDevice`

- id
- company_id
- employee_id
- user_id
- device_name
- protocol_version
- public_identity_key
- signed_prekey_bundle or MLS key package
- bundle_signature
- created_at
- last_seen_at
- revoked_at
- status
- metadata_json with no secrets

## 12.5 Conversation

`ChatConversation`

- id
- company_id
- conversation_type
- security_mode
- linked_entity_type nullable
- linked_entity_id nullable
- name nullable
- description nullable
- avatar_attachment_id nullable
- created_by_user_id
- owner_employee_id nullable
- settings_json
- last_message_sequence
- last_message_at
- archived_at nullable
- closed_at nullable
- created_at
- updated_at

Conversation types:

- `direct`
- `private_group`
- `company_channel`
- `department_channel`
- `team_channel`
- `project_channel`
- `managed_custom_channel`

## 12.6 Conversation member

`ChatConversationMember`

- id
- company_id
- conversation_id
- employee_id
- role
- membership_source
- status
- joined_at
- left_at nullable
- removed_by_user_id nullable
- last_read_sequence
- muted_until nullable
- notification_level
- pinned_at nullable
- archived_at nullable
- created_at
- updated_at

Membership sources:

- direct
- invite
- company_sync
- department_sync
- team_sync
- project_sync
- admin_add

## 12.7 Invitation

`ChatInvitation`

- id
- company_id
- conversation_id
- invited_employee_id
- invited_by_employee_id
- status
- expires_at
- responded_at nullable
- created_at

## 12.8 DM request

`ChatDirectRequest`

- id
- company_id
- requester_employee_id
- target_employee_id
- discovery_method
- status
- expires_at
- responded_at nullable
- created_at

## 12.9 Message envelope

`ChatMessage`

- id
- company_id
- conversation_id
- sender_employee_id
- sender_device_id
- client_message_id
- idempotency_key
- server_sequence
- message_type
- envelope_version
- ciphertext or managed plaintext payload depending security mode
- authenticated_metadata_json
- reply_to_message_id nullable
- thread_root_message_id nullable
- edited_from_message_id nullable
- deletion_state
- sent_at_client
- received_at_server
- edited_at nullable
- deleted_at nullable

For E2EE, never store plaintext in this table.

## 12.10 Receipts

`ChatMessageReceipt`

- company_id
- conversation_id
- message_id or sequence
- employee_id
- device_id nullable
- receipt_type
- created_at

Receipt types:

- delivered
- read

## 12.11 Reactions

`ChatMessageReaction`

For E2EE, reaction content may be encrypted or constrained to a small safe enum depending threat model.

Fields:

- company_id
- conversation_id
- message_id
- employee_id
- encrypted_reaction or safe reaction code
- created_at
- removed_at nullable

## 12.12 Attachment

`ChatAttachment`

- id
- company_id
- conversation_id
- message_id nullable
- uploader_employee_id
- storage_provider
- storage_object_key
- security_mode
- encrypted_file_size
- encrypted_mime_hint
- encryption_metadata version only, not raw secret key
- checksum of ciphertext
- upload_status
- created_at
- deleted_at nullable

For private E2EE attachments, the file key is shared inside the encrypted message envelope, not stored as plaintext on the server.

## 12.13 Block

`ChatBlock`

- company_id
- blocker_employee_id
- blocked_employee_id
- created_at

## 12.14 Report

`ChatReport`

- company_id
- reporter_employee_id
- conversation_id
- reported_employee_id nullable
- reason_code
- description
- explicitly_shared_evidence_blob nullable
- status
- reviewed_by_user_id nullable
- created_at
- resolved_at nullable

In E2EE conversations, evidence is submitted only when the reporter explicitly chooses to share selected messages.

---

# 13. API Surface

Exact route names should follow current FebGrid conventions.

## 13.1 Company settings

- `GET /api/v1/chat/settings`
- `PUT /api/v1/chat/settings`
- `GET /api/v1/chat/capabilities`

## 13.2 Profile and discovery

- `GET /api/v1/chat/profile`
- `PUT /api/v1/chat/profile`
- `POST /api/v1/chat/connect-code/rotate`
- `POST /api/v1/chat/connect-code/validate`
- `GET /api/v1/chat/directory`
- `GET /api/v1/chat/users/{handle}` only if safe and company-scoped

## 13.3 Devices and keys

- `GET /api/v1/chat/devices`
- `POST /api/v1/chat/devices/register`
- `POST /api/v1/chat/devices/{id}/revoke`
- `GET /api/v1/chat/key-bundles/{employee_id}`
- `POST /api/v1/chat/key-bundles/replenish`

Key-bundle APIs must be rate-limited and company-scoped.

## 13.4 Direct requests

- `POST /api/v1/chat/direct-requests`
- `GET /api/v1/chat/direct-requests`
- `POST /api/v1/chat/direct-requests/{id}/accept`
- `POST /api/v1/chat/direct-requests/{id}/reject`
- `POST /api/v1/chat/direct-requests/{id}/cancel`

## 13.5 Conversations

- `GET /api/v1/chat/conversations`
- `POST /api/v1/chat/conversations`
- `GET /api/v1/chat/conversations/{id}`
- `PATCH /api/v1/chat/conversations/{id}`
- `POST /api/v1/chat/conversations/{id}/archive`
- `POST /api/v1/chat/conversations/{id}/leave`
- `POST /api/v1/chat/conversations/{id}/transfer-ownership`

## 13.6 Members and invitations

- `GET /api/v1/chat/conversations/{id}/members`
- `POST /api/v1/chat/conversations/{id}/invitations`
- `GET /api/v1/chat/invitations`
- `POST /api/v1/chat/invitations/{id}/accept`
- `POST /api/v1/chat/invitations/{id}/reject`
- `POST /api/v1/chat/invitations/{id}/revoke`
- `PATCH /api/v1/chat/conversations/{id}/members/{employee_id}`
- `DELETE /api/v1/chat/conversations/{id}/members/{employee_id}`

## 13.7 Messages

- `GET /api/v1/chat/conversations/{id}/messages`
- `POST /api/v1/chat/conversations/{id}/messages`
- `PATCH /api/v1/chat/conversations/{id}/messages/{message_id}`
- `DELETE /api/v1/chat/conversations/{id}/messages/{message_id}`
- `POST /api/v1/chat/conversations/{id}/receipts`
- `POST /api/v1/chat/conversations/{id}/typing`
- `POST /api/v1/chat/conversations/{id}/messages/{message_id}/reactions`
- `DELETE /api/v1/chat/conversations/{id}/messages/{message_id}/reactions/{reaction_id}`

Typing should normally use ephemeral realtime events rather than persistent database writes.

## 13.8 Attachments

- `POST /api/v1/chat/conversations/{id}/attachments/init`
- direct signed upload of ciphertext
- `POST /api/v1/chat/conversations/{id}/attachments/{id}/complete`
- `GET /api/v1/chat/conversations/{id}/attachments/{id}/download`
- `DELETE /api/v1/chat/conversations/{id}/attachments/{id}`

## 13.9 Blocking and reporting

- `POST /api/v1/chat/blocks`
- `DELETE /api/v1/chat/blocks/{employee_id}`
- `GET /api/v1/chat/blocks`
- `POST /api/v1/chat/reports`

---

# 14. Permission Matrix

## 14.1 Company owner/admin

May:

- enable/disable Chat
- configure company Chat capabilities
- manage managed channels according to policy
- view managed channel content where membership/moderation policy allows
- review metadata-level audit events
- manage delegated Chat administrators
- suspend managed channels
- review user-submitted abuse reports

May not:

- read private E2EE content
- obtain private keys
- silently join private groups
- bypass block state to read DMs
- search private plaintext
- export private plaintext

## 14.2 Delegated Chat administrator

May only perform permissions explicitly delegated, such as:

- manage company Chat settings
- manage managed channels
- review reports
- manage channel retention

Cannot read private E2EE content.

## 14.3 Manager

By default:

- normal employee Chat access
- manages channels/groups only where explicitly owner/admin
- cannot disable company Chat
- cannot inspect employee DMs
- cannot automatically read department/team private groups

With explicit delegated permission:

- may manage selected company Chat settings or managed channels

## 14.4 HR

By default:

- normal employee Chat access
- may participate in assigned managed channels
- cannot inspect private DMs
- cannot automatically disable Chat
- cannot access private message content for investigations

With explicit delegated permission:

- may review explicit reports/evidence
- may manage selected Chat settings

## 14.5 Employee

May:

- use enabled Chat features
- manage own profile/discovery settings
- rotate own connect code
- send/receive DM requests
- create groups if enabled
- manage groups they own/administer
- block/report users
- manage own notifications and devices

Cannot:

- access another company
- read conversations without active membership
- manage company Chat settings
- read private conversations of others
- enumerate hidden employees
- bypass invitations
- add deactivated employees

---

# 15. Message Feature Rules

## 15.1 Replies

- reply references original message ID
- display safe unavailable placeholder if original is deleted or inaccessible
- E2EE reply preview is encrypted within the new message

## 15.2 Editing

- company setting controls whether editing is enabled
- limited edit window
- edit creates a new signed/encrypted revision
- show `Edited`
- retain minimal revision chain metadata
- do not expose old plaintext to server for E2EE

## 15.3 Delete for me

- local/client visibility state
- does not delete for other participants
- server may retain ciphertext according to policy

## 15.4 Delete for everyone

- limited time window
- permission checked
- create tombstone event
- clients remove visible content
- cannot guarantee deletion from screenshots, exports, compromised clients, or previously copied content

## 15.5 Reactions

- prevent duplicate same-user/same-reaction state
- support add/remove idempotently
- use a constrained set initially

## 15.6 Forwarding

For initial release:

- do not support blind forwarding of E2EE messages
- use explicit copy/share with visible warning
- sharing a FebGrid entity reference is preferred

## 15.7 Message types

Initial:

- text
- system membership event
- entity reference
- attachment
- image
- audio/voice note
- reply
- deleted tombstone

Future:

- polls
- scheduled messages
- location
- calls
- screen sharing

---

# 16. Attachments and Voice Messages

## 16.1 Private E2EE attachments

Client flow:

1. Generate random file-encryption key.
2. Encrypt file bytes locally using an authenticated encryption mode.
3. Upload ciphertext through signed URL.
4. Store only ciphertext checksum and safe metadata.
5. Put file key and required metadata inside encrypted Chat message envelope.
6. Recipient downloads ciphertext and decrypts locally.

Server must never receive the private file key in plaintext.

## 16.2 Managed channel attachments

May use existing FebGrid file pipeline with:

- authorization
- malware scanning where available
- type/size validation
- storage controls
- retention policy
- server-readable metadata

## 16.3 Limits

Define limits for:

- maximum attachment size
- image dimensions
- audio duration
- allowed file types
- number of attachments per message
- daily upload quota
- company storage quota

## 16.4 Voice messages

Private:

- record locally
- encrypt before upload
- no automatic transcription
- no Groq processing

Managed:

- transcription remains off by default
- future explicit company setting may allow it
- clear consent and security mode must be shown

---

# 17. Notifications and Presence

## 17.1 In-app notifications

Chat should use a dedicated Chat unread system for fast counts and conversation badges.

It may also create a light FebGrid notification for:

- new DM request
- new group invitation
- mention in managed channel
- membership/role change
- device security change
- report resolution

Avoid creating one global Notification record for every message if that causes excessive load.

## 17.2 Notification privacy

Default for E2EE:

- sender display name may be shown according to privacy setting
- message plaintext is hidden
- preview says `New encrypted message`

Optional device-local plaintext previews may be a future user setting, implemented without sending plaintext to server notification infrastructure.

## 17.3 Presence

Presence states:

- online
- away
- offline
- optional last seen

Requirements:

- user can hide presence
- company may disable presence
- presence is company-scoped
- presence is ephemeral
- do not store detailed long-term presence history
- do not use presence as employee performance data

## 17.4 Typing indicators

- ephemeral
- short expiry
- only active conversation members
- no persistence
- no audit event
- rate-limited

---

# 18. Search

## 18.1 E2EE conversations

Search is local-device only.

The server may search only safe metadata:

- conversation name
- participant handle/display name
- timestamps
- message type
- attachment filename only if safely available and policy permits

It cannot search E2EE plaintext.

## 18.2 Managed channels

May support server-side search with:

- company and channel authorization
- pagination
- rate limiting
- safe snippets
- retention constraints

## 18.3 Global operational search

FebGrid’s existing operational search may show:

- Chat conversations the user belongs to
- managed channel messages if policy allows
- no private E2EE plaintext
- no conversations where user lacks membership

---

# 19. Blocking, Reporting, and Abuse Controls

## 19.1 Block behavior

Blocking another employee should:

- prevent new DM requests
- stop direct message sending
- hide presence
- prevent connect-code validation by blocker/blocked pair
- not automatically remove shared organizational channel membership
- optionally hide direct interactions in shared channels
- not reveal block status explicitly to blocked user

## 19.2 Reporting E2EE conversations

Because server cannot read E2EE content:

- reporter explicitly selects messages to submit
- client decrypts selected messages locally
- client packages evidence with clear confirmation
- evidence is encrypted for the report-review service or stored securely
- UI warns that selected content will be shared with authorized reviewers
- no other conversation content is uploaded

## 19.3 Anti-spam

Implement:

- message rate limits
- request/invite rate limits
- connect-code rate limits
- group creation limits
- attachment quotas
- burst controls
- cooldown after repeated rejection
- block/report feedback signals
- temporary Chat suspension capability

Do not use private content for automated moderation.

---

# 20. Events and Audit

## 20.1 Safe auditable events

Examples:

- `chat.settings.updated`
- `chat.profile.updated`
- `chat.connect_code.rotated`
- `chat.device.registered`
- `chat.device.revoked`
- `chat.direct_request.created`
- `chat.direct_request.accepted`
- `chat.group.created`
- `chat.group.invitation.sent`
- `chat.group.invitation.accepted`
- `chat.group.member.removed`
- `chat.group.role.changed`
- `chat.managed_channel.created`
- `chat.managed_channel.archived`
- `chat.report.created`
- `chat.report.resolved`

## 20.2 Do not audit private content

Events must not contain:

- message plaintext
- decrypted attachment content
- connect code
- private key
- message encryption key
- raw ciphertext unless technically required elsewhere
- safety number
- private report evidence
- typing content
- detailed presence history

## 20.3 Message metadata audit

Do not add every Chat message to FebGrid’s universal Event Engine.

Message persistence belongs to Chat tables. The Event Engine should record major administrative/security actions, not become a duplicate message log.

---

# 21. Integration with Existing FebGrid Modules

## 21.1 Employees

- Chat identity derives from active employee record
- deactivation revokes Chat access and devices
- reactivation requires safe device/session handling
- fixed display name follows employee profile

## 21.2 Departments and teams

- managed channels follow membership
- changes trigger sync
- private group membership remains independent

## 21.3 Projects

- project channel follows project membership
- messages may share secure project/work references
- project archive archives channel
- removed project member loses channel access

## 21.4 Work Objects

Users may share a Work Object reference.

Message should include only:

- entity type
- entity ID
- safe display label
- optional encrypted note

Recipient API validates normal Work Object access before opening.

## 21.5 Files

Private Chat attachments use encrypted Chat storage flow.

Managed channel files may use existing file pipeline.

Do not silently convert a private attachment into a normal FebGrid file.

## 21.6 Notifications

Reuse user identity and action URL patterns, but avoid global notification explosion.

## 21.7 Company Memory

Private E2EE messages cannot be suggested to Company Memory automatically.

A future explicit participant action could submit selected content, but it is out of scope for v1.

Managed channel content also should not be automatically stored in Company Memory.

## 21.8 Company Pulse, Digital Twin, and Work DNA

Must not use private Chat content.

Presence, typing, DM volume, response time, and read receipts must not become employee performance metrics.

For managed channels, even aggregate communication analytics should remain out of scope until separately reviewed for privacy and labor implications.

## 21.9 Workflow Automation

Future automation may:

- post system messages into managed channels
- create managed channel notifications
- link workflow runs

Automation may not:

- decrypt E2EE messages
- send messages pretending to be an employee
- join private groups silently
- alter private conversation security mode

---

# 22. Frontend Product Experience

## 22.1 Sidebar

Show **Chats** only when:

- selected company has Chat enabled
- current employee/user is active
- user has basic Chat capability

Badge:

- unread conversation count
- pending request/invitation count indicator

## 22.2 Main Chat page layout

Desktop:

- left conversation rail
- center conversation pane
- optional right details drawer

Left rail:

- search
- new message
- new group
- invitations
- filters:
  - all
  - unread
  - direct
  - groups
  - channels
  - archived
- conversation list
- unread badges
- security mode icon

Center:

- conversation header
- security badge
- participant/channel details
- message timeline
- date separators
- unread marker
- composer
- upload action
- reply preview
- send state

Right drawer:

- participants
- role/admin controls
- media/files
- mute/pin/archive
- disappearing messages
- security and devices
- block/report
- leave group

Mobile/responsive:

- conversation list screen
- conversation screen
- details screen
- accessible back navigation

## 22.3 Chat Settings

Sections:

- Profile
- Immutable handle
- Discovery mode
- Connect code rotation
- Direct message requests
- Group invitation preference
- Presence
- Read receipts
- Notification preferences
- Devices
- Security verification
- Blocked users
- Storage/cache
- Privacy explanation

Owner/admin company settings are separate from personal settings.

## 22.4 Conversation creation UX

New message options:

- Search company directory
- Connect with code
- Create private group
- Browse permitted channels

## 22.5 Security indicators

Private E2EE header:

- lock icon
- `End-to-end encrypted`
- verification status

Managed channel header:

- building/shield icon
- `Managed company channel`
- link to retention/privacy explanation

Never use the same badge for both modes.

## 22.6 Empty/error states

Examples:

- `Chat is disabled for this company.`
- `No conversations yet.`
- `Your message request is awaiting approval.`
- `This employee is unavailable.`
- `This group invitation has expired.`
- `This device is no longer authorized.`
- `Encryption setup could not be completed. Retry securely.`
- `You no longer have access to this channel.`
- `Realtime connection lost. Messages will sync when reconnected.`

Do not show only `Failed to fetch`.

---

# 23. Security Threat Model

Codex must create and maintain a threat-model document for this phase.

At minimum, test these threats:

## 23.1 Cross-company IDOR

Attacker changes:

- conversation ID
- message ID
- attachment ID
- invitation ID
- device ID
- employee ID
- realtime topic

Expected: deny without leaking entity existence.

## 23.2 Membership bypass

Removed/non-member tries to:

- fetch history
- send message
- receive realtime events
- download attachment
- send receipt
- view members

Expected: deny immediately.

## 23.3 Employee enumeration

Attacker brute-forces names/handles/connect codes.

Controls:

- company-scoped search
- generic errors
- rate limits
- cooldown
- hidden discovery mode
- no cross-company results

## 23.4 Connect-code brute force

Controls defined earlier plus tests for batching, concurrency, and distributed attempts.

## 23.5 Realtime authorization bypass

Attempt public subscription, forged topic, stale token, removed membership, switched company.

## 23.6 Replay and duplicate messages

Use envelope version, client UUID, idempotency key, protocol replay protection, and server sequence.

## 23.7 XSS and supply-chain compromise

Because E2EE plaintext exists in browser memory:

- strict CSP
- no unsafe HTML rendering
- sanitize managed content
- dependency pinning
- lockfile review
- avoid unnecessary third-party scripts
- security headers
- no secret logging
- avoid dynamic code execution

## 23.8 Lost/stolen device

- device revoke
- security alerts
- session invalidation
- group rekey
- local lock/clear guidance
- no promise to erase previously downloaded plaintext

## 23.9 Malicious company admin

Admin cannot access private keys or private content.

Admin metadata access must be limited to operational necessity.

## 23.10 Deactivated employee

Immediate:

- auth denied
- realtime denied
- device revoked
- organizational membership removed
- group encryption membership updated
- future messages inaccessible

## 23.11 Malicious file

Private E2EE files cannot be server-scanned without breaking privacy.

Mitigations:

- safe allowed types
- size limits
- client warnings
- download confirmation for risky types
- no automatic execution
- isolated previewing
- content-disposition attachment
- managed channels may use server scanning

## 23.12 Denial of service

Rate limit:

- messages
- receipts
- typing
- presence updates
- invites
- group creation
- uploads
- history pagination
- key bundle requests

---

# 24. Performance and Scalability

## 24.1 Required indexes

At minimum:

- conversations by company and last_message_at
- members by company, employee, status
- messages by conversation and server_sequence
- messages by client_message_id/idempotency
- invitations by employee/status/expiry
- receipts by conversation/employee/sequence
- devices by employee/status
- organizational link uniqueness
- blocks by blocker/blocked

## 24.2 Pagination

Use cursor pagination for messages.

Do not use large offset pagination for long conversations.

## 24.3 Unread counts

Use:

- conversation last sequence
- member last_read_sequence

Avoid counting unread messages with a full query on every page load.

## 24.4 Realtime backpressure

- batch receipt updates
- throttle typing/presence
- avoid broadcasting complete conversation state
- broadcast message IDs/minimal envelopes
- recover through history API

## 24.5 Limits

Set configurable safe limits:

- message character size
- encrypted envelope size
- messages/minute
- typing updates/second
- presence updates/minute
- group members
- channels/company
- conversations/user
- attachments/day
- upload size
- history page size

---

# 25. Data Retention and Deletion

## 25.1 Managed channels

May follow company retention settings.

Deletion jobs must:

- be tenant-scoped
- be auditable
- handle attachments
- avoid deleting legal/required data without explicit policy
- preserve only necessary tombstone metadata

## 25.2 Private E2EE conversations

Server may delete ciphertext according to retention/disappearing-message policy.

Important limitation:

- deletion from server does not guarantee deletion from offline devices, backups, screenshots, or previously exported plaintext
- the UI must not promise guaranteed remote erasure

## 25.3 Employee departure

Policy options:

- immediately revoke access
- remove from organizational channels
- rotate group state
- retain server ciphertext under company policy
- disable key bundle access
- preserve safe membership audit events

Company admins still cannot decrypt private content.

---

# 26. Phase 4.5 Implementation Roadmap

Each step must be implemented and committed separately.

Codex must not jump ahead unless all acceptance criteria for the current step pass.

---

## Step 0 — Architecture, Threat Model, and Cryptography Feasibility Spike

### Goal

Lock the architecture before building message features.

### Deliverables

- `docs/FebGrid_Chat_Threat_Model.md`
- `docs/FebGrid_Chat_Crypto_ADR.md`
- conversation security-mode decision
- chosen realtime topology
- chosen E2EE library candidates
- browser/WASM feasibility result
- multi-device strategy
- key backup decision
- metadata exposure inventory
- managed versus E2EE feature matrix
- data model proposal
- API proposal
- RLS/realtime authorization proposal
- performance limits
- rollout plan

### Required research/prototype

- integrate candidate crypto library in an isolated test
- pass official/basic test vectors where available
- generate/register device bundle
- establish test one-to-one encrypted session
- encrypt/decrypt test message
- test out-of-order message handling if supported
- test group library basic create/add/remove if selected
- measure bundle size and runtime
- verify no private key reaches backend

### Acceptance criteria

- no custom crypto
- library choice documented
- security modes finalized
- company control policy finalized
- metadata limitations documented
- no production UI claims E2EE yet
- review completed before schema implementation

### Commit

`Define secure Chat architecture and threat model`

---

## Step 1 — Chat Foundation, Company Settings, Identity, and Schema

### Goal

Build the tenant-safe Chat control plane without sending messages yet.

### Backend

- company Chat settings
- delegated permission
- Chat profile
- immutable handle generation
- discovery modes
- connect-code hashing/rotation
- Chat device model
- conversations
- members
- invitations
- direct requests
- blocks
- initial migrations
- route registration
- audit events
- feature flag/capabilities endpoint

### Frontend

- Chats disabled/preview state
- personal Chat Settings
- owner/admin company Chat Settings
- handle display
- discovery selection
- connect-code rotation UX
- device placeholder UI
- sidebar feature gating

### Security

- cross-company tests
- handle uniqueness
- connect-code rate limits
- generic errors
- deactivated employee blocking
- role/delegated permission tests

### Acceptance criteria

- no message sending yet
- one Alembic head
- settings persist
- sidebar obeys selected company setting
- `.env` untouched
- no plaintext connect code stored
- company switch clears Chat state

### Commit

`Add secure Chat foundation and company controls`

---

## Step 2 — Realtime Transport, Managed Channel Core, and Membership Sync

### Goal

Create reliable realtime/persistence infrastructure and organizational channel membership.

### Backend

- private realtime authorization policies
- conversation membership checks
- managed channel creation
- company/department/team/project channel synchronization
- message persistence abstraction
- idempotency
- sequence ordering
- history pagination
- receipt foundation
- sync jobs with retry/idempotency
- immediate removal on membership loss

### Frontend

- Chat shell
- conversation list
- managed channel view
- composer for managed channels
- history loading
- realtime updates
- reconnect recovery
- outbox state
- unread counts
- channel details

### Restrictions

- private DMs/groups remain unavailable until E2EE step
- all realtime channels private
- no public Broadcast topics

### Acceptance criteria

- managed company/team/department/project channel works
- membership sync verified
- removed member loses history/realtime access
- messages recover after disconnect
- duplicate sends prevented
- company switch isolation verified
- no infinite refetch/realtime loops

### Commit

`Add realtime Chat transport and managed channels`

---

## Step 3 — E2EE Direct Messages v1

### Goal

Launch private, participant-only one-to-one messaging.

### Backend

- key bundle APIs
- device registration/revocation
- DM request flow
- E2EE envelope storage
- E2EE message metadata validation
- private attachment initialization foundation
- security-change events
- block enforcement

### Frontend

- crypto library integration
- local key storage
- device initialization
- directory and connect-code DM requests
- accept/reject
- session establishment
- encrypted send/decrypt
- verification/safety number
- device list
- security-change warning
- private notification preview
- local search foundation

### Acceptance criteria

- server database contains ciphertext only
- backend logs contain no plaintext
- owner/admin cannot read content
- non-member cannot fetch ciphertext
- message works asynchronously
- reconnect recovery works
- revoked device cannot receive new messages
- connect-code abuse tests pass
- security badge accurate
- independent security review before calling production-ready

### Commit

`Add end-to-end encrypted direct messages`

---

## Step 4 — E2EE Private Groups v1

### Goal

Add private encrypted groups with invitations and admin controls.

### Backend

- group roles
- invitations
- ownership transfer
- member add/remove
- group state metadata
- group membership audit
- group limits
- invitation expiry
- block/discovery rules

### Frontend

- group creation
- invite search
- accept/reject
- group member/admin management
- owner transfer
- group security state
- encrypted group messages
- membership change notices
- disappearing-message setting

### Crypto

- reviewed group protocol integration
- epoch/key rotation
- add/remove member handling
- revoked member future-message denial
- new member past-history policy

### Acceptance criteria

- removed member cannot decrypt future messages
- new member cannot silently access past plaintext
- last owner transfer rule enforced
- admins cannot remove owner
- invitations company-scoped
- cross-company and stale invitation tests pass
- private group content unavailable to owner/admin unless participant

### Commit

`Add end-to-end encrypted private groups`

---

## Step 5 — Chat Features, Attachments, Presence, and Notifications

### Goal

Complete the expected modern Chat experience.

### Features

- replies
- reactions
- editing
- delete for me
- delete for everyone/tombstones
- typing indicators
- presence
- read/delivery receipts
- mute
- archive
- pin
- mark unread
- block
- report
- private encrypted attachments
- managed attachments
- image preview
- voice messages
- notification preferences
- privacy-safe previews
- media/files panel

### Acceptance criteria

- E2EE attachment keys never reach server plaintext
- message retries idempotent
- typing/presence ephemeral
- no presence used as performance data
- private notification content hidden
- report flow explicitly shares selected E2EE evidence
- unsafe file types handled safely
- responsive UI verified

### Commit

`Complete Chat messaging and attachment features`

---

## Step 6 — Multi-Device, Recovery, Reliability, and Operational Hardening

### Goal

Make Chat resilient for real company usage.

### Work

- multiple devices per employee
- device approval
- device revoke
- session/key state synchronization
- optional encrypted backup or explicit no-backup policy
- stale device cleanup
- offline outbox
- missed-message recovery
- realtime reconnect
- group state recovery
- retry queues
- rate limiting
- storage quotas
- retention jobs
- deactivated employee lifecycle
- organizational membership race handling
- performance profiling
- index review
- load tests

### Acceptance criteria

- new device flow verified
- revoke flow verified
- deactivation revokes Chat
- no lost/duplicate message in tested failure cases
- long conversation pagination performs safely
- organization channel sync is idempotent
- rate-limit abuse tests pass
- clear recovery limitations shown

### Commit

`Harden Chat reliability and multi-device security`

---

## Step 7 — Security QA, Browser QA, and Release Candidate

### Goal

Complete full-system release hardening.

### Automated security matrix

- cross-company IDOR
- non-member history access
- realtime topic forgery
- attachment IDOR
- connect-code brute force
- invitation replay
- stale membership
- blocked user
- revoked device
- deactivated employee
- message replay
- duplicate idempotency
- group owner/admin escalation
- E2EE plaintext leakage scan
- secret/key logging scan
- source-map/build inspection
- CSP/XSS tests
- rate-limit tests
- managed/E2EE mode confusion tests

### Browser flows

Owner/admin:

- enable Chat
- configure capabilities
- verify managed company channel
- delegate Chat permission
- disable/re-enable Chat

Employee A/B:

- directory DM request
- connect-code request
- accept/reject
- encrypted message
- security verification
- block/unblock
- attachment
- revoke device

Private group:

- create
- invite
- accept/reject
- assign admin
- remove member
- transfer owner
- verify removed member cannot decrypt future content

Organizational channels:

- department/team/project membership sync
- removal blocks access
- company switch isolation

### Release gates

- backend tests pass
- frontend build/lint pass
- migrations clean
- RLS reviewed
- no `.env` staged
- no key material logged
- no private plaintext in server DB/logs
- performance limits documented
- security limitations documented
- manual browser QA completed
- independent focused crypto/security review completed
- rollback plan documented

### Commit

`Complete Secure Chat release candidate`

---

# 27. Testing Matrix

## 27.1 Backend

- model/schema tests
- migration tests
- company settings permissions
- handle uniqueness
- connect-code hash and rate limit
- directory privacy
- request/invitation state machines
- membership permissions
- organizational sync
- message idempotency
- sequence ordering
- cursor pagination
- block enforcement
- device revoke
- deactivation
- attachment authorization
- report authorization
- cross-company rejection
- realtime authorization policy checks

## 27.2 Crypto/client

- test vectors
- encrypt/decrypt
- wrong-key failure
- tamper failure
- out-of-order messages
- duplicate/replay
- skipped messages
- new device
- revoked device
- group add/remove
- epoch/key update
- corrupted local state
- backup/recovery if implemented

## 27.3 Frontend

- sidebar feature flag
- company switch
- conversation loading
- outbox
- retry
- unread counts
- request/invite flows
- settings
- group administration
- responsive layout
- keyboard navigation
- screen-reader labels
- dark/light mode
- error states
- reconnect
- no raw ciphertext shown as content
- no raw JSON
- no false sent status

## 27.4 Security

- IDOR
- CSRF where applicable
- XSS
- content sanitization in managed channels
- rate limiting
- enumeration
- authorization race
- stale JWT/session
- malicious attachment
- forged realtime topic
- dependency audit
- secret scan

---

# 28. Observability

Allowed metrics:

- active realtime connections
- message command success/failure count
- delivery latency
- reconnect rate
- queue/outbox retry rate
- invitation success/failure
- rate-limit triggers
- attachment upload failure
- organizational sync lag
- device registration/revocation count
- conversation count
- ciphertext storage volume

Do not collect:

- private plaintext
- decrypted content
- detailed employee response-time performance metrics
- typing-history analytics
- long-term presence surveillance
- private keyword analytics

Logs must redact:

- connect codes
- private keys
- file keys
- authorization headers
- encryption bundles beyond necessary public data
- ciphertext where not needed
- report evidence

---

# 29. Rollout Strategy

## Stage 1 — Internal developer mode

- test company only
- managed channels first
- E2EE marked experimental
- verbose safe diagnostics
- no external production claim

## Stage 2 — Private beta

- selected companies
- feature flag
- limited attachment sizes
- security feedback channel
- monitored rate limits
- no key backup unless verified

## Stage 3 — General beta

- security review fixes complete
- multi-device stable
- recovery policy documented
- support documentation
- retention controls
- incident response plan

## Stage 4 — Production

- independent security review
- threat model updated
- dependency monitoring
- documented cryptographic versioning
- migration/rollback plan
- availability and performance targets
- privacy terms updated

---

# 30. Incident Response Requirements

Prepare playbooks for:

- exposed server credential
- compromised Chat device
- malicious dependency
- key protocol vulnerability
- realtime authorization bypass
- cross-company data leak
- spam attack
- storage abuse
- message delivery outage
- lost/corrupted local key state

A protocol vulnerability may require:

- disabling new E2EE sends
- preserving ciphertext
- forcing client update
- rotating keys
- revoking unsafe protocol versions
- notifying affected users transparently

---

# 31. Codex Working Rules

Before every Chat step, Codex must read:

- `docs/FebGrid_Product_Requirements_Document.md`
- `docs/FebGrid_Communication_Layer_v2_Secure_Chat_Roadmap.md`
- `docs/FebGrid_Chat_Threat_Model.md` once created
- `docs/FebGrid_Chat_Crypto_ADR.md` once created
- `AGENTS.md`
- `README.md`

Codex must:

- execute one roadmap step at a time
- preserve existing FebGrid features
- inspect existing patterns before adding new abstractions
- keep company/tenant checks backend-enforced
- use migrations safely
- keep one Alembic head
- avoid broad rewrites
- add tests with every security-sensitive feature
- leave `.env` untouched
- never print credentials
- never implement custom cryptography
- never claim E2EE if content is server-readable
- never use private Chat content in AI or intelligence features
- remove temporary probe files
- report honest limitations
- not commit automatically unless explicitly instructed

At the end of each step, report:

- exact files changed
- migrations added
- routes added
- models added
- tests added
- security cases verified
- browser flows completed
- limitations
- next correct roadmap step

---

# 32. Definition of Done for Phase 4.5

Phase 4.5 is complete only when:

- company Chat settings work
- sidebar feature gating works
- immutable handles work
- connect-code discovery is rate-limited and safe
- DMs are truly E2EE
- private groups are truly E2EE
- managed organizational channels work
- company/department/team/project memberships synchronize
- realtime channels are private and authorized
- history recovery works
- outbox/idempotency works
- attachments work according to security mode
- notifications preserve privacy
- device registration and revocation work
- deactivated employees lose access
- block/report flows work
- owner/admin cannot decrypt private conversations
- private messages are excluded from AI and operational intelligence
- no cross-company leakage exists
- security mode is clearly shown
- migrations, tests, build, lint, and browser QA pass
- threat model and crypto ADR are complete
- an independent focused security review has been performed before production E2EE claims
- rollback and incident response plans exist

---

# 33. Explicit Out-of-Scope Items for Initial Chat Release

- audio/video calling
- screen sharing
- external guest users
- federation with other companies
- public communities
- bots in private E2EE chats
- AI reading private messages
- automatic Company Memory creation from Chat
- employee productivity analytics from Chat
- presence-based attendance
- response-time performance scoring
- customer support inbox
- WhatsApp/Slack/Teams bridging
- legal hold for private E2EE plaintext
- remote guarantee of deleting plaintext from participant devices
- custom cryptographic protocol
- anonymous company messaging
- cryptocurrency or payments in Chat

These may be separately reviewed in future roadmap phases.

---

# 34. Recommended Immediate Next Action

After Layer 2 / Phase 4 Step 4 is manually verified and committed:

1. Add this file under `docs/`.
2. Update the main PRD roadmap to reference Phase 4.5 without rewriting original completed history.
3. Start only:
   **Phase 4.5 Step 0 — Architecture, Threat Model, and Cryptography Feasibility Spike.**
4. Do not begin database implementation or E2EE UI until the Step 0 architecture decision is approved.

---

# 35. Standards and Primary References

The implementation should follow current official specifications and product documentation. These references guide architecture; they do not replace a dedicated security review.

1. **Messaging Layer Security Protocol — RFC 9420**  
   https://www.rfc-editor.org/rfc/rfc9420.html

2. **Messaging Layer Security Architecture — RFC 9750**  
   https://www.rfc-editor.org/rfc/rfc9750.html

3. **Signal Protocol specifications — Double Ratchet, X3DH/PQXDH, Sesame**  
   https://signal.org/docs/

4. **Supabase Realtime Authorization**  
   https://supabase.com/docs/guides/realtime/authorization

5. **Supabase Realtime Broadcast**  
   https://supabase.com/docs/guides/realtime/broadcast

6. **Supabase Realtime Presence**  
   https://supabase.com/docs/guides/realtime/presence

7. **OWASP API Security — Broken Authentication**  
   https://owasp.org/API-Security/editions/2023/en/0xa2-broken-authentication/

8. **OWASP API Security — Unrestricted Resource Consumption**  
   https://owasp.org/API-Security/editions/2023/en/0xa4-unrestricted-resource-consumption/

---

# 36. Final Product Decision Summary

FebGrid Phase 4.5 will introduce a full company-scoped Chat platform with:

- E2EE employee direct messages
- E2EE private custom groups
- managed company, department, team, and project channels
- company-controlled feature settings
- immutable employee handles
- secure rotatable connect codes
- group invitations and admin roles
- realtime messaging
- offline recovery
- device security
- encrypted private attachments
- blocking and reporting
- strict tenant isolation
- clear separation from AI and employee analytics

The owner controls whether Chat is available, but cannot decrypt private conversations.

The server controls membership and delivery, but private participants control private content.

The system must be built from reviewed standards and libraries, never custom cryptography.

This roadmap becomes the source of truth for Phase 4.5 implementation.
