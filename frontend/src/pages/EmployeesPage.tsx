import { Plus, UserRoundCheck } from "lucide-react";
import { type FormEvent, useMemo, useState } from "react";

import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { DataTable, type DataTableColumn } from "../components/ui/DataTable";
import { FieldShell, SelectInput, TextInput } from "../components/ui/FormControls";
import { Modal } from "../components/ui/Modal";
import { ModuleBoundary } from "../components/ui/ModuleBoundary";
import { SectionPanel } from "../components/ui/SectionPanel";
import { statusTone } from "../components/ui/tone";
import type { Employee, EmployeeCreatePayload } from "../types/api";
import type { ModulePageProps } from "../types/page";
import { formatLabel } from "../utils/format";

interface EmployeesPageProps extends ModulePageProps {
  onCreateEmployee: (payload: Omit<EmployeeCreatePayload, "company_id">) => Promise<void>;
}

const initialForm = {
  full_name: "",
  email: "",
  phone: "",
  role: "",
  department: "",
  employment_type: "full_time",
  status: "available",
  manager_id: "",
  location: "",
  skills: "",
};

export function EmployeesPage({
  data,
  selectedCompany,
  isLoadingModules,
  moduleError,
  onRetry,
  onCreateEmployee,
  isMutating,
}: EmployeesPageProps): JSX.Element {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [form, setForm] = useState(initialForm);
  const [formError, setFormError] = useState<string | null>(null);

  const workCounts = useMemo(() => {
    return data.workObjects.reduce<Record<string, number>>((counts, workObject) => {
      if (workObject.assigned_to_employee_id) {
        counts[workObject.assigned_to_employee_id] = (counts[workObject.assigned_to_employee_id] ?? 0) + 1;
      }
      return counts;
    }, {});
  }, [data.workObjects]);

  const columns: DataTableColumn<Employee>[] = [
    {
      key: "name",
      label: "Employee",
      render: (employee) => (
        <span className="flex min-w-48 items-center gap-3">
          <span className="flex size-9 shrink-0 items-center justify-center rounded-md bg-grid-100 text-ink-700">
            <UserRoundCheck className="size-4" aria-hidden="true" />
          </span>
          <span className="min-w-0">
            <span className="block truncate font-bold text-ink-950">{employee.full_name}</span>
            <span className="block truncate text-xs text-ink-500">{employee.email}</span>
          </span>
        </span>
      ),
    },
    { key: "role", label: "Role", render: (employee) => employee.role },
    { key: "department", label: "Department", render: (employee) => employee.department ?? "Not set" },
    { key: "status", label: "Status", render: (employee) => <Badge label={formatLabel(employee.status)} tone={statusTone(employee.status)} /> },
    { key: "work", label: "Active work", render: (employee) => (workCounts[employee.id] ?? 0).toString(), className: "text-right" },
  ];

  function openModal(): void {
    setForm(initialForm);
    setFormError(null);
    setIsModalOpen(true);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    setFormError(null);
    if (!selectedCompany) {
      setFormError("Create or select a company first.");
      return;
    }

    try {
      await onCreateEmployee({
        full_name: form.full_name.trim(),
        email: form.email.trim(),
        phone: form.phone.trim() || null,
        role: form.role.trim(),
        department: form.department.trim() || null,
        employment_type: form.employment_type,
        status: form.status,
        manager_id: form.manager_id || null,
        location: form.location.trim() || null,
        profile_image_url: null,
        skills: form.skills.split(",").map((skill) => skill.trim()).filter(Boolean),
        metadata: {},
      });
      setIsModalOpen(false);
    } catch {
      setFormError("Employee could not be created. Check the details and try again.");
    }
  }

  return (
    <>
      <SectionPanel
        eyebrow={selectedCompany?.name ?? "People directory"}
        title="Employees"
        action={<Button disabled={!selectedCompany} variant="primary" icon={<Plus className="size-4" aria-hidden="true" />} onClick={openModal}>Add employee</Button>}
      >
        <ModuleBoundary
          emptyDescription={selectedCompany ? "Add employees to build the company directory and assign work objects." : "Create or select a company before adding employees."}
          emptyTitle="No employees yet"
          error={moduleError}
          isEmpty={data.employees.length === 0}
          isLoading={isLoadingModules}
          onRetry={onRetry}
          emptyAction={selectedCompany ? <Button variant="primary" icon={<Plus className="size-4" aria-hidden="true" />} onClick={openModal}>Add employee</Button> : undefined}
        >
          <DataTable columns={columns} rows={data.employees} getRowKey={(employee) => employee.id} />
        </ModuleBoundary>
      </SectionPanel>

      <Modal description="Add a company-scoped employee record for Phase 1 operations." isOpen={isModalOpen} title="Add employee" onClose={() => setIsModalOpen(false)}>
        <form className="space-y-4 p-5" onSubmit={handleSubmit}>
          <div className="grid gap-4 sm:grid-cols-2">
            <FieldShell label="Full name">
              <TextInput required value={form.full_name} onChange={(event) => setForm((current) => ({ ...current, full_name: event.target.value }))} />
            </FieldShell>
            <FieldShell label="Email">
              <TextInput required type="email" value={form.email} onChange={(event) => setForm((current) => ({ ...current, email: event.target.value }))} />
            </FieldShell>
            <FieldShell label="Role">
              <TextInput required value={form.role} onChange={(event) => setForm((current) => ({ ...current, role: event.target.value }))} />
            </FieldShell>
            <FieldShell label="Department">
              <TextInput value={form.department} onChange={(event) => setForm((current) => ({ ...current, department: event.target.value }))} />
            </FieldShell>
            <FieldShell label="Phone">
              <TextInput value={form.phone} onChange={(event) => setForm((current) => ({ ...current, phone: event.target.value }))} />
            </FieldShell>
            <FieldShell label="Location">
              <TextInput value={form.location} onChange={(event) => setForm((current) => ({ ...current, location: event.target.value }))} />
            </FieldShell>
            <FieldShell label="Status">
              <SelectInput value={form.status} onChange={(event) => setForm((current) => ({ ...current, status: event.target.value }))}>
                <option value="available">Available</option>
                <option value="working">Working</option>
                <option value="busy">Busy</option>
                <option value="on_leave">On Leave</option>
                <option value="offline">Offline</option>
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
            <FieldShell label="Manager">
              <SelectInput value={form.manager_id} onChange={(event) => setForm((current) => ({ ...current, manager_id: event.target.value }))}>
                <option value="">No manager</option>
                {data.employees.map((employee) => (
                  <option key={employee.id} value={employee.id}>
                    {employee.full_name}
                  </option>
                ))}
              </SelectInput>
            </FieldShell>
            <FieldShell label="Skills">
              <TextInput placeholder="Operations, Vendor coordination" value={form.skills} onChange={(event) => setForm((current) => ({ ...current, skills: event.target.value }))} />
            </FieldShell>
          </div>
          {formError ? <p className="text-sm font-semibold text-rose-700">{formError}</p> : null}
          <div className="flex justify-end gap-2 border-t border-grid-200 pt-4">
            <Button onClick={() => setIsModalOpen(false)}>Cancel</Button>
            <Button disabled={isMutating} type="submit" variant="primary">
              {isMutating ? "Creating..." : "Create employee"}
            </Button>
          </div>
        </form>
      </Modal>
    </>
  );
}
