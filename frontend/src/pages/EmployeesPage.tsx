import { Eye, Pencil, Plus, Power, UserRoundCheck } from "lucide-react";
import { type FormEvent, useMemo, useState } from "react";

import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { DataTable, type DataTableColumn } from "../components/ui/DataTable";
import { FieldShell, SelectInput, TextInput } from "../components/ui/FormControls";
import { Modal } from "../components/ui/Modal";
import { ModuleBoundary } from "../components/ui/ModuleBoundary";
import { SectionPanel } from "../components/ui/SectionPanel";
import { statusTone } from "../components/ui/tone";
import type { Employee, EmployeeCreatePayload, EmployeeUpdatePayload } from "../types/api";
import type { ModulePageProps } from "../types/page";
import { compactList, formatDate, formatLabel } from "../utils/format";

interface EmployeesPageProps extends ModulePageProps {
  onCreateEmployee: (payload: Omit<EmployeeCreatePayload, "company_id">) => Promise<void>;
  onUpdateEmployee: (employeeId: string, payload: EmployeeUpdatePayload) => Promise<void>;
  onDeactivateEmployee: (employeeId: string) => Promise<void>;
  onUpdateEmployeeStatus: (employeeId: string, currentStatus: string) => Promise<void>;
}

const statusOptions = [
  "working",
  "on_break",
  "offline",
  "on_leave",
  "done_for_the_day",
  "busy",
  "available",
];

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

type EmployeeForm = typeof initialForm;

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

function joinedAtToIso(value: string): string | null {
  if (!value) return null;
  return `${value}T00:00:00.000Z`;
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
  isMutating,
}: EmployeesPageProps): JSX.Element {
  const [form, setForm] = useState<EmployeeForm>(initialForm);
  const [formError, setFormError] = useState<string | null>(null);
  const [editingEmployee, setEditingEmployee] = useState<Employee | null>(null);
  const [profileEmployee, setProfileEmployee] = useState<Employee | null>(null);
  const [isFormOpen, setIsFormOpen] = useState(false);

  const departmentNames = useMemo(
    () => Object.fromEntries(data.departments.map((department) => [department.id, department.name])),
    [data.departments],
  );
  const teamNames = useMemo(() => Object.fromEntries(data.teams.map((team) => [team.id, team.name])), [data.teams]);
  const employeeNames = useMemo(() => Object.fromEntries(data.employees.map((employee) => [employee.id, employee.full_name])), [data.employees]);

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
      render: (employee) => compactList([employee.department_id ? departmentNames[employee.department_id] : employee.department, employee.team_id ? teamNames[employee.team_id] : null]) || "Not assigned",
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
    { key: "active", label: "Active", render: (employee) => <Badge label={employee.is_active ? "Active" : "Inactive"} tone={employee.is_active ? "green" : "slate"} /> },
    {
      key: "actions",
      label: "Actions",
      render: (employee) => (
        <div className="flex flex-wrap justify-end gap-2">
          <Button className="size-9 px-0" aria-label="View profile" icon={<Eye className="size-4" aria-hidden="true" />} onClick={() => setProfileEmployee(employee)}>
            <span className="sr-only">View</span>
          </Button>
          <Button className="size-9 px-0" aria-label="Edit employee" icon={<Pencil className="size-4" aria-hidden="true" />} onClick={() => openEdit(employee)}>
            <span className="sr-only">Edit</span>
          </Button>
          <Button
            className="size-9 px-0"
            aria-label="Deactivate employee"
            disabled={isMutating || !employee.is_active}
            icon={<Power className="size-4" aria-hidden="true" />}
            onClick={() => void onDeactivateEmployee(employee.id)}
          >
            <span className="sr-only">Deactivate</span>
          </Button>
        </div>
      ),
      className: "text-right",
    },
  ];

  function openCreate(): void {
    setEditingEmployee(null);
    setForm(initialForm);
    setFormError(null);
    setIsFormOpen(true);
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
      skills: form.skills.split(",").map((skill) => skill.trim()).filter(Boolean),
      metadata: {},
      joined_at: joinedAtToIso(form.joined_at),
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

  return (
    <>
      <SectionPanel
        eyebrow={selectedCompany?.name ?? "People directory"}
        title="Employees"
        action={<Button disabled={!selectedCompany} variant="primary" icon={<Plus className="size-4" aria-hidden="true" />} onClick={openCreate}>Add employee</Button>}
      >
        <ModuleBoundary
          emptyDescription={selectedCompany ? "Add employees to build the company directory and assign work." : "Create or select a company before adding employees."}
          emptyTitle="No employees yet"
          error={moduleError}
          isEmpty={data.employees.length === 0}
          isLoading={isLoadingModules}
          onRetry={onRetry}
          emptyAction={selectedCompany ? <Button variant="primary" icon={<Plus className="size-4" aria-hidden="true" />} onClick={openCreate}>Add employee</Button> : undefined}
        >
          <DataTable columns={columns} rows={data.employees} getRowKey={(employee) => employee.id} />
        </ModuleBoundary>
      </SectionPanel>

      <Modal description="Manage the company-scoped employee profile." isOpen={isFormOpen} title={editingEmployee ? "Edit employee" : "Add employee"} onClose={() => setIsFormOpen(false)}>
        <form className="space-y-4 p-5" onSubmit={handleSubmit}>
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
                {data.employees.filter((employee) => employee.id !== editingEmployee?.id).map((employee) => (
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

      <Modal description="Employee profile foundation for Sprint 3." isOpen={Boolean(profileEmployee)} title={profileEmployee?.full_name ?? "Employee profile"} onClose={() => setProfileEmployee(null)}>
        {profileEmployee ? (
          <div className="grid gap-4 p-5 sm:grid-cols-2">
            <ProfileItem label="Role" value={profileEmployee.role_title} />
            <ProfileItem label="Status" value={formatLabel(profileEmployee.current_status)} badgeTone={statusTone(profileEmployee.current_status)} />
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
    <div className="rounded-lg border border-grid-200 bg-grid-50 p-4">
      <p className="text-xs font-bold uppercase tracking-normal text-ink-500">{label}</p>
      <div className="mt-2">{badgeTone ? <Badge label={value} tone={badgeTone} /> : <p className="text-sm font-bold text-ink-950">{value}</p>}</div>
    </div>
  );
}
