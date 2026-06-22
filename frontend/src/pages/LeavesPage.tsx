import { Archive, Ban, CheckCircle2, Eye, Pencil, Plus, XCircle } from "lucide-react";
import { type FormEvent, useCallback, useMemo, useState } from "react";

import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { DataTable, type DataTableColumn } from "../components/ui/DataTable";
import { FieldShell, SelectInput, TextArea, TextInput } from "../components/ui/FormControls";
import { Modal } from "../components/ui/Modal";
import { ModuleBoundary } from "../components/ui/ModuleBoundary";
import { SectionPanel } from "../components/ui/SectionPanel";
import { EmptyState, ErrorState, LoadingState } from "../components/ui/States";
import { statusTone } from "../components/ui/tone";
import { api } from "../services/api";
import type {
  Event as FebGridEvent,
  LeaveCancelPayload,
  LeaveCreatePayload,
  LeaveDecisionPayload,
  LeaveRequest,
  LeaveUpdatePayload,
} from "../types/api";
import type { ModulePageProps } from "../types/page";
import { compactList, formatDate, formatLabel, formatTime } from "../utils/format";

interface LeavesPageProps extends ModulePageProps {
  onApproveLeave: (leaveId: string, payload: Omit<LeaveDecisionPayload, "company_id">) => Promise<void>;
  onCancelLeave: (leaveId: string, payload: Omit<LeaveCancelPayload, "company_id">) => Promise<void>;
  onCreateLeave: (payload: Omit<LeaveCreatePayload, "company_id">) => Promise<void>;
  onDeactivateLeave: (leaveId: string) => Promise<void>;
  onRejectLeave: (leaveId: string, payload: Omit<LeaveDecisionPayload, "company_id">) => Promise<void>;
  onUpdateLeave: (leaveId: string, payload: LeaveUpdatePayload) => Promise<void>;
}

const leaveTypeOptions = ["paid_leave", "sick_leave", "casual_leave", "half_day", "unpaid_leave", "work_from_home", "other"];

const initialForm = {
  employee_id: "",
  approver_employee_id: "",
  start_date: "",
  end_date: "",
  leave_type: "casual_leave",
  reason: "",
};

const initialDecisionForm = {
  approver_employee_id: "",
  manager_note: "",
};

type LeaveForm = typeof initialForm;
type DecisionAction = "approve" | "reject" | "cancel";
type DecisionState = { action: DecisionAction; leave: LeaveRequest } | null;
type BadgeTone = "blue" | "green" | "amber" | "red" | "teal" | "slate";

function leaveToForm(leave: LeaveRequest): LeaveForm {
  return {
    employee_id: leave.employee_id,
    approver_employee_id: leave.approver_employee_id ?? "",
    start_date: leave.start_date.slice(0, 10),
    end_date: leave.end_date.slice(0, 10),
    leave_type: leave.leave_type,
    reason: leave.reason ?? "",
  };
}

function calculateTotalDays(startDate: string, endDate: string, leaveType: string): number {
  if (!startDate || !endDate) return 0;
  const start = new Date(`${startDate}T00:00:00`);
  const end = new Date(`${endDate}T00:00:00`);
  if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime()) || end < start) return 0;
  if (leaveType === "half_day") return 0.5;
  return Math.floor((end.getTime() - start.getTime()) / 86_400_000) + 1;
}

export function LeavesPage({
  data,
  selectedCompany,
  isLoadingModules,
  moduleError,
  onRetry,
  onApproveLeave,
  onCancelLeave,
  onCreateLeave,
  onDeactivateLeave,
  onRejectLeave,
  onUpdateLeave,
  isMutating,
}: LeavesPageProps): JSX.Element {
  const selectedCompanyId = selectedCompany?.id ?? null;
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [editingLeave, setEditingLeave] = useState<LeaveRequest | null>(null);
  const [form, setForm] = useState<LeaveForm>(initialForm);
  const [formError, setFormError] = useState<string | null>(null);
  const [decisionState, setDecisionState] = useState<DecisionState>(null);
  const [decisionForm, setDecisionForm] = useState(initialDecisionForm);
  const [decisionError, setDecisionError] = useState<string | null>(null);
  const [detailLeave, setDetailLeave] = useState<LeaveRequest | null>(null);
  const [detailEvents, setDetailEvents] = useState<FebGridEvent[]>([]);
  const [isDetailLoading, setIsDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);

  const employeeNames = useMemo(
    () => Object.fromEntries(data.employees.map((employee) => [employee.id, employee.full_name])),
    [data.employees],
  );

  const visibleLeaves = useMemo(() => data.leaves.filter((leave) => leave.is_active), [data.leaves]);
  const calculatedDays = calculateTotalDays(form.start_date, form.end_date, form.leave_type);

  const loadLeaveDetail = useCallback(
    async (leaveId: string): Promise<void> => {
      if (!selectedCompanyId) return;
      setIsDetailLoading(true);
      setDetailError(null);
      try {
        const events = await api.leaveTimeline(leaveId, selectedCompanyId);
        setDetailEvents(events);
      } catch {
        setDetailError("Unable to load leave timeline.");
      } finally {
        setIsDetailLoading(false);
      }
    },
    [selectedCompanyId],
  );

  const columns: DataTableColumn<LeaveRequest>[] = [
    {
      key: "employee",
      label: "Employee",
      render: (leave) => <span className="font-bold text-ink-950">{employeeNames[leave.employee_id] ?? "Employee"}</span>,
    },
    { key: "type", label: "Type", render: (leave) => formatLabel(leave.leave_type) },
    { key: "dates", label: "Dates", render: (leave) => `${formatDate(leave.start_date)} - ${formatDate(leave.end_date)}` },
    { key: "total", label: "Days", render: (leave) => leave.total_days.toString() },
    { key: "status", label: "Status", render: (leave) => <Badge label={formatLabel(leave.status)} tone={statusTone(leave.status)} /> },
    { key: "approver", label: "Approver", render: (leave) => leave.approver_employee_id ? employeeNames[leave.approver_employee_id] ?? "Approver" : "Not assigned" },
    {
      key: "reason",
      label: "Reason",
      render: (leave) => <span className="line-clamp-2 max-w-56 text-sm text-ink-600">{leave.reason || "No reason recorded"}</span>,
    },
    { key: "submitted", label: "Submitted", render: (leave) => formatDate(leave.submitted_at) },
    {
      key: "actions",
      label: "Actions",
      render: (leave) => (
        <div className="flex flex-wrap justify-end gap-2">
          <Button className="size-9 px-0" aria-label="View leave request" icon={<Eye className="size-4" aria-hidden="true" />} onClick={() => openDetail(leave)}>
            <span className="sr-only">View</span>
          </Button>
          <Button
            className="size-9 px-0"
            aria-label="Edit leave request"
            disabled={isMutating || leave.status !== "pending"}
            icon={<Pencil className="size-4" aria-hidden="true" />}
            onClick={() => openEdit(leave)}
          >
            <span className="sr-only">Edit</span>
          </Button>
          <Button
            className="size-9 px-0"
            aria-label="Approve leave request"
            disabled={isMutating || leave.status !== "pending"}
            icon={<CheckCircle2 className="size-4" aria-hidden="true" />}
            onClick={() => openDecision("approve", leave)}
          >
            <span className="sr-only">Approve</span>
          </Button>
          <Button
            className="size-9 px-0"
            aria-label="Reject leave request"
            disabled={isMutating || leave.status !== "pending"}
            icon={<XCircle className="size-4" aria-hidden="true" />}
            onClick={() => openDecision("reject", leave)}
          >
            <span className="sr-only">Reject</span>
          </Button>
          <Button
            className="size-9 px-0"
            aria-label="Cancel leave request"
            disabled={isMutating || !["pending", "approved"].includes(leave.status)}
            icon={<Ban className="size-4" aria-hidden="true" />}
            onClick={() => openDecision("cancel", leave)}
          >
            <span className="sr-only">Cancel</span>
          </Button>
          <Button
            className="size-9 px-0"
            aria-label="Archive leave request"
            disabled={isMutating || !leave.is_active}
            icon={<Archive className="size-4" aria-hidden="true" />}
            onClick={() => void onDeactivateLeave(leave.id)}
          >
            <span className="sr-only">Archive</span>
          </Button>
        </div>
      ),
      className: "text-right",
    },
  ];

  function openCreate(): void {
    setEditingLeave(null);
    setForm({ ...initialForm, employee_id: data.employees[0]?.id ?? "" });
    setFormError(null);
    setIsFormOpen(true);
  }

  function openEdit(leave: LeaveRequest): void {
    setEditingLeave(leave);
    setDetailLeave(null);
    setForm(leaveToForm(leave));
    setFormError(null);
    setIsFormOpen(true);
  }

  function openDetail(leave: LeaveRequest): void {
    setDetailLeave(leave);
    setDetailEvents([]);
    setDetailError(null);
    void loadLeaveDetail(leave.id);
  }

  function openDecision(action: DecisionAction, leave: LeaveRequest): void {
    setDecisionState({ action, leave });
    setDecisionForm({
      approver_employee_id: leave.approver_employee_id ?? data.employees[0]?.id ?? "",
      manager_note: "",
    });
    setDecisionError(null);
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
    if (!form.leave_type) {
      setFormError("Choose a leave type.");
      return;
    }
    if (!form.start_date || !form.end_date) {
      setFormError("Start and end dates are required.");
      return;
    }
    if (form.end_date < form.start_date) {
      setFormError("End date must be on or after start date.");
      return;
    }

    const payload = {
      employee_id: form.employee_id,
      approver_employee_id: form.approver_employee_id || null,
      start_date: form.start_date,
      end_date: form.end_date,
      leave_type: form.leave_type,
      reason: form.reason.trim() || null,
      metadata: {},
    };

    try {
      if (editingLeave) {
        await onUpdateLeave(editingLeave.id, payload);
      } else {
        await onCreateLeave({ ...payload, status: "pending" });
      }
      setIsFormOpen(false);
    } catch {
      setFormError("Leave request could not be saved. Check the details and try again.");
    }
  }

  async function handleDecisionSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (!decisionState) return;
    setDecisionError(null);
    const payload = {
      approver_employee_id: decisionForm.approver_employee_id || null,
      manager_note: decisionForm.manager_note.trim() || null,
    };

    try {
      if (decisionState.action === "approve") {
        await onApproveLeave(decisionState.leave.id, payload);
      } else if (decisionState.action === "reject") {
        await onRejectLeave(decisionState.leave.id, payload);
      } else {
        await onCancelLeave(decisionState.leave.id, { manager_note: payload.manager_note });
      }
      setDecisionState(null);
      setDetailLeave(null);
    } catch {
      setDecisionError("Leave decision could not be saved. Try again.");
    }
  }

  return (
    <>
      <SectionPanel
        eyebrow={selectedCompany?.name ?? "Availability"}
        title="Leave Requests"
        action={<Button disabled={!selectedCompany || data.employees.length === 0} variant="primary" icon={<Plus className="size-4" aria-hidden="true" />} onClick={openCreate}>Submit leave</Button>}
      >
        <ModuleBoundary
          emptyDescription={data.employees.length === 0 ? "Add employees before submitting leave requests." : "Submitted leave requests will appear here for review."}
          emptyTitle="No leave requests yet"
          error={moduleError}
          isEmpty={visibleLeaves.length === 0}
          isLoading={isLoadingModules}
          onRetry={onRetry}
          emptyAction={selectedCompany && data.employees.length > 0 ? <Button variant="primary" icon={<Plus className="size-4" aria-hidden="true" />} onClick={openCreate}>Submit leave</Button> : undefined}
        >
          <DataTable columns={columns} rows={visibleLeaves} getRowKey={(leave) => leave.id} />
        </ModuleBoundary>
      </SectionPanel>

      <Modal description="Submit or update a tenant-scoped leave request." isOpen={isFormOpen} title={editingLeave ? "Edit leave request" : "Submit leave"} onClose={() => setIsFormOpen(false)}>
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
              <SelectInput required value={form.leave_type} onChange={(event) => setForm((current) => ({ ...current, leave_type: event.target.value }))}>
                {leaveTypeOptions.map((leaveType) => (
                  <option key={leaveType} value={leaveType}>{formatLabel(leaveType)}</option>
                ))}
              </SelectInput>
            </FieldShell>
            <FieldShell label="Start date">
              <TextInput required type="date" value={form.start_date} onChange={(event) => setForm((current) => ({ ...current, start_date: event.target.value }))} />
            </FieldShell>
            <FieldShell label="End date">
              <TextInput required type="date" value={form.end_date} onChange={(event) => setForm((current) => ({ ...current, end_date: event.target.value }))} />
            </FieldShell>
            <div className="rounded-lg border border-grid-200 bg-grid-50 p-3">
              <p className="text-xs font-bold uppercase tracking-normal text-ink-500">Total days</p>
              <p className="mt-2 text-sm font-bold text-ink-950">{calculatedDays || "Set dates"}</p>
            </div>
          </div>
          <FieldShell label="Reason">
            <TextArea value={form.reason} onChange={(event) => setForm((current) => ({ ...current, reason: event.target.value }))} />
          </FieldShell>
          {formError ? <p className="text-sm font-semibold text-rose-700">{formError}</p> : null}
          <div className="flex justify-end gap-2 border-t border-grid-200 pt-4">
            <Button onClick={() => setIsFormOpen(false)}>Cancel</Button>
            <Button disabled={isMutating} type="submit" variant="primary">
              {isMutating ? "Saving..." : editingLeave ? "Save changes" : "Submit leave"}
            </Button>
          </div>
        </form>
      </Modal>

      <Modal
        description="Record the manager decision for this leave request."
        isOpen={Boolean(decisionState)}
        title={decisionState ? `${formatLabel(decisionState.action)} leave` : "Leave decision"}
        onClose={() => setDecisionState(null)}
      >
        {decisionState ? (
          <form className="space-y-4 p-5" onSubmit={handleDecisionSubmit}>
            {decisionState.action !== "cancel" ? (
              <FieldShell label="Approver">
                <SelectInput value={decisionForm.approver_employee_id} onChange={(event) => setDecisionForm((current) => ({ ...current, approver_employee_id: event.target.value }))}>
                  <option value="">No approver</option>
                  {data.employees.map((employee) => (
                    <option key={employee.id} value={employee.id}>{employee.full_name}</option>
                  ))}
                </SelectInput>
              </FieldShell>
            ) : null}
            <FieldShell label="Manager note">
              <TextArea value={decisionForm.manager_note} onChange={(event) => setDecisionForm((current) => ({ ...current, manager_note: event.target.value }))} />
            </FieldShell>
            {decisionError ? <p className="text-sm font-semibold text-rose-700">{decisionError}</p> : null}
            <div className="flex justify-end gap-2 border-t border-grid-200 pt-4">
              <Button onClick={() => setDecisionState(null)}>Cancel</Button>
              <Button disabled={isMutating} type="submit" variant="primary">
                {isMutating ? "Saving..." : decisionState.action === "cancel" ? "Confirm cancel" : formatLabel(decisionState.action)}
              </Button>
            </div>
          </form>
        ) : null}
      </Modal>

      <Modal description="Leave context, approval state, and event history." isOpen={Boolean(detailLeave)} title={detailLeave ? `${formatLabel(detailLeave.leave_type)} leave` : "Leave request"} onClose={() => setDetailLeave(null)}>
        {detailLeave ? (
          <div className="space-y-5 p-5">
            <div className="grid gap-4 sm:grid-cols-2">
              <DetailItem label="Employee" value={employeeNames[detailLeave.employee_id] ?? "Employee"} />
              <DetailItem label="Status" value={formatLabel(detailLeave.status)} badgeTone={statusTone(detailLeave.status)} />
              <DetailItem label="Leave type" value={formatLabel(detailLeave.leave_type)} />
              <DetailItem label="Approver" value={detailLeave.approver_employee_id ? employeeNames[detailLeave.approver_employee_id] ?? "Approver" : "Not assigned"} />
              <DetailItem label="Dates" value={compactList([formatDate(detailLeave.start_date), formatDate(detailLeave.end_date)])} />
              <DetailItem label="Total days" value={detailLeave.total_days.toString()} />
              <DetailItem label="Submitted" value={formatDate(detailLeave.submitted_at)} />
              <DetailItem label="Decision" value={compactList([detailLeave.approved_at ? `Approved ${formatDate(detailLeave.approved_at)}` : null, detailLeave.rejected_at ? `Rejected ${formatDate(detailLeave.rejected_at)}` : null, detailLeave.cancelled_at ? `Cancelled ${formatDate(detailLeave.cancelled_at)}` : null]) || "Pending"} />
            </div>

            {detailLeave.reason ? <p className="rounded-lg border border-grid-200 bg-grid-50 p-4 text-sm font-medium text-ink-600">{detailLeave.reason}</p> : null}
            {detailLeave.manager_note ? <p className="rounded-lg border border-grid-200 bg-grid-50 p-4 text-sm font-medium text-ink-600">{detailLeave.manager_note}</p> : null}

            <div className="flex flex-wrap gap-2">
              <Button disabled={detailLeave.status !== "pending"} icon={<Pencil className="size-4" aria-hidden="true" />} onClick={() => openEdit(detailLeave)}>Edit</Button>
              <Button disabled={isMutating || detailLeave.status !== "pending"} variant="primary" icon={<CheckCircle2 className="size-4" aria-hidden="true" />} onClick={() => openDecision("approve", detailLeave)}>Approve</Button>
              <Button disabled={isMutating || detailLeave.status !== "pending"} icon={<XCircle className="size-4" aria-hidden="true" />} onClick={() => openDecision("reject", detailLeave)}>Reject</Button>
              <Button disabled={isMutating || !["pending", "approved"].includes(detailLeave.status)} icon={<Ban className="size-4" aria-hidden="true" />} onClick={() => openDecision("cancel", detailLeave)}>Cancel</Button>
            </div>

            {isDetailLoading ? <LoadingState label="Loading leave timeline" /> : null}
            {detailError ? <ErrorState message={detailError} onRetry={() => loadLeaveDetail(detailLeave.id)} /> : null}
            {!isDetailLoading && !detailError ? (
              <section className="rounded-lg border border-grid-200">
                <div className="border-b border-grid-200 px-4 py-3">
                  <h3 className="text-sm font-bold text-ink-950">Timeline</h3>
                </div>
                {detailEvents.length === 0 ? (
                  <EmptyState description="Leave workflow events will appear here." title="No leave events yet" />
                ) : (
                  <div className="divide-y divide-grid-100">
                    {detailEvents.slice(0, 8).map((event) => (
                      <article key={event.id} className="px-4 py-3">
                        <p className="truncate text-sm font-bold text-ink-950">{event.title}</p>
                        <p className="mt-1 text-xs font-semibold text-ink-500">{formatTime(event.created_at)} / {formatLabel(event.event_type)}</p>
                      </article>
                    ))}
                  </div>
                )}
              </section>
            ) : null}
          </div>
        ) : null}
      </Modal>
    </>
  );
}

function DetailItem({ label, value, badgeTone }: { label: string; value: string; badgeTone?: BadgeTone }): JSX.Element {
  return (
    <div className="rounded-lg border border-grid-200 bg-grid-50 p-4">
      <p className="text-xs font-bold uppercase tracking-normal text-ink-500">{label}</p>
      <div className="mt-2">{badgeTone ? <Badge label={value} tone={badgeTone} /> : <p className="text-sm font-bold text-ink-950">{value}</p>}</div>
    </div>
  );
}
