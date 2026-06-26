# FebGrid Employee Onboarding Bridge Plan

## Document purpose

This document defines the next FebGrid bridge step before continuing deeper into Phase 2.

**Bridge step name:** Phase 1/2 Bridge — Employee Invitation, Manual Employee Activation, Account Linking, and Employee POV Dashboard.

This file should be used by Codex together with:

- `docs/FebGrid_Product_Requirements_Document.md`
- `AGENTS.md`
- `README.md`

The PRD remains the primary source of truth. This document clarifies the missing employee onboarding/account lifecycle and employee POV work that must be added without breaking existing completed features.

---

## Current completed FebGrid work

The project already has the following completed foundations:

- Phase 1 core foundation completed.
- Company/User Foundation completed.
- Employee Management completed.
- Project Management Foundation completed.
- Work Object Engine v1 completed.
- Leave Management v1 completed.
- File Upload v1 completed.
- Notification v1 completed.
- Event/Notification Stream Polish completed.
- Communication Layer Phase 1 completed.
- Basic Dashboard / Sprint 9 Dashboard Polish completed.
- Light/Dark mode toggle completed.
- Phase 2 Step 1 completed: Operational Search v1, Better Filters, Activity Feed improvements, Audit Log foundation.
- Phase 2 Step 2 completed: Advanced Notifications, Mention Improvements, Notification Preferences, Email Alert Preparation.
- Phase 2 Step 3 completed: Company Settings, Industry Templates v1, Configurable Work Object Types, Custom Fields foundation.

---

## Why this bridge step is needed

Employee invitation, employee account activation, employee login, employee profile completion, employee dashboard, role-based access, assigned work visibility, leave submission, notifications, and employee self-profile are core PRD flows.

Existing employee CRUD already exists, but the full employee account lifecycle is still missing:

- Owner/Admin/HR/Manager should be able to invite an employee.
- Employee should receive an email/link.
- Employee should activate/login only using the invited/added email.
- Employee should see the company they were invited/added to.
- Employee should fill missing profile information.
- Employee should join directly or wait for approval depending on pre-verification setting.
- Employee should get a limited employee POV dashboard and role-based sidebar.

This must be completed before continuing with Phase 2 Step 4.

---

## Do not build in this bridge step

Do not build or add:

- AI
- Company Pulse
- Employee Digital Twin
- Billing/payment
- Real external email provider setup
- WhatsApp/SMS
- MCP
- Mobile app
- OCR/file parsing
- Chat/DM system
- Complex HRMS payroll
- Attendance/payroll
- Domain protection
- Full redesign
- Full CSV bulk import implementation now

---

## Confirmed selected requirements

These features are confirmed and selected:

1. Invite preview page.
2. Pre-filled + employee-filled profile.
3. Invite resend/revoke.
4. Bulk invite CSV later as future-ready placeholder only.
5. Approval/pre-verification mode.
6. Employee POV dashboard.
7. Role-based sidebar.
8. Audit/events for invite/account/profile/approval/manual activation actions.
9. Keep existing manual create/add employee flow.
10. Manual employee activation email/link after manual add.
11. Employee must activate/login only with the same email used in invite or manual add.
12. No random person can join a company.

Not selected for now:

- Domain protection. Do not implement company email-domain restriction unless requested later.

---

## Overall onboarding flows

FebGrid must support two onboarding flows.

### Flow 1: Invite-first employee onboarding

1. Owner/Admin/HR/Manager sends invitation.
2. Invite email/link is generated using a secure token.
3. Employee clicks link.
4. Employee sees invite preview page with company and role information.
5. Employee signs up/logs in using the exact invited email only.
6. Employee fills missing profile information.
7. If pre-verification is OFF, employee joins directly.
8. If pre-verification is ON, employee waits for authorized approval.
9. After approval, employee joins company FebGrid system.
10. Employee sees employee POV dashboard and limited sidebar.

### Flow 2: Manual employee add + activation

1. Owner/Admin/HR/Manager manually creates employee by entering all details.
2. Employee record appears in company employee directory.
3. Employee account/login remains pending until activation.
4. FebGrid sends activation email/link to the same email used in employee creation.
5. Email lists company/profile information and the exact login email.
6. Employee clicks accept/activate.
7. Employee sees preview page with company and profile details.
8. Employee activates/logs in using the same added email only.
9. Employee account is linked to the manually created employee record.
10. Employee enters employee POV dashboard.

---

## Core security rule

Even if an employee is manually added, the employee must not be able to join using a different email.

Backend must validate:

- token
- invited/added email
- company
- invitation/activation status
- expiry
- revoked state
- accepted state

The frontend must not be trusted for company ID, email, or role.

---

## Roles allowed to invite/manual add/approve

Use the existing role and permission system.

Allowed roles should include, only where safely supported by current architecture:

- Owner
- Admin
- HR
- Manager

Rules:

- Owner/Admin should have full company-scoped onboarding permissions.
- HR should have employee/invite/profile/leave-related onboarding permissions if HR role exists.
- Manager should be allowed to invite/manage only where existing permission pattern supports it safely, ideally team-scoped where applicable.
- Employee must not invite, approve, revoke, or manually add other employees.
- Backend must enforce permissions. Frontend sidebar hiding is not security.

---

## Invite-first flow requirements

### Invite form fields

The invite form should support:

- employee email
- role
- department optional
- team optional
- manager optional
- job title optional
- joining date optional
- employment type optional
- approval/pre-verification required toggle
- expiry duration if simple
- optional note/message

### Invite behavior

When invitation is sent:

- Create an invitation record.
- Do not create a fully active user immediately.
- Optionally create a pending employee shell/profile if needed.
- Generate secure invitation token.
- Store only token hash in database, not the raw token.
- Send invite email using existing EmailService placeholder/outbox/dev-safe mechanism.
- Do not add real SMTP/SendGrid/Resend credentials.
- For local dev, expose/copy invitation link safely after sending or show through dev-safe email placeholder/outbox.
- Generate an event such as `employee_invite.sent` or `employee.invited`.
- Generate useful notifications, but avoid noise.

### Invitation statuses

Invitation status should support:

- `pending`
- `accepted`
- `expired`
- `revoked`
- `submitted_for_approval`
- `approved`
- `rejected`

---

## Invite preview page requirements

Add a public route such as:

- `/join/:token`
- or `/accept-invite/:token`

Preview page must:

- Validate token before showing sensitive information.
- Show company name.
- Show inviter name if safe.
- Show invited email.
- Show role.
- Show department/team/manager/job title/joining date if prefilled.
- Show whether approval/pre-verification is ON or OFF.
- Show expiry information.
- Show clear CTA:
  - “Create account with this email”
  - or “Login with this email”
- If token is expired/revoked/accepted, show clear error state.
- Not show unrelated company data.
- Not allow changing company.
- Not allow changing invited email.

---

## Account activation / signup from invite

Rules:

- User must use exactly the invited email.
- Email matching should be case-insensitive and normalized consistently.
- Backend must validate token hash, expiry, company, invited email, revoked state, and accepted state.
- Frontend can show the email as read-only.
- Backend must not trust frontend email/company ID.
- If no user exists for that email, allow setting password and creating user.
- If user already exists with the same email and safe company context, allow login/linking safely.
- If user exists in conflicting unsupported company context, return a clear error instead of unsafe linking.
- Link user account to employee record.
- Link employee record to company.
- Role must come from invitation/admin, not employee input.
- Employee cannot choose company or role manually.

---

## Employee-filled profile requirements

After invite acceptance, employee should fill missing personal/profile fields:

- full name
- phone optional
- profile photo optional only if existing upload supports it safely, otherwise skip
- location/address optional
- skills optional
- bio optional
- emergency contact optional if simple
- any missing employee fields safe for employee to fill

Employee should not be able to change:

- company
- assigned role
- department if company prefilled and locked
- team if company prefilled and locked
- manager if company prefilled and locked
- approval/pre-verification mode
- invited email

If fields are prefilled by company:

- show them clearly
- allow employee to review
- lock company-controlled fields unless existing permission model says otherwise

---

## Approval / pre-verification mode

Approval/pre-verification must support two levels:

1. Company-level default setting if suitable.
2. Per-invite toggle that can use or override the company default.

### Confirmation popup before sending invite

Before sending invite or activation message, show a confirmation popup.

If approval/pre-verification is ON, show:

> You have turned ON pre-verification. The employee can submit their profile, but they will not fully join the company FebGrid system until an authorized company user approves them.

If approval/pre-verification is OFF, show:

> You have kept pre-verification OFF. After the employee accepts the invite and completes their profile, they can directly join the company FebGrid system.

### Flow when approval/pre-verification is ON

1. Employee accepts invite.
2. Employee creates/logs into account.
3. Employee fills profile.
4. Status becomes `submitted_for_approval` or `pending_approval`.
5. Owner/Admin/HR/Manager sees pending approval.
6. Authorized user can approve or reject.
7. On approve:
   - employee becomes active/accepted
   - invitation becomes accepted/approved
   - user can access employee POV
   - event generated
   - notification generated
8. On reject:
   - employee remains inactive/rejected
   - invitation/profile status rejected
   - employee sees rejection message
   - event generated

### Flow when approval/pre-verification is OFF

1. Employee accepts invite.
2. Employee creates/logs into account.
3. Employee fills profile.
4. Employee becomes active immediately.
5. Invitation becomes accepted.
6. Employee enters employee POV dashboard.

---

## Manual employee add flow requirements

Keep the existing manual add/create employee flow.

Owner/Admin/HR/Manager can still manually create an employee by entering all details themselves.

Manual add behavior:

- Employee record is created in company.
- Employee appears in company employee directory.
- Employee account/login is pending until employee accepts/activates.
- Send email/activation message to employee using existing EmailService placeholder/outbox/dev-safe mechanism.
- Email must say they were added to FebGrid by that company.
- Employee clicks accept.
- Employee preview page shows company and profile info.
- Employee activates/logs in with the same email only.
- Backend validates token + added email + company.
- No different email can activate this employee account.

### Manual add email/activation message must include

- company name
- added/invited by person
- employee name
- role
- department
- team
- manager
- joining date if present
- work/login email
- clear message: “Use this same email to activate/login to FebGrid”
- accept/activate button/link
- expiry date

### Manual flow statuses

Manual activation statuses should support:

- `manually_added_pending_activation`
- `activation_sent`
- `activated`
- `expired`
- `revoked`

Do not remove or break current manual employee CRUD. Improve it safely.

---

## Invite resend / revoke requirements

Authorized users must be able to manage invites.

Required actions:

- View pending invitations.
- Resend invitation.
- Revoke invitation.
- See expired invitations.
- See accepted invitations.
- Resend manual activation email for manually added employees if practical.

Rules:

- Resend should create a new token or refresh expiry safely.
- Old token should be invalidated if new token is issued.
- Revoke should immediately block token usage.
- Accepted invites cannot be reused.
- Expired invites cannot be accepted unless resent.

Events:

- `employee_invite.resent`
- `employee_invite.revoked`
- `employee_invite.expired` if handled
- `manual_employee_activation.resent`

---

## Bulk invite CSV later

Do not implement full CSV bulk invite now.

Add only future-ready placeholder if simple:

- disabled button or “Coming later” UI text
- service/model structure should not block future bulk invites
- no CSV parsing now
- no complex import engine now

---

## Employee POV dashboard requirements

After login/activation, employee should get a limited employee-specific dashboard.

Employee should see:

- company name/info
- own profile status
- own assigned work objects
- own work status summary
- own leave requests
- submit leave button
- own notifications
- own mentions/comments if available
- company announcements
- recent activity relevant to them
- files/uploads related to their work if existing data supports it safely

Employee should not see:

- company-wide admin settings
- billing
- all employee management controls
- all-company audit log unless role allows
- all-company data
- other employees’ private details
- owner/admin dashboard controls

Manager/HR/Admin/Owner should retain their current broader views.

---

## Role-based sidebar requirements

Update sidebar/navigation based on role.

### Owner/Admin sidebar

Owner/Admin should keep broad access based on current system.

### HR sidebar

HR should get employee/invite/profile/leave-related access only if role exists or current permission pattern supports it.

### Manager sidebar

Manager should get team/work/leave/invite access only if current permission pattern supports it safely.

### Employee sidebar

Employee should see a limited sidebar such as:

- My Dashboard
- My Work
- My Leave
- Notifications
- Announcements
- My Profile
- maybe Files related to own work if safe

Rules:

- Frontend hiding is not enough.
- Backend must enforce permissions.
- Do not trust sidebar visibility for security.

---

## My Profile page requirements

Add an employee self-profile page.

Employee can:

- view own profile
- update safe personal fields
- view company-controlled fields read-only
- see role/department/team/manager/company
- see account/activation status

Employee cannot:

- change role
- change company
- change department/team/manager unless authorized
- activate another employee
- view/edit another employee profile unless role allows

---

## Events and audit requirements

Generate events for:

- `employee_invite.sent`
- `employee_invite.resent`
- `employee_invite.revoked`
- `employee_invite.expired` if handled
- `employee_invite.accepted`
- `employee_profile.submitted`
- `employee_profile.approved`
- `employee_profile.rejected`
- `employee.joined`
- `manual_employee.created`
- `manual_employee.activation_sent`
- `manual_employee.activation_accepted`
- `employee_account.linked`
- `employee_role.assigned` if changed
- `employee_profile.updated`

Avoid noisy events such as preview tracking unless intentionally useful.

Audit requirements:

- Events must include `company_id`.
- Events must include `actor_user_id` where available.
- Events must include target employee/invite.
- Metadata must be safe.
- Metadata must not include raw token/password.
- Do not log raw invite tokens.
- Do not log passwords.
- Do not expose secret values.
- Important invite/profile actions should appear in Events/Audit pages.

---

## Notification requirements

Use existing NotificationService.

Notify:

- invited employee by email placeholder/outbox link
- owner/admin/HR/manager when approval is required
- employee when approved/rejected
- inviter when employee accepts/joins if useful
- employee when manually added/activation sent by email placeholder

Avoid:

- duplicate notifications
- useless self-notifications
- cross-company notifications
- noisy notifications for every preview/open

---

## Email placeholder / delivery preparation

Real external email provider setup is not part of this step.

Requirements:

- Use existing EmailService placeholder if available.
- Do not add real SMTP/SendGrid/Resend credentials.
- Do not require `.env` changes.
- Do not read, print, expose, or commit `.env` values.
- Generate clean email subject/body templates.
- Store email delivery metadata as pending/skipped/dev if existing pattern supports it.
- For local testing, provide invite/activation link in UI after sending or in dev-safe logs/outbox.
- Make it easy to connect real email later.

Email templates needed:

- invite-first employee invitation email
- manual employee added activation email
- invite resent email
- approval approved email
- approval rejected email

---

## Security measures

### Token security

Must enforce:

- Generate cryptographically secure random token.
- Store only token hash.
- Raw token appears only in email/link once.
- Token expires.
- Token can be used only once.
- Revoked token cannot be used.
- Resent invite invalidates old token if practical.
- Accepted invite cannot be reused.
- Do not expose token hash.
- Do not log raw token.

### Email/company security

Must enforce:

- Employee must activate/login with exact invited/added email.
- Email normalization should be case-insensitive and consistent.
- Backend must validate token + email + company.
- Employee cannot pass random company ID to join.
- Employee cannot change role/company from frontend.
- No random person can join without valid active invite/activation token.

### Permission security

Must enforce:

- Only authorized roles can invite/manual add/resend/revoke/approve/reject.
- Employee can only access own profile/work/leave/notifications.
- Manager/HR access must stay company-scoped and role-scoped.
- Owner/Admin full access remains company-scoped.
- Backend checks every protected route.

### Tenant security

Must enforce:

- All invite, employee, user, work, leave, notification, and event queries must be company-scoped.
- Cross-company token usage must fail.
- Cross-company profile/work/leave access must fail.
- Company selector must remain stable.
- No infinite refetch loops.

### Data security

Must enforce:

- Never store raw password.
- Never log password.
- Never log raw token.
- Never expose token hash.
- Never expose `.env`.
- Do not commit secrets.
- Do not include unnecessary sensitive info in public preview.
- Metadata JSON must be safe for null/non-dict values.

### Abuse prevention

Must enforce or add TODO where not yet supported:

- Prevent duplicate active invites for the same company/email unless resending.
- Prevent duplicate unsafe user/employee creation.
- Rate limiting is optional if architecture supports it; otherwise add TODO only.
- Clear error messages without leaking unrelated user/company existence.

---

## Suggested backend models/tables

Likely model/table:

`EmployeeInvitation` or `EmployeeInvite`

Suggested fields:

- `id`
- `company_id`
- `employee_id` nullable
- `invited_email`
- `normalized_email`
- `invited_role`
- `department_id` nullable
- `team_id` nullable
- `manager_employee_id` nullable
- `job_title` nullable
- `employment_type` nullable
- `joining_date` nullable
- `invite_source`: `invite_first` or `manual_add`
- `approval_required` boolean
- `status`
- `token_hash`
- `expires_at`
- `sent_at`
- `accepted_at`
- `revoked_at`
- `revoked_by_user_id` nullable
- `approved_at`
- `approved_by_user_id` nullable
- `rejected_at`
- `rejected_by_user_id` nullable
- `rejection_reason` nullable
- `invited_by_user_id`
- `metadata` JSON
- `created_at`
- `updated_at`

Existing employee model may need safe fields such as:

- `account_status`
- `activation_status`
- `user_id` or user link if not already present
- `profile_completion_status`

Keep backward compatibility with existing employees.

---

## Suggested backend endpoints

Public endpoints:

- `GET /api/v1/invitations/preview/{token}`
- `POST /api/v1/invitations/accept`
- `POST /api/v1/invitations/complete-profile`

Protected endpoints:

- `GET /api/v1/invitations?company_id=`
- `POST /api/v1/invitations`
- `POST /api/v1/invitations/{id}/resend`
- `POST /api/v1/invitations/{id}/revoke`
- `POST /api/v1/invitations/{id}/approve`
- `POST /api/v1/invitations/{id}/reject`
- `GET /api/v1/employees/me`
- `PATCH /api/v1/employees/me`
- `GET /api/v1/dashboard/my-summary`
- or `GET /api/v1/employee-dashboard/summary`

Manual employee activation:

- when employee is created manually, create activation invitation/source record
- send activation email placeholder
- support resend activation

Existing employee routes:

- keep existing employee create/edit/detail/status flows working
- add account/activation status if needed
- avoid breaking existing data

---

## Frontend implementation suggestions

Add pages/components:

- Invite preview/accept page
- Employee profile completion page
- Employee invitation management section
- Pending invitations list
- Pending approvals list
- Employee POV dashboard
- My Profile page
- Role-based sidebar logic

Update existing Employees page:

- Keep manual add employee.
- Add “Invite Employee” action.
- Manual add should also send activation email placeholder.
- Show activation/invite status.
- Show resend/revoke actions where applicable.
- Show pending approval status.
- Add approve/reject UI for authorized users.
- Add confirmation popup for approval/pre-verification setting before invite/manual activation send.

UI rules:

- Keep current design.
- Keep light/dark mode working.
- Keep action icons visible with `aria-label` and `title`.
- Include loading/error/empty states.
- No full redesign.
- No huge layout changes.
- Employee POV should feel simpler than admin dashboard.

---

## Database and migration rules

A migration will probably be needed.

If migration is needed:

- Add one Alembic migration per implementation part if necessary.
- Do not create duplicate Alembic heads.
- Existing employees must remain valid.
- Existing users must remain valid.
- Existing manually created employees should not break.
- Add indexes where useful:
  - `company_id`
  - `normalized_email`
  - `token_hash`
  - `status`
  - `expires_at`
  - `employee_id`
- Migration should be reversible where practical.

---

# Split implementation plan for Codex

Use this section to split the work into smaller safe Codex runs.

## Part 1 — Backend invitation + manual activation foundation

Implement backend foundation only.

### Part 1 scope

Build:

- invitation/activation model and migration
- secure token generation and hash storage
- invite-first backend APIs
- manual add activation backend behavior
- preview/accept/profile completion backend APIs
- approval ON/OFF backend flow
- resend/revoke backend APIs
- employee account linking backend rules
- employee `/me` backend endpoint if not present
- events/audit integration
- notification/email placeholder integration
- permission and tenant checks

Do not build full frontend UI yet except tiny backend-needed wiring if unavoidable.

### Part 1 backend verification

Run and report:

- `python -m compileall app alembic`
- backend import check
- SQLAlchemy mapper check
- Alembic heads check
- Alembic offline SQL render check
- `python -m alembic upgrade head`
- API route table check
- invitation create probe
- invite preview valid token probe
- expired token rejection probe
- revoked token rejection probe
- accepted token reuse rejection probe
- wrong email rejection probe
- wrong company rejection probe
- invite accept/profile complete probe
- approval required flow probe
- approval not required flow probe
- manual employee create activation probe
- manual activation accept same email probe
- manual activation wrong email rejection probe
- resend invalidates old token probe if implemented
- revoke blocks token probe
- employee `/me` access probe
- employee cannot access another employee probe if route exists
- cross-company isolation probe
- event creation probe
- notification/email placeholder metadata probe
- metadata serialization probe

### Part 1 Codex instruction

When starting Part 1, tell Codex:

> Read `docs/Employee_Onboarding_Bridge_Plan.md`, `docs/FebGrid_Product_Requirements_Document.md`, `AGENTS.md`, and `README.md`. Implement Part 1 only: Backend invitation + manual activation foundation. Do not start Part 2 or Part 3. Keep frontend changes minimal unless required for backend compatibility. Do not add real email provider, AI, billing, MCP, WhatsApp/SMS, OCR, or mobile features.

---

## Part 2 — Frontend admin/invite flow

Implement frontend/admin onboarding UI after Part 1 is tested and committed.

### Part 2 scope

Build:

- Invite Employee UI
- invite confirmation popup for approval/pre-verification ON/OFF
- pending invitations list
- resend/revoke actions
- pending approvals list
- approve/reject UI
- manual add employee activation link/email placeholder behavior display
- invite preview page
- accept/signup/login with invited/added email only
- profile completion page
- loading/error/empty states
- light/dark support
- icon accessibility

Do not build Employee POV dashboard/sidebar yet except minimal routing required.

### Part 2 frontend verification

Run and report:

- `npm.cmd run build`
- `npm.cmd run lint`
- `git diff --check`

Manual test:

1. Login as owner/admin.
2. Create invite with approval/pre-verification OFF.
3. Confirm popup says employee can directly join after profile completion.
4. Send invite.
5. Open invite preview link.
6. Confirm company, email, role, department/team/manager info display correctly.
7. Accept using same email.
8. Complete profile.
9. Confirm employee joins directly or reaches correct backend status.
10. Create invite with approval/pre-verification ON.
11. Confirm popup says employee needs approval before joining.
12. Accept invite and complete profile.
13. Confirm pending approval shows for authorized users.
14. Approve and reject flows work.
15. Test resend invite.
16. Test revoke invite and confirm token cannot be used.
17. Manually add employee with full details.
18. Confirm employee appears as pending activation.
19. Confirm manual activation link/email placeholder shows profile/company/login email details.
20. Accept manual activation with same email.
21. Try wrong email and confirm backend rejects it.
22. Confirm accepted token cannot be reused.
23. Confirm events/audit show actions.
24. Toggle light/dark mode.

### Part 2 Codex instruction

When starting Part 2, tell Codex:

> Read `docs/Employee_Onboarding_Bridge_Plan.md`, `docs/FebGrid_Product_Requirements_Document.md`, `AGENTS.md`, and `README.md`. Part 1 backend foundation is already completed and committed. Implement Part 2 only: Frontend admin/invite flow, invite preview, accept/profile completion pages, resend/revoke, pending approvals, manual activation UI. Do not start Employee POV dashboard/sidebar Part 3 yet. Do not add real email provider, AI, billing, MCP, WhatsApp/SMS, OCR, or mobile features.

---

## Part 3 — Employee POV dashboard, My Profile, and role-based sidebar

Implement employee-facing experience after Part 2 is tested and committed.

### Part 3 scope

Build:

- Employee POV dashboard
- employee dashboard summary API if not already done
- My Profile page
- employee profile self-update for safe fields
- role-based sidebar
- employee-only route access controls
- employee access to own work/leaves/notifications/announcements
- restricted visibility for admin-only pages
- backend permission hardening for employee POV

### Part 3 verification

Run and report:

Backend:

- `python -m compileall app alembic`
- backend import check
- mapper check
- route check
- employee dashboard summary probe
- employee `/me` probe
- employee can update safe own profile fields
- employee cannot change role/company/department/team/manager
- employee cannot access another employee profile
- employee cannot access company settings/admin-only pages through API
- employee sees only own work/leaves/notifications where applicable
- manager/admin still retain expected access
- cross-company isolation probe

Frontend:

- `npm.cmd run build`
- `npm.cmd run lint`
- `git diff --check`

Manual test:

1. Login as activated employee.
2. Confirm employee sees Employee POV dashboard.
3. Confirm sidebar is limited.
4. Confirm employee sees own assigned work only.
5. Confirm employee can submit leave.
6. Confirm employee sees own notifications/mentions/announcements.
7. Confirm employee can view/update safe own profile fields.
8. Confirm employee cannot access admin settings, employee management, billing, or audit logs unless role allows.
9. Login as manager/HR/admin/owner and confirm broader views still work.
10. Switch company and confirm no cross-company leaks.
11. Toggle light/dark mode.
12. Confirm dashboard, work objects, leaves, projects, notifications, search, settings still work.

### Part 3 Codex instruction

When starting Part 3, tell Codex:

> Read `docs/Employee_Onboarding_Bridge_Plan.md`, `docs/FebGrid_Product_Requirements_Document.md`, `AGENTS.md`, and `README.md`. Parts 1 and 2 are already completed and committed. Implement Part 3 only: Employee POV dashboard, My Profile, role-based sidebar, and employee access hardening. Do not add AI, billing, MCP, WhatsApp/SMS, OCR, mobile, real email provider, or unrelated future features.

---

## Final expected result after all three parts

After all three parts are complete, FebGrid should support real employee onboarding and employee POV.

Companies can:

- invite employees to fill their own profile
- manually add employees and send activation email/link
- resend/revoke invites
- approve/reject profile submissions when pre-verification is ON
- choose per-invite approval/pre-verification mode
- keep manual employee creation flow

Employees can:

- accept invitation or manual activation using only the exact invited/added email
- see company/profile info before joining
- fill missing profile details
- join directly when approval is OFF
- wait for approval when approval is ON
- access employee-specific dashboard after activation
- view/update safe own profile fields
- see own work/leaves/notifications/announcements

System security should ensure:

- no random person can join company
- no wrong email can activate invite/manual employee
- no reused/expired/revoked token can be accepted
- no cross-company data leak
- no role/company tampering from frontend
- all important actions create events/audit entries
- email remains placeholder/dev-safe only until real provider is added later
