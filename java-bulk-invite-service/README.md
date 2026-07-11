# FebGrid Bulk Invite Validation Service

This isolated Spring Boot service performs CSV parsing, row normalization, and
structural validation for the FebGrid bulk employee invite preview. It has no
database configuration, no FebGrid models, no email integration, and no
invitation-token logic.

FebGrid's Python backend remains responsible for authentication, company access,
live database validation, invitation creation, email preparation, events, and
notifications. The Java service is called only by the Python backend over an
internal network.

## Local run

Use Java 17 or newer and Maven 3.9 or newer:

```powershell
mvn test
$env:FEBGRID_INTERNAL_SERVICE_KEY = "local-development-key"
mvn spring-boot:run
```

The validation endpoint requires `X-FebGrid-Service-Key`; the health endpoint
does not reveal configuration or secrets. Do not use a production service key
for local development and do not place one in this repository.

## Docker and production boundary

Build the service locally:

```powershell
docker build -t febgrid-bulk-invite-validation .
```

For development only, bind it to loopback so the Python backend on the same
machine can reach it:

```powershell
docker run --rm -p 127.0.0.1:8080:8080 -e FEBGRID_INTERNAL_SERVICE_KEY=<development-only-value> febgrid-bulk-invite-validation
```

For production, run this container only on the private Docker/service network
shared with the FebGrid Python backend. Do not publish port `8080` publicly.
Python calls the validator with `JAVA_BULK_INVITE_BASE_URL` and a matching
`JAVA_BULK_INVITE_SERVICE_KEY`; neither value belongs in source control. The
service has no database configuration, user authentication, email delivery,
invitation token generation, or FebGrid business operations.

Endpoints:

- `GET /internal/v1/health`
- `POST /internal/v1/bulk-invites/validate` with a multipart `file` field

Limits default to 2 MiB and 500 data rows. They can be changed at runtime with
`BULK_INVITE_MAX_FILE_BYTES` and `BULK_INVITE_MAX_ROWS`.

## CSV contract

Required columns are `email`, `full_name`, `job_title`, and `role`. Optional
columns are `department`, `team`, `manager_email`, `employment_type`, `phone`,
and `employee_code`. Headers are case-insensitive and surrounding whitespace is
trimmed. The service returns row-level validation only; Python performs the
company-aware department, team, manager, employee, invitation, role, and
employee-code checks before creating any invitations.
