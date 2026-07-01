import { Archive, Eye, Pencil, Plus, UserPlus } from "lucide-react";
import { type FormEvent, useCallback, useMemo, useState } from "react";

import { AISummaryPanel } from "../components/ai/AISummaryPanel";
import { CommentsSection } from "../components/communication/CommentsSection";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { DataTable, type DataTableColumn } from "../components/ui/DataTable";
import { FilterBar, FilterField } from "../components/ui/FilterBar";
import { FieldShell, SelectInput, TextArea, TextInput } from "../components/ui/FormControls";
import { Modal } from "../components/ui/Modal";
import { ModuleBoundary } from "../components/ui/ModuleBoundary";
import { ProgressBar } from "../components/ui/ProgressBar";
import { SectionPanel } from "../components/ui/SectionPanel";
import { EmptyState, ErrorState, LoadingState } from "../components/ui/States";
import { priorityTone, statusTone } from "../components/ui/tone";
import { api } from "../services/api";
import type {
  AIJob,
  Event as FebGridEvent,
  Project,
  ProjectCreatePayload,
  ProjectMember,
  ProjectMemberCreatePayload,
  ProjectUpdatePayload,
  WorkObject,
} from "../types/api";
import type { ModulePageProps } from "../types/page";
import { compactList, formatDate, formatLabel, formatTime } from "../utils/format";

interface ProjectsPageProps extends ModulePageProps {
  onCreateProject: (payload: Omit<ProjectCreatePayload, "company_id">) => Promise<void>;
  onUpdateProject: (projectId: string, payload: ProjectUpdatePayload) => Promise<void>;
  onDeactivateProject: (projectId: string) => Promise<void>;
  onUpdateProjectStatus: (projectId: string, status: string) => Promise<void>;
  onUpdateProjectPriority: (projectId: string, priority: string) => Promise<void>;
  onAddProjectMember: (projectId: string, payload: Omit<ProjectMemberCreatePayload, "company_id">) => Promise<void>;
  onRemoveProjectMember: (projectId: string, employeeId: string) => Promise<void>;
}

const statusOptions = ["not_started", "active", "on_hold", "completed", "cancelled", "delayed"];
const priorityOptions = ["low", "medium", "high", "critical"];
const riskOptions = ["", "low", "medium", "high", "critical"];

const initialProjectForm = {
  name: "",
  code: "",
  description: "",
  owner_employee_id: "",
  department_id: "",
  team_id: "",
  status: "not_started",
  priority: "medium",
  start_date: "",
  due_date: "",
  progress_percent: "0",
  risk_level: "",
  tags: "",
};

const initialMemberForm = {
  employee_id: "",
  role_on_project: "",
};

type ProjectForm = typeof initialProjectForm;
type BadgeTone = "blue" | "green" | "amber" | "red" | "teal" | "slate";

function projectToForm(project: Project): ProjectForm {
  return {
    name: project.name,
    code: project.code ?? "",
    description: project.description ?? "",
    owner_employee_id: project.owner_employee_id ?? "",
    department_id: project.department_id ?? "",
    team_id: project.team_id ?? "",
    status: project.status,
    priority: project.priority,
    start_date: project.start_date ?? "",
    due_date: project.due_date ?? "",
    progress_percent: project.progress_percent.toString(),
    risk_level: project.risk_level ?? "",
    tags: project.tags.join(", "),
  };
}

function dateOrNull(value: string): string | null {
  return value || null;
}

function parseProgress(value: string): number | null {
  const parsed = Number(value);
  if (!Number.isFinite(parsed) || parsed < 0 || parsed > 100) return null;
  return parsed;
}

export function ProjectsPage({
  data,
  selectedCompany,
  isLoadingModules,
  isMutating,
  moduleError,
  onRetry,
  onCreateProject,
  onUpdateProject,
  onDeactivateProject,
  onUpdateProjectStatus,
  onUpdateProjectPriority,
  onAddProjectMember,
  onRemoveProjectMember,
}: ProjectsPageProps): JSX.Element {
  const selectedCompanyId = selectedCompany?.id ?? null;
  const [form, setForm] = useState<ProjectForm>(initialProjectForm);
  const [formError, setFormError] = useState<string | null>(null);
  const [editingProject, setEditingProject] = useState<Project | null>(null);
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [detailProject, setDetailProject] = useState<Project | null>(null);
  const [detailMembers, setDetailMembers] = useState<ProjectMember[]>([]);
  const [detailEvents, setDetailEvents] = useState<FebGridEvent[]>([]);
  const [detailWorkObjects, setDetailWorkObjects] = useState<WorkObject[]>([]);
  const [isDetailLoading, setIsDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [aiSummary, setAISummary] = useState<AIJob | null>(null);
  const [isAISummaryLoading, setIsAISummaryLoading] = useState(false);
  const [isAISummaryGenerating, setIsAISummaryGenerating] = useState(false);
  const [aiSummaryError, setAISummaryError] = useState<string | null>(null);
  const [memberForm, setMemberForm] = useState(initialMemberForm);
  const [memberError, setMemberError] = useState<string | null>(null);
  const [searchFilter, setSearchFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [priorityFilter, setPriorityFilter] = useState("");
  const [ownerFilter, setOwnerFilter] = useState("");

  const employeeNames = useMemo(() => Object.fromEntries(data.employees.map((employee) => [employee.id, employee.full_name])), [data.employees]);
  const departmentNames = useMemo(
    () => Object.fromEntries(data.departments.map((department) => [department.id, department.name])),
    [data.departments],
  );
  const teamNames = useMemo(() => Object.fromEntries(data.teams.map((team) => [team.id, team.name])), [data.teams]);
  const activeMemberEmployeeIds = useMemo(() => new Set(detailMembers.filter((member) => member.is_active).map((member) => member.employee_id)), [detailMembers]);
  const filteredProjects = useMemo(() => {
    const query = searchFilter.trim().toLowerCase();
    return data.projects.filter((project) => {
      const searchable = [
        project.name,
        project.code,
        project.description,
        project.risk_level,
        project.tags.join(" "),
        project.owner_employee_id ? employeeNames[project.owner_employee_id] : null,
        project.department_id ? departmentNames[project.department_id] : null,
        project.team_id ? teamNames[project.team_id] : null,
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();
      if (query && !searchable.includes(query)) return false;
      if (statusFilter && project.status !== statusFilter) return false;
      if (priorityFilter && project.priority !== priorityFilter) return false;
      if (ownerFilter && project.owner_employee_id !== ownerFilter) return false;
      return true;
    });
  }, [data.projects, departmentNames, employeeNames, ownerFilter, priorityFilter, searchFilter, statusFilter, teamNames]);
  const hasActiveFilters = Boolean(searchFilter || statusFilter || priorityFilter || ownerFilter);

  const loadProjectDetail = useCallback(
    async (projectId: string): Promise<void> => {
      if (!selectedCompanyId) return;
      setIsDetailLoading(true);
      setIsAISummaryLoading(true);
      setDetailError(null);
      setAISummaryError(null);
      try {
        const [membersResult, eventsResult, workObjectsResult, summaryResult] = await Promise.allSettled([
          api.projectMembers(projectId, selectedCompanyId),
          api.projectTimeline(projectId, selectedCompanyId),
          api.projectWorkObjects(projectId, selectedCompanyId),
          api.latestProjectAISummary(projectId, selectedCompanyId),
        ]);
        if (membersResult.status === "fulfilled") setDetailMembers(membersResult.value);
        else setDetailError("Unable to load project members.");
        if (eventsResult.status === "fulfilled") setDetailEvents(eventsResult.value);
        else setDetailError("Unable to load project timeline.");
        if (workObjectsResult.status === "fulfilled") setDetailWorkObjects(workObjectsResult.value);
        else setDetailError("Unable to load linked work objects.");
        if (summaryResult.status === "fulfilled") setAISummary(summaryResult.value);
        else setAISummaryError("Unable to load the latest AI project summary.");
      } finally {
        setIsDetailLoading(false);
        setIsAISummaryLoading(false);
      }
    },
    [selectedCompanyId],
  );

  const columns: DataTableColumn<Project>[] = [
    {
      key: "name",
      label: "Project",
      render: (project) => (
        <span className="min-w-56">
          <span className="block truncate font-bold text-ink-950">{project.name}</span>
          <span className="block truncate text-xs text-ink-500">{project.code ?? "No code"}</span>
        </span>
      ),
    },
    { key: "owner", label: "Owner", render: (project) => project.owner_employee_id ? employeeNames[project.owner_employee_id] ?? "Assigned" : "No owner" },
    {
      key: "org",
      label: "Department / Team",
      render: (project) => compactList([project.department_id ? departmentNames[project.department_id] : null, project.team_id ? teamNames[project.team_id] : null]) || "Not assigned",
    },
    {
      key: "status",
      label: "Status",
      render: (project) => (
        <SelectInput
          aria-label={`Update ${project.name} status`}
          disabled={isMutating || !project.is_active}
          value={project.status}
          onChange={(event) => void onUpdateProjectStatus(project.id, event.target.value)}
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
      render: (project) => (
        <SelectInput
          aria-label={`Update ${project.name} priority`}
          disabled={isMutating || !project.is_active}
          value={project.priority}
          onChange={(event) => void onUpdateProjectPriority(project.id, event.target.value)}
        >
          {priorityOptions.map((priority) => (
            <option key={priority} value={priority}>
              {formatLabel(priority)}
            </option>
          ))}
        </SelectInput>
      ),
    },
    { key: "progress", label: "Progress", render: (project) => <ProgressBar value={project.progress_percent} /> },
    { key: "due", label: "Due", render: (project) => formatDate(project.due_date) },
    { key: "risk", label: "Risk", render: (project) => project.risk_level ? <Badge label={formatLabel(project.risk_level)} tone={priorityTone(project.risk_level)} /> : "None" },
    {
      key: "actions",
      label: "Actions",
      render: (project) => (
        <div className="flex flex-wrap justify-end gap-2">
          <Button className="size-9 px-0" aria-label="View project" icon={<Eye className="size-4" aria-hidden="true" />} onClick={() => openDetail(project)}>
            <span className="sr-only">View</span>
          </Button>
          <Button className="size-9 px-0" aria-label="Edit project" icon={<Pencil className="size-4" aria-hidden="true" />} onClick={() => openEdit(project)}>
            <span className="sr-only">Edit</span>
          </Button>
          <Button
            className="size-9 px-0"
            aria-label="Archive project"
            disabled={isMutating || !project.is_active}
            icon={<Archive className="size-4" aria-hidden="true" />}
            onClick={() => void onDeactivateProject(project.id)}
          >
            <span className="sr-only">Archive</span>
          </Button>
        </div>
      ),
      className: "text-right",
    },
  ];

  function openCreate(): void {
    setEditingProject(null);
    setForm(initialProjectForm);
    setFormError(null);
    setIsFormOpen(true);
  }

  function openEdit(project: Project): void {
    setEditingProject(project);
    setForm(projectToForm(project));
    setFormError(null);
    setIsFormOpen(true);
  }

  function openDetail(project: Project): void {
    setDetailProject(project);
    setDetailMembers([]);
    setDetailEvents([]);
    setDetailWorkObjects([]);
    setAISummary(null);
    setAISummaryError(null);
    setMemberForm(initialMemberForm);
    setMemberError(null);
    void loadProjectDetail(project.id);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    setFormError(null);
    if (!selectedCompany) {
      setFormError("Create or select a company first.");
      return;
    }

    const progress = parseProgress(form.progress_percent);
    if (progress === null) {
      setFormError("Progress must be between 0 and 100.");
      return;
    }

    const payload = {
      owner_employee_id: form.owner_employee_id || null,
      owner_user_id: null,
      department_id: form.department_id || null,
      team_id: form.team_id || null,
      name: form.name.trim(),
      code: form.code.trim() || null,
      description: form.description.trim() || null,
      status: form.status,
      priority: form.priority,
      start_date: dateOrNull(form.start_date),
      due_date: dateOrNull(form.due_date),
      progress_percent: progress,
      risk_level: form.risk_level || null,
      is_active: true,
      tags: form.tags.split(",").map((tag) => tag.trim()).filter(Boolean),
    };

    try {
      if (editingProject) {
        await onUpdateProject(editingProject.id, payload);
      } else {
        await onCreateProject(payload);
      }
      setIsFormOpen(false);
    } catch {
      setFormError("Project could not be saved. Check the details and try again.");
    }
  }

  async function handleAddMember(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    setMemberError(null);
    if (!detailProject || !memberForm.employee_id) {
      setMemberError("Select an employee.");
      return;
    }

    try {
      await onAddProjectMember(detailProject.id, {
        employee_id: memberForm.employee_id,
        role_on_project: memberForm.role_on_project.trim() || null,
      });
      setMemberForm(initialMemberForm);
      await loadProjectDetail(detailProject.id);
    } catch {
      setMemberError("Member could not be added.");
    }
  }

  async function handleRemoveMember(employeeId: string): Promise<void> {
    if (!detailProject) return;
    try {
      await onRemoveProjectMember(detailProject.id, employeeId);
      await loadProjectDetail(detailProject.id);
    } catch {
      setMemberError("Member could not be removed.");
    }
  }

  async function handleGenerateAISummary(): Promise<void> {
    if (!detailProject || !selectedCompanyId) return;
    setIsAISummaryGenerating(true);
    setAISummaryError(null);
    try {
      const job = await api.generateProjectAISummary(detailProject.id, selectedCompanyId);
      setAISummary(job);
      void loadProjectDetail(detailProject.id);
    } catch (caughtError) {
      setAISummaryError(caughtError instanceof Error ? caughtError.message : "AI project summary could not be generated.");
    } finally {
      setIsAISummaryGenerating(false);
    }
  }

  return (
    <>
      <SectionPanel
        eyebrow={selectedCompany?.name ?? "Delivery tracking"}
        title="Projects"
        action={<Button disabled={!selectedCompany} variant="primary" icon={<Plus className="size-4" aria-hidden="true" />} onClick={openCreate}>New project</Button>}
      >
        <ModuleBoundary
          emptyDescription={selectedCompany ? "Create a project to organize ownership, members, progress, and linked work." : "Create or select a company before adding projects."}
          emptyTitle="No projects yet"
          error={moduleError}
          isEmpty={data.projects.length === 0}
          isLoading={isLoadingModules}
          onRetry={onRetry}
          emptyAction={selectedCompany ? <Button variant="primary" icon={<Plus className="size-4" aria-hidden="true" />} onClick={openCreate}>New project</Button> : undefined}
        >
          <FilterBar
            isResetDisabled={!hasActiveFilters}
            onReset={() => {
              setSearchFilter("");
              setStatusFilter("");
              setPriorityFilter("");
              setOwnerFilter("");
            }}
          >
            <FilterField label="Search">
              <TextInput placeholder="Name, code, risk" value={searchFilter} onChange={(event) => setSearchFilter(event.target.value)} />
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
            <FilterField label="Priority">
              <SelectInput value={priorityFilter} onChange={(event) => setPriorityFilter(event.target.value)}>
                <option value="">All priorities</option>
                {priorityOptions.map((priority) => (
                  <option key={priority} value={priority}>
                    {formatLabel(priority)}
                  </option>
                ))}
              </SelectInput>
            </FilterField>
            <FilterField label="Owner">
              <SelectInput value={ownerFilter} onChange={(event) => setOwnerFilter(event.target.value)}>
                <option value="">All owners</option>
                {data.employees.map((employee) => (
                  <option key={employee.id} value={employee.id}>
                    {employee.full_name}
                  </option>
                ))}
              </SelectInput>
            </FilterField>
          </FilterBar>
          {filteredProjects.length === 0 ? (
            <div className="px-5 py-10 text-center">
              <p className="text-sm font-bold text-ink-950">No projects match these filters</p>
              <p className="mt-1 text-sm font-medium text-ink-500">Reset filters to return to all projects.</p>
            </div>
          ) : (
            <DataTable columns={columns} rows={filteredProjects} getRowKey={(project) => project.id} />
          )}
        </ModuleBoundary>
      </SectionPanel>

      <Modal description="Create the project foundation for work ownership and timeline tracking." isOpen={isFormOpen} title={editingProject ? "Edit project" : "New project"} onClose={() => setIsFormOpen(false)}>
        <form className="space-y-4 p-5" onSubmit={handleSubmit}>
          <div className="grid gap-4 sm:grid-cols-2">
            <FieldShell label="Project name">
              <TextInput required value={form.name} onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))} />
            </FieldShell>
            <FieldShell label="Code">
              <TextInput value={form.code} onChange={(event) => setForm((current) => ({ ...current, code: event.target.value }))} />
            </FieldShell>
            <FieldShell label="Owner employee">
              <SelectInput value={form.owner_employee_id} onChange={(event) => setForm((current) => ({ ...current, owner_employee_id: event.target.value }))}>
                <option value="">No owner</option>
                {data.employees.map((employee) => (
                  <option key={employee.id} value={employee.id}>
                    {employee.full_name}
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
            <FieldShell label="Status">
              <SelectInput value={form.status} onChange={(event) => setForm((current) => ({ ...current, status: event.target.value }))}>
                {statusOptions.map((status) => (
                  <option key={status} value={status}>
                    {formatLabel(status)}
                  </option>
                ))}
              </SelectInput>
            </FieldShell>
            <FieldShell label="Priority">
              <SelectInput value={form.priority} onChange={(event) => setForm((current) => ({ ...current, priority: event.target.value }))}>
                {priorityOptions.map((priority) => (
                  <option key={priority} value={priority}>
                    {formatLabel(priority)}
                  </option>
                ))}
              </SelectInput>
            </FieldShell>
            <FieldShell label="Risk level">
              <SelectInput value={form.risk_level} onChange={(event) => setForm((current) => ({ ...current, risk_level: event.target.value }))}>
                {riskOptions.map((risk) => (
                  <option key={risk || "none"} value={risk}>
                    {risk ? formatLabel(risk) : "None"}
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
            <FieldShell label="Progress">
              <TextInput min="0" max="100" type="number" value={form.progress_percent} onChange={(event) => setForm((current) => ({ ...current, progress_percent: event.target.value }))} />
            </FieldShell>
            <FieldShell label="Tags">
              <TextInput placeholder="Client, Internal" value={form.tags} onChange={(event) => setForm((current) => ({ ...current, tags: event.target.value }))} />
            </FieldShell>
          </div>
          <FieldShell label="Description">
            <TextArea value={form.description} onChange={(event) => setForm((current) => ({ ...current, description: event.target.value }))} />
          </FieldShell>
          {formError ? <p className="text-sm font-semibold text-rose-700">{formError}</p> : null}
          <div className="flex justify-end gap-2 border-t border-grid-200 pt-4">
            <Button onClick={() => setIsFormOpen(false)}>Cancel</Button>
            <Button disabled={isMutating} type="submit" variant="primary">
              {isMutating ? "Saving..." : editingProject ? "Save changes" : "Create project"}
            </Button>
          </div>
        </form>
      </Modal>

      <Modal description="Project ownership, members, events, and linked work." isOpen={Boolean(detailProject)} title={detailProject?.name ?? "Project detail"} onClose={() => setDetailProject(null)}>
        {detailProject ? (
          <div className="space-y-5 p-5">
            <div className="grid gap-4 sm:grid-cols-2">
              <DetailItem label="Owner" value={detailProject.owner_employee_id ? employeeNames[detailProject.owner_employee_id] ?? "Assigned" : "No owner"} />
              <DetailItem label="Status" value={formatLabel(detailProject.status)} badgeTone={statusTone(detailProject.status)} />
              <DetailItem label="Priority" value={formatLabel(detailProject.priority)} badgeTone={priorityTone(detailProject.priority)} />
              <DetailItem label="Risk" value={detailProject.risk_level ? formatLabel(detailProject.risk_level) : "None"} badgeTone={detailProject.risk_level ? priorityTone(detailProject.risk_level) : undefined} />
              <DetailItem label="Department" value={detailProject.department_id ? departmentNames[detailProject.department_id] ?? "Assigned" : "Not assigned"} />
              <DetailItem label="Team" value={detailProject.team_id ? teamNames[detailProject.team_id] ?? "Assigned" : "Not assigned"} />
              <DetailItem label="Dates" value={compactList([formatDate(detailProject.start_date), `Due ${formatDate(detailProject.due_date)}`])} />
              <DetailItem label="Progress" value={`${detailProject.progress_percent}%`} />
            </div>

            {detailProject.description ? <p className="rounded-lg border border-grid-200 bg-grid-50 p-4 text-sm font-medium text-ink-600">{detailProject.description}</p> : null}

            <AISummaryPanel
              error={aiSummaryError}
              generateLabel="Generate AI Project Summary"
              isGenerating={isAISummaryGenerating}
              isLoading={isAISummaryLoading}
              job={aiSummary}
              kind="project"
              onGenerate={() => void handleGenerateAISummary()}
            />

            {isDetailLoading ? <LoadingState label="Loading project detail" /> : null}
            {detailError ? <ErrorState message={detailError} onRetry={() => loadProjectDetail(detailProject.id)} /> : null}

            <section className="rounded-lg border border-grid-200">
              <div className="border-b border-grid-200 px-4 py-3">
                <h3 className="text-sm font-bold text-ink-950">Members</h3>
              </div>
              <div className="space-y-3 p-4">
                {detailMembers.length === 0 ? (
                  <EmptyState description="Add employees as project members." title="No members yet" />
                ) : (
                  <div className="divide-y divide-grid-100">
                    {detailMembers.map((member) => (
                      <div key={member.id} className="flex flex-col gap-2 py-3 sm:flex-row sm:items-center sm:justify-between">
                        <div className="min-w-0">
                          <p className="truncate text-sm font-bold text-ink-950">{employeeNames[member.employee_id] ?? "Employee"}</p>
                          <p className="truncate text-xs font-semibold text-ink-500">{member.role_on_project ?? "Member"}</p>
                        </div>
                        <Button disabled={isMutating} onClick={() => void handleRemoveMember(member.employee_id)}>Remove</Button>
                      </div>
                    ))}
                  </div>
                )}
                <form className="grid gap-3 border-t border-grid-200 pt-4 sm:grid-cols-[1fr_1fr_auto]" onSubmit={handleAddMember}>
                  <SelectInput value={memberForm.employee_id} onChange={(event) => setMemberForm((current) => ({ ...current, employee_id: event.target.value }))}>
                    <option value="">Select employee</option>
                    {data.employees.filter((employee) => !activeMemberEmployeeIds.has(employee.id)).map((employee) => (
                      <option key={employee.id} value={employee.id}>
                        {employee.full_name}
                      </option>
                    ))}
                  </SelectInput>
                  <TextInput placeholder="Role on project" value={memberForm.role_on_project} onChange={(event) => setMemberForm((current) => ({ ...current, role_on_project: event.target.value }))} />
                  <Button disabled={isMutating} type="submit" variant="primary" icon={<UserPlus className="size-4" aria-hidden="true" />}>Add</Button>
                </form>
                {memberError ? <p className="text-sm font-semibold text-rose-700">{memberError}</p> : null}
              </div>
            </section>

            <CommentsSection
              companyId={selectedCompanyId}
              employees={data.employees}
              employeeNames={employeeNames}
              targetEntityId={detailProject.id}
              targetEntityType="project"
              onChanged={() => void loadProjectDetail(detailProject.id)}
            />

            <section className="grid gap-4 lg:grid-cols-2">
              <div className="rounded-lg border border-grid-200">
                <div className="border-b border-grid-200 px-4 py-3">
                  <h3 className="text-sm font-bold text-ink-950">Recent events</h3>
                </div>
                {detailEvents.length === 0 ? (
                  <EmptyState description="Project events will appear here." title="No project events yet" />
                ) : (
                  <div className="divide-y divide-grid-100">
                    {detailEvents.slice(0, 6).map((event) => (
                      <article key={event.id} className="px-4 py-3">
                        <p className="truncate text-sm font-bold text-ink-950">{event.title}</p>
                        <p className="mt-1 text-xs font-semibold text-ink-500">{formatTime(event.created_at)} / {formatLabel(event.event_type)}</p>
                      </article>
                    ))}
                  </div>
                )}
              </div>

              <div className="rounded-lg border border-grid-200">
                <div className="border-b border-grid-200 px-4 py-3">
                  <h3 className="text-sm font-bold text-ink-950">Work objects</h3>
                </div>
                {detailWorkObjects.length === 0 ? (
                  <EmptyState description="Linked work objects will appear here after Sprint 4 work object flows expand." title="No linked work yet" />
                ) : (
                  <div className="divide-y divide-grid-100">
                    {detailWorkObjects.slice(0, 6).map((workObject) => (
                      <article key={workObject.id} className="px-4 py-3">
                        <p className="truncate text-sm font-bold text-ink-950">{workObject.title}</p>
                        <div className="mt-2 flex flex-wrap gap-2">
                          <Badge label={formatLabel(workObject.status)} tone={statusTone(workObject.status)} />
                          <Badge label={formatLabel(workObject.priority)} tone={priorityTone(workObject.priority)} />
                        </div>
                      </article>
                    ))}
                  </div>
                )}
              </div>
            </section>
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
