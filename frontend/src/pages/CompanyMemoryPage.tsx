import { Archive, CheckCircle2, Edit3, Plus, RefreshCw, XCircle } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";

import { api } from "../services/api";
import type {
  AuthUser,
  Company,
  CompanyMemory,
  CompanyMemoryCreatePayload,
  CompanyMemoryImportance,
  CompanyMemoryStatus,
  CompanyMemoryVisibility,
} from "../types/api";
import { formatLabel, formatTime } from "../utils/format";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { FieldShell, SelectInput, TextArea, TextInput } from "../components/ui/FormControls";
import { Modal } from "../components/ui/Modal";
import { SectionPanel } from "../components/ui/SectionPanel";
import { EmptyState, ErrorState, LoadingState } from "../components/ui/States";

interface CompanyMemoryPageProps {
  selectedCompany: Company | null;
  currentUserRole: AuthUser["role"] | null;
}

const memoryTypeOptions = [
  "general_note",
  "decision",
  "policy",
  "process",
  "project_context",
  "work_context",
  "file_insight",
  "company_brief",
  "risk",
  "operational_fact",
];

const statusOptions: CompanyMemoryStatus[] = ["draft", "suggested", "approved", "rejected", "archived"];
const importanceOptions: CompanyMemoryImportance[] = ["low", "normal", "high", "critical"];
const visibilityOptions: CompanyMemoryVisibility[] = ["owner_admin", "manager_hr", "team", "project_members", "employee_self", "company"];

interface MemoryFormState {
  title: string;
  memory_type: string;
  content: string;
  summary: string;
  tags: string;
  importance: CompanyMemoryImportance;
  status: CompanyMemoryStatus;
  visibility: CompanyMemoryVisibility;
}

function initialForm(): MemoryFormState {
  return {
    title: "",
    memory_type: "general_note",
    content: "",
    summary: "",
    tags: "",
    importance: "normal",
    status: "suggested",
    visibility: "owner_admin",
  };
}

function statusTone(status: CompanyMemoryStatus): "blue" | "green" | "amber" | "red" | "slate" {
  if (status === "approved") return "green";
  if (status === "suggested") return "amber";
  if (status === "rejected") return "red";
  if (status === "archived") return "slate";
  return "blue";
}

function importanceTone(importance: CompanyMemoryImportance): "blue" | "green" | "amber" | "red" | "slate" {
  if (importance === "critical") return "red";
  if (importance === "high") return "amber";
  if (importance === "low") return "slate";
  return "blue";
}

function parseTags(value: string): string[] {
  return value
    .split(",")
    .map((tag) => tag.trim())
    .filter(Boolean)
    .slice(0, 12);
}

function formFromMemory(memory: CompanyMemory): MemoryFormState {
  return {
    title: memory.title,
    memory_type: memory.memory_type,
    content: memory.content,
    summary: memory.summary ?? "",
    tags: memory.tags.join(", "),
    importance: memory.importance,
    status: memory.status,
    visibility: memory.visibility,
  };
}

export function CompanyMemoryPage({ selectedCompany, currentUserRole }: CompanyMemoryPageProps): JSX.Element {
  const [memories, setMemories] = useState<CompanyMemory[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const [importanceFilter, setImportanceFilter] = useState("");
  const [form, setForm] = useState<MemoryFormState>(() => initialForm());
  const [editingMemory, setEditingMemory] = useState<CompanyMemory | null>(null);
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [isMutating, setIsMutating] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);

  const canManageMemory = currentUserRole === "company_owner" || currentUserRole === "admin";

  const loadMemories = useCallback(async (): Promise<void> => {
    if (!selectedCompany) return;
    setIsLoading(true);
    setError(null);
    try {
      const nextMemories = await api.companyMemory(selectedCompany.id, {
        q: query,
        status: statusFilter,
        memory_type: typeFilter,
        importance: importanceFilter,
        limit: 100,
      });
      setMemories(nextMemories);
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Unable to load Company Memory.");
    } finally {
      setIsLoading(false);
    }
  }, [importanceFilter, query, selectedCompany, statusFilter, typeFilter]);

  useEffect(() => {
    void loadMemories();
  }, [loadMemories]);

  const counts = useMemo(
    () => ({
      approved: memories.filter((memory) => memory.status === "approved").length,
      suggested: memories.filter((memory) => memory.status === "suggested").length,
      important: memories.filter((memory) => memory.status === "approved" && ["high", "critical"].includes(memory.importance)).length,
    }),
    [memories],
  );

  function openCreateModal(): void {
    setEditingMemory(null);
    setForm(initialForm());
    setIsFormOpen(true);
  }

  function openEditModal(memory: CompanyMemory): void {
    setEditingMemory(memory);
    setForm(formFromMemory(memory));
    setIsFormOpen(true);
  }

  function closeForm(): void {
    if (isMutating) return;
    setIsFormOpen(false);
    setEditingMemory(null);
  }

  async function handleSubmit(): Promise<void> {
    if (!selectedCompany) return;
    setIsMutating(true);
    setNotice(null);
    try {
      if (editingMemory) {
        await api.updateCompanyMemory(editingMemory.id, selectedCompany.id, {
          title: form.title,
          memory_type: form.memory_type,
          content: form.content,
          summary: form.summary || null,
          tags: parseTags(form.tags),
          importance: form.importance,
          visibility: form.visibility,
        });
        setNotice("Memory updated.");
      } else {
        const payload: CompanyMemoryCreatePayload = {
          company_id: selectedCompany.id,
          title: form.title,
          memory_type: form.memory_type,
          scope_type: "company",
          content: form.content,
          summary: form.summary || null,
          tags: parseTags(form.tags),
          importance: form.importance,
          status: form.status,
          visibility: form.visibility,
          source_type: "manual",
          metadata: { created_from: "memory_page" },
        };
        await api.createCompanyMemory(payload);
        setNotice(form.status === "approved" ? "Memory saved and approved." : "Memory saved for review.");
      }
      setIsFormOpen(false);
      setEditingMemory(null);
      await loadMemories();
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Unable to save Company Memory.");
    } finally {
      setIsMutating(false);
    }
  }

  async function handleApprove(memory: CompanyMemory): Promise<void> {
    if (!selectedCompany) return;
    setIsMutating(true);
    try {
      await api.approveCompanyMemory(memory.id, selectedCompany.id);
      setNotice("Memory approved.");
      await loadMemories();
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Unable to approve memory.");
    } finally {
      setIsMutating(false);
    }
  }

  async function handleReject(memory: CompanyMemory): Promise<void> {
    if (!selectedCompany || !window.confirm("Reject this memory suggestion?")) return;
    setIsMutating(true);
    try {
      await api.rejectCompanyMemory(memory.id, selectedCompany.id);
      setNotice("Memory rejected.");
      await loadMemories();
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Unable to reject memory.");
    } finally {
      setIsMutating(false);
    }
  }

  async function handleArchive(memory: CompanyMemory): Promise<void> {
    if (!selectedCompany || !window.confirm("Archive this memory entry?")) return;
    setIsMutating(true);
    try {
      await api.archiveCompanyMemory(memory.id, selectedCompany.id);
      setNotice("Memory archived.");
      await loadMemories();
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Unable to archive memory.");
    } finally {
      setIsMutating(false);
    }
  }

  if (!selectedCompany) {
    return (
      <EmptyState
        title="No company selected"
        description="Select a company before opening Company Memory."
      />
    );
  }

  if (!canManageMemory) {
    return <ErrorState message="Company Memory management is currently limited to owner/admin users." />;
  }

  const emptyFiltered = !isLoading && !error && memories.length === 0;

  return (
    <div className="space-y-6">
      <SectionPanel
        eyebrow={selectedCompany.name}
        title="Company Memory"
        description="Reviewable, source-linked company knowledge for decisions, facts, summaries, and operational context."
        action={
          <div className="flex flex-wrap gap-2">
            <Button
              title="Refresh Company Memory"
              aria-label="Refresh Company Memory"
              icon={<RefreshCw className="size-4" aria-hidden="true" />}
              onClick={() => void loadMemories()}
            >
              Refresh
            </Button>
            <Button
              title="Create memory"
              aria-label="Create memory"
              icon={<Plus className="size-4" aria-hidden="true" />}
              variant="primary"
              onClick={openCreateModal}
            >
              Create memory
            </Button>
          </div>
        }
      >
        <div className="grid gap-3 border-b border-grid-200 p-5 md:grid-cols-3">
          <MemoryStat label="Approved memories" value={counts.approved} />
          <MemoryStat label="Pending suggestions" value={counts.suggested} />
          <MemoryStat label="Important memories" value={counts.important} />
        </div>
        <div className="grid gap-3 border-b border-grid-200 p-5 lg:grid-cols-4">
          <FieldShell label="Search">
            <TextInput value={query} placeholder="Decision, policy, project, source" onChange={(event) => setQuery(event.target.value)} />
          </FieldShell>
          <FieldShell label="Status">
            <SelectInput value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}>
              <option value="">All statuses</option>
              {statusOptions.map((status) => (
                <option key={status} value={status}>
                  {formatLabel(status)}
                </option>
              ))}
            </SelectInput>
          </FieldShell>
          <FieldShell label="Type">
            <SelectInput value={typeFilter} onChange={(event) => setTypeFilter(event.target.value)}>
              <option value="">All types</option>
              {memoryTypeOptions.map((memoryType) => (
                <option key={memoryType} value={memoryType}>
                  {formatLabel(memoryType)}
                </option>
              ))}
            </SelectInput>
          </FieldShell>
          <FieldShell label="Importance">
            <SelectInput value={importanceFilter} onChange={(event) => setImportanceFilter(event.target.value)}>
              <option value="">All importance</option>
              {importanceOptions.map((importance) => (
                <option key={importance} value={importance}>
                  {formatLabel(importance)}
                </option>
              ))}
            </SelectInput>
          </FieldShell>
        </div>

        {notice ? <p className="mx-5 mt-5 rounded-lg border border-green-200 bg-green-50 px-4 py-3 text-sm font-bold text-green-700">{notice}</p> : null}
        {isLoading ? <LoadingState label="Loading Company Memory" /> : null}
        {error ? <ErrorState message={error} onRetry={() => void loadMemories()} /> : null}
        {emptyFiltered ? (
          <EmptyState
            title="No memory entries yet"
            description="Create a manual memory or save AI summaries into Company Memory for owner/admin review."
            action={
              <Button title="Create memory" aria-label="Create memory" icon={<Plus className="size-4" aria-hidden="true" />} onClick={openCreateModal}>
                Create memory
              </Button>
            }
          />
        ) : null}

        {!isLoading && !error && memories.length > 0 ? (
          <div className="divide-y divide-grid-200">
            {memories.map((memory) => (
              <article key={memory.id} className="grid gap-4 p-5 xl:grid-cols-[minmax(0,1fr)_auto]">
                <div className="min-w-0 space-y-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge label={formatLabel(memory.status)} tone={statusTone(memory.status)} />
                    <Badge label={formatLabel(memory.memory_type)} tone="blue" />
                    <Badge label={formatLabel(memory.importance)} tone={importanceTone(memory.importance)} />
                    <Badge label={formatLabel(memory.visibility)} tone="slate" />
                  </div>
                  <div>
                    <h3 className="text-base font-black text-ink-950">{memory.title}</h3>
                    <p className="mt-1 max-w-3xl text-sm font-semibold leading-6 text-ink-600">
                      {memory.summary || memory.content}
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2 text-xs font-bold text-ink-500">
                    <span>Scope: {formatLabel(memory.scope_type)}</span>
                    {memory.source_type ? <span>Source: {formatLabel(memory.source_type)}</span> : null}
                    <span>Updated {formatTime(memory.updated_at)}</span>
                  </div>
                  {memory.tags.length > 0 ? (
                    <div className="flex flex-wrap gap-2">
                      {memory.tags.map((tag) => (
                        <Badge key={tag} label={tag} tone="teal" />
                      ))}
                    </div>
                  ) : null}
                </div>
                <div className="flex flex-wrap items-start gap-2 xl:justify-end">
                  <Button
                    title="Edit memory"
                    aria-label="Edit memory"
                    icon={<Edit3 className="size-4" aria-hidden="true" />}
                    onClick={() => openEditModal(memory)}
                  >
                    Edit
                  </Button>
                  {memory.status === "suggested" ? (
                    <>
                      <Button
                        title="Approve memory"
                        aria-label="Approve memory"
                        icon={<CheckCircle2 className="size-4" aria-hidden="true" />}
                        variant="primary"
                        disabled={isMutating}
                        onClick={() => void handleApprove(memory)}
                      >
                        Approve
                      </Button>
                      <Button
                        title="Reject memory"
                        aria-label="Reject memory"
                        icon={<XCircle className="size-4" aria-hidden="true" />}
                        variant="danger"
                        disabled={isMutating}
                        onClick={() => void handleReject(memory)}
                      >
                        Reject
                      </Button>
                    </>
                  ) : null}
                  {memory.status !== "archived" ? (
                    <Button
                      title="Archive memory"
                      aria-label="Archive memory"
                      icon={<Archive className="size-4" aria-hidden="true" />}
                      variant="danger"
                      disabled={isMutating}
                      onClick={() => void handleArchive(memory)}
                    >
                      Archive
                    </Button>
                  ) : null}
                </div>
              </article>
            ))}
          </div>
        ) : null}
      </SectionPanel>

      <Modal
        title={editingMemory ? "Edit memory" : "Create memory"}
        description="Keep entries concise, source-linked where possible, and free of secrets or raw prompts."
        isOpen={isFormOpen}
        onClose={closeForm}
      >
        <div className="space-y-4 p-5">
          <FieldShell label="Title">
            <TextInput value={form.title} onChange={(event) => setForm((current) => ({ ...current, title: event.target.value }))} />
          </FieldShell>
          <div className="grid gap-4 md:grid-cols-3">
            <FieldShell label="Type">
              <SelectInput value={form.memory_type} onChange={(event) => setForm((current) => ({ ...current, memory_type: event.target.value }))}>
                {memoryTypeOptions.map((memoryType) => (
                  <option key={memoryType} value={memoryType}>
                    {formatLabel(memoryType)}
                  </option>
                ))}
              </SelectInput>
            </FieldShell>
            <FieldShell label="Importance">
              <SelectInput
                value={form.importance}
                onChange={(event) => setForm((current) => ({ ...current, importance: event.target.value as CompanyMemoryImportance }))}
              >
                {importanceOptions.map((importance) => (
                  <option key={importance} value={importance}>
                    {formatLabel(importance)}
                  </option>
                ))}
              </SelectInput>
            </FieldShell>
            {!editingMemory ? (
              <FieldShell label="Status">
                <SelectInput value={form.status} onChange={(event) => setForm((current) => ({ ...current, status: event.target.value as CompanyMemoryStatus }))}>
                  <option value="suggested">Suggested</option>
                  <option value="approved">Approve and save</option>
                  <option value="draft">Draft</option>
                </SelectInput>
              </FieldShell>
            ) : (
              <FieldShell label="Visibility">
                <SelectInput
                  value={form.visibility}
                  onChange={(event) => setForm((current) => ({ ...current, visibility: event.target.value as CompanyMemoryVisibility }))}
                >
                  {visibilityOptions.map((visibility) => (
                    <option key={visibility} value={visibility}>
                      {formatLabel(visibility)}
                    </option>
                  ))}
                </SelectInput>
              </FieldShell>
            )}
          </div>
          {!editingMemory ? (
            <FieldShell label="Visibility">
              <SelectInput
                value={form.visibility}
                onChange={(event) => setForm((current) => ({ ...current, visibility: event.target.value as CompanyMemoryVisibility }))}
              >
                {visibilityOptions.map((visibility) => (
                  <option key={visibility} value={visibility}>
                    {formatLabel(visibility)}
                  </option>
                ))}
              </SelectInput>
            </FieldShell>
          ) : null}
          <FieldShell label="Summary">
            <TextArea
              value={form.summary}
              placeholder="Short, readable memory summary"
              onChange={(event) => setForm((current) => ({ ...current, summary: event.target.value }))}
            />
          </FieldShell>
          <FieldShell label="Content">
            <TextArea
              value={form.content}
              placeholder="Decision, context, operational fact, policy, or lesson learned"
              onChange={(event) => setForm((current) => ({ ...current, content: event.target.value }))}
            />
          </FieldShell>
          <FieldShell label="Tags" helperText="Comma-separated tags, up to 12.">
            <TextInput value={form.tags} placeholder="operations, project, policy" onChange={(event) => setForm((current) => ({ ...current, tags: event.target.value }))} />
          </FieldShell>
          <div className="flex justify-end gap-2 border-t border-grid-200 pt-4">
            <Button onClick={closeForm}>Cancel</Button>
            <Button
              title={editingMemory ? "Save memory" : "Create memory"}
              aria-label={editingMemory ? "Save memory" : "Create memory"}
              disabled={isMutating || !form.title.trim() || !form.content.trim()}
              variant="primary"
              onClick={() => void handleSubmit()}
            >
              {isMutating ? "Saving..." : editingMemory ? "Save memory" : "Create memory"}
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}

function MemoryStat({ label, value }: { label: string; value: number }): JSX.Element {
  return (
    <div className="rounded-lg border border-grid-200 bg-grid-50 p-4">
      <p className="text-xs font-black uppercase tracking-normal text-ink-500">{label}</p>
      <p className="mt-2 text-2xl font-black text-ink-950">{value}</p>
    </div>
  );
}
