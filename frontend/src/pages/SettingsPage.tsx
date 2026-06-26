import { Archive, Pencil, Plus, Save, Wand2 } from "lucide-react";
import { type FormEvent, useEffect, useMemo, useState } from "react";

import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { DataTable, type DataTableColumn } from "../components/ui/DataTable";
import { FieldShell, SelectInput, TextArea, TextInput } from "../components/ui/FormControls";
import { Modal } from "../components/ui/Modal";
import { ModuleBoundary } from "../components/ui/ModuleBoundary";
import { SectionPanel } from "../components/ui/SectionPanel";
import { EmptyState } from "../components/ui/States";
import type {
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
import { formatDate, formatLabel } from "../utils/format";

interface SettingsPageProps extends ModulePageProps {
  currentUserRole: UserRole | null;
  onApplyIndustryTemplate: (templateKey: string) => Promise<void>;
  onArchiveCustomField: (fieldId: string) => Promise<void>;
  onArchiveWorkObjectType: (typeId: string) => Promise<void>;
  onCreateCustomField: (payload: Omit<CustomFieldCreatePayload, "company_id">) => Promise<void>;
  onCreateWorkObjectType: (payload: Omit<WorkObjectTypeCreatePayload, "company_id">) => Promise<void>;
  onUpdateCompanySettings: (payload: CompanySettingsUpdatePayload) => Promise<void>;
  onUpdateCustomField: (fieldId: string, payload: CustomFieldUpdatePayload) => Promise<void>;
  onUpdateWorkObjectType: (typeId: string, payload: WorkObjectTypeUpdatePayload) => Promise<void>;
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

export function SettingsPage({
  data,
  selectedCompany,
  isLoadingModules,
  moduleError,
  onRetry,
  isMutating,
  currentUserRole,
  onApplyIndustryTemplate,
  onArchiveCustomField,
  onArchiveWorkObjectType,
  onCreateCustomField,
  onCreateWorkObjectType,
  onUpdateCompanySettings,
  onUpdateCustomField,
  onUpdateWorkObjectType,
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
  const [formError, setFormError] = useState<string | null>(null);

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
            {settingsMessage ? <p className="rounded-lg border border-grid-200 bg-grid-50 px-4 py-3 text-sm font-semibold text-ink-700">{settingsMessage}</p> : null}

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

            <div className="rounded-lg border border-grid-200 p-4">
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
          <label className="flex items-center gap-2 rounded-md border border-grid-200 bg-grid-50 px-3 py-2 text-sm font-semibold text-ink-700">
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
          <label className="flex items-center gap-2 rounded-md border border-grid-200 bg-grid-50 px-3 py-2 text-sm font-semibold text-ink-700">
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
