import {
  Ban,
  CheckCircle2,
  Clipboard,
  Eye,
  Link2,
  MailPlus,
  Pencil,
  Plus,
  Power,
  RotateCcw,
  Send,
  UserRoundCheck,
  XCircle,
} from "lucide-react";
import { type FormEvent, useMemo, useState } from "react";

import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { DataTable, type DataTableColumn } from "../components/ui/DataTable";
import { FilterBar, FilterField } from "../components/ui/FilterBar";
import { FieldShell, SelectInput, TextArea, TextInput } from "../components/ui/FormControls";
import { Modal } from "../components/ui/Modal";
import { ModuleBoundary } from "../components/ui/ModuleBoundary";
import { SectionPanel } from "../components/ui/SectionPanel";
import { EmptyState, LoadingState } from "../components/ui/States";
import { statusTone } from "../components/ui/tone";
import type {
  Employee,
  EmployeeCreatePayload,
  EmployeeInvitation,
  EmployeeInvitationActionResult,
  EmployeeInvitationCreatePayload,
  EmployeeUpdatePayload,
  UserRole,
} from "../types/api";
import type { ModulePageProps } from "../types/page";
import { compactList, formatDate, formatLabel } from "../utils/format";

interface EmployeesPageProps extends ModulePageProps {
  onCreateEmployee: (payload: Omit<EmployeeCreatePayload, "company_id">) => Promise<void>;
  onUpdateEmployee: (employeeId: string, payload: EmployeeUpdatePayload) => Promise<void>;
  onDeactivateEmployee: (employeeId: string) => Promise<void>;
  onUpdateEmployeeStatus: (employeeId: string, currentStatus: string) => Promise<void>;
  onCreateInvitation: (payload: Omit<EmployeeInvitationCreatePayload, "company_id">) => Promise<EmployeeInvitationActionResult | null>;
  onResendInvitation: (invitationId: string) => Promise<EmployeeInvitationActionResult | null>;
  onRevokeInvitation: (invitationId: string) => Promise<void>;
  onApproveInvitation: (invitationId: string) => Promise<void>;
  onRejectInvitation: (invitationId: string, rejectionReason?: string | null) => Promise<void>;
}

const statusOptions = ["working", "online", "on_break", "offline", "on_leave", "done_for_the_day", "busy", "available"];
const inviteRoleOptions: UserRole[] = ["employee", "manager"];
const resendableInvitationStatuses = new Set(["pending", "activation_sent", "expired"]);
const revokableInvitationStatuses = new Set(["pending", "activation_sent", "expired"]);

type BadgeTone = "blue" | "green" | "amber" | "red" | "teal" | "slate";

const initialForm = {
  full_name: "",
  email: "",
  phone: "",
  role_title: "",
  department_id: "",
  team_id: "",
  manager_id: "",
  employment_type: "full_time",
  current_status: "available",
  location: "",
  skills: "",
  joined_at: "",
};

const initialInviteForm = {
  invited_email: "",
  invited_role: "employee" as UserRole,
  full_name: "",
  department_id: "",
  team_id: "",
  manager_employee_id: "",
  job_title: "",
  joining_date: "",
  employment_type: "full_time",
  approval_required: false,
  note: "",
};

type EmployeeForm = typeof initialForm;
type InviteForm = typeof initialInviteForm;

interface LinkResult {
  title: string;
  email: string;
  url: string;
}

function employeeToForm(employee: Employee): EmployeeForm {
  return {
    full_name: employee.full_name,
    email: employee.email ?? "",
    phone: employee.phone ?? "",
    role_title: employee.role_title,
    department_id: employee.department_id ?? "",
    team_id: employee.team_id ?? "",
    manager_id: employee.manager_id ?? "",
    employment_type: employee.employment_type,
    current_status: employee.current_status,
    location: employee.location ?? "",
    skills: employee.skills.join(", "),
    joined_at: employee.joined_at ? employee.joined_at.slice(0, 10) : "",
  };
}

function dateToIso(value: string): string | null {
  if (!value) return null;
  return `${value}T00:00:00.000Z`;
}

function buildInviteUrl(path: string): string {
  if (/^https?:\/\//i.test(path)) return path;
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${window.location.origin}${normalizedPath}`;
}

function invitationStatusTone(status: string): BadgeTone {
  if (status === "accepted" || status === "approved") return "green";
  if (status === "submitted_for_approval") return "blue";
  if (status === "rejected" || status === "revoked" || status === "expired") return "red";
  if (status === "activation_sent") return "teal";
  return "amber";
}

function accountStatusTone(status: string): BadgeTone {
  if (status === "active") return "green";
  if (status.includes("rejected") || status.includes("revoked")) return "red";
  if (status.includes("pending")) return "amber";
  return "slate";
}

function inviteAssignment(invitation: EmployeeInvitation, departmentNames: Record<string, string>, teamNames: Record<string, string>, employeeNames: Record<string, string>): string {
  return (
    compactList([
      invitation.department_id ? departmentNames[invitation.department_id] : null,
      invitation.team_id ? teamNames[invitation.team_id] : null,
      invitation.manager_employee_id ? `Manager: ${employeeNames[invitation.manager_employee_id] ?? "Assigned"}` : null,
    ]) || "No org assignment"
  );
}

export function EmployeesPage({
  data,
  selectedCompany,
  isLoadingModules,
  moduleError,
  onRetry,
  onCreateEmployee,
  onUpdateEmployee,
  onDeactivateEmployee,
  onUpdateEmployeeStatus,
  onCreateInvitation,
  onResendInvitation,
  onRevokeInvitation,
  onApproveInvitation,
  onRejectInvitation,
  isMutating,
}: EmployeesPageProps): JSX.Element {
  const [form, setForm] = useState<EmployeeForm>(initialForm);
  const [inviteForm, setInviteForm] = useState<InviteForm>(initialInviteForm);
  const [formError, setFormError] = useState<string | null>(null);
  const [inviteError, setInviteError] = useState<string | null>(null);
  const [editingEmployee, setEditingEmployee] = useState<Employee | null>(null);
  const [profileEmployee, setProfileEmployee] = useState<Employee | null>(null);
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [isInviteOpen, setIsInviteOpen] = useState(false);
  const [isConfirmInviteOpen, setIsConfirmInviteOpen] = useState(false);
  const [linkResult, setLinkResult] = useState<LinkResult | null>(null);
  const [rejectingInvitation, setRejectingInvitation] = useState<EmployeeInvitation | null>(null);
  const [rejectionReason, setRejectionReason] = useState("");
  const [searchFilter, setSearchFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [departmentFilter, setDepartmentFilter] = useState("");
  const [teamFilter, setTeamFilter] = useState("");

  const departmentNames = useMemo(
    () => Object.fromEntries(data.departments.map((department) => [department.id, department.name])),
    [data.departments],
  );
  const teamNames = useMemo(() => Object.fromEntries(data.teams.map((team) => [team.id, team.name])), [data.teams]);
  const employeeNames = useMemo(() => Object.fromEntries(data.employees.map((employee) => [employee.id, employee.full_name])), [data.employees]);
  const pendingApprovals = useMemo(
    () => data.invitations.filter((invitation) => invitation.status === "submitted_for_approval"),
    [data.invitations],
  );
  const invitationQueue = useMemo(
    () => data.invitations.filter((invitation) => invitation.status !== "submitted_for_approval"),
    [data.invitations],
  );
  const filteredEmployees = useMemo(() => {
    const query = searchFilter.trim().toLowerCase();
    return data.employees.filter((employee) => {
      const searchable = [
        employee.full_name,
        employee.email,
        employee.phone,
        employee.role_title,
        employee.department,
        employee.location,
        employee.account_status,
        employee.activation_status,
        employee.profile_completion_status,
        employee.skills.join(" "),
        employee.department_id ? departmentNames[employee.department_id] : null,
        employee.team_id ? teamNames[employee.team_id] : null,
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();
      if (query && !searchable.includes(query)) return false;
      if (statusFilter && employee.current_status !== statusFilter) return false;
      if (departmentFilter && employee.department_id !== departmentFilter) return false;
      if (teamFilter && employee.team_id !== teamFilter) return false;
      return true;
    });
  }, [data.employees, departmentFilter, departmentNames, searchFilter, statusFilter, teamFilter, teamNames]);
  const hasActiveFilters = Boolean(searchFilter || statusFilter || departmentFilter || teamFilter);

  const columns: DataTableColumn<Employee>[] = [
    {
      key: "name",
      label: "Employee",
      render: (employee) => (
        <span className="flex min-w-56 items-center gap-3">
          <span className="flex size-9 shrink-0 items-center justify-center rounded-md bg-grid-100 text-ink-700">
            <UserRoundCheck className="size-4" aria-hidden="true" />
          </span>
          <span className="min-w-0">
            <span className="block truncate font-bold text-ink-950">{employee.full_name}</span>
            <span className="block truncate text-xs text-ink-500">{employee.email ?? "No email"}</span>
          </span>
        </span>
      ),
    },
    { key: "role", label: "Role", render: (employee) => employee.role_title },
    {
      key: "org",
      label: "Department / Team",
      render: (employee) =>
        compactList([employee.department_id ? departmentNames[employee.department_id] : employee.department, employee.team_id ? teamNames[employee.team_id] : null]) ||
        "Not assigned",
    },
    {
      key: "status",
      label: "Status",
      render: (employee) => (
        <SelectInput
          aria-label={`Update ${employee.full_name} status`}
          disabled={isMutating || !employee.is_active}
          value={employee.current_status}
          onChange={(event) => void onUpdateEmployeeStatus(employee.id, event.target.value)}
        >
          {statusOptions.map((status) => (
            <option key={status} value={status}>
              {formatLabel(status)}
            </option>
          ))}
        </SelectInput>
      ),
    },
    {
      key: "account",
      label: "Account",
      render: (employee) => (
        <div className="flex flex-col gap-1">
          <Badge label={formatLabel(employee.account_status)} tone={accountStatusTone(employee.account_status)} />
          <span className="text-xs font-medium text-ink-500">{formatLabel(employee.activation_status)}</span>
        </div>
      ),
    },
    { key: "active", label: "Active", render: (employee) => <Badge label={employee.is_active ? "Active" : "Inactive"} tone={employee.is_active ? "green" : "slate"} /> },
    {
      key: "actions",
      label: "Actions",
      render: (employee) => (
        <div className="flex flex-wrap justify-end gap-2">
          <Button className="size-9 px-0" aria-label="View profile" title="View profile" icon={<Eye className="size-4" aria-hidden="true" />} onClick={() => setProfileEmployee(employee)}>
            <span className="sr-only">View profile</span>
          </Button>
          <Button className="size-9 px-0" aria-label="Edit employee" title="Edit employee" icon={<Pencil className="size-4" aria-hidden="true" />} onClick={() => openEdit(employee)}>
            <span className="sr-only">Edit employee</span>
          </Button>
          <Button
            className="size-9 px-0"
            aria-label="Deactivate employee"
            title="Deactivate employee"
            disabled={isMutating || !employee.is_active}
            icon={<Power className="size-4" aria-hidden="true" />}
            onClick={() => void onDeactivateEmployee(employee.id)}
          >
            <span className="sr-only">Deactivate employee</span>
          </Button>
        </div>
      ),
      className: "text-right",
    },
  ];

  const invitationColumns: DataTableColumn<EmployeeInvitation>[] = [
    {
      key: "invitee",
      label: "Invitee",
      render: (invitation) => (
        <div className="min-w-64">
          <p className="font-bold text-ink-950">{invitation.invited_email}</p>
          <p className="text-xs font-medium text-ink-500">
            {invitation.invite_source === "manual_add" ? "Manual activation" : "Invite-first"} / {formatLabel(invitation.invited_role)}
          </p>
        </div>
      ),
    },
    {
      key: "assignment",
      label: "Assignment",
      render: (invitation) => (
        <div className="min-w-52">
          <p className="font-semibold text-ink-700">{invitation.job_title || "Role title pending"}</p>
          <p className="text-xs font-medium text-ink-500">{inviteAssignment(invitation, departmentNames, teamNames, employeeNames)}</p>
        </div>
      ),
    },
    {
      key: "status",
      label: "Status",
      render: (invitation) => (
        <div className="flex flex-col gap-1">
          <Badge label={formatLabel(invitation.status)} tone={invitationStatusTone(invitation.status)} />
          <span className="text-xs font-medium text-ink-500">{invitation.approval_required ? "Pre-verification on" : "Direct after profile"}</span>
        </div>
      ),
    },
    {
      key: "dates",
      label: "Sent / Expires",
      render: (invitation) => (
        <div className="min-w-36">
          <p>{formatDate(invitation.sent_at)}</p>
          <p className="text-xs font-medium text-ink-500">Expires {formatDate(invitation.expires_at)}</p>
        </div>
      ),
    },
    {
      key: "actions",
      label: "Actions",
      className: "text-right",
      render: (invitation) => (
        <div className="flex flex-wrap justify-end gap-2">
          {resendableInvitationStatuses.has(invitation.status) ? (
            <Button
              className="size-9 px-0"
              aria-label="Resend invite"
              title="Resend invite"
              disabled={isMutating}
              icon={<RotateCcw className="size-4" aria-hidden="true" />}
              onClick={() => void handleResend(invitation)}
            >
              <span className="sr-only">Resend invite</span>
            </Button>
          ) : null}
          {revokableInvitationStatuses.has(invitation.status) ? (
            <Button
              className="size-9 px-0"
              aria-label="Revoke invite"
              title="Revoke invite"
              disabled={isMutating}
              icon={<Ban className="size-4" aria-hidden="true" />}
              onClick={() => void onRevokeInvitation(invitation.id)}
            >
              <span className="sr-only">Revoke invite</span>
            </Button>
          ) : null}
        </div>
      ),
    },
  ];

  const approvalColumns: DataTableColumn<EmployeeInvitation>[] = [
    ...invitationColumns.slice(0, 4),
    {
      key: "approvalActions",
      label: "Actions",
      className: "text-right",
      render: (invitation) => (
        <div className="flex flex-wrap justify-end gap-2">
          <Button
            className="size-9 px-0"
            aria-label="Approve profile"
            title="Approve profile"
            disabled={isMutating}
            icon={<CheckCircle2 className="size-4" aria-hidden="true" />}
            onClick={() => void onApproveInvitation(invitation.id)}
          >
            <span className="sr-only">Approve profile</span>
          </Button>
          <Button
            className="size-9 px-0"
            aria-label="Reject profile"
            title="Reject profile"
            disabled={isMutating}
            icon={<XCircle className="size-4" aria-hidden="true" />}
            onClick={() => {
              setRejectingInvitation(invitation);
              setRejectionReason("");
            }}
          >
            <span className="sr-only">Reject profile</span>
          </Button>
        </div>
      ),
    },
  ];

  function openCreate(): void {
    setEditingEmployee(null);
    setForm(initialForm);
    setFormError(null);
    setIsFormOpen(true);
  }

  function openInvite(): void {
    setInviteForm(initialInviteForm);
    setInviteError(null);
    setIsInviteOpen(true);
  }

  function openEdit(employee: Employee): void {
    setEditingEmployee(employee);
    setForm(employeeToForm(employee));
    setFormError(null);
    setIsFormOpen(true);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    setFormError(null);
    if (!selectedCompany) {
      setFormError("Create or select a company first.");
      return;
    }

    const payload = {
      full_name: form.full_name.trim(),
      email: form.email.trim() || null,
      phone: form.phone.trim() || null,
      role_title: form.role_title.trim(),
      department_id: form.department_id || null,
      team_id: form.team_id || null,
      manager_id: form.manager_id || null,
      employment_type: form.employment_type,
      current_status: form.current_status,
      location: form.location.trim() || null,
      profile_image_url: null,
      skills: form.skills
        .split(",")
        .map((skill) => skill.trim())
        .filter(Boolean),
      metadata: {},
      joined_at: dateToIso(form.joined_at),
      is_active: true,
    };

    try {
      if (editingEmployee) {
        await onUpdateEmployee(editingEmployee.id, payload);
      } else {
        await onCreateEmployee(payload);
      }
      setIsFormOpen(false);
    } catch {
      setFormError("Employee could not be saved. Check the details and try again.");
    }
  }

  function handleInviteSubmit(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault();
    setInviteError(null);
    if (!selectedCompany) {
      setInviteError("Create or select a company first.");
      return;
    }
    if (!inviteForm.invited_email.trim()) {
      setInviteError("Employee email is required.");
      return;
    }
    setIsConfirmInviteOpen(true);
  }

  async function sendInvite(): Promise<void> {
    setInviteError(null);
    const payload: Omit<EmployeeInvitationCreatePayload, "company_id"> = {
      invited_email: inviteForm.invited_email.trim(),
      invited_role: inviteForm.invited_role,
      full_name: inviteForm.full_name.trim() || null,
      department_id: inviteForm.department_id || null,
      team_id: inviteForm.team_id || null,
      manager_employee_id: inviteForm.manager_employee_id || null,
      job_title: inviteForm.job_title.trim() || null,
      joining_date: dateToIso(inviteForm.joining_date),
      employment_type: inviteForm.employment_type,
      approval_required: inviteForm.approval_required,
      note: inviteForm.note.trim() || null,
      metadata: {},
    };
    try {
      const result = await onCreateInvitation(payload);
      setIsConfirmInviteOpen(false);
      setIsInviteOpen(false);
      if (result) {
        setLinkResult({
          title: result.invitation.invite_source === "manual_add" ? "Activation link prepared" : "Invite link prepared",
          email: result.invitation.invited_email,
          url: buildInviteUrl(result.acceptance_url),
        });
      }
    } catch {
      setIsConfirmInviteOpen(false);
      setInviteError("Invite could not be sent. Check the details and try again.");
    }
  }

  async function handleResend(invitation: EmployeeInvitation): Promise<void> {
    try {
      const result = await onResendInvitation(invitation.id);
      if (result) {
        setLinkResult({
          title: invitation.invite_source === "manual_add" ? "Activation link refreshed" : "Invite link refreshed",
          email: result.invitation.invited_email,
          url: buildInviteUrl(result.acceptance_url),
        });
      }
    } catch {
      setLinkResult(null);
    }
  }

  async function copyLink(url: string): Promise<void> {
    try {
      await navigator.clipboard.writeText(url);
    } catch {
      // The link remains visible for manual copy.
    }
  }

  async function submitRejection(): Promise<void> {
    if (!rejectingInvitation) return;
    await onRejectInvitation(rejectingInvitation.id, rejectionReason.trim() || null);
    setRejectingInvitation(null);
    setRejectionReason("");
  }

  return (
    <>
      <div className="space-y-6">
        <SectionPanel
          eyebrow={selectedCompany?.name ?? "People directory"}
          title="Employees"
          action={
            <div className="flex flex-wrap gap-2">
              <Button disabled={!selectedCompany} icon={<MailPlus className="size-4" aria-hidden="true" />} onClick={openInvite}>
                Invite employee
              </Button>
              <Button disabled={!selectedCompany} variant="primary" icon={<Plus className="size-4" aria-hidden="true" />} onClick={openCreate}>
                Add employee
              </Button>
            </div>
          }
        >
          <ModuleBoundary
            emptyDescription={selectedCompany ? "Add employees to build the company directory and assign work." : "Create or select a company before adding employees."}
            emptyTitle="No employees yet"
            error={moduleError}
            isEmpty={data.employees.length === 0}
            isLoading={isLoadingModules}
            onRetry={onRetry}
            emptyAction={
              selectedCompany ? (
                <div className="flex flex-wrap justify-center gap-2">
                  <Button icon={<MailPlus className="size-4" aria-hidden="true" />} onClick={openInvite}>
                    Invite employee
                  </Button>
                  <Button variant="primary" icon={<Plus className="size-4" aria-hidden="true" />} onClick={openCreate}>
                    Add employee
                  </Button>
                </div>
              ) : undefined
            }
          >
            <FilterBar
              isResetDisabled={!hasActiveFilters}
              onReset={() => {
                setSearchFilter("");
                setStatusFilter("");
                setDepartmentFilter("");
                setTeamFilter("");
              }}
            >
              <FilterField label="Search">
                <TextInput placeholder="Name, email, role, account" value={searchFilter} onChange={(event) => setSearchFilter(event.target.value)} />
              </FilterField>
              <FilterField label="Status">
                <SelectInput value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}>
                  <option value="">All statuses</option>
                  {statusOptions.map((status) => (
                    <option key={status} value={status}>
                      {formatLabel(status)}
                    </option>
                  ))}
                </SelectInput>
              </FilterField>
              <FilterField label="Department">
                <SelectInput value={departmentFilter} onChange={(event) => setDepartmentFilter(event.target.value)}>
                  <option value="">All departments</option>
                  {data.departments.map((department) => (
                    <option key={department.id} value={department.id}>
                      {department.name}
                    </option>
                  ))}
                </SelectInput>
              </FilterField>
              <FilterField label="Team">
                <SelectInput value={teamFilter} onChange={(event) => setTeamFilter(event.target.value)}>
                  <option value="">All teams</option>
                  {data.teams.map((team) => (
                    <option key={team.id} value={team.id}>
                      {team.name}
                    </option>
                  ))}
                </SelectInput>
              </FilterField>
            </FilterBar>
            {filteredEmployees.length === 0 ? (
              <div className="px-5 py-10 text-center">
                <p className="text-sm font-bold text-ink-950">No employees match these filters</p>
                <p className="mt-1 text-sm font-medium text-ink-500">Reset filters to return to the full directory.</p>
              </div>
            ) : (
              <DataTable columns={columns} rows={filteredEmployees} getRowKey={(employee) => employee.id} />
            )}
          </ModuleBoundary>
        </SectionPanel>

        <SectionPanel
          eyebrow="Onboarding"
          title="Pending invitations and activations"
          action={
            <Button disabled icon={<Clipboard className="size-4" aria-hidden="true" />} title="Bulk invite CSV later" aria-label="Bulk invite CSV later">
              Bulk invite CSV later
            </Button>
          }
        >
          {isLoadingModules ? (
            <LoadingState label="Loading invitations" />
          ) : invitationQueue.length === 0 ? (
            <EmptyState title="No invitations yet" description="Invite employees or manually add them with an email to prepare activation records." />
          ) : (
            <DataTable columns={invitationColumns} rows={invitationQueue} getRowKey={(invitation) => invitation.id} />
          )}
        </SectionPanel>

        <SectionPanel eyebrow="Pre-verification" title="Pending approvals">
          {isLoadingModules ? (
            <LoadingState label="Loading approval queue" />
          ) : pendingApprovals.length === 0 ? (
            <EmptyState title="No pending approvals" description="When pre-verification is on, submitted employee profiles will appear here for approval or rejection." />
          ) : (
            <DataTable columns={approvalColumns} rows={pendingApprovals} getRowKey={(invitation) => invitation.id} />
          )}
        </SectionPanel>
      </div>

      <Modal description="Manage the company-scoped employee profile." isOpen={isFormOpen} title={editingEmployee ? "Edit employee" : "Add employee"} onClose={() => setIsFormOpen(false)}>
        <form className="space-y-4 p-5" onSubmit={handleSubmit}>
          <div className="rounded-lg border border-blue-200 bg-blue-50 px-4 py-3 text-sm font-semibold text-blue-700">
            Manual add keeps the employee in the directory. If an email is provided and no account is linked, FebGrid prepares an activation record that can be resent from the invitation queue.
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <FieldShell label="Full name">
              <TextInput required value={form.full_name} onChange={(event) => setForm((current) => ({ ...current, full_name: event.target.value }))} />
            </FieldShell>
            <FieldShell label="Email">
              <TextInput type="email" value={form.email} onChange={(event) => setForm((current) => ({ ...current, email: event.target.value }))} />
            </FieldShell>
            <FieldShell label="Role title">
              <TextInput required value={form.role_title} onChange={(event) => setForm((current) => ({ ...current, role_title: event.target.value }))} />
            </FieldShell>
            <FieldShell label="Phone">
              <TextInput value={form.phone} onChange={(event) => setForm((current) => ({ ...current, phone: event.target.value }))} />
            </FieldShell>
            <FieldShell label="Department">
              <SelectInput value={form.department_id} onChange={(event) => setForm((current) => ({ ...current, department_id: event.target.value }))}>
                <option value="">No department</option>
                {data.departments.map((department) => (
                  <option key={department.id} value={department.id}>
                    {department.name}
                  </option>
                ))}
              </SelectInput>
            </FieldShell>
            <FieldShell label="Team">
              <SelectInput value={form.team_id} onChange={(event) => setForm((current) => ({ ...current, team_id: event.target.value }))}>
                <option value="">No team</option>
                {data.teams.map((team) => (
                  <option key={team.id} value={team.id}>
                    {team.name}
                  </option>
                ))}
              </SelectInput>
            </FieldShell>
            <FieldShell label="Manager">
              <SelectInput value={form.manager_id} onChange={(event) => setForm((current) => ({ ...current, manager_id: event.target.value }))}>
                <option value="">No manager</option>
                {data.employees
                  .filter((employee) => employee.id !== editingEmployee?.id)
                  .map((employee) => (
                    <option key={employee.id} value={employee.id}>
                      {employee.full_name}
                    </option>
                  ))}
              </SelectInput>
            </FieldShell>
            <FieldShell label="Status">
              <SelectInput value={form.current_status} onChange={(event) => setForm((current) => ({ ...current, current_status: event.target.value }))}>
                {statusOptions.map((status) => (
                  <option key={status} value={status}>
                    {formatLabel(status)}
                  </option>
                ))}
              </SelectInput>
            </FieldShell>
            <FieldShell label="Employment type">
              <SelectInput value={form.employment_type} onChange={(event) => setForm((current) => ({ ...current, employment_type: event.target.value }))}>
                <option value="full_time">Full Time</option>
                <option value="part_time">Part Time</option>
                <option value="contractor">Contractor</option>
                <option value="intern">Intern</option>
              </SelectInput>
            </FieldShell>
            <FieldShell label="Joined date">
              <TextInput type="date" value={form.joined_at} onChange={(event) => setForm((current) => ({ ...current, joined_at: event.target.value }))} />
            </FieldShell>
            <FieldShell label="Location">
              <TextInput value={form.location} onChange={(event) => setForm((current) => ({ ...current, location: event.target.value }))} />
            </FieldShell>
            <FieldShell label="Skills">
              <TextInput placeholder="Operations, Vendor coordination" value={form.skills} onChange={(event) => setForm((current) => ({ ...current, skills: event.target.value }))} />
            </FieldShell>
          </div>
          {formError ? <p className="text-sm font-semibold text-rose-700">{formError}</p> : null}
          <div className="flex justify-end gap-2 border-t border-grid-200 pt-4">
            <Button onClick={() => setIsFormOpen(false)}>Cancel</Button>
            <Button disabled={isMutating} type="submit" variant="primary">
              {isMutating ? "Saving..." : editingEmployee ? "Save changes" : "Create employee"}
            </Button>
          </div>
        </form>
      </Modal>

      <Modal description="Send a secure invitation tied to the selected company and email." isOpen={isInviteOpen} title="Invite employee" onClose={() => setIsInviteOpen(false)}>
        <form className="space-y-4 p-5" onSubmit={handleInviteSubmit}>
          <div className="grid gap-4 sm:grid-cols-2">
            <FieldShell label="Employee email">
              <TextInput required type="email" value={inviteForm.invited_email} onChange={(event) => setInviteForm((current) => ({ ...current, invited_email: event.target.value }))} />
            </FieldShell>
            <FieldShell label="Account role">
              <SelectInput value={inviteForm.invited_role} onChange={(event) => setInviteForm((current) => ({ ...current, invited_role: event.target.value as UserRole }))}>
                {inviteRoleOptions.map((role) => (
                  <option key={role} value={role}>
                    {formatLabel(role)}
                  </option>
                ))}
              </SelectInput>
            </FieldShell>
            <FieldShell label="Full name">
              <TextInput value={inviteForm.full_name} onChange={(event) => setInviteForm((current) => ({ ...current, full_name: event.target.value }))} />
            </FieldShell>
            <FieldShell label="Job title">
              <TextInput value={inviteForm.job_title} onChange={(event) => setInviteForm((current) => ({ ...current, job_title: event.target.value }))} />
            </FieldShell>
            <FieldShell label="Department">
              <SelectInput value={inviteForm.department_id} onChange={(event) => setInviteForm((current) => ({ ...current, department_id: event.target.value }))}>
                <option value="">No department</option>
                {data.departments.map((department) => (
                  <option key={department.id} value={department.id}>
                    {department.name}
                  </option>
                ))}
              </SelectInput>
            </FieldShell>
            <FieldShell label="Team">
              <SelectInput value={inviteForm.team_id} onChange={(event) => setInviteForm((current) => ({ ...current, team_id: event.target.value }))}>
                <option value="">No team</option>
                {data.teams.map((team) => (
                  <option key={team.id} value={team.id}>
                    {team.name}
                  </option>
                ))}
              </SelectInput>
            </FieldShell>
            <FieldShell label="Manager">
              <SelectInput value={inviteForm.manager_employee_id} onChange={(event) => setInviteForm((current) => ({ ...current, manager_employee_id: event.target.value }))}>
                <option value="">No manager</option>
                {data.employees.map((employee) => (
                  <option key={employee.id} value={employee.id}>
                    {employee.full_name}
                  </option>
                ))}
              </SelectInput>
            </FieldShell>
            <FieldShell label="Joining date">
              <TextInput type="date" value={inviteForm.joining_date} onChange={(event) => setInviteForm((current) => ({ ...current, joining_date: event.target.value }))} />
            </FieldShell>
            <FieldShell label="Employment type">
              <SelectInput value={inviteForm.employment_type} onChange={(event) => setInviteForm((current) => ({ ...current, employment_type: event.target.value }))}>
                <option value="full_time">Full Time</option>
                <option value="part_time">Part Time</option>
                <option value="contractor">Contractor</option>
                <option value="intern">Intern</option>
              </SelectInput>
            </FieldShell>
            <label className="febgrid-muted-surface flex min-h-10 items-center gap-3 rounded-md px-3 py-2 text-sm font-bold text-ink-900">
              <input
                type="checkbox"
                checked={inviteForm.approval_required}
                onChange={(event) => setInviteForm((current) => ({ ...current, approval_required: event.target.checked }))}
              />
              Approval / pre-verification required
            </label>
          </div>
          <FieldShell label="Optional note/message">
            <TextArea value={inviteForm.note} onChange={(event) => setInviteForm((current) => ({ ...current, note: event.target.value }))} />
          </FieldShell>
          {inviteError ? <p className="text-sm font-semibold text-rose-700">{inviteError}</p> : null}
          <div className="flex justify-end gap-2 border-t border-grid-200 pt-4">
            <Button onClick={() => setIsInviteOpen(false)}>Cancel</Button>
            <Button disabled={isMutating} type="submit" variant="primary" icon={<Send className="size-4" aria-hidden="true" />}>
              Continue
            </Button>
          </div>
        </form>
      </Modal>

      <Modal
        description="Review the onboarding behavior before sending this invite."
        isOpen={isConfirmInviteOpen}
        title="Confirm employee invitation"
        onClose={() => setIsConfirmInviteOpen(false)}
      >
        <div className="space-y-4 p-5">
          <div className="febgrid-muted-surface rounded-lg p-4">
            <p className="text-sm font-bold text-ink-950">{inviteForm.invited_email}</p>
            <p className="mt-1 text-sm font-medium text-ink-500">
              {inviteForm.approval_required
                ? "You have turned ON pre-verification. The employee can submit their profile, but they will not fully join the company FebGrid system until an authorized company user approves them."
                : "You have kept pre-verification OFF. After the employee accepts the invite and completes their profile, they can directly join the company FebGrid system."}
            </p>
          </div>
          <div className="flex justify-end gap-2 border-t border-grid-200 pt-4">
            <Button onClick={() => setIsConfirmInviteOpen(false)}>Back</Button>
            <Button disabled={isMutating} variant="primary" icon={<Send className="size-4" aria-hidden="true" />} onClick={() => void sendInvite()}>
              {isMutating ? "Sending..." : "Send invite"}
            </Button>
          </div>
        </div>
      </Modal>

      <Modal description="Use this development-safe link while real email delivery remains a placeholder." isOpen={Boolean(linkResult)} title={linkResult?.title ?? "Invite link"} onClose={() => setLinkResult(null)}>
        {linkResult ? (
          <div className="space-y-4 p-5">
            <div className="rounded-lg border border-teal-200 bg-teal-50 p-4">
              <p className="text-sm font-bold text-teal-700">Link prepared for {linkResult.email}</p>
              <p className="mt-2 break-all text-sm font-semibold text-ink-900">{linkResult.url}</p>
            </div>
            <div className="flex flex-wrap justify-end gap-2">
              <Button icon={<Link2 className="size-4" aria-hidden="true" />} onClick={() => window.open(linkResult.url, "_blank", "noopener,noreferrer")}>
                Open link
              </Button>
              <Button variant="primary" icon={<Clipboard className="size-4" aria-hidden="true" />} onClick={() => void copyLink(linkResult.url)}>
                Copy link
              </Button>
            </div>
          </div>
        ) : null}
      </Modal>

      <Modal description="Rejecting keeps the employee profile inactive until a new decision is made." isOpen={Boolean(rejectingInvitation)} title="Reject employee profile" onClose={() => setRejectingInvitation(null)}>
        <div className="space-y-4 p-5">
          <FieldShell label="Manager note">
            <TextArea value={rejectionReason} onChange={(event) => setRejectionReason(event.target.value)} />
          </FieldShell>
          <div className="flex justify-end gap-2 border-t border-grid-200 pt-4">
            <Button onClick={() => setRejectingInvitation(null)}>Cancel</Button>
            <Button disabled={isMutating} variant="primary" icon={<XCircle className="size-4" aria-hidden="true" />} onClick={() => void submitRejection()}>
              Reject
            </Button>
          </div>
        </div>
      </Modal>

      <Modal description="Employee profile foundation for Sprint 3." isOpen={Boolean(profileEmployee)} title={profileEmployee?.full_name ?? "Employee profile"} onClose={() => setProfileEmployee(null)}>
        {profileEmployee ? (
          <div className="grid gap-4 p-5 sm:grid-cols-2">
            <ProfileItem label="Role" value={profileEmployee.role_title} />
            <ProfileItem label="Status" value={formatLabel(profileEmployee.current_status)} badgeTone={statusTone(profileEmployee.current_status)} />
            <ProfileItem label="Account" value={formatLabel(profileEmployee.account_status)} badgeTone={accountStatusTone(profileEmployee.account_status)} />
            <ProfileItem label="Activation" value={formatLabel(profileEmployee.activation_status)} />
            <ProfileItem label="Profile completion" value={formatLabel(profileEmployee.profile_completion_status)} />
            <ProfileItem label="Department" value={profileEmployee.department_id ? departmentNames[profileEmployee.department_id] : profileEmployee.department ?? "Not assigned"} />
            <ProfileItem label="Team" value={profileEmployee.team_id ? teamNames[profileEmployee.team_id] : "Not assigned"} />
            <ProfileItem label="Manager" value={profileEmployee.manager_id ? employeeNames[profileEmployee.manager_id] ?? "Assigned" : "No manager"} />
            <ProfileItem label="Employment" value={formatLabel(profileEmployee.employment_type)} />
            <ProfileItem label="Joined" value={formatDate(profileEmployee.joined_at)} />
            <ProfileItem label="Linked user" value={profileEmployee.user_id ? "Linked" : "Not linked"} />
            <ProfileItem label="Phone" value={profileEmployee.phone ?? "Not set"} />
            <ProfileItem label="Location" value={profileEmployee.location ?? "Not set"} />
          </div>
        ) : null}
      </Modal>
    </>
  );
}

function ProfileItem({ label, value, badgeTone }: { label: string; value: string; badgeTone?: BadgeTone }): JSX.Element {
  return (
    <div className="febgrid-muted-surface rounded-lg p-4">
      <p className="text-xs font-bold uppercase tracking-normal text-ink-500">{label}</p>
      <div className="mt-2">{badgeTone ? <Badge label={value} tone={badgeTone} /> : <p className="text-sm font-bold text-ink-950">{value}</p>}</div>
    </div>
  );
}
