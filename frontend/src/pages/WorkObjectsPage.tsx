import { Archive, CheckCircle2, Download, Eye, FileText, Pencil, Plus, Sparkles, Trash2, Upload } from "lucide-react";
import { type FormEvent, useCallback, useMemo, useState } from "react";

import { CommentsSection } from "../components/communication/CommentsSection";
import { AISummaryPanel } from "../components/ai/AISummaryPanel";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { DataTable, type DataTableColumn } from "../components/ui/DataTable";
import { FilterBar, FilterField } from "../components/ui/FilterBar";
import { FieldShell, SelectInput, TextArea, TextInput } from "../components/ui/FormControls";
import { Modal } from "../components/ui/Modal";
import { ModuleBoundary } from "../components/ui/ModuleBoundary";
import { SectionPanel } from "../components/ui/SectionPanel";
import { EmptyState, ErrorState, LoadingState } from "../components/ui/States";
import { priorityTone, statusTone } from "../components/ui/tone";
import { api } from "../services/api";
import type { AIJob, Attachment, CustomFieldDefinition, Event as FebGridEvent, WorkObject, WorkObjectCreatePayload, WorkObjectUpdatePayload } from "../types/api";
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

const fallbackObjectTypeOptions = ["task", "approval_request", "issue", "site_visit", "invoice", "document_review", "general"];
const statusOptions = ["assigned", "in_progress", "under_review", "blocked", "completed", "cancelled"];
const priorityOptions = ["low", "medium", "high", "critical"];
const maxUploadBytes = 10 * 1024 * 1024;
const allowedAttachmentExtensions = [".png", ".jpg", ".jpeg", ".webp", ".pdf", ".csv", ".txt", ".md", ".json", ".log", ".doc", ".docx", ".xls", ".xlsx"];

interface WorkObjectForm {
  title: string;
  description: string;
  object_type: string;
  status: string;
  priority: string;
  project_id: string;
  department_id: string;
  team_id: string;
  creator_employee_id: string;
  assignee_employee_id: string;
  start_date: string;
  due_date: string;
  tags: string;
  metadata_notes: string;
  custom_fields: Record<string, string | boolean>;
}

const initialForm: WorkObjectForm = {
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
  custom_fields: {},
};

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
    custom_fields: Object.fromEntries(
      Object.entries(workObject.custom_fields ?? {}).map(([key, value]) => [
        key,
        Array.isArray(value) ? value.join(", ") : typeof value === "boolean" ? value : value == null ? "" : String(value),
      ]),
    ),
  };
}

function dateToIso(value: string, endOfDay = false): string | null {
  if (!value) return null;
  return `${value}T${endOfDay ? "23:59:00" : "00:00:00"}.000Z`;
}

function formatBytes(value: number | null): string {
  if (value === null) return "Unknown size";
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
  return `${(value / (1024 * 1024)).toFixed(1)} MB`;
}

function validateAttachmentFile(file: File): string | null {
  const lowerName = file.name.toLowerCase();
  if (!allowedAttachmentExtensions.some((extension) => lowerName.endsWith(extension))) {
    return "This file type is not allowed for File Upload v1.";
  }
  if (file.size > maxUploadBytes) {
    return "File must be 10 MB or smaller.";
  }
  return null;
}

function customFieldDefinitionsFor(fields: CustomFieldDefinition[], typeKey: string, includeInactive = false): CustomFieldDefinition[] {
  return fields
    .filter((field) => field.type_key === typeKey && (includeInactive || field.is_active))
    .sort((left, right) => left.sort_order - right.sort_order || left.label.localeCompare(right.label));
}

function serializeCustomFields(definitions: CustomFieldDefinition[], formValues: Record<string, string | boolean>): Record<string, unknown> {
  return Object.fromEntries(
    definitions.map((definition) => {
      const rawValue = formValues[definition.field_key];
      if (definition.field_type === "checkbox") {
        return [definition.field_key, Boolean(rawValue)];
      }
      if (typeof rawValue !== "string" || rawValue.trim() === "") {
        return [definition.field_key, null];
      }
      if (definition.field_type === "number") {
        const numeric = Number(rawValue);
        return [definition.field_key, Number.isFinite(numeric) ? numeric : rawValue];
      }
      if (definition.field_type === "multiselect") {
        return [definition.field_key, rawValue.split(",").map((item) => item.trim()).filter(Boolean)];
      }
      return [definition.field_key, rawValue];
    }),
  );
}

function formatCustomFieldValue(value: unknown): string {
  if (Array.isArray(value)) return value.join(", ") || "None";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (value === null || value === undefined || value === "") return "None";
  return String(value);
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
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const [isAttachmentLoading, setIsAttachmentLoading] = useState(false);
  const [attachmentError, setAttachmentError] = useState<string | null>(null);
  const [aiSummary, setAISummary] = useState<AIJob | null>(null);
  const [isAISummaryLoading, setIsAISummaryLoading] = useState(false);
  const [isAISummaryGenerating, setIsAISummaryGenerating] = useState(false);
  const [aiSummaryError, setAISummaryError] = useState<string | null>(null);
  const [fileSummaryAttachment, setFileSummaryAttachment] = useState<Attachment | null>(null);
  const [fileAISummary, setFileAISummary] = useState<AIJob | null>(null);
  const [isFileAISummaryLoading, setIsFileAISummaryLoading] = useState(false);
  const [isFileAISummaryGenerating, setIsFileAISummaryGenerating] = useState(false);
  const [fileAISummaryError, setFileAISummaryError] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadDescription, setUploadDescription] = useState("");
  const [isUploading, setIsUploading] = useState(false);
  const [editingAttachmentId, setEditingAttachmentId] = useState<string | null>(null);
  const [editingAttachmentDescription, setEditingAttachmentDescription] = useState("");
  const [searchFilter, setSearchFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [priorityFilter, setPriorityFilter] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const [assigneeFilter, setAssigneeFilter] = useState("");
  const [projectFilter, setProjectFilter] = useState("");

  const employeeNames = useMemo(() => Object.fromEntries(data.employees.map((employee) => [employee.id, employee.full_name])), [data.employees]);
  const projectNames = useMemo(() => Object.fromEntries(data.projects.map((project) => [project.id, project.name])), [data.projects]);
  const departmentNames = useMemo(
    () => Object.fromEntries(data.departments.map((department) => [department.id, department.name])),
    [data.departments],
  );
  const teamNames = useMemo(() => Object.fromEntries(data.teams.map((team) => [team.id, team.name])), [data.teams]);
  const activeWorkObjectTypes = useMemo(() => {
    const configured = data.workObjectTypes
      .filter((type) => type.is_active)
      .sort((left, right) => left.sort_order - right.sort_order || left.name.localeCompare(right.name));
    if (configured.length > 0) return configured;
    return fallbackObjectTypeOptions.map((key, index) => ({
      id: key,
      company_id: selectedCompany?.id ?? "",
      key,
      name: formatLabel(key),
      description: null,
      icon: null,
      color: null,
      is_default: key === "task",
      is_active: true,
      sort_order: index + 1,
      metadata: {},
      created_at: "",
      updated_at: "",
    }));
  }, [data.workObjectTypes, selectedCompany?.id]);
  const formCustomFields = useMemo(() => customFieldDefinitionsFor(data.customFields, form.object_type), [data.customFields, form.object_type]);
  const filteredWorkObjects = useMemo(() => {
    const query = searchFilter.trim().toLowerCase();
    return data.workObjects.filter((workObject) => {
      const searchable = [
        workObject.title,
        workObject.description,
        workObject.object_type,
        workObject.tags.join(" "),
        Object.values(workObject.custom_fields ?? {}).map(formatCustomFieldValue).join(" "),
        workObject.project_id ? projectNames[workObject.project_id] : null,
        workObject.assignee_employee_id ? employeeNames[workObject.assignee_employee_id] : null,
        workObject.department_id ? departmentNames[workObject.department_id] : null,
        workObject.team_id ? teamNames[workObject.team_id] : null,
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();
      if (query && !searchable.includes(query)) return false;
      if (statusFilter && workObject.status !== statusFilter) return false;
      if (priorityFilter && workObject.priority !== priorityFilter) return false;
      if (typeFilter && workObject.object_type !== typeFilter) return false;
      if (assigneeFilter && workObject.assignee_employee_id !== assigneeFilter) return false;
      if (projectFilter && workObject.project_id !== projectFilter) return false;
      return true;
    });
  }, [assigneeFilter, data.workObjects, departmentNames, employeeNames, priorityFilter, projectFilter, projectNames, searchFilter, statusFilter, teamNames, typeFilter]);
  const hasActiveFilters = Boolean(searchFilter || statusFilter || priorityFilter || typeFilter || assigneeFilter || projectFilter);

  const loadWorkObjectDetail = useCallback(
    async (workObjectId: string): Promise<void> => {
      if (!selectedCompanyId) return;
      setIsDetailLoading(true);
      setIsAttachmentLoading(true);
      setIsAISummaryLoading(true);
      setDetailError(null);
      setAttachmentError(null);
      setAISummaryError(null);
      try {
        const [eventsResult, attachmentsResult, summaryResult] = await Promise.allSettled([
          api.workObjectTimeline(workObjectId, selectedCompanyId),
          api.workObjectAttachments(workObjectId, selectedCompanyId),
          api.latestWorkObjectAISummary(workObjectId, selectedCompanyId),
        ]);
        if (eventsResult.status === "fulfilled") setDetailEvents(eventsResult.value);
        else setDetailError("Unable to load work object timeline.");
        if (attachmentsResult.status === "fulfilled") setAttachments(attachmentsResult.value);
        else setAttachmentError("Unable to load attachments.");
        if (summaryResult.status === "fulfilled") setAISummary(summaryResult.value);
        else setAISummaryError("Unable to load the latest AI summary.");
      } finally {
        setIsDetailLoading(false);
        setIsAttachmentLoading(false);
        setIsAISummaryLoading(false);
      }
    },
    [selectedCompanyId],
  );

  const loadAttachments = useCallback(
    async (workObjectId: string): Promise<void> => {
      if (!selectedCompanyId) return;
      setIsAttachmentLoading(true);
      setAttachmentError(null);
      try {
        const nextAttachments = await api.workObjectAttachments(workObjectId, selectedCompanyId);
        setAttachments(nextAttachments);
      } catch {
        setAttachmentError("Unable to load attachments.");
      } finally {
        setIsAttachmentLoading(false);
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
    setForm({ ...initialForm, object_type: activeWorkObjectTypes[0]?.key ?? "task" });
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
    setAttachments([]);
    setDetailError(null);
    setAttachmentError(null);
    setAISummary(null);
    setAISummaryError(null);
    setFileSummaryAttachment(null);
    setFileAISummary(null);
    setFileAISummaryError(null);
    setSelectedFile(null);
    setUploadDescription("");
    setEditingAttachmentId(null);
    setEditingAttachmentDescription("");
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
      custom_fields: editingWorkObject
        ? { ...editingWorkObject.custom_fields, ...serializeCustomFields(formCustomFields, form.custom_fields) }
        : serializeCustomFields(formCustomFields, form.custom_fields),
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

  async function handleGenerateAISummary(): Promise<void> {
    if (!detailWorkObject || !selectedCompanyId) return;
    setIsAISummaryGenerating(true);
    setAISummaryError(null);
    try {
      const job = await api.generateWorkObjectAISummary(detailWorkObject.id, selectedCompanyId);
      setAISummary(job);
      void loadWorkObjectDetail(detailWorkObject.id);
    } catch (caughtError) {
      setAISummaryError(caughtError instanceof Error ? caughtError.message : "AI summary could not be generated.");
    } finally {
      setIsAISummaryGenerating(false);
    }
  }

  async function loadFileAISummary(attachment: Attachment): Promise<void> {
    if (!selectedCompanyId) return;
    setFileSummaryAttachment(attachment);
    setIsFileAISummaryLoading(true);
    setFileAISummaryError(null);
    try {
      const job = await api.latestFileAISummary(attachment.id, selectedCompanyId);
      setFileAISummary(job);
    } catch (caughtError) {
      setFileAISummaryError(caughtError instanceof Error ? caughtError.message : "Unable to load the latest file summary.");
    } finally {
      setIsFileAISummaryLoading(false);
    }
  }

  async function handleGenerateFileAISummary(): Promise<void> {
    if (!fileSummaryAttachment || !selectedCompanyId) return;
    setIsFileAISummaryGenerating(true);
    setFileAISummaryError(null);
    try {
      const job = await api.generateFileAISummary(fileSummaryAttachment.id, selectedCompanyId);
      setFileAISummary(job);
      if (detailWorkObject) void loadWorkObjectDetail(detailWorkObject.id);
    } catch (caughtError) {
      setFileAISummaryError(caughtError instanceof Error ? caughtError.message : "AI file summary could not be generated.");
    } finally {
      setIsFileAISummaryGenerating(false);
    }
  }

  async function handleUploadAttachment(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    setAttachmentError(null);
    if (!detailWorkObject || !selectedCompanyId) return;
    if (!selectedFile) {
      setAttachmentError("Choose a file to upload.");
      return;
    }
    const validationError = validateAttachmentFile(selectedFile);
    if (validationError) {
      setAttachmentError(validationError);
      return;
    }

    setIsUploading(true);
    try {
      await api.uploadWorkObjectAttachment(detailWorkObject.id, selectedCompanyId, selectedFile, uploadDescription.trim() || null);
      setSelectedFile(null);
      setUploadDescription("");
      await loadWorkObjectDetail(detailWorkObject.id);
    } catch {
      setAttachmentError("File could not be uploaded. Check type and size, then try again.");
    } finally {
      setIsUploading(false);
    }
  }

  async function handleDownloadAttachment(attachment: Attachment): Promise<void> {
    if (!selectedCompanyId) return;
    setAttachmentError(null);
    try {
      const blob = await api.downloadAttachment(attachment.id, selectedCompanyId);
      const objectUrl = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = objectUrl;
      link.download = attachment.original_file_name;
      document.body.append(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(objectUrl);
    } catch {
      setAttachmentError("File could not be downloaded.");
    }
  }

  async function handleUpdateAttachmentDescription(attachment: Attachment): Promise<void> {
    if (!selectedCompanyId || !detailWorkObject) return;
    setAttachmentError(null);
    try {
      await api.updateAttachment(attachment.id, selectedCompanyId, {
        description: editingAttachmentDescription.trim() || null,
      });
      setEditingAttachmentId(null);
      setEditingAttachmentDescription("");
      await loadWorkObjectDetail(detailWorkObject.id);
    } catch {
      setAttachmentError("Attachment description could not be updated.");
    }
  }

  async function handleDeleteAttachment(attachment: Attachment): Promise<void> {
    if (!selectedCompanyId || !detailWorkObject) return;
    setAttachmentError(null);
    try {
      await api.deleteAttachment(attachment.id, selectedCompanyId);
      if (fileSummaryAttachment?.id === attachment.id) {
        setFileSummaryAttachment(null);
        setFileAISummary(null);
      }
      await loadWorkObjectDetail(detailWorkObject.id);
    } catch {
      setAttachmentError("Attachment could not be removed.");
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
          <FilterBar
            isResetDisabled={!hasActiveFilters}
            onReset={() => {
              setSearchFilter("");
              setStatusFilter("");
              setPriorityFilter("");
              setTypeFilter("");
              setAssigneeFilter("");
              setProjectFilter("");
            }}
          >
            <FilterField label="Search">
              <TextInput placeholder="Title, type, tag" value={searchFilter} onChange={(event) => setSearchFilter(event.target.value)} />
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
            <FilterField label="Type">
              <SelectInput value={typeFilter} onChange={(event) => setTypeFilter(event.target.value)}>
                <option value="">All types</option>
                {activeWorkObjectTypes.map((objectType) => (
                  <option key={objectType.id} value={objectType.key}>
                    {objectType.name}
                  </option>
                ))}
              </SelectInput>
            </FilterField>
            <FilterField label="Assignee">
              <SelectInput value={assigneeFilter} onChange={(event) => setAssigneeFilter(event.target.value)}>
                <option value="">All assignees</option>
                {data.employees.map((employee) => (
                  <option key={employee.id} value={employee.id}>
                    {employee.full_name}
                  </option>
                ))}
              </SelectInput>
            </FilterField>
            <FilterField label="Project">
              <SelectInput value={projectFilter} onChange={(event) => setProjectFilter(event.target.value)}>
                <option value="">All projects</option>
                {data.projects.map((project) => (
                  <option key={project.id} value={project.id}>
                    {project.name}
                  </option>
                ))}
              </SelectInput>
            </FilterField>
          </FilterBar>
          {filteredWorkObjects.length === 0 ? (
            <div className="px-5 py-10 text-center">
              <p className="text-sm font-bold text-ink-950">No work objects match these filters</p>
              <p className="mt-1 text-sm font-medium text-ink-500">Reset filters to see the full work grid.</p>
            </div>
          ) : (
            <DataTable columns={columns} rows={filteredWorkObjects} getRowKey={(workObject) => workObject.id} />
          )}
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
                {!activeWorkObjectTypes.some((objectType) => objectType.key === form.object_type) ? (
                  <option value={form.object_type}>{formatLabel(form.object_type)}</option>
                ) : null}
                {activeWorkObjectTypes.map((objectType) => (
                  <option key={objectType.id} value={objectType.key}>
                    {objectType.name}
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
          {formCustomFields.length > 0 ? (
            <div className="rounded-lg border border-grid-200 bg-grid-50 p-4">
              <p className="text-xs font-bold uppercase tracking-normal text-ink-500">Custom fields</p>
              <div className="mt-4 grid gap-4 sm:grid-cols-2">
                {formCustomFields.map((field) => (
                  <CustomFieldInput
                    key={field.id}
                    definition={field}
                    value={form.custom_fields[field.field_key] ?? (field.field_type === "checkbox" ? false : "")}
                    onChange={(value) => setForm((current) => ({ ...current, custom_fields: { ...current.custom_fields, [field.field_key]: value } }))}
                  />
                ))}
              </div>
            </div>
          ) : null}
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
            <CustomFieldsDetail fields={data.customFields} workObject={detailWorkObject} />

            <AISummaryPanel
              error={aiSummaryError}
              generateLabel="Generate AI Summary"
              isGenerating={isAISummaryGenerating}
              isLoading={isAISummaryLoading}
              job={aiSummary}
              kind="work_object"
              onGenerate={() => void handleGenerateAISummary()}
            />

            <div className="flex flex-wrap gap-2">
              <Button icon={<Pencil className="size-4" aria-hidden="true" />} onClick={() => openEdit(detailWorkObject)}>Edit</Button>
              <Button disabled={isMutating || detailWorkObject.status === "completed"} variant="primary" icon={<CheckCircle2 className="size-4" aria-hidden="true" />} onClick={() => void onCompleteWorkObject(detailWorkObject.id)}>Complete</Button>
              <Button disabled={isMutating || !detailWorkObject.is_active} icon={<Archive className="size-4" aria-hidden="true" />} onClick={() => void onDeactivateWorkObject(detailWorkObject.id)}>Archive</Button>
            </div>

            <section className="rounded-lg border border-grid-200">
              <div className="flex flex-col gap-3 border-b border-grid-200 px-4 py-3 md:flex-row md:items-center md:justify-between">
                <h3 className="text-sm font-bold text-ink-950">Attachments</h3>
                <Button icon={<Upload className="size-4" aria-hidden="true" />} onClick={() => {
                  if (detailWorkObject) void loadAttachments(detailWorkObject.id);
                }}>Retry</Button>
              </div>
              <form className="grid gap-3 border-b border-grid-100 p-4 lg:grid-cols-[1fr_1fr_auto]" onSubmit={handleUploadAttachment}>
                <FieldShell label="File">
                  <TextInput
                    key={selectedFile?.name ?? "empty-file"}
                    accept=".png,.jpg,.jpeg,.webp,.pdf,.csv,.txt,.md,.json,.log,.doc,.docx,.xls,.xlsx"
                    type="file"
                    onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)}
                  />
                </FieldShell>
                <FieldShell label="Description">
                  <TextInput value={uploadDescription} onChange={(event) => setUploadDescription(event.target.value)} />
                </FieldShell>
                <div className="flex items-end">
                  <Button disabled={isUploading || !selectedFile} type="submit" variant="primary" icon={<Upload className="size-4" aria-hidden="true" />}>
                    {isUploading ? "Uploading..." : "Upload"}
                  </Button>
                </div>
                {selectedFile ? (
                  <p className="text-xs font-semibold text-ink-500 lg:col-span-3">
                    {selectedFile.name} / {formatBytes(selectedFile.size)}
                  </p>
                ) : null}
              </form>
              {isAttachmentLoading ? <LoadingState label="Loading attachments" /> : null}
              {attachmentError ? <ErrorState message={attachmentError} onRetry={() => {
                if (detailWorkObject) void loadAttachments(detailWorkObject.id);
              }} /> : null}
              {!isAttachmentLoading && !attachmentError ? (
                attachments.length === 0 ? (
                  <EmptyState description="Uploaded work evidence and documents will appear here." title="No attachments yet" />
                ) : (
                  <div className="divide-y divide-grid-100">
                    {attachments.map((attachment) => (
                      <article key={attachment.id} className="grid gap-3 px-4 py-3 lg:grid-cols-[1fr_1fr_auto] lg:items-center">
                        <div className="min-w-0">
                          <p className="flex min-w-0 items-center gap-2 truncate text-sm font-bold text-ink-950">
                            <FileText className="size-4 shrink-0 text-ink-500" aria-hidden="true" />
                            <span className="truncate">{attachment.original_file_name}</span>
                          </p>
                          <p className="mt-1 truncate text-xs font-semibold text-ink-500">
                            {compactList([attachment.content_type ?? "Unknown type", formatBytes(attachment.file_size), formatDate(attachment.created_at)])}
                          </p>
                          {attachment.uploaded_by_employee_id ? (
                            <p className="mt-1 truncate text-xs font-semibold text-ink-500">
                              Uploaded by {employeeNames[attachment.uploaded_by_employee_id] ?? "employee"}
                            </p>
                          ) : null}
                        </div>
                        {editingAttachmentId === attachment.id ? (
                          <div className="flex gap-2">
                            <TextInput value={editingAttachmentDescription} onChange={(event) => setEditingAttachmentDescription(event.target.value)} />
                            <Button aria-label="Save description" className="shrink-0" onClick={() => void handleUpdateAttachmentDescription(attachment)}>
                              Save
                            </Button>
                          </div>
                        ) : (
                          <button
                            className="min-w-0 truncate rounded-md border border-grid-200 bg-grid-50 px-3 py-2 text-left text-sm font-medium text-ink-600"
                            type="button"
                            onClick={() => {
                              setEditingAttachmentId(attachment.id);
                              setEditingAttachmentDescription(attachment.description ?? "");
                            }}
                          >
                            {attachment.description || "Add description"}
                          </button>
                        )}
                        <div className="flex justify-end gap-2">
                          <Button
                            className="size-9 px-0"
                            aria-label={`Generate AI summary for ${attachment.original_file_name}`}
                            icon={<Sparkles className="size-4" aria-hidden="true" />}
                            title={`Generate AI summary for ${attachment.original_file_name}`}
                            onClick={() => void loadFileAISummary(attachment)}
                          >
                            <span className="sr-only">Summarize file</span>
                          </Button>
                          <Button className="size-9 px-0" aria-label="Download attachment" icon={<Download className="size-4" aria-hidden="true" />} onClick={() => void handleDownloadAttachment(attachment)}>
                            <span className="sr-only">Download</span>
                          </Button>
                          <Button className="size-9 px-0" aria-label="Delete attachment" icon={<Trash2 className="size-4" aria-hidden="true" />} onClick={() => void handleDeleteAttachment(attachment)}>
                            <span className="sr-only">Delete</span>
                          </Button>
                        </div>
                      </article>
                    ))}
                  </div>
                )
              ) : null}
              {fileSummaryAttachment ? (
                <div className="border-t border-grid-200 p-4">
                  <p className="mb-3 text-xs font-black uppercase tracking-normal text-ink-500">
                    File summary / {fileSummaryAttachment.original_file_name}
                  </p>
                  <AISummaryPanel
                    error={fileAISummaryError}
                    generateLabel="Generate AI File Summary"
                    isGenerating={isFileAISummaryGenerating}
                    isLoading={isFileAISummaryLoading}
                    job={fileAISummary}
                    kind="file"
                    onGenerate={() => void handleGenerateFileAISummary()}
                  />
                </div>
              ) : null}
            </section>

            <CommentsSection
              companyId={selectedCompanyId}
              employees={data.employees}
              employeeNames={employeeNames}
              targetEntityId={detailWorkObject.id}
              targetEntityType="work_object"
              onChanged={() => void loadWorkObjectDetail(detailWorkObject.id)}
            />

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

function CustomFieldInput({
  definition,
  value,
  onChange,
}: {
  definition: CustomFieldDefinition;
  value: string | boolean;
  onChange: (value: string | boolean) => void;
}): JSX.Element {
  if (definition.field_type === "checkbox") {
    return (
      <label className="flex min-h-10 items-center gap-2 rounded-md border border-grid-200 bg-white px-3 py-2 text-sm font-semibold text-ink-700">
        <input checked={Boolean(value)} type="checkbox" onChange={(event) => onChange(event.target.checked)} />
        {definition.label}
      </label>
    );
  }
  if (definition.field_type === "select") {
    return (
      <FieldShell label={definition.label}>
        <SelectInput required={definition.required} value={typeof value === "string" ? value : ""} onChange={(event) => onChange(event.target.value)}>
          <option value="">Select</option>
          {definition.options.map((option) => (
            <option key={option} value={option}>
              {formatLabel(option)}
            </option>
          ))}
        </SelectInput>
      </FieldShell>
    );
  }
  if (definition.field_type === "textarea") {
    return (
      <FieldShell label={definition.label}>
        <TextArea required={definition.required} value={typeof value === "string" ? value : ""} onChange={(event) => onChange(event.target.value)} />
      </FieldShell>
    );
  }
  return (
    <FieldShell label={definition.label}>
      <TextInput
        placeholder={definition.field_type === "multiselect" ? "Comma-separated values" : definition.help_text ?? undefined}
        required={definition.required}
        type={definition.field_type === "number" || definition.field_type === "date" ? definition.field_type : "text"}
        value={typeof value === "string" ? value : ""}
        onChange={(event) => onChange(event.target.value)}
      />
    </FieldShell>
  );
}

function CustomFieldsDetail({ fields, workObject }: { fields: CustomFieldDefinition[]; workObject: WorkObject }): JSX.Element | null {
  const values = workObject.custom_fields ?? {};
  const valueKeys = Object.keys(values);
  if (valueKeys.length === 0) return null;
  const knownFields = customFieldDefinitionsFor(fields, workObject.object_type, true);
  const knownKeys = new Set(knownFields.map((field) => field.field_key));
  const unknownKeys = valueKeys.filter((key) => !knownKeys.has(key));
  const rows = [
    ...knownFields.filter((field) => valueKeys.includes(field.field_key)).map((field) => ({
      key: field.field_key,
      label: field.label,
      value: values[field.field_key],
      isActive: field.is_active,
    })),
    ...unknownKeys.map((key) => ({ key, label: formatLabel(key), value: values[key], isActive: true })),
  ];

  if (rows.length === 0) return null;

  return (
    <section className="rounded-lg border border-grid-200 bg-grid-50 p-4">
      <p className="text-xs font-bold uppercase tracking-normal text-ink-500">Custom fields</p>
      <div className="mt-3 grid gap-3 sm:grid-cols-2">
        {rows.map((row) => (
          <div key={row.key} className="rounded-md border border-grid-200 bg-white p-3">
            <p className="flex items-center gap-2 text-xs font-bold uppercase tracking-normal text-ink-500">
              {row.label}
              {!row.isActive ? <Badge label="Archived" tone="slate" /> : null}
            </p>
            <p className="mt-1 text-sm font-bold text-ink-950">{formatCustomFieldValue(row.value)}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
