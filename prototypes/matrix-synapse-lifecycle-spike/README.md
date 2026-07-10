# Matrix Synapse Lifecycle Spike

Phase 4.5 Step 0.2 only. This disposable Docker environment is separate from
FebGrid. It uses synthetic Matrix accounts, two isolated internal networks, two
Synapse instances, and two PostgreSQL instances. The generated `data/` folder
contains ephemeral signing keys and must never be committed.

The probe is intended to validate a real Matrix server lifecycle: registration,
encrypted room creation, invite/join, encrypted messaging, a second device,
member removal, encrypted attachments, federation listener exposure, and
cross-company denial. It does not contain a FebGrid production authentication
bridge; that remains a reviewed design gate.

All containers, volumes, media, generated keys, and test accounts must be
destroyed after the spike. No FebGrid `.env`, database, account, or upload is
used.
