# FebGrid Java Bulk Employee Invite System Roadmap

**Document status:** Implementation-ready  
**Target:** Production-ready bulk employee invitation feature in 3 focused Codex steps  
**Primary goal:** Add a meaningful Java component to FebGrid without replacing, duplicating, or destabilizing the existing Python FastAPI backend or React frontend  
**Recommended repository path:** `docs/FebGrid_Java_Bulk_Invite_System_Roadmap.md`

---

## 1. Purpose

FebGrid already supports single employee invitation and manual employee onboarding through the existing Python FastAPI backend.

This feature adds a **Bulk Employee Invite system** where an authorized user uploads a CSV file, previews validation results, confirms the operation, and sends invitations to all valid employees in the file.

The Java component must have a real, clearly explainable responsibility:

> FebGrid uses Python FastAPI as the primary backend, while the Bulk Employee Invite CSV Validation Engine is implemented as an independent Java Spring Boot service.

This feature must be added with minimal changes and must not break the current invitation, employee, authentication, company, department, team, notification, email, or frontend flows.

---

## 2. Core Architecture

### 2.1 Responsibilities

```text
React frontend
    |
    | Upload CSV / preview / confirm
    v
Python FastAPI backend
    |
    | Authentication
    | Tenant/company validation
    | Role and permission checks
    | Existing employee/invitation checks
    | Existing invitation creation
    | Secure invitation token generation
    | Email delivery
    | Audit events and notifications
    |
    | Internal HTTP request
    v
Java Spring Boot Bulk Invite Service
    |
    | CSV parsing
    | Required-column validation
    | Row normalization
    | Email-format validation
    | Duplicate-row detection
    | Row-level validation results
    | Bulk summary generation
```

### 2.2 Critical safety rule

The Java service must **not**:

- connect directly to the FebGrid PostgreSQL/Supabase database;
- create employees or invitation records;
- generate invitation tokens;
- send invitation emails;
- perform FebGrid authentication;
- determine company access independently;
- duplicate Python invitation business logic;
- modify existing single-invite endpoints;
- become required for unrelated FebGrid pages to load.

The Python backend remains the only authority for:

- authentication and authorization;
- tenant isolation;
- company membership;
- roles and capabilities;
- departments, teams, and managers;
- employee existence checks;
- invitation creation;
- token generation;
- email sending;
- audit events and notifications;
- database transactions.

---

## 3. End-to-End Flow

### 3.1 Preview

```text
1. Authorized user clicks Bulk Invite.
2. React opens a modal/page.
3. User downloads a template or uploads a CSV.
4. React sends the file to Python:
   POST /api/v1/companies/{company_id}/bulk-invites/preview
5. Python checks:
   - authenticated user;
   - active company membership;
   - company/tenant match;
   - invite permission;
   - file type and size.
6. Python forwards the file internally to Java:
   POST /internal/v1/bulk-invites/validate
7. Java parses and validates the CSV.
8. Java returns normalized rows and row-level errors.
9. Python enriches validation using live FebGrid data:
   - existing employees;
   - existing active invitations;
   - roles;
   - departments;
   - teams;
   - managers.
10. Python returns the preview to React.
11. React displays valid, invalid, duplicate, existing, and warning rows.
```

### 3.2 Confirmation

```text
1. User reviews the preview.
2. User clicks Send Invitations.
3. React calls:
   POST /api/v1/companies/{company_id}/bulk-invites/confirm
4. Request includes a short-lived preview token and idempotency key.
5. Python revalidates user, company, token, and current database state.
6. Python calls the existing single-invitation service internally for each valid row.
7. Existing email, token, audit, notification, and onboarding logic is reused.
8. Python returns row-level outcomes.
9. React shows the final summary and error report.
```

---

## 4. Technology

### Java

- Java 21 preferred; Java 17 acceptable
- Spring Boot
- Maven
- Apache Commons CSV
- Jakarta Validation
- JUnit 5
- Spring Boot Test

### Existing FebGrid

- Python FastAPI
- SQLAlchemy/Supabase/PostgreSQL
- existing authentication and permissions
- existing invitation and email flow
- existing audit/event engine
- React frontend and current design system

### Explicitly avoid

- Kafka;
- RabbitMQ;
- Redis as a new mandatory dependency;
- Java database access;
- Java email sending;
- second authentication system;
- duplicate invitation tables;
- replacing existing onboarding;
- unrelated refactoring.

---

## 5. Repository Structure

```text
FebGrid/
├── backend/
├── frontend/
├── java-bulk-invite-service/
│   ├── pom.xml
│   ├── Dockerfile
│   ├── README.md
│   └── src/
│       ├── main/
│       │   ├── java/com/febgrid/bulkinvite/
│       │   │   ├── BulkInviteApplication.java
│       │   │   ├── controller/
│       │   │   ├── service/
│       │   │   ├── parser/
│       │   │   ├── validation/
│       │   │   ├── model/
│       │   │   ├── security/
│       │   │   └── exception/
│       │   └── resources/application.yml
│       └── test/
└── docs/
    └── FebGrid_Java_Bulk_Invite_System_Roadmap.md
```

---

## 6. CSV Contract

### Required columns

```csv
email,full_name,job_title,role
```

### Optional columns

```csv
department,team,manager_email,employment_type,phone,employee_code
```

### Template

```csv
email,full_name,job_title,role,department,team,manager_email,employment_type,phone,employee_code
rahul@example.com,Rahul Patil,Backend Developer,employee,Software Engineering,Backend,manager@example.com,full_time,+919999999999,EMP-001
priya@example.com,Priya Shah,UI Designer,employee,Design,Product Design,manager@example.com,full_time,+918888888888,EMP-002
```

### Rules

- UTF-8;
- header row required;
- case-insensitive header matching;
- trim surrounding whitespace;
- ignore empty lines;
- recommended maximum size: 2 MB;
- recommended maximum rows: 500;
- report duplicate emails inside the same CSV;
- neutralize spreadsheet-formula injection in exported reports;
- unknown columns generate warnings, not hard failures;
- malformed CSV returns a safe structured error;
- do not log CSV contents;
- delete temporary files immediately.

---

## 7. Java Responsibilities

### File validation

- file exists and is non-empty;
- accepted CSV type;
- size within limit;
- valid CSV syntax;
- required headers present;
- row count within limit;
- supported encoding.

### Row validation

- email required and syntactically valid;
- full name required;
- job title required;
- role required;
- duplicate email detection;
- optional phone validation;
- maximum field lengths;
- control-character checks;
- whitespace/case normalization;
- quoted commas and multiline values;
- row number preserved.

### Java response

```json
{
  "requestId": "request-id",
  "fileName": "employees.csv",
  "totalRows": 5,
  "validRowCount": 3,
  "invalidRowCount": 2,
  "duplicateRowCount": 1,
  "rows": [
    {
      "rowNumber": 2,
      "status": "VALID",
      "normalized": {
        "email": "rahul@example.com",
        "fullName": "Rahul Patil",
        "jobTitle": "Backend Developer",
        "role": "employee",
        "department": "Software Engineering",
        "team": "Backend",
        "managerEmail": "manager@example.com",
        "employmentType": "full_time",
        "phone": "+919999999999",
        "employeeCode": "EMP-001"
      },
      "errors": [],
      "warnings": []
    }
  ]
}
```

Java must never receive or return passwords, invitation tokens, user sessions, database credentials, or production secrets.

---

## 8. Python Integration

### Public endpoints

```text
GET  /api/v1/companies/{company_id}/bulk-invites/template
POST /api/v1/companies/{company_id}/bulk-invites/preview
POST /api/v1/companies/{company_id}/bulk-invites/confirm
```

An operation-status endpoint is optional and should be omitted initially unless needed.

### Java endpoints

```text
POST /internal/v1/bulk-invites/validate
GET  /internal/v1/health
```

One Java validation endpoint is enough.

### Reuse existing invitation logic

Codex must locate the existing single-employee invitation service/use case.

Bulk confirmation must call the same internal service. It must not:

- call the public route repeatedly;
- copy invitation logic;
- manually create invitation records;
- create tokens separately;
- send email through a new path.

If invitation logic is currently embedded in a route, make only a small safe refactor:

```text
Existing single-invite route
    -> shared invitation service

Bulk confirmation
    -> same shared invitation service
```

The existing single-invite API and behavior must remain unchanged.

### Database validation in Python

- employee does not already exist in the company;
- active/pending invitation does not already exist;
- role is allowed;
- inviter may assign that role;
- department exists in the same company;
- team exists in the same company;
- team/department relationship is valid;
- manager exists and is active in the same company;
- employee code is unique if supplied;
- invited email follows the existing exact-email activation rule.

### Preview token

Python should return a signed, short-lived preview token:

- company ID;
- user ID;
- hash of normalized rows;
- expiry of 15–30 minutes.

Confirmation must verify the token and still revalidate database state.

---

## 9. Permissions and Tenant Isolation

Use the current FebGrid capability system. Do not invent a separate permission model.

Expected authorized actors:

- owner;
- authorized admin;
- HR with invite capability;
- manager with invite capability.

Required checks:

- authenticated user;
- active company membership;
- current tenant/company match;
- existing invite capability;
- no cross-company resource references;
- departments, teams, and managers belong to the same company.

Java never decides tenant permissions.

---

## 10. Internal Service Security

- internal network only where possible;
- dedicated service key;
- secrets from runtime environment only;
- never commit or print secrets;
- strict request-size limits;
- strict timeouts;
- reject unsupported content types;
- generic errors;
- no row-content logging;
- health endpoint contains no sensitive information.

Recommended headers:

```text
X-FebGrid-Service-Key: <secret>
X-Request-ID: <request-id>
```

Recommended Python timeout:

```text
connect: 3 seconds
read: 20 seconds
```

If Java is unavailable:

- preview returns `503`;
- existing single invite and all other FebGrid functions continue working;
- backend startup must not fail;
- frontend displays retry guidance;
- no invitation is partially created during preview.

---

## 11. Idempotency and Partial Failure

React sends an idempotency key on confirmation.

Python must prevent duplicate invitation creation if the same request is retried.

Each row is processed independently through the shared invitation service.

Possible statuses:

```text
INVITED
SKIPPED_EXISTING_EMPLOYEE
SKIPPED_ACTIVE_INVITATION
SKIPPED_DUPLICATE_CSV_ROW
FAILED_VALIDATION
FAILED_EMAIL
FAILED_INTERNAL
```

One failed row must not cancel successful rows.

---

## 12. Frontend

Replace the current disabled **Bulk invite CSV later** control with a permission-aware production action.

### Three-stage UI

```text
1. Upload
2. Preview
3. Confirm and result
```

### Upload

- drag and drop;
- file picker;
- download template;
- accepted format and limits;
- progress;
- cancel.

### Preview

- total rows;
- valid/invalid/duplicate/warning counts;
- existing employee/invitation counts;
- filterable row table;
- row number;
- email;
- name;
- assignment;
- status;
- validation message;
- continue with valid rows only.

Editing rows inside FebGrid is out of scope; users correct and re-upload the CSV.

### Confirmation

- exact count to invite;
- explicit confirmation;
- disabled submit while processing;
- double-submit protection.

### Result

- invited successfully;
- already employees;
- already invited;
- invalid;
- failed;
- detailed row results;
- retry for eligible failures;
- downloadable error report;
- link back to Employees.

### UI safety

- reuse current FebGrid components;
- preserve light/dark mode;
- preserve responsive layout;
- do not redesign unrelated employee sections;
- do not change single-invite UX;
- accessible labels and focus handling.

---

## 13. Audit and Notifications

Reuse existing audit/event infrastructure.

Recommended events:

```text
bulk_invite_preview_generated
bulk_invite_confirmed
bulk_invite_completed
bulk_invite_partially_failed
bulk_invite_failed
employee_invited_via_bulk
```

Do not store raw CSV contents, invitation tokens, secrets, or unnecessary personal data in audit logs.

Successful invitations should produce the same normal invitation notifications/events as single invites.

---

## 14. Errors

Recommended error codes:

```text
BULK_INVITE_FILE_REQUIRED
BULK_INVITE_FILE_TOO_LARGE
BULK_INVITE_UNSUPPORTED_FILE
BULK_INVITE_MISSING_HEADERS
BULK_INVITE_TOO_MANY_ROWS
BULK_INVITE_MALFORMED_CSV
BULK_INVITE_VALIDATION_FAILED
BULK_INVITE_PREVIEW_EXPIRED
BULK_INVITE_PREVIEW_MISMATCH
BULK_INVITE_PERMISSION_DENIED
BULK_INVITE_SERVICE_UNAVAILABLE
BULK_INVITE_CONFIRMATION_IN_PROGRESS
BULK_INVITE_INTERNAL_ERROR
```

Never expose stack traces or raw Java/Python exception messages.

---

## 15. Initial Production Limits

```text
Maximum file size: 2 MB
Maximum rows: 500
Preview expiry: 20 minutes
Java read timeout: 20 seconds
Processing: synchronous
```

A background queue is not required for this first release.

---

## 16. Backward Compatibility

The following must continue working unchanged:

- single invitation;
- manual employee add;
- invitation acceptance;
- pre-verification and approval;
- resend/revoke;
- employee login and activation;
- exact invited-email enforcement;
- department/team/manager assignment;
- notifications and audit events;
- company switching;
- role-based sidebar;
- Employees page;
- existing APIs;
- existing migrations.

No existing endpoint may be removed or renamed.

Any invitation-service refactor requires regression tests for the original route.

---

## 17. Database Strategy

Prefer no new table:

- signed preview token;
- existing invitation records;
- existing events;
- request-scoped result.

Only add one small `BulkInviteOperation` table if idempotency/status truly requires it:

```text
id
company_id
actor_user_id
idempotency_key
file_name
total_rows
valid_rows
invited_rows
skipped_rows
failed_rows
status
created_at
completed_at
```

Never store raw CSV files or invitation tokens.

Do not create a Java database.

---

## 18. Testing

### Java

- valid CSV;
- missing headers;
- malformed CSV;
- empty file;
- duplicate emails;
- invalid emails;
- whitespace normalization;
- quoted commas;
- multiline values;
- row limit;
- oversized fields;
- optional fields;
- formula-injection-safe export values;
- deterministic row numbers;
- no content logging;
- service-key protection;
- wrong content type;
- request too large;
- health endpoint.

### Python

- allowed and denied permissions;
- tenant isolation;
- Java success/timeout/unavailable;
- existing employee;
- active invitation;
- invalid department/team;
- foreign manager;
- denied role assignment;
- preview expiry/tampering;
- confirmation revalidation;
- idempotent retry;
- partial success;
- shared invitation regression;
- no duplicate invitations.

### Frontend

- authorized/unauthorized action;
- upload;
- invalid file;
- preview filters;
- confirmation;
- double-submit protection;
- partial results;
- Java unavailable;
- light/dark mode;
- accessibility basics;
- Employees page regression.

### Browser QA

1. Owner uploads valid CSV.
2. Preview shows valid rows.
3. Confirmation sends invitations.
4. Pending invitations update.
5. Existing email flow is used.
6. One invite is accepted with the exact invited email.
7. Mixed valid/invalid CSV.
8. Existing employee.
9. Existing invitation.
10. Duplicate email.
11. Unauthorized user denied.
12. Company switch causes no leakage.
13. Stop Java service: bulk preview fails safely while FebGrid remains usable.
14. Existing single invite still works.

---

## 19. Deployment

Recommended services:

```text
febgrid-backend
febgrid-frontend
febgrid-java-bulk-invite
```

Java should be reachable only from Python over an internal Docker network.

### Python environment placeholders

```text
JAVA_BULK_INVITE_BASE_URL
JAVA_BULK_INVITE_SERVICE_KEY
JAVA_BULK_INVITE_TIMEOUT_SECONDS
BULK_INVITE_MAX_ROWS
BULK_INVITE_MAX_FILE_BYTES
```

### Java environment placeholders

```text
FEBGRID_INTERNAL_SERVICE_KEY
SERVER_PORT
BULK_INVITE_MAX_ROWS
BULK_INVITE_MAX_FILE_BYTES
```

Only update `.env.example`. Never read, print, overwrite, stage, or commit the real `.env`.

Python startup must not fail when Java is unavailable.

---

# 20. Three-Step Codex Plan

The feature must be completed in **three substantial steps maximum**. Do not split it into many small tasks.

---

## Step 1 — Java Engine and Safe Python Foundation

### Goal

Build the complete Java CSV validation service and connect it safely to the existing Python architecture without changing existing invitation behavior.

### Codex preflight

Read:

- `docs/FebGrid_Java_Bulk_Invite_System_Roadmap.md`
- `docs/FebGrid_Product_Requirements_Document.md`
- current invitation implementation;
- employee permissions/capabilities;
- department/team/manager models;
- email flow;
- audit/event flow;
- `AGENTS.md`;
- `README.md`.

Inspect:

- git status;
- Alembic heads;
- current tests;
- Docker configuration;
- `.env.example`;
- frontend API conventions.

Preserve unrelated uncommitted changes.

### Implement Java

- Spring Boot project;
- Maven;
- CSV parser;
- normalization;
- validation;
- duplicate detection;
- structured models/errors;
- request limits;
- service-key security;
- health endpoint;
- tests;
- Dockerfile;
- README.

### Implement Python foundation

- Java client;
- typed response schemas;
- timeout and safe errors;
- template endpoint;
- preview endpoint;
- permission/tenant checks;
- database enrichment validation;
- signed preview token;
- small shared invitation-service refactor only if required;
- regression tests for single invite.

Do not build the full frontend flow yet.

### Acceptance

- Java build/tests pass;
- Python tests pass;
- Java validates CSV independently;
- Python remains authority;
- single invite unchanged;
- backend starts without Java;
- no Java DB/email/token logic;
- no secrets;
- one Alembic head;
- no automatic commit.

---

## Step 2 — Frontend and Complete Invitation Flow

### Goal

Deliver the complete UI and confirmation flow using the existing Python invitation service.

### Implement frontend

- enable Bulk Invite;
- permission-aware action;
- template download;
- upload;
- preview;
- filters;
- row statuses;
- confirmation;
- result screen;
- error report;
- idempotency key;
- safe retry;
- loading/error states;
- responsive/light-dark/accessibility.

### Implement Python confirmation

- confirm endpoint;
- preview-token validation;
- company/user validation;
- database revalidation;
- idempotency;
- per-row shared invitation calls;
- partial success;
- audit events;
- existing notifications/emails;
- no duplicates.

### Integration

- Docker Compose service if applicable;
- `.env.example`;
- internal network;
- health behavior;
- local startup docs.

### Acceptance

- preview works;
- invalid rows visible;
- confirmation uses existing invitation flow;
- pending invitations update;
- exact-email rule preserved;
- mixed outcomes work;
- retries do not duplicate;
- tenant/permission tests pass;
- single invite still works;
- all builds/lints/tests pass;
- no automatic commit.

---

## Step 3 — Production Hardening and Release QA

### Goal

Complete security hardening, regression QA, browser QA, cleanup, and release documentation.

### Security

- internal authentication;
- file/request limits;
- timeouts;
- no CSV logging;
- no secrets;
- CSV injection handling;
- preview tamper resistance;
- tenant isolation;
- permission matrix;
- idempotency;
- temp-file cleanup;
- generic errors;
- Java not publicly exposed.

### Verification

Run:

- Java full tests;
- Python targeted/regression tests;
- frontend tests;
- backend compile/import;
- SQLAlchemy mapper checks;
- Alembic checks;
- frontend build/lint;
- `git diff --check`;
- secret scan;
- `.env` ignore verification.

### Browser QA

Complete all scenarios in Section 18.

### Cleanup

Remove:

- temporary CSVs;
- debug logs;
- unneeded build artifacts;
- test credentials;
- temporary containers;
- unused code/dependencies.

### Documentation

Update:

- root README;
- Java README;
- API docs;
- local setup;
- CSV template instructions;
- architecture;
- limits;
- college explanation.

### Final report

Report:

- exact files changed;
- endpoints;
- Java/Python responsibilities;
- DB changes;
- tests;
- browser QA;
- limitations;
- release decision;
- suggested commit command.

Do not commit automatically.

---

## 21. Out of Scope

- `.xlsx`;
- thousands of rows/background queues;
- scheduled invites;
- external guests;
- multi-company CSV;
- Java database access;
- Java email sending;
- second onboarding system;
- replacing FastAPI;
- Chat-system changes;
- AI processing of CSVs;
- employee scoring;
- unrelated redesign;
- unrelated billing changes.

---

## 22. College Explanation

> FebGrid is a polyglot application. Python FastAPI manages authentication, permissions, employee records, invitation tokens, emails, and database operations. The Bulk Employee Invite CSV Validation Engine is implemented as a Java Spring Boot microservice. Java parses and validates employee files, detects invalid and duplicate rows, and returns a structured preview. Python then creates invitations through the same secure onboarding flow used for individual invitations.

Suggested demonstration:

1. Open Employees.
2. Open Bulk Invite.
3. Show CSV template.
4. Upload valid and invalid rows.
5. Show Java-generated validation.
6. Confirm valid invitations.
7. Show pending invitations.
8. Show Java parser/tests.
9. Show Python integration and explain why Python remains the authority.

---

## 23. Strict Codex Rules

Codex must:

- treat this file as source of truth;
- preserve current architecture;
- reuse invitation logic;
- keep Java isolated;
- make minimal Python/frontend changes;
- avoid unrelated refactors;
- protect tenant boundaries;
- preserve exact-email activation;
- keep Chat work separate;
- never touch/expose `.env`;
- never commit automatically;
- stop and report migration, permission, or regression blockers;
- complete the feature in three steps maximum.

---

## 24. Short Codex Start Prompt

```text
Continue FebGrid development from the current repository state.

Read and follow:
- docs/FebGrid_Java_Bulk_Invite_System_Roadmap.md
- docs/FebGrid_Product_Requirements_Document.md
- AGENTS.md
- README.md

Execute only Step 1 — Java Engine and Safe Python Foundation.

Preserve all existing employee invitation, onboarding, permission, email, audit, notification, backend, and frontend flows.

Java must remain an isolated CSV validation service. It must not access the database, generate invitation tokens, send email, or replace Python business logic.

Do not start Step 2, do not touch or expose .env, and do not commit automatically.

Finish with files changed, tests run, regressions checked, blockers, and whether Step 2 is safe to begin.
```
