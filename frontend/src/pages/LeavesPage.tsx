import { Plus } from "lucide-react";
import { type FormEvent, useMemo, useState } from "react";

import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { DataTable, type DataTableColumn } from "../components/ui/DataTable";
import { FieldShell, SelectInput, TextArea, TextInput } from "../components/ui/FormControls";
import { Modal } from "../components/ui/Modal";
import { ModuleBoundary } from "../components/ui/ModuleBoundary";
import { SectionPanel } from "../components/ui/SectionPanel";
import { statusTone } from "../components/ui/tone";
import type { LeaveCreatePayload, LeaveRequest } from "../types/api";
import type { ModulePageProps } from "../types/page";
import { formatDate, formatLabel } from "../utils/format";

interface LeavesPageProps extends ModulePageProps {
  onCreateLeave: (payload: Omit<LeaveCreatePayload, "company_id">) => Promise<void>;
}

const initialForm = {
  employee_id: "",
  approver_employee_id: "",
  start_date: "",
  end_date: "",
  leave_type: "casual_leave",
  reason: "",
};

export function LeavesPage({
  data,
  selectedCompany,
  isLoadingModules,
  moduleError,
  onRetry,
  onCreateLeave,
  isMutating,
}: LeavesPageProps): JSX.Element {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [form, setForm] = useState(initialForm);
  const [formError, setFormError] = useState<string | null>(null);

  const employeeNames = useMemo(
    () => Object.fromEntries(data.employees.map((employee) => [employee.id, employee.full_name])),
    [data.employees],
  );

  const columns: DataTableColumn<LeaveRequest>[] = [
    { key: "employee", label: "Employee", render: (leave) => <span className="font-bold text-ink-950">{employeeNames[leave.employee_id] ?? "Employee"}</span> },
    { key: "type", label: "Type", render: (leave) => formatLabel(leave.leave_type) },
    { key: "dates", label: "Dates", render: (leave) => `${formatDate(leave.start_date)} - ${formatDate(leave.end_date)}` },
    { key: "status", label: "Status", render: (leave) => <Badge label={formatLabel(leave.status)} tone={statusTone(leave.status)} /> },
    { key: "approver", label: "Approver", render: (leave) => leave.approver_employee_id ? employeeNames[leave.approver_employee_id] ?? "Approver" : "Not assigned" },
  ];

  function openModal(): void {
    setForm({ ...initialForm, employee_id: data.employees[0]?.id ?? "" });
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
    if (!form.employee_id) {
      setFormError("Choose an employee for the leave request.");
      return;
    }
    if (form.end_date < form.start_date) {
      setFormError("End date must be on or after start date.");
      return;
    }

    try {
      await onCreateLeave({
        employee_id: form.employee_id,
        approver_employee_id: form.approver_employee_id || null,
        start_date: form.start_date,
        end_date: form.end_date,
        leave_type: form.leave_type,
        reason: form.reason.trim() || null,
        status: "pending",
        decision_note: null,
      });
      setIsModalOpen(false);
    } catch {
      setFormError("Leave request could not be submitted. Check the details and try again.");
    }
  }

  return (
    <>
      <SectionPanel
        eyebrow={selectedCompany?.name ?? "Availability"}
        title="Leave Requests"
        action={<Button disabled={!selectedCompany || data.employees.length === 0} variant="primary" icon={<Plus className="size-4" aria-hidden="true" />} onClick={openModal}>Submit leave</Button>}
      >
        <ModuleBoundary
          emptyDescription={data.employees.length === 0 ? "Add employees before submitting leave requests." : "Submitted leave requests will appear here for review."}
          emptyTitle="No leave requests yet"
          error={moduleError}
          isEmpty={data.leaves.length === 0}
          isLoading={isLoadingModules}
          onRetry={onRetry}
          emptyAction={selectedCompany && data.employees.length > 0 ? <Button variant="primary" icon={<Plus className="size-4" aria-hidden="true" />} onClick={openModal}>Submit leave</Button> : undefined}
        >
          <DataTable columns={columns} rows={data.leaves} getRowKey={(leave) => leave.id} />
        </ModuleBoundary>
      </SectionPanel>

      <Modal description="Submit a real leave request. The event engine records the request." isOpen={isModalOpen} title="Submit leave" onClose={() => setIsModalOpen(false)}>
        <form className="space-y-4 p-5" onSubmit={handleSubmit}>
          <div className="grid gap-4 sm:grid-cols-2">
            <FieldShell label="Employee">
              <SelectInput required value={form.employee_id} onChange={(event) => setForm((current) => ({ ...current, employee_id: event.target.value }))}>
                {data.employees.map((employee) => (
                  <option key={employee.id} value={employee.id}>{employee.full_name}</option>
                ))}
              </SelectInput>
            </FieldShell>
            <FieldShell label="Approver">
              <SelectInput value={form.approver_employee_id} onChange={(event) => setForm((current) => ({ ...current, approver_employee_id: event.target.value }))}>
                <option value="">No approver</option>
                {data.employees.map((employee) => (
                  <option key={employee.id} value={employee.id}>{employee.full_name}</option>
                ))}
              </SelectInput>
            </FieldShell>
            <FieldShell label="Leave type">
              <SelectInput value={form.leave_type} onChange={(event) => setForm((current) => ({ ...current, leave_type: event.target.value }))}>
                <option value="sick_leave">Sick Leave</option>
                <option value="casual_leave">Casual Leave</option>
                <option value="paid_leave">Paid Leave</option>
                <option value="unpaid_leave">Unpaid Leave</option>
                <option value="emergency_leave">Emergency Leave</option>
                <option value="half_day">Half Day</option>
              </SelectInput>
            </FieldShell>
            <FieldShell label="Start date">
              <TextInput required type="date" value={form.start_date} onChange={(event) => setForm((current) => ({ ...current, start_date: event.target.value }))} />
            </FieldShell>
            <FieldShell label="End date">
              <TextInput required type="date" value={form.end_date} onChange={(event) => setForm((current) => ({ ...current, end_date: event.target.value }))} />
            </FieldShell>
          </div>
          <FieldShell label="Reason">
            <TextArea value={form.reason} onChange={(event) => setForm((current) => ({ ...current, reason: event.target.value }))} />
          </FieldShell>
          {formError ? <p className="text-sm font-semibold text-rose-700">{formError}</p> : null}
          <div className="flex justify-end gap-2 border-t border-grid-200 pt-4">
            <Button onClick={() => setIsModalOpen(false)}>Cancel</Button>
            <Button disabled={isMutating} type="submit" variant="primary">
              {isMutating ? "Submitting..." : "Submit leave"}
            </Button>
          </div>
        </form>
      </Modal>
    </>
  );
}
