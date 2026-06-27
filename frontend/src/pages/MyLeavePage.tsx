import { Ban, Eye, Pencil, Plus } from "lucide-react";
import { type FormEvent, useCallback, useState } from "react";

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
import type { Event as FebGridEvent, LeaveCancelPayload, LeaveCreatePayload, LeaveRequest, LeaveUpdatePayload } from "../types/api";
import type { ModulePageProps } from "../types/page";
import { compactList, formatDate, formatLabel, formatTime } from "../utils/format";

interface MyLeavePageProps extends ModulePageProps {
  onCancelLeave: (leaveId: string, payload: Omit<LeaveCancelPayload, "company_id">) => Promise<void>;
  onCreateLeave: (payload: Omit<LeaveCreatePayload, "company_id">) => Promise<void>;
  onUpdateLeave: (leaveId: string, payload: LeaveUpdatePayload) => Promise<void>;
}

const leaveTypeOptions = ["paid_leave", "sick_leave", "casual_leave", "half_day", "unpaid_leave", "work_from_home", "other"];

const initialForm = {
  start_date: "",
  end_date: "",
  leave_type: "casual_leave",
  approver_employee_id: "",
  reason: "",
};

type LeaveForm = typeof initialForm;

function leaveToForm(leave: LeaveRequest): LeaveForm {
  return {
    start_date: leave.start_date.slice(0, 10),
    end_date: leave.end_date.slice(0, 10),
    leave_type: leave.leave_type,
    approver_employee_id: leave.approver_employee_id ?? "",
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

export function MyLeavePage({
  data,
  selectedCompany,
  isLoadingModules,
  isMutating,
  moduleError,
  onRetry,
  onCancelLeave,
  onCreateLeave,
  onUpdateLeave,
}: MyLeavePageProps): JSX.Element {
  const selectedCompanyId = selectedCompany?.id ?? null;
  const profile = data.employees[0] ?? null;
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [editingLeave, setEditingLeave] = useState<LeaveRequest | null>(null);
  const [form, setForm] = useState<LeaveForm>(initialForm);
  const [formError, setFormError] = useState<string | null>(null);
  const [detailLeave, setDetailLeave] = useState<LeaveRequest | null>(null);
  const [detailEvents, setDetailEvents] = useState<FebGridEvent[]>([]);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [isDetailLoading, setIsDetailLoading] = useState(false);
  const calculatedDays = calculateTotalDays(form.start_date, form.end_date, form.leave_type);
  const employeeNames = {
    ...Object.fromEntries(data.leaveApprovers.map((employee) => [employee.id, employee.full_name])),
    ...Object.fromEntries(data.employees.map((employee) => [employee.id, employee.full_name])),
  };

  const loadDetail = useCallback(
    async (leaveId: string): Promise<void> => {
      if (!selectedCompanyId) return;
      setIsDetailLoading(true);
      setDetailError(null);
      try {
        const events = await api.leaveTimeline(leaveId, selectedCompanyId);
        setDetailEvents(events);
      } catch {
        setDetailError("Unable to load leave activity.");
      } finally {
        setIsDetailLoading(false);
      }
    },
    [selectedCompanyId],
  );

  function openCreate(): void {
    setEditingLeave(null);
    setForm(initialForm);
    setFormError(null);
    setIsFormOpen(true);
  }

  function openEdit(leave: LeaveRequest): void {
    setEditingLeave(leave);
    setForm(leaveToForm(leave));
    setFormError(null);
    setIsFormOpen(true);
  }

  function openDetail(leave: LeaveRequest): void {
    setDetailLeave(leave);
    setDetailEvents([]);
    setDetailError(null);
    void loadDetail(leave.id);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    setFormError(null);
    if (!profile) {
      setFormError("Your employee profile is not ready for leave submission.");
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
      employee_id: profile.id,
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
      setFormError("Leave request could not be saved.");
    }
  }

  const columns: DataTableColumn<LeaveRequest>[] = [
    { key: "type", label: "Type", render: (leave) => formatLabel(leave.leave_type) },
    { key: "dates", label: "Dates", render: (leave) => `${formatDate(leave.start_date)} - ${formatDate(leave.end_date)}` },
    { key: "days", label: "Days", render: (leave) => leave.total_days.toString() },
    { key: "status", label: "Status", render: (leave) => <Badge label={formatLabel(leave.status)} tone={statusTone(leave.status)} /> },
    { key: "approver", label: "Approver", render: (leave) => (leave.approver_employee_id ? employeeNames[leave.approver_employee_id] ?? "Assigned approver" : "Owner/admin fallback") },
    { key: "reason", label: "Reason", render: (leave) => <span className="line-clamp-2 max-w-72 text-sm text-ink-600">{leave.reason || "No reason recorded"}</span> },
    { key: "submitted", label: "Submitted", render: (leave) => formatDate(leave.submitted_at) },
    {
      key: "actions",
      label: "Actions",
      render: (leave) => (
        <div className="flex justify-end gap-2">
          <Button className="size-9 px-0" aria-label="View leave request" icon={<Eye className="size-4" aria-hidden="true" />} title="View leave request" onClick={() => openDetail(leave)}>
            <span className="sr-only">View leave request</span>
          </Button>
          <Button
            className="size-9 px-0"
            aria-label="Edit leave request"
            disabled={isMutating || leave.status !== "pending"}
            icon={<Pencil className="size-4" aria-hidden="true" />}
            title="Edit leave request"
            onClick={() => openEdit(leave)}
          >
            <span className="sr-only">Edit leave request</span>
          </Button>
          <Button
            className="size-9 px-0"
            aria-label="Cancel leave request"
            disabled={isMutating || !["pending", "approved"].includes(leave.status)}
            icon={<Ban className="size-4" aria-hidden="true" />}
            title="Cancel leave request"
            onClick={() => void onCancelLeave(leave.id, { manager_note: null })}
          >
            <span className="sr-only">Cancel leave request</span>
          </Button>
        </div>
      ),
      className: "text-right",
    },
  ];

  return (
    <>
      <SectionPanel
        eyebrow={selectedCompany?.name ?? "My availability"}
        title="My Leave"
        action={<Button disabled={!profile} variant="primary" icon={<Plus className="size-4" aria-hidden="true" />} onClick={openCreate}>Submit leave</Button>}
      >
        <ModuleBoundary
          emptyDescription="Your submitted leave requests will appear here."
          emptyTitle="No leave requests yet"
          error={moduleError}
          isEmpty={data.leaves.length === 0}
          isLoading={isLoadingModules}
          onRetry={onRetry}
          emptyAction={profile ? <Button variant="primary" icon={<Plus className="size-4" aria-hidden="true" />} onClick={openCreate}>Submit leave</Button> : undefined}
        >
          <DataTable columns={columns} rows={data.leaves} getRowKey={(leave) => leave.id} />
        </ModuleBoundary>
      </SectionPanel>

      <Modal description="Submit or update your own leave request." isOpen={isFormOpen} title={editingLeave ? "Edit my leave" : "Submit leave"} onClose={() => setIsFormOpen(false)}>
        <form className="space-y-4 p-5" onSubmit={handleSubmit}>
          <div className="rounded-lg border border-grid-200 bg-grid-50 p-4">
            <p className="text-xs font-bold uppercase tracking-normal text-ink-500">Employee</p>
            <p className="mt-2 text-sm font-bold text-ink-950">{profile?.full_name ?? "My profile"}</p>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <FieldShell label="Leave type">
              <SelectInput required value={form.leave_type} onChange={(event) => setForm((current) => ({ ...current, leave_type: event.target.value }))}>
                {leaveTypeOptions.map((leaveType) => (
                  <option key={leaveType} value={leaveType}>{formatLabel(leaveType)}</option>
                ))}
              </SelectInput>
            </FieldShell>
            <FieldShell label="Approver">
              <SelectInput value={form.approver_employee_id} onChange={(event) => setForm((current) => ({ ...current, approver_employee_id: event.target.value }))}>
                <option value="">Owner/admin fallback</option>
                {data.leaveApprovers.map((approver) => (
                  <option key={approver.id} value={approver.id}>
                    {approver.full_name}
                  </option>
                ))}
              </SelectInput>
            </FieldShell>
            <div className="rounded-lg border border-grid-200 bg-grid-50 p-3">
              <p className="text-xs font-bold uppercase tracking-normal text-ink-500">Total days</p>
              <p className="mt-2 text-sm font-bold text-ink-950">{calculatedDays || "Set dates"}</p>
            </div>
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
            <Button onClick={() => setIsFormOpen(false)}>Cancel</Button>
            <Button disabled={isMutating} type="submit" variant="primary">
              {isMutating ? "Saving..." : editingLeave ? "Save changes" : "Submit leave"}
            </Button>
          </div>
        </form>
      </Modal>

      <Modal description="Your leave request timeline." isOpen={Boolean(detailLeave)} title={detailLeave ? `${formatLabel(detailLeave.leave_type)} leave` : "Leave request"} onClose={() => setDetailLeave(null)}>
        {detailLeave ? (
          <div className="space-y-5 p-5">
            <div className="grid gap-4 sm:grid-cols-2">
              <DetailItem label="Status" value={formatLabel(detailLeave.status)} tone={statusTone(detailLeave.status)} />
              <DetailItem label="Dates" value={compactList([formatDate(detailLeave.start_date), formatDate(detailLeave.end_date)])} />
              <DetailItem label="Total days" value={detailLeave.total_days.toString()} />
              <DetailItem label="Approver" value={detailLeave.approver_employee_id ? employeeNames[detailLeave.approver_employee_id] ?? "Assigned approver" : "Owner/admin fallback"} />
              <DetailItem label="Submitted" value={formatDate(detailLeave.submitted_at)} />
            </div>
            {detailLeave.reason ? <p className="rounded-lg border border-grid-200 bg-grid-50 p-4 text-sm font-medium text-ink-600">{detailLeave.reason}</p> : null}
            {detailLeave.manager_note ? <p className="rounded-lg border border-grid-200 bg-grid-50 p-4 text-sm font-medium text-ink-600">{detailLeave.manager_note}</p> : null}

            {isDetailLoading ? <LoadingState label="Loading leave activity" /> : null}
            {detailError ? <ErrorState message={detailError} onRetry={() => loadDetail(detailLeave.id)} /> : null}
            {!isDetailLoading && !detailError ? (
              <section className="rounded-lg border border-grid-200">
                <div className="border-b border-grid-200 px-4 py-3">
                  <h3 className="text-sm font-bold text-ink-950">Activity</h3>
                </div>
                {detailEvents.length === 0 ? (
                  <EmptyState description="Leave workflow activity will appear here." title="No activity yet" />
                ) : (
                  <div className="divide-y divide-grid-100">
                    {detailEvents.slice(0, 8).map((event) => (
                      <article key={event.id} className="px-4 py-3">
                        <p className="text-sm font-bold text-ink-950">{event.title}</p>
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

function DetailItem({ label, value, tone }: { label: string; value: string; tone?: "blue" | "green" | "amber" | "red" | "teal" | "slate" }): JSX.Element {
  return (
    <div className="rounded-lg border border-grid-200 bg-grid-50 p-4">
      <p className="text-xs font-bold uppercase tracking-normal text-ink-500">{label}</p>
      <div className="mt-2">{tone ? <Badge label={value} tone={tone} /> : <p className="text-sm font-bold text-ink-950">{value}</p>}</div>
    </div>
  );
}
