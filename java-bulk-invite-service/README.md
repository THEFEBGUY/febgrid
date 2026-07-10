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

Endpoints:

- `GET /internal/v1/health`
- `POST /internal/v1/bulk-invites/validate` with a multipart `file` field

Limits default to 2 MiB and 500 data rows. They can be changed at runtime with
`BULK_INVITE_MAX_FILE_BYTES` and `BULK_INVITE_MAX_ROWS`.
