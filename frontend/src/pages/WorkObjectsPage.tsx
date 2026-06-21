import { Archive, CheckCircle2, Eye, Pencil, Plus } from "lucide-react";
import { type FormEvent, useCallback, useMemo, useState } from "react";

import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { DataTable, type DataTableColumn } from "../components/ui/DataTable";
import { FieldShell, SelectInput, TextArea, TextInput } from "../components/ui/FormControls";
import { Modal } from "../components/ui/Modal";
import { ModuleBoundary } from "../components/ui/ModuleBoundary";
import { SectionPanel } from "../components/ui/SectionPanel";
import { EmptyState, ErrorState, LoadingState } from "../components/ui/States";
import { priorityTone, statusTone } from "../components/ui/tone";
import { api } from "../services/api";
import type { Event as FebGridEvent, WorkObject, WorkObjectCreatePayload, WorkObjectUpdatePayload } from "../types/api";
import type { ModulePageProps } from "../types/page";
import { compactList, formatDate, formatLabel, formatTime } from "../utils/format";

interface WorkObjectsPageProps extends ModulePageProps {
  onCreateWorkObject: (payload: Omit<WorkObjectCreatePayload, "company_id">) => Promise<void>;
  onUpdateWorkObject: (workObjectId: string, payload: WorkObjectUpdatePayload) => Promise<void>;
  onDeactivateWorkObject: (workObjectId: string) => Promise<void>;
  onAssignWorkObject: (workObjectId: string, assigneeEmployeeId: string | null) => Promise<void>;
  onUpdateWorkObjectStatus: (workObjectId: string, status: string) => Promise<void>;
  onUpdateWorkObjectPriority: (workObjectId: string, priority: string) => Promise<void>;
  onCompleteWorkObject: (workObjectId: string) => Promise<void>;
}

const objectTypeOptions = ["task", "approval_request", "issue", "site_visit", "invoice", "document_review", "general"];
const statusOptions = ["assigned", "in_progress", "under_review", "blocked", "completed", "cancelled"];
const priorityOptions = ["low", "medium", "high", "critical"];

const initialForm = {
  title: "",
  description: "",
  object_type: "task",
  status: "assigned",
  priority: "medium",
  project_id: "",
  department_id: "",
  team_id: "",
  creator_employee_id: "",
  assignee_employee_id: "",
  start_date: "",
  due_date: "",
  tags: "",
  metadata_notes: "",
};

type WorkObjectForm = typeof initialForm;
type BadgeTone = "blue" | "green" | "amber" | "red" | "teal" | "slate";

function workObjectToForm(workObject: WorkObject): WorkObjectForm {
  return {
    title: workObject.title,
    description: workObject.description ?? "",
    object_type: workObject.object_type,
    status: workObject.status,
    priority: workObject.priority,
    project_id: workObject.project_id ?? "",
    department_id: workObject.department_id ?? "",
    team_id: workObject.team_id ?? "",
    creator_employee_id: workObject.creator_employee_id ?? "",
    assignee_employee_id: workObject.assignee_employee_id ?? "",
    start_date: workObject.start_date ? workObject.start_date.slice(0, 10) : "",
    due_date: workObject.due_date ? workObject.due_date.slice(0, 10) : "",
    tags: workObject.tags.join(", "),
    metadata_notes: typeof workObject.metadata.notes === "string" ? workObject.metadata.notes : "",
  };
}

function dateToIso(value: string, endOfDay = false): string | null {
  if (!value) return null;
  return `${value}T${endOfDay ? "23:59:00" : "00:00:00"}.000Z`;
}

export function WorkObjectsPage({
  data,
  selectedCompany,
  isLoadingModules,
  moduleError,
  onRetry,
  onCreateWorkObject,
  onUpdateWorkObject,
  onDeactivateWorkObject,
  onAssignWorkObject,
  onUpdateWorkObjectStatus,
  onUpdateWorkObjectPriority,
  onCompleteWorkObject,
  isMutating,
}: WorkObjectsPageProps): JSX.Element {
  const selectedCompanyId = selectedCompany?.id ?? null;
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [form, setForm] = useState<WorkObjectForm>(initialForm);
  const [formError, setFormError] = useState<string | null>(null);
  const [editingWorkObject, setEditingWorkObject] = useState<WorkObject | null>(null);
  const [detailWorkObject, setDetailWorkObject] = useState<WorkObject | null>(null);
  const [detailEvents, setDetailEvents] = useState<FebGridEvent[]>([]);
  const [isDetailLoading, setIsDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);

  const employeeNames = useMemo(() => Object.fromEntries(data.employees.map((employee) => [employee.id, employee.full_name])), [data.employees]);
  const projectNames = useMemo(() => Object.fromEntries(data.projects.map((project) => [project.id, project.name])), [data.projects]);
  const departmentNames = useMemo(
    () => Object.fromEntries(data.departments.map((department) => [department.id, department.name])),
    [data.departments],
  );
  const teamNames = useMemo(() => Object.fromEntries(data.teams.map((team) => [team.id, team.name])), [data.teams]);

  const loadWorkObjectDetail = useCallback(
    async (workObjectId: string): Promise<void> => {
      if (!selectedCompanyId) return;
      setIsDetailLoading(true);
      setDetailError(null);
      try {
        const events = await api.workObjectTimeline(workObjectId, selectedCompanyId);
        setDetailEvents(events);
      } catch {
        setDetailError("Unable to load work object timeline.");
      } finally {
        setIsDetailLoading(false);
      }
    },
    [selectedCompanyId],
  );

  const columns: DataTableColumn<WorkObject>[] = [
    {
      key: "title",
      label: "Work object",
      render: (workObject) => (
        <span className="min-w-56">
          <span className="block truncate font-bold text-ink-950">{workObject.title}</span>
          <span className="block truncate text-xs text-ink-500">{formatLabel(workObject.object_type)}</span>
        </span>
      ),
    },
    { key: "project", label: "Project", render: (workObject) => workObject.project_id ? projectNames[workObject.project_id] ?? "Linked" : "None" },
    {
      key: "assignee",
      label: "Assignee",
      render: (workObject) => (
        <SelectInput
          aria-label={`Assign ${workObject.title}`}
          disabled={isMutating || !workObject.is_active}
          value={workObject.assignee_employee_id ?? ""}
          onChange={(event) => void onAssignWorkObject(workObject.id, event.target.value || null)}
        >
          <option value="">Unassigned</option>
          {data.employees.map((employee) => (
            <option key={employee.id} value={employee.id}>
              {employee.full_name}
            </option>
          ))}
        </SelectInput>
      ),
    },
    {
      key: "org",
      label: "Department / Team",
      render: (workObject) => compactList([workObject.department_id ? departmentNames[workObject.department_id] : null, workObject.team_id ? teamNames[workObject.team_id] : null]) || "Not assigned",
    },
    {
      key: "status",
      label: "Status",
      render: (workObject) => (
        <SelectInput
          aria-label={`Update ${workObject.title} status`}
          disabled={isMutating || !workObject.is_active}
          value={workObject.status}
          onChange={(event) => void onUpdateWorkObjectStatus(workObject.id, event.target.value)}
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
      key: "priority",
      label: "Priority",
      render: (workObject) => (
        <SelectInput
          aria-label={`Update ${workObject.title} priority`}
          disabled={isMutating || !workObject.is_active}
          value={workObject.priority}
          onChange={(event) => void onUpdateWorkObjectPriority(workObject.id, event.target.value)}
        >
          {priorityOptions.map((priority) => (
            <option key={priority} value={priority}>
              {formatLabel(priority)}
            </option>
          ))}
        </SelectInput>
      ),
    },
    { key: "due", label: "Due", render: (workObject) => formatDate(workObject.due_date) },
    { key: "updated", label: "Updated", render: (workObject) => formatDate(workObject.updated_at) },
    {
      key: "actions",
      label: "Actions",
      render: (workObject) => (
        <div className="flex flex-wrap justify-end gap-2">
          <Button className="size-9 px-0" aria-label="View work object" icon={<Eye className="size-4" aria-hidden="true" />} onClick={() => openDetail(workObject)}>
            <span className="sr-only">View</span>
          </Button>
          <Button className="size-9 px-0" aria-label="Edit work object" icon={<Pencil className="size-4" aria-hidden="true" />} onClick={() => openEdit(workObject)}>
            <span className="sr-only">Edit</span>
          </Button>
          <Button
            className="size-9 px-0"
            aria-label="Complete work object"
            disabled={isMutating || workObject.status === "completed" || !workObject.is_active}
            icon={<CheckCircle2 className="size-4" aria-hidden="true" />}
            onClick={() => void onCompleteWorkObject(workObject.id)}
          >
            <span className="sr-only">Complete</span>
          </Button>
          <Button
            className="size-9 px-0"
            aria-label="Archive work object"
            disabled={isMutating || !workObject.is_active}
            icon={<Archive className="size-4" aria-hidden="true" />}
            onClick={() => void onDeactivateWorkObject(workObject.id)}
          >
            <span className="sr-only">Archive</span>
          </Button>
        </div>
      ),
      className: "text-right",
    },
  ];

  function openCreate(): void {
    setEditingWorkObject(null);
    setForm(initialForm);
    setFormError(null);
    setIsFormOpen(true);
  }

  function openEdit(workObject: WorkObject): void {
    setEditingWorkObject(workObject);
    setForm(workObjectToForm(workObject));
    setFormError(null);
    setIsFormOpen(true);
  }

  function openDetail(workObject: WorkObject): void {
    setDetailWorkObject(workObject);
    setDetailEvents([]);
    setDetailError(null);
    void loadWorkObjectDetail(workObject.id);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    setFormError(null);
    if (!selectedCompany) {
      setFormError("Create or select a company first.");
      return;
    }

    const payload = {
      title: form.title.trim(),
      description: form.description.trim() || null,
      object_type: form.object_type,
      status: form.status,
      priority: form.priority,
      project_id: form.project_id || null,
      department_id: form.department_id || null,
      team_id: form.team_id || null,
      creator_employee_id: form.creator_employee_id || null,
      assignee_employee_id: form.assignee_employee_id || null,
      start_date: dateToIso(form.start_date),
      due_date: dateToIso(form.due_date, true),
      tags: form.tags.split(",").map((tag) => tag.trim()).filter(Boolean),
      metadata: form.metadata_notes.trim() ? { notes: form.metadata_notes.trim() } : {},
      custom_fields: {},
      is_active: true,
    };

    try {
      if (editingWorkObject) {
        await onUpdateWorkObject(editingWorkObject.id, payload);
      } else {
        await onCreateWorkObject(payload);
      }
      setIsFormOpen(false);
    } catch {
      setFormError("Work object could not be saved. Check the details and try again.");
    }
  }

  return (
    <>
      <SectionPanel
        eyebrow={selectedCompany?.name ?? "Core work engine"}
        title="Work Objects"
        action={<Button disabled={!selectedCompany} variant="primary" icon={<Plus className="size-4" aria-hidden="true" />} onClick={openCreate}>New object</Button>}
      >
        <ModuleBoundary
          emptyDescription={selectedCompany ? "Create the first work object to start building the operational timeline." : "Create or select a company before adding work."}
          emptyTitle="No work objects yet"
          error={moduleError}
          isEmpty={data.workObjects.length === 0}
          isLoading={isLoadingModules}
          onRetry={onRetry}
          emptyAction={selectedCompany ? <Button variant="primary" icon={<Plus className="size-4" aria-hidden="true" />} onClick={openCreate}>New object</Button> : undefined}
        >
          <DataTable columns={columns} rows={data.workObjects} getRowKey={(workObject) => workObject.id} />
        </ModuleBoundary>
      </SectionPanel>

      <Modal description="Create or update a tenant-scoped work object." isOpen={isFormOpen} title={editingWorkObject ? "Edit work object" : "New work object"} onClose={() => setIsFormOpen(false)}>
        <form className="space-y-4 p-5" onSubmit={handleSubmit}>
          <div className="grid gap-4 sm:grid-cols-2">
            <FieldShell label="Title">
              <TextInput required value={form.title} onChange={(event) => setForm((current) => ({ ...current, title: event.target.value }))} />
            </FieldShell>
            <FieldShell label="Object type">
              <SelectInput required value={form.object_type} onChange={(event) => setForm((current) => ({ ...current, object_type: event.target.value }))}>
                {objectTypeOptions.map((objectType) => (
                  <option key={objectType} value={objectType}>
                    {formatLabel(objectType)}
                  </option>
                ))}
              </SelectInput>
            </FieldShell>
            <FieldShell label="Project">
              <SelectInput value={form.project_id} onChange={(event) => setForm((current) => ({ ...current, project_id: event.target.value }))}>
                <option value="">No project</option>
                {data.projects.map((project) => (
                  <option key={project.id} value={project.id}>
                    {project.name}
                  </option>
                ))}
              </SelectInput>
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
            <FieldShell label="Assignee">
              <SelectInput value={form.assignee_employee_id} onChange={(event) => setForm((current) => ({ ...current, assignee_employee_id: event.target.value }))}>
                <option value="">Unassigned</option>
                {data.employees.map((employee) => (
                  <option key={employee.id} value={employee.id}>
                    {employee.full_name}
                  </option>
                ))}
              </SelectInput>
            </FieldShell>
            <FieldShell label="Creator">
              <SelectInput value={form.creator_employee_id} onChange={(event) => setForm((current) => ({ ...current, creator_employee_id: event.target.value }))}>
                <option value="">Current user</option>
                {data.employees.map((employee) => (
                  <option key={employee.id} value={employee.id}>
                    {employee.full_name}
                  </option>
                ))}
              </SelectInput>
            </FieldShell>
            <FieldShell label="Status">
              <SelectInput required value={form.status} onChange={(event) => setForm((current) => ({ ...current, status: event.target.value }))}>
                {statusOptions.map((status) => (
                  <option key={status} value={status}>
                    {formatLabel(status)}
                  </option>
                ))}
              </SelectInput>
            </FieldShell>
            <FieldShell label="Priority">
              <SelectInput required value={form.priority} onChange={(event) => setForm((current) => ({ ...current, priority: event.target.value }))}>
                {priorityOptions.map((priority) => (
                  <option key={priority} value={priority}>
                    {formatLabel(priority)}
                  </option>
                ))}
              </SelectInput>
            </FieldShell>
            <FieldShell label="Start date">
              <TextInput type="date" value={form.start_date} onChange={(event) => setForm((current) => ({ ...current, start_date: event.target.value }))} />
            </FieldShell>
            <FieldShell label="Due date">
              <TextInput type="date" value={form.due_date} onChange={(event) => setForm((current) => ({ ...current, due_date: event.target.value }))} />
            </FieldShell>
            <FieldShell label="Tags">
              <TextInput placeholder="site, urgent, finance" value={form.tags} onChange={(event) => setForm((current) => ({ ...current, tags: event.target.value }))} />
            </FieldShell>
          </div>
          <FieldShell label="Description">
            <TextArea value={form.description} onChange={(event) => setForm((current) => ({ ...current, description: event.target.value }))} />
          </FieldShell>
          <FieldShell label="Notes">
            <TextArea value={form.metadata_notes} onChange={(event) => setForm((current) => ({ ...current, metadata_notes: event.target.value }))} />
          </FieldShell>
          {formError ? <p className="text-sm font-semibold text-rose-700">{formError}</p> : null}
          <div className="flex justify-end gap-2 border-t border-grid-200 pt-4">
            <Button onClick={() => setIsFormOpen(false)}>Cancel</Button>
            <Button disabled={isMutating} type="submit" variant="primary">
              {isMutating ? "Saving..." : editingWorkObject ? "Save changes" : "Create work object"}
            </Button>
          </div>
        </form>
      </Modal>

      <Modal description="Work object context, status, ownership, and event history." isOpen={Boolean(detailWorkObject)} title={detailWorkObject?.title ?? "Work object"} onClose={() => setDetailWorkObject(null)}>
        {detailWorkObject ? (
          <div className="space-y-5 p-5">
            <div className="grid gap-4 sm:grid-cols-2">
              <DetailItem label="Type" value={formatLabel(detailWorkObject.object_type)} />
              <DetailItem label="Status" value={formatLabel(detailWorkObject.status)} badgeTone={statusTone(detailWorkObject.status)} />
              <DetailItem label="Priority" value={formatLabel(detailWorkObject.priority)} badgeTone={priorityTone(detailWorkObject.priority)} />
              <DetailItem label="Assignee" value={detailWorkObject.assignee_employee_id ? employeeNames[detailWorkObject.assignee_employee_id] ?? "Assigned" : "Unassigned"} />
              <DetailItem label="Creator" value={detailWorkObject.creator_employee_id ? employeeNames[detailWorkObject.creator_employee_id] ?? "Recorded" : "Current user"} />
              <DetailItem label="Project" value={detailWorkObject.project_id ? projectNames[detailWorkObject.project_id] ?? "Linked" : "None"} />
              <DetailItem label="Department" value={detailWorkObject.department_id ? departmentNames[detailWorkObject.department_id] ?? "Assigned" : "Not assigned"} />
              <DetailItem label="Team" value={detailWorkObject.team_id ? teamNames[detailWorkObject.team_id] ?? "Assigned" : "Not assigned"} />
              <DetailItem label="Dates" value={compactList([formatDate(detailWorkObject.start_date), `Due ${formatDate(detailWorkObject.due_date)}`, detailWorkObject.completed_at ? `Done ${formatDate(detailWorkObject.completed_at)}` : null])} />
              <DetailItem label="Tags" value={detailWorkObject.tags.length > 0 ? detailWorkObject.tags.join(", ") : "None"} />
            </div>

            {detailWorkObject.description ? <p className="rounded-lg border border-grid-200 bg-grid-50 p-4 text-sm font-medium text-ink-600">{detailWorkObject.description}</p> : null}
            {typeof detailWorkObject.metadata.notes === "string" ? <p className="rounded-lg border border-grid-200 bg-grid-50 p-4 text-sm font-medium text-ink-600">{detailWorkObject.metadata.notes}</p> : null}

            <div className="flex flex-wrap gap-2">
              <Button icon={<Pencil className="size-4" aria-hidden="true" />} onClick={() => openEdit(detailWorkObject)}>Edit</Button>
              <Button disabled={isMutating || detailWorkObject.status === "completed"} variant="primary" icon={<CheckCircle2 className="size-4" aria-hidden="true" />} onClick={() => void onCompleteWorkObject(detailWorkObject.id)}>Complete</Button>
              <Button disabled={isMutating || !detailWorkObject.is_active} icon={<Archive className="size-4" aria-hidden="true" />} onClick={() => void onDeactivateWorkObject(detailWorkObject.id)}>Archive</Button>
            </div>

            {isDetailLoading ? <LoadingState label="Loading work object timeline" /> : null}
            {detailError ? <ErrorState message={detailError} onRetry={() => loadWorkObjectDetail(detailWorkObject.id)} /> : null}
            {!isDetailLoading && !detailError ? (
              <section className="rounded-lg border border-grid-200">
                <div className="border-b border-grid-200 px-4 py-3">
                  <h3 className="text-sm font-bold text-ink-950">Timeline</h3>
                </div>
                {detailEvents.length === 0 ? (
                  <EmptyState description="Work events will appear here after actions are recorded." title="No work events yet" />
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
