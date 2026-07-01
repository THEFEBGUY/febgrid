import { Archive, Bot, CreditCard, FileText, Pencil, Play, Plus, RotateCcw, Save, ShieldAlert, Wand2, XCircle } from "lucide-react";
import { type FormEvent, useEffect, useMemo, useState } from "react";

import { MagicBentoCard } from "../components/premium/MagicBento";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { DataTable, type DataTableColumn } from "../components/ui/DataTable";
import { FieldShell, SelectInput, TextArea, TextInput } from "../components/ui/FormControls";
import { Modal } from "../components/ui/Modal";
import { ModuleBoundary } from "../components/ui/ModuleBoundary";
import { SectionPanel } from "../components/ui/SectionPanel";
import { EmptyState } from "../components/ui/States";
import type {
  Attachment,
  AttachmentUpdatePayload,
  AIJob,
  AIJobCreatePayload,
  AISafetySettingsUpdatePayload,
  CompanyPlanUpdatePayload,
  CompanySettingsUpdatePayload,
  CustomFieldCreatePayload,
  CustomFieldDefinition,
  CustomFieldType,
  CustomFieldUpdatePayload,
  UserRole,
  WorkObjectTypeCreatePayload,
  WorkObjectTypeDefinition,
  WorkObjectTypeUpdatePayload,
} from "../types/api";
import type { ModulePageProps } from "../types/page";
import { compactList, formatDate, formatLabel } from "../utils/format";

interface SettingsPageProps extends ModulePageProps {
  currentUserRole: UserRole | null;
  onApplyIndustryTemplate: (templateKey: string) => Promise<void>;
  onArchiveFile: (attachmentId: string) => Promise<void>;
  onArchiveCustomField: (fieldId: string) => Promise<void>;
  onArchiveWorkObjectType: (typeId: string) => Promise<void>;
  onCancelAIJob: (jobId: string) => Promise<void>;
  onCreateAIJob: (payload: Omit<AIJobCreatePayload, "company_id">) => Promise<void>;
  onCreateCustomField: (payload: Omit<CustomFieldCreatePayload, "company_id">) => Promise<void>;
  onCreateWorkObjectType: (payload: Omit<WorkObjectTypeCreatePayload, "company_id">) => Promise<void>;
  onRunAIJob: (jobId: string) => Promise<void>;
  onUpdateAISafetySettings: (payload: AISafetySettingsUpdatePayload) => Promise<void>;
  onUpdateCompanySettings: (payload: CompanySettingsUpdatePayload) => Promise<void>;
  onUpdateCompanyPlan: (payload: CompanyPlanUpdatePayload) => Promise<void>;
  onUpdateCustomField: (fieldId: string, payload: CustomFieldUpdatePayload) => Promise<void>;
  onUpdateFile: (attachmentId: string, payload: AttachmentUpdatePayload) => Promise<void>;
  onUpdateWorkObjectType: (typeId: string, payload: WorkObjectTypeUpdatePayload) => Promise<void>;
  onRestoreFile: (attachmentId: string) => Promise<void>;
}

const weekDays = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"];
const priorities = ["low", "medium", "high", "critical"];
const fieldTypes: CustomFieldType[] = ["text", "textarea", "number", "date", "checkbox", "select", "multiselect"];

const emptyTypeForm = {
  key: "",
  name: "",
  description: "",
  color: "",
  is_default: false,
  sort_order: "100",
};

const emptyFieldForm = {
  field_key: "",
  label: "",
  field_type: "text" as CustomFieldType,
  required: false,
  options: "",
  default_value: "",
  help_text: "",
  sort_order: "100",
};

const emptyFileForm = {
  description: "",
  tags: "",
};

function slugify(value: string): string {
  return value
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "")
    .replace(/_{2,}/g, "_");
}

function parseOptions(value: string): string[] {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function parseDefaultValue(fieldType: CustomFieldType, value: string): unknown {
  if (!value.trim()) return null;
  if (fieldType === "number") {
    const numeric = Number(value);
    return Number.isFinite(numeric) ? numeric : value;
  }
  if (fieldType === "checkbox") {
    return value === "true";
  }
  if (fieldType === "multiselect") {
    return parseOptions(value);
  }
  return value;
}

function formatFileSize(value: number | null): string {
  if (!value) return "0 MB";
  return `${(value / (1024 * 1024)).toFixed(value > 1024 * 1024 ? 2 : 3)} MB`;
}

function aiJobTone(status: string): "blue" | "green" | "amber" | "red" | "slate" {
  if (status === "succeeded") return "green";
  if (status === "failed") return "red";
  if (status === "running") return "blue";
  if (status === "cancelled" || status === "skipped") return "slate";
  return "amber";
}

function aiOutputSummary(job: AIJob): string {
  const summary = job.output_payload.summary;
  if (typeof summary === "string" && summary.trim()) return summary;
  if (job.error_message) return job.error_message;
  return "No mock output yet.";
}

export function SettingsPage({
  data,
  selectedCompany,
  isLoadingModules,
  moduleError,
  onRetry,
  isMutating,
  currentUserRole,
  onApplyIndustryTemplate,
  onArchiveFile,
  onArchiveCustomField,
  onArchiveWorkObjectType,
  onCancelAIJob,
  onCreateAIJob,
  onCreateCustomField,
  onCreateWorkObjectType,
  onRunAIJob,
  onUpdateAISafetySettings,
  onUpdateCompanySettings,
  onUpdateCompanyPlan,
  onUpdateCustomField,
  onUpdateFile,
  onUpdateWorkObjectType,
  onRestoreFile,
}: SettingsPageProps): JSX.Element {
  const canManage = currentUserRole === "company_owner" || currentUserRole === "admin";
  const activeTypes = useMemo(() => data.workObjectTypes.filter((type) => type.is_active), [data.workObjectTypes]);
  const [settingsForm, setSettingsForm] = useState({
    name: "",
    industry: "",
    size: "",
    timezone: "UTC",
    description: "",
    work_week: ["monday", "tuesday", "wednesday", "thursday", "friday"],
    default_work_object_type: "task",
    default_priority: "medium",
    file_upload_max_mb: "10",
  });
  const [templateKey, setTemplateKey] = useState("");
  const [settingsMessage, setSettingsMessage] = useState<string | null>(null);
  const [selectedTypeKey, setSelectedTypeKey] = useState("task");
  const [isTypeModalOpen, setIsTypeModalOpen] = useState(false);
  const [editingType, setEditingType] = useState<WorkObjectTypeDefinition | null>(null);
  const [typeForm, setTypeForm] = useState(emptyTypeForm);
  const [isFieldModalOpen, setIsFieldModalOpen] = useState(false);
  const [editingField, setEditingField] = useState<CustomFieldDefinition | null>(null);
  const [fieldForm, setFieldForm] = useState(emptyFieldForm);
  const [fileSearch, setFileSearch] = useState("");
  const [fileTypeFilter, setFileTypeFilter] = useState("");
  const [editingFile, setEditingFile] = useState<Attachment | null>(null);
  const [fileForm, setFileForm] = useState(emptyFileForm);
  const [formError, setFormError] = useState<string | null>(null);
  const [isExternalAIWarningOpen, setIsExternalAIWarningOpen] = useState(false);

  useEffect(() => {
    const settings = data.companySettings;
    if (!settings) return;
    setSettingsForm({
      name: settings.name,
      industry: settings.industry ?? "",
      size: settings.size ?? "",
      timezone: settings.timezone || "UTC",
      description: settings.description ?? "",
      work_week: settings.work_week.length > 0 ? settings.work_week : ["monday", "tuesday", "wednesday", "thursday", "friday"],
      default_work_object_type: settings.default_work_object_type || "task",
      default_priority: settings.default_priority || "medium",
      file_upload_max_mb: settings.file_upload_max_mb.toString(),
    });
    setTemplateKey(settings.template_key ?? data.industryTemplates[0]?.key ?? "");
  }, [data.companySettings, data.industryTemplates]);

  useEffect(() => {
    if (activeTypes.length === 0) {
      setSelectedTypeKey("task");
      return;
    }
    if (!activeTypes.some((type) => type.key === selectedTypeKey)) {
      setSelectedTypeKey(activeTypes[0].key);
    }
  }, [activeTypes, selectedTypeKey]);

  const fieldsForSelectedType = useMemo(
    () =>
      data.customFields
        .filter((field) => field.type_key === selectedTypeKey)
        .sort((left, right) => left.sort_order - right.sort_order || left.label.localeCompare(right.label)),
    [data.customFields, selectedTypeKey],
  );
  const fileTypes = useMemo(
    () => Array.from(new Set(data.files.map((file) => file.content_type).filter(Boolean) as string[])).sort(),
    [data.files],
  );
  const filteredFiles = useMemo(() => {
    const query = fileSearch.trim().toLowerCase();
    return data.files.filter((file) => {
      const searchable = [file.original_file_name, file.file_name, file.description, file.content_type, file.extension, file.tags.join(" ")]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();
      if (query && !searchable.includes(query)) return false;
      if (fileTypeFilter && file.content_type !== fileTypeFilter) return false;
      return true;
    });
  }, [data.files, fileSearch, fileTypeFilter]);

  const typeColumns: DataTableColumn<WorkObjectTypeDefinition>[] = [
    {
      key: "name",
      label: "Type",
      render: (type) => (
        <span>
          <span className="block font-bold text-ink-950">{type.name}</span>
          <span className="block text-xs font-semibold text-ink-500">{type.key}</span>
        </span>
      ),
    },
    { key: "description", label: "Description", render: (type) => type.description ?? "No description" },
    { key: "default", label: "Default", render: (type) => (type.is_default ? <Badge label="Default" tone="blue" /> : "No") },
    { key: "active", label: "State", render: (type) => <Badge label={type.is_active ? "Active" : "Inactive"} tone={type.is_active ? "green" : "slate"} /> },
    { key: "updated", label: "Updated", render: (type) => formatDate(type.updated_at) },
    {
      key: "actions",
      label: "Actions",
      render: (type) => (
        <div className="flex justify-end gap-2">
          <Button
            aria-label={`Edit ${type.name}`}
            className="size-9 px-0"
            disabled={!canManage}
            icon={<Pencil className="size-4" aria-hidden="true" />}
            title={`Edit ${type.name}`}
            onClick={() => openTypeModal(type)}
          >
            <span className="sr-only">Edit</span>
          </Button>
          <Button
            aria-label={`Deactivate ${type.name}`}
            className="size-9 px-0"
            disabled={!canManage || !type.is_active || type.key === "task"}
            icon={<Archive className="size-4" aria-hidden="true" />}
            title={`Deactivate ${type.name}`}
            onClick={() => void onArchiveWorkObjectType(type.id)}
          >
            <span className="sr-only">Deactivate</span>
          </Button>
        </div>
      ),
      className: "text-right",
    },
  ];

  const fieldColumns: DataTableColumn<CustomFieldDefinition>[] = [
    {
      key: "label",
      label: "Field",
      render: (field) => (
        <span>
          <span className="block font-bold text-ink-950">{field.label}</span>
          <span className="block text-xs font-semibold text-ink-500">{field.field_key}</span>
        </span>
      ),
    },
    { key: "type", label: "Type", render: (field) => formatLabel(field.field_type) },
    { key: "required", label: "Required", render: (field) => (field.required ? <Badge label="Required" tone="amber" /> : "Optional") },
    { key: "options", label: "Options", render: (field) => field.options.join(", ") || "None" },
    { key: "state", label: "State", render: (field) => <Badge label={field.is_active ? "Active" : "Inactive"} tone={field.is_active ? "green" : "slate"} /> },
    {
      key: "actions",
      label: "Actions",
      render: (field) => (
        <div className="flex justify-end gap-2">
          <Button
            aria-label={`Edit ${field.label}`}
            className="size-9 px-0"
            disabled={!canManage}
            icon={<Pencil className="size-4" aria-hidden="true" />}
            title={`Edit ${field.label}`}
            onClick={() => openFieldModal(field)}
          >
            <span className="sr-only">Edit</span>
          </Button>
          <Button
            aria-label={`Deactivate ${field.label}`}
            className="size-9 px-0"
            disabled={!canManage || !field.is_active}
            icon={<Archive className="size-4" aria-hidden="true" />}
            title={`Deactivate ${field.label}`}
            onClick={() => void onArchiveCustomField(field.id)}
          >
            <span className="sr-only">Deactivate</span>
          </Button>
        </div>
      ),
      className: "text-right",
    },
  ];

  const fileColumns: DataTableColumn<Attachment>[] = [
    {
      key: "file",
      label: "File",
      render: (file) => (
        <span>
          <span className="block font-bold text-ink-950">{file.original_file_name}</span>
          <span className="block text-xs font-semibold text-ink-500">{file.description || file.content_type || "No description"}</span>
        </span>
      ),
    },
    { key: "size", label: "Size", render: (file) => formatFileSize(file.file_size) },
    { key: "status", label: "Pipeline", render: (file) => <Badge label={formatLabel(file.processing_status)} tone={file.is_active ? "blue" : "slate"} /> },
    { key: "scan", label: "Scan", render: (file) => <Badge label={formatLabel(file.scan_status)} tone="slate" /> },
    { key: "linked", label: "Linked entity", render: (file) => compactList([formatLabel(file.linked_entity_type), file.linked_entity_id.slice(0, 8)]) },
    { key: "uploaded", label: "Uploaded", render: (file) => formatDate(file.created_at) },
    {
      key: "actions",
      label: "Actions",
      render: (file) => (
        <div className="flex justify-end gap-2">
          <Button
            aria-label={`Edit ${file.original_file_name}`}
            className="size-9 px-0"
            disabled={!canManage}
            icon={<Pencil className="size-4" aria-hidden="true" />}
            title={`Edit ${file.original_file_name}`}
            onClick={() => openFileModal(file)}
          >
            <span className="sr-only">Edit file</span>
          </Button>
          {file.is_active ? (
            <Button
              aria-label={`Archive ${file.original_file_name}`}
              className="size-9 px-0"
              disabled={!canManage || isMutating}
              icon={<Archive className="size-4" aria-hidden="true" />}
              title={`Archive ${file.original_file_name}`}
              onClick={() => void onArchiveFile(file.id)}
            >
              <span className="sr-only">Archive file</span>
            </Button>
          ) : (
            <Button
              aria-label={`Restore ${file.original_file_name}`}
              className="size-9 px-0"
              disabled={!canManage || isMutating}
              icon={<RotateCcw className="size-4" aria-hidden="true" />}
              title={`Restore ${file.original_file_name}`}
              onClick={() => void onRestoreFile(file.id)}
            >
              <span className="sr-only">Restore file</span>
            </Button>
          )}
        </div>
      ),
      className: "text-right",
    },
  ];

  const aiJobColumns: DataTableColumn<AIJob>[] = [
    {
      key: "job",
      label: "Job",
      render: (job) => (
        <span>
          <span className="block font-bold text-ink-950">{formatLabel(job.job_type)}</span>
          <span className="block text-xs font-semibold text-ink-500">{aiOutputSummary(job)}</span>
        </span>
      ),
    },
    { key: "status", label: "Status", render: (job) => <Badge label={formatLabel(job.status)} tone={aiJobTone(job.status)} /> },
    { key: "provider", label: "Provider", render: (job) => <Badge label={formatLabel(job.provider_mode)} tone="slate" /> },
    { key: "attempts", label: "Attempts", render: (job) => `${job.attempts}/${job.max_attempts}` },
    { key: "created", label: "Created", render: (job) => formatDate(job.created_at) },
    {
      key: "actions",
      label: "Actions",
      render: (job) => (
        <div className="flex justify-end gap-2">
          <Button
            aria-label={`Run ${formatLabel(job.job_type)}`}
            className="size-9 px-0"
            disabled={!canManage || isMutating || job.status !== "queued"}
            icon={<Play className="size-4" aria-hidden="true" />}
            title={`Run ${formatLabel(job.job_type)}`}
            onClick={() => void onRunAIJob(job.id)}
          >
            <span className="sr-only">Run AI job</span>
          </Button>
          <Button
            aria-label={`Cancel ${formatLabel(job.job_type)}`}
            className="size-9 px-0"
            disabled={!canManage || isMutating || !["queued", "running"].includes(job.status)}
            icon={<XCircle className="size-4" aria-hidden="true" />}
            title={`Cancel ${formatLabel(job.job_type)}`}
            onClick={() => void onCancelAIJob(job.id)}
          >
            <span className="sr-only">Cancel AI job</span>
          </Button>
        </div>
      ),
      className: "text-right",
    },
  ];

  function toggleWorkDay(day: string): void {
    setSettingsForm((current) => {
      const hasDay = current.work_week.includes(day);
      return {
        ...current,
        work_week: hasDay ? current.work_week.filter((item) => item !== day) : [...current.work_week, day],
      };
    });
  }

  function openTypeModal(type?: WorkObjectTypeDefinition): void {
    setEditingType(type ?? null);
    setFormError(null);
    setTypeForm(
      type
        ? {
            key: type.key,
            name: type.name,
            description: type.description ?? "",
            color: type.color ?? "",
            is_default: type.is_default,
            sort_order: type.sort_order.toString(),
          }
        : emptyTypeForm,
    );
    setIsTypeModalOpen(true);
  }

  function openFieldModal(field?: CustomFieldDefinition): void {
    setEditingField(field ?? null);
    setFormError(null);
    setFieldForm(
      field
        ? {
            field_key: field.field_key,
            label: field.label,
            field_type: field.field_type,
            required: field.required,
            options: field.options.join(", "),
            default_value: field.default_value == null ? "" : Array.isArray(field.default_value) ? field.default_value.join(", ") : String(field.default_value),
            help_text: field.help_text ?? "",
            sort_order: field.sort_order.toString(),
          }
        : emptyFieldForm,
    );
    setIsFieldModalOpen(true);
  }

  function openFileModal(file: Attachment): void {
    setEditingFile(file);
    setFormError(null);
    setFileForm({
      description: file.description ?? "",
      tags: file.tags.join(", "),
    });
  }

  async function handlePlanChange(planKey: string): Promise<void> {
    if (!planKey || !canManage) return;
    setSettingsMessage(null);
    try {
      await onUpdateCompanyPlan({ plan_key: planKey });
      setSettingsMessage("Local billing plan updated. Payment integration remains intentionally disabled.");
    } catch {
      setSettingsMessage("Billing plan could not be updated.");
    }
  }

  async function handleSettingsSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    setSettingsMessage(null);
    try {
      await onUpdateCompanySettings({
        name: settingsForm.name.trim(),
        industry: settingsForm.industry.trim() || null,
        size: settingsForm.size.trim() || null,
        timezone: settingsForm.timezone.trim() || "UTC",
        description: settingsForm.description.trim() || null,
        work_week: settingsForm.work_week,
        default_work_object_type: settingsForm.default_work_object_type,
        default_priority: settingsForm.default_priority,
        file_upload_max_mb: Number(settingsForm.file_upload_max_mb) || 10,
      });
      setSettingsMessage("Settings saved.");
    } catch {
      setSettingsMessage("Settings could not be saved.");
    }
  }

  async function handleApplyTemplate(): Promise<void> {
    if (!templateKey) return;
    setSettingsMessage(null);
    try {
      await onApplyIndustryTemplate(templateKey);
      setSettingsMessage("Industry template applied without deleting existing data.");
    } catch {
      setSettingsMessage("Template could not be applied.");
    }
  }

  async function handleTypeSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    setFormError(null);
    const key = slugify(typeForm.key || typeForm.name);
    if (!key || !typeForm.name.trim()) {
      setFormError("Type name and key are required.");
      return;
    }
    const payload = {
      name: typeForm.name.trim(),
      description: typeForm.description.trim() || null,
      color: typeForm.color.trim() || null,
      is_default: typeForm.is_default,
      sort_order: Number(typeForm.sort_order) || 100,
      metadata: {},
    };
    try {
      if (editingType) {
        await onUpdateWorkObjectType(editingType.id, payload);
      } else {
        await onCreateWorkObjectType({ ...payload, key, is_active: true });
      }
      setIsTypeModalOpen(false);
    } catch {
      setFormError("Work object type could not be saved.");
    }
  }

  async function handleFieldSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    setFormError(null);
    const fieldKey = slugify(fieldForm.field_key || fieldForm.label);
    if (!fieldKey || !fieldForm.label.trim()) {
      setFormError("Field label and key are required.");
      return;
    }
    const payload = {
      label: fieldForm.label.trim(),
      field_type: fieldForm.field_type,
      required: fieldForm.required,
      options: parseOptions(fieldForm.options),
      default_value: parseDefaultValue(fieldForm.field_type, fieldForm.default_value),
      help_text: fieldForm.help_text.trim() || null,
      sort_order: Number(fieldForm.sort_order) || 100,
      metadata: {},
    };
    try {
      if (editingField) {
        await onUpdateCustomField(editingField.id, payload);
      } else {
        const selectedType = data.workObjectTypes.find((type) => type.key === selectedTypeKey);
        await onCreateCustomField({
          ...payload,
          field_key: fieldKey,
          type_key: selectedTypeKey,
          work_object_type_id: selectedType?.id ?? null,
          is_active: true,
        });
      }
      setIsFieldModalOpen(false);
    } catch {
      setFormError("Custom field could not be saved.");
    }
  }

  async function handleFileSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (!editingFile) return;
    setFormError(null);
    try {
      await onUpdateFile(editingFile.id, {
        description: fileForm.description.trim() || null,
        tags: parseOptions(fileForm.tags),
      });
      setEditingFile(null);
    } catch {
      setFormError("File metadata could not be saved.");
    }
  }

  async function handleCreateMockAIJob(): Promise<void> {
    if (!canManage) return;
    setSettingsMessage(null);
    try {
      await onCreateAIJob({
        job_type: "company_brief_mock",
        priority: "normal",
        input_entity_type: selectedCompany ? "company" : null,
        input_entity_id: selectedCompany?.id ?? null,
        input_payload: { source: "settings_ai_foundation" },
        metadata: { mock_only: true },
      });
      setSettingsMessage("Mock AI job queued. Real AI providers remain disconnected.");
    } catch {
      setSettingsMessage("Mock AI job could not be queued.");
    }
  }

  async function handleToggleAIEnabled(nextValue: boolean): Promise<void> {
    if (!canManage) return;
    setSettingsMessage(null);
    try {
      await onUpdateAISafetySettings({ ai_enabled: nextValue });
      setSettingsMessage(nextValue ? "AI foundation enabled for this company." : "AI foundation disabled for this company.");
    } catch {
      setSettingsMessage("AI safety setting could not be updated.");
    }
  }

  async function confirmEnableExternalAI(): Promise<void> {
    if (!canManage) return;
    setSettingsMessage(null);
    try {
      await onUpdateAISafetySettings({ external_ai_processing_allowed: true });
      setSettingsMessage("External AI processing is now explicitly allowed for this company.");
      setIsExternalAIWarningOpen(false);
    } catch {
      setSettingsMessage("External AI processing could not be enabled.");
    }
  }

  async function disableExternalAI(): Promise<void> {
    if (!canManage) return;
    setSettingsMessage(null);
    try {
      await onUpdateAISafetySettings({ external_ai_processing_allowed: false });
      setSettingsMessage("External AI processing is disabled for this company.");
    } catch {
      setSettingsMessage("External AI processing could not be disabled.");
    }
  }

  const aiProviderStatus = data.aiProviderStatus;
  const aiSafetySettings = data.aiSafetySettings;
  const displayedProviderMode = aiProviderStatus?.provider_mode ?? data.aiCapabilities?.provider_mode ?? "mock";
  const displayedModelName = aiProviderStatus?.model_name ?? (displayedProviderMode === "mock" ? "mock-deterministic" : "Not configured");
  const externalProcessingAllowed = Boolean(aiSafetySettings?.external_ai_processing_allowed ?? aiProviderStatus?.external_processing_allowed);
  const aiEnabled = Boolean(aiSafetySettings?.ai_enabled ?? aiProviderStatus?.ai_enabled ?? true);

  return (
    <>
      <SectionPanel
        eyebrow={selectedCompany?.name ?? "Company settings"}
        title="Settings"
        action={
          <Button disabled={!canManage || !selectedCompany} icon={<Save className="size-4" aria-hidden="true" />} type="submit" form="company-settings-form">
            Save settings
          </Button>
        }
      >
        <ModuleBoundary
          emptyDescription="Create or select a company before editing settings."
          emptyTitle="No company selected"
          error={moduleError}
          isEmpty={!selectedCompany}
          isLoading={isLoadingModules}
          onRetry={onRetry}
        >
          <div className="space-y-6 p-5">
            {!canManage ? (
              <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm font-semibold text-amber-800">
                Settings are read-only for your current role.
              </div>
            ) : null}
            {settingsMessage ? <p className="febgrid-muted-surface rounded-lg px-4 py-3 text-sm font-semibold text-ink-700">{settingsMessage}</p> : null}

            <form id="company-settings-form" className="grid gap-4 lg:grid-cols-3" onSubmit={handleSettingsSubmit}>
              <FieldShell label="Company display name">
                <TextInput disabled={!canManage} required value={settingsForm.name} onChange={(event) => setSettingsForm((current) => ({ ...current, name: event.target.value }))} />
              </FieldShell>
              <FieldShell label="Industry">
                <TextInput disabled={!canManage} value={settingsForm.industry} onChange={(event) => setSettingsForm((current) => ({ ...current, industry: event.target.value }))} />
              </FieldShell>
              <FieldShell label="Company size">
                <TextInput disabled={!canManage} placeholder="1-10, 11-50, 51-200" value={settingsForm.size} onChange={(event) => setSettingsForm((current) => ({ ...current, size: event.target.value }))} />
              </FieldShell>
              <FieldShell label="Timezone">
                <TextInput disabled={!canManage} value={settingsForm.timezone} onChange={(event) => setSettingsForm((current) => ({ ...current, timezone: event.target.value }))} />
              </FieldShell>
              <FieldShell label="Default work type">
                <SelectInput disabled={!canManage} value={settingsForm.default_work_object_type} onChange={(event) => setSettingsForm((current) => ({ ...current, default_work_object_type: event.target.value }))}>
                  {activeTypes.map((type) => (
                    <option key={type.id} value={type.key}>
                      {type.name}
                    </option>
                  ))}
                </SelectInput>
              </FieldShell>
              <FieldShell label="Default priority">
                <SelectInput disabled={!canManage} value={settingsForm.default_priority} onChange={(event) => setSettingsForm((current) => ({ ...current, default_priority: event.target.value }))}>
                  {priorities.map((priority) => (
                    <option key={priority} value={priority}>
                      {formatLabel(priority)}
                    </option>
                  ))}
                </SelectInput>
              </FieldShell>
              <FieldShell label="File upload limit MB">
                <TextInput disabled={!canManage} min={1} max={100} type="number" value={settingsForm.file_upload_max_mb} onChange={(event) => setSettingsForm((current) => ({ ...current, file_upload_max_mb: event.target.value }))} />
              </FieldShell>
              <div className="lg:col-span-3">
                <FieldShell label="Company description">
                  <TextArea disabled={!canManage} value={settingsForm.description} onChange={(event) => setSettingsForm((current) => ({ ...current, description: event.target.value }))} />
                </FieldShell>
              </div>
              <div className="lg:col-span-3">
                <p className="mb-2 text-sm font-bold text-ink-700">Work week</p>
                <div className="grid gap-2 sm:grid-cols-4 lg:grid-cols-7">
                  {weekDays.map((day) => (
                    <label key={day} className="flex items-center gap-2 rounded-md border border-grid-200 bg-white px-3 py-2 text-sm font-semibold text-ink-700">
                      <input checked={settingsForm.work_week.includes(day)} disabled={!canManage} type="checkbox" onChange={() => toggleWorkDay(day)} />
                      {formatLabel(day)}
                    </label>
                  ))}
                </div>
              </div>
            </form>

            <div className="febgrid-command-card rounded-lg p-4">
              <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
                <div>
                  <p className="text-xs font-bold uppercase tracking-normal text-ink-500">Industry template</p>
                  <h3 className="mt-1 text-base font-bold text-ink-950">Apply safe defaults</h3>
                  <p className="mt-1 text-sm font-medium text-ink-500">Templates add missing work types and custom fields without deleting existing data.</p>
                </div>
                <div className="flex min-w-72 gap-2">
                  <SelectInput disabled={!canManage} value={templateKey} onChange={(event) => setTemplateKey(event.target.value)}>
                    {data.industryTemplates.map((template) => (
                      <option key={template.key} value={template.key}>
                        {template.name}
                      </option>
                    ))}
                  </SelectInput>
                  <Button disabled={!canManage || !templateKey || isMutating} icon={<Wand2 className="size-4" aria-hidden="true" />} onClick={() => void handleApplyTemplate()}>
                    Apply
                  </Button>
                </div>
              </div>
            </div>
          </div>
        </ModuleBoundary>
      </SectionPanel>

      <div className="mt-6 grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
        <SectionPanel
          eyebrow="Billing preparation"
          title="Plan and usage"
          action={<CreditCard className="size-5 text-ink-500" aria-hidden="true" />}
        >
          {data.billingSummary ? (
            <div className="space-y-5 p-5">
              <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                <MagicBentoCard className="p-4" tone="blue">
                  <p className="text-xs font-black uppercase tracking-normal text-ink-500">Current plan</p>
                  <p className="mt-2 text-2xl font-black text-ink-950">{formatLabel(data.billingSummary.plan.plan_key)}</p>
                  <p className="mt-1 text-sm font-semibold text-ink-500">{formatLabel(data.billingSummary.plan.billing_status)}</p>
                </MagicBentoCard>
                <MagicBentoCard className="p-4" tone="green">
                  <p className="text-xs font-black uppercase tracking-normal text-ink-500">Employees</p>
                  <p className="mt-2 text-2xl font-black text-ink-950">
                    {data.billingSummary.usage.active_employees}/{data.billingSummary.plan.employee_limit}
                  </p>
                </MagicBentoCard>
                <MagicBentoCard className="p-4" tone="teal">
                  <p className="text-xs font-black uppercase tracking-normal text-ink-500">Work objects</p>
                  <p className="mt-2 text-2xl font-black text-ink-950">
                    {data.billingSummary.usage.active_work_objects}/{data.billingSummary.plan.work_object_limit}
                  </p>
                </MagicBentoCard>
                <MagicBentoCard className="p-4" tone="amber">
                  <p className="text-xs font-black uppercase tracking-normal text-ink-500">Storage</p>
                  <p className="mt-2 text-2xl font-black text-ink-950">
                    {data.billingSummary.usage.storage_used_mb}/{data.billingSummary.plan.storage_limit_mb} MB
                  </p>
                </MagicBentoCard>
              </div>
              <div className="grid gap-3 md:grid-cols-[1fr_1.3fr]">
                <FieldShell label="Local/dev plan">
                  <SelectInput disabled={!canManage || isMutating} value={data.billingSummary.plan.plan_key} onChange={(event) => void handlePlanChange(event.target.value)}>
                    {data.billingPlans.map((plan) => (
                      <option key={plan.key} value={plan.key}>
                        {plan.name}
                      </option>
                    ))}
                  </SelectInput>
                </FieldShell>
                <div className="febgrid-muted-surface rounded-lg px-4 py-3 text-sm font-semibold text-ink-600">
                  {data.billingSummary.payment_provider_note} No card, bank, invoice, Stripe, or Razorpay flow exists in this foundation.
                </div>
              </div>
              {data.billingSummary.warnings.length > 0 ? (
                <div className="space-y-2">
                  {data.billingSummary.warnings.map((warning) => (
                    <div key={warning.code} className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm font-semibold text-amber-800">
                      {warning.message}
                    </div>
                  ))}
                </div>
              ) : (
                <p className="febgrid-muted-surface rounded-lg px-4 py-3 text-sm font-semibold text-ink-600">Usage is within prepared plan limits.</p>
              )}
            </div>
          ) : (
            <EmptyState description="Billing preparation data will appear after the company modules load." title="No billing summary" />
          )}
        </SectionPanel>

        <SectionPanel
          eyebrow="File pipeline"
          title="Company files"
          action={<FileText className="size-5 text-ink-500" aria-hidden="true" />}
        >
          <div className="grid gap-3 border-b border-grid-200 p-5 md:grid-cols-[1fr_240px]">
            <FieldShell label="Search files">
              <TextInput placeholder="Name, description, type, tag" value={fileSearch} onChange={(event) => setFileSearch(event.target.value)} />
            </FieldShell>
            <FieldShell label="File type">
              <SelectInput value={fileTypeFilter} onChange={(event) => setFileTypeFilter(event.target.value)}>
                <option value="">All file types</option>
                {fileTypes.map((fileType) => (
                  <option key={fileType} value={fileType}>
                    {fileType}
                  </option>
                ))}
              </SelectInput>
            </FieldShell>
          </div>
          {filteredFiles.length === 0 ? (
            <EmptyState description="Files uploaded to permitted work objects will appear here with pipeline metadata." title="No files found" />
          ) : (
            <DataTable columns={fileColumns} rows={filteredFiles} getRowKey={(file) => file.id} />
          )}
        </SectionPanel>
      </div>

      <SectionPanel
        eyebrow="AI foundation"
        title="Provider-safe AI jobs"
        className="mt-6"
        action={
          <div className="flex flex-wrap justify-end gap-2">
            <Button disabled={!canManage || !selectedCompany || isMutating} icon={<Bot className="size-4" aria-hidden="true" />} onClick={() => void handleCreateMockAIJob()}>
              Create mock job
            </Button>
          </div>
        }
      >
        <div className="space-y-5 p-5">
          <div className="grid gap-3 lg:grid-cols-[0.9fr_1.1fr]">
            <MagicBentoCard className="p-4" tone="teal">
              <p className="text-xs font-black uppercase tracking-normal text-ink-500">Provider mode</p>
              <p className="mt-2 text-2xl font-black text-ink-950">{formatLabel(displayedProviderMode)}</p>
              <p className="mt-1 text-sm font-semibold text-ink-500">
                {aiProviderStatus?.message ?? "AI provider status loads after company modules finish."}
              </p>
            </MagicBentoCard>
            <div className="febgrid-muted-surface rounded-lg p-4">
              <p className="text-sm font-bold text-ink-950">Provider safety</p>
              <div className="mt-3 grid gap-2 sm:grid-cols-2">
                <div className="rounded-lg border border-grid-200 bg-white/70 p-3">
                  <p className="text-xs font-black uppercase text-ink-500">Model</p>
                  <p className="mt-1 truncate text-sm font-black text-ink-950">{displayedModelName}</p>
                </div>
                <div className="rounded-lg border border-grid-200 bg-white/70 p-3">
                  <p className="text-xs font-black uppercase text-ink-500">Configured</p>
                  <Badge label={aiProviderStatus?.configured ? "Ready" : "Not configured"} tone={aiProviderStatus?.configured ? "green" : "amber"} />
                </div>
                <div className="rounded-lg border border-grid-200 bg-white/70 p-3">
                  <p className="text-xs font-black uppercase text-ink-500">AI enabled</p>
                  <Badge label={aiEnabled ? "Enabled" : "Disabled"} tone={aiEnabled ? "green" : "slate"} />
                </div>
                <div className="rounded-lg border border-grid-200 bg-white/70 p-3">
                  <p className="text-xs font-black uppercase text-ink-500">External processing</p>
                  <Badge label={externalProcessingAllowed ? "Allowed" : "Off"} tone={externalProcessingAllowed ? "amber" : "slate"} />
                </div>
              </div>
              <p className="mt-3 text-sm font-semibold text-ink-500">
                Groq is the current real AI provider target. Switching providers later should only require environment/config changes.
              </p>
            </div>
          </div>
          <div className="grid gap-3 lg:grid-cols-[1fr_1.2fr]">
            <div className="rounded-lg border border-grid-200 bg-white/70 p-4">
              <p className="text-sm font-black text-ink-950">Company AI controls</p>
              <p className="mt-1 text-sm font-semibold text-ink-500">
                External AI is never enabled silently. Company owners/admins must explicitly allow sanitized context to leave FebGrid.
              </p>
              <div className="mt-4 flex flex-wrap gap-2">
                <Button disabled={!canManage || isMutating || aiEnabled} onClick={() => void handleToggleAIEnabled(true)}>
                  Enable AI
                </Button>
                <Button disabled={!canManage || isMutating || !aiEnabled} onClick={() => void handleToggleAIEnabled(false)}>
                  Disable AI
                </Button>
                {externalProcessingAllowed ? (
                  <Button disabled={!canManage || isMutating} icon={<ShieldAlert className="size-4" aria-hidden="true" />} onClick={() => void disableExternalAI()}>
                    Disable external AI
                  </Button>
                ) : (
                  <Button disabled={!canManage || isMutating || !aiEnabled} icon={<ShieldAlert className="size-4" aria-hidden="true" />} onClick={() => setIsExternalAIWarningOpen(true)}>
                    Allow external AI
                  </Button>
                )}
              </div>
            </div>
            <div className="rounded-lg border border-grid-200 bg-white/70 p-4">
              <p className="text-sm font-bold text-ink-950">Capabilities prepared for Phase 3</p>
              <div className="mt-3 flex flex-wrap gap-2">
                {(data.aiCapabilities?.capabilities ?? []).map((capability) => (
                  <Badge key={capability.job_type} label={capability.label} tone={capability.mock_only ? "blue" : "teal"} />
                ))}
                {!data.aiCapabilities ? <Badge label="Mock provider" tone="slate" /> : null}
              </div>
              <p className="mt-3 text-sm font-semibold text-ink-500">
                Safe real jobs are text-only and server-prompted. Raw files, tokens, passwords, and prompt templates are not sent.
              </p>
            </div>
          </div>
          {data.aiJobs.length === 0 ? (
            <EmptyState description="Create a mock foundation job or generate work/project summaries to verify tenant-safe AI job storage, events, and notifications." title="No AI jobs yet" />
          ) : (
            <DataTable columns={aiJobColumns} rows={data.aiJobs} getRowKey={(job) => job.id} />
          )}
        </div>
      </SectionPanel>

      <div className="mt-6 grid gap-6 xl:grid-cols-[1fr_0.9fr]">
        <SectionPanel
          eyebrow="Work object engine"
          title="Work Object Types"
          action={
            <Button disabled={!canManage || !selectedCompany} icon={<Plus className="size-4" aria-hidden="true" />} onClick={() => openTypeModal()}>
              Add type
            </Button>
          }
        >
          {data.workObjectTypes.length === 0 ? (
            <EmptyState description="The default task type will be created automatically for each company." title="No types configured" />
          ) : (
            <DataTable columns={typeColumns} rows={[...data.workObjectTypes].sort((left, right) => left.sort_order - right.sort_order)} getRowKey={(type) => type.id} />
          )}
        </SectionPanel>

        <SectionPanel
          eyebrow="Custom fields"
          title="Type Fields"
          action={
            <Button disabled={!canManage || !selectedCompany || activeTypes.length === 0} icon={<Plus className="size-4" aria-hidden="true" />} onClick={() => openFieldModal()}>
              Add field
            </Button>
          }
        >
          <div className="space-y-4 p-5">
            <FieldShell label="Work object type">
              <SelectInput value={selectedTypeKey} onChange={(event) => setSelectedTypeKey(event.target.value)}>
                {activeTypes.map((type) => (
                  <option key={type.id} value={type.key}>
                    {type.name}
                  </option>
                ))}
              </SelectInput>
            </FieldShell>
          </div>
          {fieldsForSelectedType.length === 0 ? (
            <EmptyState description="Add simple optional fields for this work type." title="No custom fields yet" />
          ) : (
            <DataTable columns={fieldColumns} rows={fieldsForSelectedType} getRowKey={(field) => field.id} />
          )}
        </SectionPanel>
      </div>

      <Modal
        description="External AI processing can send selected, sanitized business context to the configured provider."
        isOpen={isExternalAIWarningOpen}
        title="Allow external AI processing?"
        onClose={() => setIsExternalAIWarningOpen(false)}
      >
        <div className="space-y-4 p-5">
          <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm font-semibold text-amber-900">
            FebGrid will only send server-built, text-only context for allowlisted jobs. Secrets, passwords, tokens, raw files, file paths, and API keys must never be sent.
          </div>
          <p className="text-sm font-semibold text-ink-600">
            Groq is the current real provider target. If `GROQ_API_KEY` is not configured locally, real jobs will fail safely without exposing any secret.
          </p>
          <div className="flex justify-end gap-2 border-t border-grid-200 pt-4">
            <Button onClick={() => setIsExternalAIWarningOpen(false)}>Cancel</Button>
            <Button disabled={isMutating} variant="primary" onClick={() => void confirmEnableExternalAI()}>
              I understand, allow
            </Button>
          </div>
        </div>
      </Modal>

      <Modal description="Update searchable file metadata. Storage and scan providers are intentionally not configurable here." isOpen={Boolean(editingFile)} title="Edit file metadata" onClose={() => setEditingFile(null)}>
        <form className="space-y-4 p-5" onSubmit={handleFileSubmit}>
          <FieldShell label="Description">
            <TextArea value={fileForm.description} onChange={(event) => setFileForm((current) => ({ ...current, description: event.target.value }))} />
          </FieldShell>
          <FieldShell label="Tags">
            <TextInput placeholder="invoice, receipt, proof" value={fileForm.tags} onChange={(event) => setFileForm((current) => ({ ...current, tags: event.target.value }))} />
          </FieldShell>
          {editingFile ? (
            <div className="febgrid-muted-surface rounded-lg px-4 py-3 text-sm font-semibold text-ink-600">
              {editingFile.original_file_name} / {formatFileSize(editingFile.file_size)} / {formatLabel(editingFile.processing_status)}
            </div>
          ) : null}
          {formError ? <p className="text-sm font-semibold text-rose-700">{formError}</p> : null}
          <div className="flex justify-end gap-2 border-t border-grid-200 pt-4">
            <Button onClick={() => setEditingFile(null)}>Cancel</Button>
            <Button disabled={isMutating} type="submit" variant="primary">
              {isMutating ? "Saving..." : "Save file"}
            </Button>
          </div>
        </form>
      </Modal>

      <Modal description="Configure a company-specific work object type." isOpen={isTypeModalOpen} title={editingType ? "Edit work type" : "Add work type"} onClose={() => setIsTypeModalOpen(false)}>
        <form className="space-y-4 p-5" onSubmit={handleTypeSubmit}>
          <div className="grid gap-4 sm:grid-cols-2">
            <FieldShell label="Name">
              <TextInput required value={typeForm.name} onChange={(event) => setTypeForm((current) => ({ ...current, name: event.target.value, key: current.key || slugify(event.target.value) }))} />
            </FieldShell>
            <FieldShell label="Key">
              <TextInput disabled={Boolean(editingType)} required value={typeForm.key} onChange={(event) => setTypeForm((current) => ({ ...current, key: slugify(event.target.value) }))} />
            </FieldShell>
            <FieldShell label="Color token">
              <TextInput placeholder="blue, green, amber" value={typeForm.color} onChange={(event) => setTypeForm((current) => ({ ...current, color: event.target.value }))} />
            </FieldShell>
            <FieldShell label="Sort order">
              <TextInput type="number" value={typeForm.sort_order} onChange={(event) => setTypeForm((current) => ({ ...current, sort_order: event.target.value }))} />
            </FieldShell>
          </div>
          <FieldShell label="Description">
            <TextArea value={typeForm.description} onChange={(event) => setTypeForm((current) => ({ ...current, description: event.target.value }))} />
          </FieldShell>
          <label className="febgrid-muted-surface flex items-center gap-2 rounded-md px-3 py-2 text-sm font-semibold text-ink-700">
            <input checked={typeForm.is_default} type="checkbox" onChange={(event) => setTypeForm((current) => ({ ...current, is_default: event.target.checked }))} />
            Make default type
          </label>
          {formError ? <p className="text-sm font-semibold text-rose-700">{formError}</p> : null}
          <div className="flex justify-end gap-2 border-t border-grid-200 pt-4">
            <Button onClick={() => setIsTypeModalOpen(false)}>Cancel</Button>
            <Button disabled={isMutating} type="submit" variant="primary">
              {isMutating ? "Saving..." : "Save type"}
            </Button>
          </div>
        </form>
      </Modal>

      <Modal description={`Configure fields for ${formatLabel(selectedTypeKey)} work.`} isOpen={isFieldModalOpen} title={editingField ? "Edit custom field" : "Add custom field"} onClose={() => setIsFieldModalOpen(false)}>
        <form className="space-y-4 p-5" onSubmit={handleFieldSubmit}>
          <div className="grid gap-4 sm:grid-cols-2">
            <FieldShell label="Label">
              <TextInput required value={fieldForm.label} onChange={(event) => setFieldForm((current) => ({ ...current, label: event.target.value, field_key: current.field_key || slugify(event.target.value) }))} />
            </FieldShell>
            <FieldShell label="Field key">
              <TextInput disabled={Boolean(editingField)} required value={fieldForm.field_key} onChange={(event) => setFieldForm((current) => ({ ...current, field_key: slugify(event.target.value) }))} />
            </FieldShell>
            <FieldShell label="Field type">
              <SelectInput value={fieldForm.field_type} onChange={(event) => setFieldForm((current) => ({ ...current, field_type: event.target.value as CustomFieldType }))}>
                {fieldTypes.map((fieldType) => (
                  <option key={fieldType} value={fieldType}>
                    {formatLabel(fieldType)}
                  </option>
                ))}
              </SelectInput>
            </FieldShell>
            <FieldShell label="Sort order">
              <TextInput type="number" value={fieldForm.sort_order} onChange={(event) => setFieldForm((current) => ({ ...current, sort_order: event.target.value }))} />
            </FieldShell>
            <FieldShell label="Options">
              <TextInput placeholder="low, medium, high" value={fieldForm.options} onChange={(event) => setFieldForm((current) => ({ ...current, options: event.target.value }))} />
            </FieldShell>
            <FieldShell label="Default value">
              <TextInput value={fieldForm.default_value} onChange={(event) => setFieldForm((current) => ({ ...current, default_value: event.target.value }))} />
            </FieldShell>
          </div>
          <FieldShell label="Help text">
            <TextArea value={fieldForm.help_text} onChange={(event) => setFieldForm((current) => ({ ...current, help_text: event.target.value }))} />
          </FieldShell>
          <label className="febgrid-muted-surface flex items-center gap-2 rounded-md px-3 py-2 text-sm font-semibold text-ink-700">
            <input checked={fieldForm.required} type="checkbox" onChange={(event) => setFieldForm((current) => ({ ...current, required: event.target.checked }))} />
            Required field
          </label>
          {formError ? <p className="text-sm font-semibold text-rose-700">{formError}</p> : null}
          <div className="flex justify-end gap-2 border-t border-grid-200 pt-4">
            <Button onClick={() => setIsFieldModalOpen(false)}>Cancel</Button>
            <Button disabled={isMutating} type="submit" variant="primary">
              {isMutating ? "Saving..." : "Save field"}
            </Button>
          </div>
        </form>
      </Modal>
    </>
  );
}
