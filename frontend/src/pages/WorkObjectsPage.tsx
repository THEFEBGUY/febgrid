import { Plus } from "lucide-react";
import { type FormEvent, useMemo, useState } from "react";

import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { DataTable, type DataTableColumn } from "../components/ui/DataTable";
import { FieldShell, SelectInput, TextArea, TextInput } from "../components/ui/FormControls";
import { Modal } from "../components/ui/Modal";
import { ModuleBoundary } from "../components/ui/ModuleBoundary";
import { SectionPanel } from "../components/ui/SectionPanel";
import { priorityTone, statusTone } from "../components/ui/tone";
import type { WorkObject, WorkObjectCreatePayload } from "../types/api";
import type { ModulePageProps } from "../types/page";
import { formatDate, formatLabel } from "../utils/format";

interface WorkObjectsPageProps extends ModulePageProps {
  onCreateWorkObject: (payload: Omit<WorkObjectCreatePayload, "company_id">) => Promise<void>;
}

const initialForm = {
  title: "",
  description: "",
  object_type: "task",
  status: "assigned",
  priority: "medium",
  project_id: "",
  created_by_employee_id: "",
  assigned_to_employee_id: "",
  due_date: "",
  tags: "",
};

export function WorkObjectsPage({
  data,
  selectedCompany,
  isLoadingModules,
  moduleError,
  onRetry,
  onCreateWorkObject,
  isMutating,
}: WorkObjectsPageProps): JSX.Element {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [form, setForm] = useState(initialForm);
  const [formError, setFormError] = useState<string | null>(null);

  const employeeNames = useMemo(
    () => Object.fromEntries(data.employees.map((employee) => [employee.id, employee.full_name])),
    [data.employees],
  );
  const projectNames = useMemo(() => Object.fromEntries(data.projects.map((project) => [project.id, project.name])), [data.projects]);

  const columns: DataTableColumn<WorkObject>[] = [
    { key: "title", label: "Work object", render: (workObject) => <span className="font-bold text-ink-950">{workObject.title}</span> },
    { key: "type", label: "Type", render: (workObject) => formatLabel(workObject.object_type) },
    { key: "assignee", label: "Assignee", render: (workObject) => workObject.assigned_to_employee_id ? employeeNames[workObject.assigned_to_employee_id] ?? "Assigned" : "Unassigned" },
    { key: "status", label: "Status", render: (workObject) => <Badge label={formatLabel(workObject.status)} tone={statusTone(workObject.status)} /> },
    { key: "priority", label: "Priority", render: (workObject) => <Badge label={formatLabel(workObject.priority)} tone={priorityTone(workObject.priority)} /> },
    { key: "project", label: "Project", render: (workObject) => workObject.project_id ? projectNames[workObject.project_id] ?? "Linked" : "None" },
    { key: "due", label: "Due", render: (workObject) => formatDate(workObject.due_date) },
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
      await onCreateWorkObject({
        title: form.title.trim(),
        description: form.description.trim() || null,
        object_type: form.object_type,
        status: form.status,
        priority: form.priority,
        project_id: form.project_id || null,
        created_by_employee_id: form.created_by_employee_id || null,
        assigned_to_employee_id: form.assigned_to_employee_id || null,
        due_date: form.due_date ? new Date(`${form.due_date}T23:59:00`).toISOString() : null,
        tags: form.tags.split(",").map((tag) => tag.trim()).filter(Boolean),
        custom_fields: {},
        ai_summary: null,
      });
      setIsModalOpen(false);
    } catch {
      setFormError("Work object could not be created. Check the details and try again.");
    }
  }

  return (
    <>
      <SectionPanel
        eyebrow={selectedCompany?.name ?? "Core work engine"}
        title="Work Objects"
        action={<Button disabled={!selectedCompany} variant="primary" icon={<Plus className="size-4" aria-hidden="true" />} onClick={openModal}>New object</Button>}
      >
        <ModuleBoundary
          emptyDescription={selectedCompany ? "Create the first work object to start building the operational timeline." : "Create or select a company before adding work."}
          emptyTitle="No work objects yet"
          error={moduleError}
          isEmpty={data.workObjects.length === 0}
          isLoading={isLoadingModules}
          onRetry={onRetry}
          emptyAction={selectedCompany ? <Button variant="primary" icon={<Plus className="size-4" aria-hidden="true" />} onClick={openModal}>New object</Button> : undefined}
        >
          <DataTable columns={columns} rows={data.workObjects} getRowKey={(workObject) => workObject.id} />
        </ModuleBoundary>
      </SectionPanel>

      <Modal description="Create a real backend work object. The event engine records this action." isOpen={isModalOpen} title="New work object" onClose={() => setIsModalOpen(false)}>
        <form className="space-y-4 p-5" onSubmit={handleSubmit}>
          <div className="grid gap-4 sm:grid-cols-2">
            <FieldShell label="Title">
              <TextInput required value={form.title} onChange={(event) => setForm((current) => ({ ...current, title: event.target.value }))} />
            </FieldShell>
            <FieldShell label="Object type">
              <TextInput required value={form.object_type} onChange={(event) => setForm((current) => ({ ...current, object_type: event.target.value }))} />
            </FieldShell>
            <FieldShell label="Status">
              <SelectInput value={form.status} onChange={(event) => setForm((current) => ({ ...current, status: event.target.value }))}>
                <option value="draft">Draft</option>
                <option value="assigned">Assigned</option>
                <option value="in_progress">In Progress</option>
                <option value="blocked">Blocked</option>
                <option value="under_review">Under Review</option>
                <option value="completed">Completed</option>
              </SelectInput>
            </FieldShell>
            <FieldShell label="Priority">
              <SelectInput value={form.priority} onChange={(event) => setForm((current) => ({ ...current, priority: event.target.value }))}>
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
                <option value="critical">Critical</option>
              </SelectInput>
            </FieldShell>
            <FieldShell label="Project">
              <SelectInput value={form.project_id} onChange={(event) => setForm((current) => ({ ...current, project_id: event.target.value }))}>
                <option value="">No project</option>
                {data.projects.map((project) => (
                  <option key={project.id} value={project.id}>{project.name}</option>
                ))}
              </SelectInput>
            </FieldShell>
            <FieldShell label="Assignee">
              <SelectInput value={form.assigned_to_employee_id} onChange={(event) => setForm((current) => ({ ...current, assigned_to_employee_id: event.target.value }))}>
                <option value="">Unassigned</option>
                {data.employees.map((employee) => (
                  <option key={employee.id} value={employee.id}>{employee.full_name}</option>
                ))}
              </SelectInput>
            </FieldShell>
            <FieldShell label="Creator">
              <SelectInput value={form.created_by_employee_id} onChange={(event) => setForm((current) => ({ ...current, created_by_employee_id: event.target.value }))}>
                <option value="">System / unknown</option>
                {data.employees.map((employee) => (
                  <option key={employee.id} value={employee.id}>{employee.full_name}</option>
                ))}
              </SelectInput>
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
          {formError ? <p className="text-sm font-semibold text-rose-700">{formError}</p> : null}
          <div className="flex justify-end gap-2 border-t border-grid-200 pt-4">
            <Button onClick={() => setIsModalOpen(false)}>Cancel</Button>
            <Button disabled={isMutating} type="submit" variant="primary">
              {isMutating ? "Creating..." : "Create work object"}
            </Button>
          </div>
        </form>
      </Modal>
    </>
  );
}
