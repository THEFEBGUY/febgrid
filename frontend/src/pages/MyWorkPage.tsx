import { CheckCircle2, Download, Eye, FileSearch, ImageIcon, Mic, Sparkles, Upload } from "lucide-react";
import { type FormEvent, useCallback, useMemo, useState } from "react";

import { AISummaryPanel } from "../components/ai/AISummaryPanel";
import { CommentsSection } from "../components/communication/CommentsSection";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { DataTable, type DataTableColumn } from "../components/ui/DataTable";
import { FieldShell, SelectInput, TextInput } from "../components/ui/FormControls";
import { Modal } from "../components/ui/Modal";
import { ModuleBoundary } from "../components/ui/ModuleBoundary";
import { SectionPanel } from "../components/ui/SectionPanel";
import { EmptyState, ErrorState, LoadingState } from "../components/ui/States";
import { priorityTone, statusTone } from "../components/ui/tone";
import { api } from "../services/api";
import { aiJobTerminalError, pollAIJob } from "../services/aiJobPolling";
import type { AIJob, Attachment, Event as FebGridEvent, WorkObject } from "../types/api";
import type { ModulePageProps } from "../types/page";
import { isSupportedAudioAttachment, isSupportedImageAttachment } from "../utils/files";
import { compactList, formatDate, formatLabel, formatTime } from "../utils/format";

interface MyWorkPageProps extends ModulePageProps {
  onCompleteWorkObject: (workObjectId: string) => Promise<void>;
  onUpdateWorkObjectStatus: (workObjectId: string, status: string) => Promise<void>;
}

const statusOptions = ["assigned", "in_progress", "under_review", "blocked", "completed", "cancelled"];

function formatBytes(value: number | null): string {
  if (value === null) return "Unknown size";
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
  return `${(value / (1024 * 1024)).toFixed(1)} MB`;
}

export function MyWorkPage({
  data,
  selectedCompany,
  isLoadingModules,
  isMutating,
  moduleError,
  onRetry,
  onCompleteWorkObject,
  onUpdateWorkObjectStatus,
}: MyWorkPageProps): JSX.Element {
  const selectedCompanyId = selectedCompany?.id ?? null;
  const [detailWorkObject, setDetailWorkObject] = useState<WorkObject | null>(null);
  const [detailEvents, setDetailEvents] = useState<FebGridEvent[]>([]);
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const [isDetailLoading, setIsDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [aiSummary, setAISummary] = useState<AIJob | null>(null);
  const [isAISummaryLoading, setIsAISummaryLoading] = useState(false);
  const [isAISummaryGenerating, setIsAISummaryGenerating] = useState(false);
  const [aiSummaryError, setAISummaryError] = useState<string | null>(null);
  const [isSavingWorkMemory, setIsSavingWorkMemory] = useState(false);
  const [workMemoryMessage, setWorkMemoryMessage] = useState<string | null>(null);
  const [workMemoryError, setWorkMemoryError] = useState<string | null>(null);
  const [fileSummaryAttachment, setFileSummaryAttachment] = useState<Attachment | null>(null);
  const [fileAIInsightMode, setFileAIInsightMode] = useState<"summary" | "analysis" | "image" | "audio">("summary");
  const [fileAISummary, setFileAISummary] = useState<AIJob | null>(null);
  const [isFileAISummaryLoading, setIsFileAISummaryLoading] = useState(false);
  const [isFileAISummaryGenerating, setIsFileAISummaryGenerating] = useState(false);
  const [fileAISummaryError, setFileAISummaryError] = useState<string | null>(null);
  const [isSavingFileMemory, setIsSavingFileMemory] = useState(false);
  const [fileMemoryMessage, setFileMemoryMessage] = useState<string | null>(null);
  const [fileMemoryError, setFileMemoryError] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [fileDescription, setFileDescription] = useState("");
  const [fileInputKey, setFileInputKey] = useState(0);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const mentionEmployees = useMemo(() => {
    const employeesById = new Map(data.employees.map((employee) => [employee.id, employee]));
    data.leaveApprovers.forEach((employee) => employeesById.set(employee.id, employee));
    return Array.from(employeesById.values());
  }, [data.employees, data.leaveApprovers]);
  const employeeNames = useMemo(() => Object.fromEntries(mentionEmployees.map((employee) => [employee.id, employee.full_name])), [mentionEmployees]);
  const visibleWorkObjects = useMemo(() => data.workObjects.filter((workObject) => workObject.is_active), [data.workObjects]);

  const loadDetail = useCallback(
    async (workObjectId: string): Promise<void> => {
      if (!selectedCompanyId) return;
      setIsDetailLoading(true);
      setIsAISummaryLoading(true);
      setDetailError(null);
      setAISummaryError(null);
      setWorkMemoryMessage(null);
      setWorkMemoryError(null);
      try {
        const [eventsResult, attachmentsResult, summaryResult] = await Promise.allSettled([
          api.workObjectTimeline(workObjectId, selectedCompanyId),
          api.workObjectAttachments(workObjectId, selectedCompanyId),
          api.latestWorkObjectAISummary(workObjectId, selectedCompanyId),
        ]);
        if (eventsResult.status === "fulfilled") setDetailEvents(eventsResult.value);
        else setDetailError("Unable to load this work object's timeline.");
        if (attachmentsResult.status === "fulfilled") setAttachments(attachmentsResult.value);
        else setDetailError("Unable to load this work object's files.");
        if (summaryResult.status === "fulfilled") setAISummary(summaryResult.value);
        else setAISummaryError("Unable to load the latest AI summary.");
      } finally {
        setIsDetailLoading(false);
        setIsAISummaryLoading(false);
      }
    },
    [selectedCompanyId],
  );

  function openDetail(workObject: WorkObject): void {
    setDetailWorkObject(workObject);
    setDetailEvents([]);
    setAttachments([]);
    setDetailError(null);
    setAISummary(null);
    setAISummaryError(null);
    setWorkMemoryMessage(null);
    setWorkMemoryError(null);
    setFileSummaryAttachment(null);
    setFileAISummary(null);
    setFileAISummaryError(null);
    setFileMemoryMessage(null);
    setFileMemoryError(null);
    setSelectedFile(null);
    setFileDescription("");
    setUploadError(null);
    setFileInputKey((current) => current + 1);
    void loadDetail(workObject.id);
  }

  async function handleGenerateAISummary(): Promise<void> {
    if (!detailWorkObject || !selectedCompanyId) return;
    setIsAISummaryGenerating(true);
    setAISummaryError(null);
    try {
      const job = await api.generateWorkObjectAISummary(detailWorkObject.id, selectedCompanyId);
      setAISummary(job);
      const completedJob = await pollAIJob(job, selectedCompanyId, { onUpdate: setAISummary });
      const terminalError = aiJobTerminalError(completedJob);
      if (terminalError) setAISummaryError(terminalError);
    } catch (caughtError) {
      setAISummaryError(caughtError instanceof Error ? caughtError.message : "AI summary could not be generated.");
    } finally {
      setIsAISummaryGenerating(false);
    }
  }

  async function loadFileAISummary(attachment: Attachment): Promise<void> {
    if (!selectedCompanyId) return;
    setFileSummaryAttachment(attachment);
    setFileAIInsightMode("summary");
    setIsFileAISummaryLoading(true);
    setFileAISummaryError(null);
    setFileMemoryMessage(null);
    setFileMemoryError(null);
    try {
      const job = await api.latestFileAISummary(attachment.id, selectedCompanyId);
      setFileAISummary(job);
    } catch (caughtError) {
      setFileAISummaryError(caughtError instanceof Error ? caughtError.message : "Unable to load the latest file summary.");
    } finally {
      setIsFileAISummaryLoading(false);
    }
  }

  async function loadFileAIAnalysis(attachment: Attachment): Promise<void> {
    if (!selectedCompanyId) return;
    setFileSummaryAttachment(attachment);
    setFileAIInsightMode("analysis");
    setIsFileAISummaryLoading(true);
    setFileAISummaryError(null);
    setFileMemoryMessage(null);
    setFileMemoryError(null);
    try {
      const job = await api.latestFileAIAnalysis(attachment.id, selectedCompanyId);
      setFileAISummary(job);
    } catch (caughtError) {
      setFileAISummaryError(caughtError instanceof Error ? caughtError.message : "Unable to load the latest document analysis.");
    } finally {
      setIsFileAISummaryLoading(false);
    }
  }

  async function loadFileAIImageAnalysis(attachment: Attachment): Promise<void> {
    if (!selectedCompanyId) return;
    setFileSummaryAttachment(attachment);
    setFileAIInsightMode("image");
    setIsFileAISummaryLoading(true);
    setFileAISummaryError(null);
    setFileMemoryMessage(null);
    setFileMemoryError(null);
    try {
      const job = await api.latestFileAIImageAnalysis(attachment.id, selectedCompanyId);
      setFileAISummary(job);
    } catch (caughtError) {
      setFileAISummaryError(caughtError instanceof Error ? caughtError.message : "Unable to load the latest image analysis.");
    } finally {
      setIsFileAISummaryLoading(false);
    }
  }

  async function loadFileAITranscription(attachment: Attachment): Promise<void> {
    if (!selectedCompanyId) return;
    setFileSummaryAttachment(attachment);
    setFileAIInsightMode("audio");
    setIsFileAISummaryLoading(true);
    setFileAISummaryError(null);
    setFileMemoryMessage(null);
    setFileMemoryError(null);
    try {
      const job = await api.latestFileAITranscription(attachment.id, selectedCompanyId);
      setFileAISummary(job);
    } catch (caughtError) {
      setFileAISummaryError(caughtError instanceof Error ? caughtError.message : "Unable to load the latest audio transcription.");
    } finally {
      setIsFileAISummaryLoading(false);
    }
  }

  async function handleGenerateFileAISummary(): Promise<void> {
    if (!fileSummaryAttachment || !selectedCompanyId) return;
    setIsFileAISummaryGenerating(true);
    setFileAISummaryError(null);
    try {
      const job =
        fileAIInsightMode === "audio"
          ? await api.generateFileAITranscription(fileSummaryAttachment.id, selectedCompanyId)
          : fileAIInsightMode === "image"
          ? await api.generateFileAIImageAnalysis(fileSummaryAttachment.id, selectedCompanyId)
          : fileAIInsightMode === "analysis"
          ? await api.generateFileAIAnalysis(fileSummaryAttachment.id, selectedCompanyId)
          : await api.generateFileAISummary(fileSummaryAttachment.id, selectedCompanyId);
      setFileAISummary(job);
      const completedJob = await pollAIJob(job, selectedCompanyId, { onUpdate: setFileAISummary });
      const terminalError = aiJobTerminalError(completedJob);
      if (terminalError) setFileAISummaryError(terminalError);
    } catch (caughtError) {
      setFileAISummaryError(
        caughtError instanceof Error
          ? caughtError.message
          : fileAIInsightMode === "audio"
            ? "AI audio transcription could not be generated."
            : fileAIInsightMode === "image"
            ? "AI image analysis could not be generated."
            : fileAIInsightMode === "analysis"
            ? "AI document analysis could not be generated."
            : "AI file summary could not be generated.",
      );
    } finally {
      setIsFileAISummaryGenerating(false);
    }
  }

  async function handleSuggestWorkMemory(): Promise<void> {
    if (!aiSummary || !selectedCompanyId || isSavingWorkMemory) return;
    setIsSavingWorkMemory(true);
    setWorkMemoryError(null);
    setWorkMemoryMessage(null);
    try {
      await api.createCompanyMemoryFromAIJob(aiSummary.id, {
        company_id: selectedCompanyId,
        memory_type: "work_context",
        importance: "normal",
        tags: ["work_context", "ai_summary"],
      });
      setWorkMemoryMessage("Work summary submitted to Company Memory for review.");
    } catch (caughtError) {
      setWorkMemoryError(caughtError instanceof Error ? caughtError.message : "Unable to suggest this work summary.");
    } finally {
      setIsSavingWorkMemory(false);
    }
  }

  async function handleSuggestFileMemory(): Promise<void> {
    if (!fileAISummary || !selectedCompanyId || isSavingFileMemory) return;
    setIsSavingFileMemory(true);
    setFileMemoryError(null);
    setFileMemoryMessage(null);
    try {
      await api.createCompanyMemoryFromAIJob(fileAISummary.id, {
        company_id: selectedCompanyId,
        memory_type: "file_insight",
        importance: "normal",
        tags:
          fileAIInsightMode === "audio"
            ? ["file_insight", "audio_transcription"]
            : fileAIInsightMode === "image"
              ? ["file_insight", "image_analysis"]
              : fileAIInsightMode === "analysis"
                ? ["file_insight", "document_analysis"]
                : ["file_insight", "ai_summary"],
      });
      setFileMemoryMessage(
        fileAIInsightMode === "audio"
          ? "Audio transcription submitted to Company Memory for review."
          : fileAIInsightMode === "image"
          ? "Image analysis submitted to Company Memory for review."
          : fileAIInsightMode === "analysis"
            ? "Document analysis submitted to Company Memory for review."
            : "File summary submitted to Company Memory for review.",
      );
    } catch (caughtError) {
      setFileMemoryError(caughtError instanceof Error ? caughtError.message : "Unable to suggest this file insight.");
    } finally {
      setIsSavingFileMemory(false);
    }
  }

  async function handleUploadAttachment(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (!selectedCompanyId || !detailWorkObject || !selectedFile) return;
    setIsUploading(true);
    setUploadError(null);
    try {
      await api.uploadWorkObjectAttachment(detailWorkObject.id, selectedCompanyId, selectedFile, fileDescription.trim() || null);
      setSelectedFile(null);
      setFileDescription("");
      setFileInputKey((current) => current + 1);
      await loadDetail(detailWorkObject.id);
    } catch {
      setUploadError("File could not be uploaded. Check the file type and size, then try again.");
    } finally {
      setIsUploading(false);
    }
  }

  async function handleDownloadAttachment(attachment: Attachment): Promise<void> {
    if (!selectedCompanyId) return;
    const blob = await api.downloadAttachment(attachment.id, selectedCompanyId);
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = attachment.original_file_name;
    link.click();
    window.URL.revokeObjectURL(url);
  }

  const columns: DataTableColumn<WorkObject>[] = [
    {
      key: "title",
      label: "Work",
      render: (workObject) => (
        <span className="min-w-56">
          <span className="block truncate font-bold text-ink-950">{workObject.title}</span>
          <span className="block truncate text-xs text-ink-500">{formatLabel(workObject.object_type)}</span>
        </span>
      ),
    },
    { key: "status", label: "Status", render: (workObject) => (
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
    ) },
    { key: "priority", label: "Priority", render: (workObject) => <Badge label={formatLabel(workObject.priority)} tone={priorityTone(workObject.priority)} /> },
    { key: "due", label: "Due", render: (workObject) => formatDate(workObject.due_date) },
    { key: "updated", label: "Updated", render: (workObject) => formatDate(workObject.updated_at) },
    {
      key: "actions",
      label: "Actions",
      render: (workObject) => (
        <div className="flex justify-end gap-2">
          <Button className="size-9 px-0" aria-label="View work details" icon={<Eye className="size-4" aria-hidden="true" />} title="View work details" onClick={() => openDetail(workObject)}>
            <span className="sr-only">View details</span>
          </Button>
          <Button
            className="size-9 px-0"
            aria-label="Complete work"
            disabled={isMutating || workObject.status === "completed" || !workObject.is_active}
            icon={<CheckCircle2 className="size-4" aria-hidden="true" />}
            title="Complete work"
            onClick={() => void onCompleteWorkObject(workObject.id)}
          >
            <span className="sr-only">Complete work</span>
          </Button>
        </div>
      ),
      className: "text-right",
    },
  ];

  return (
    <>
      <SectionPanel eyebrow={selectedCompany?.name ?? "My work"} title="My Work">
        <ModuleBoundary
          emptyDescription="Assigned work will appear here when your manager or team creates it."
          emptyTitle="No assigned work yet"
          error={moduleError}
          isEmpty={visibleWorkObjects.length === 0}
          isLoading={isLoadingModules}
          onRetry={onRetry}
        >
          <DataTable columns={columns} rows={visibleWorkObjects} getRowKey={(workObject) => workObject.id} />
        </ModuleBoundary>
      </SectionPanel>

      <Modal
        description="Your assigned work details, files, comments, and timeline."
        isOpen={Boolean(detailWorkObject)}
        title={detailWorkObject?.title ?? "Work details"}
        onClose={() => setDetailWorkObject(null)}
      >
        {detailWorkObject ? (
          <div className="space-y-5 p-5">
            <div className="grid gap-4 sm:grid-cols-2">
              <DetailItem label="Status" value={formatLabel(detailWorkObject.status)} tone={statusTone(detailWorkObject.status)} />
              <DetailItem label="Priority" value={formatLabel(detailWorkObject.priority)} tone={priorityTone(detailWorkObject.priority)} />
              <DetailItem label="Assignee" value={detailWorkObject.assignee_employee_id ? employeeNames[detailWorkObject.assignee_employee_id] ?? "Assigned to me" : "Unassigned"} />
              <DetailItem label="Dates" value={compactList([formatDate(detailWorkObject.start_date), `Due ${formatDate(detailWorkObject.due_date)}`])} />
            </div>

            {detailWorkObject.description ? <p className="febgrid-muted-surface rounded-lg p-4 text-sm font-medium text-ink-600">{detailWorkObject.description}</p> : null}

            <AISummaryPanel
              error={aiSummaryError}
              generateLabel="Generate AI Summary"
              isGenerating={isAISummaryGenerating}
              isLoading={isAISummaryLoading}
              isSavingToMemory={isSavingWorkMemory}
              job={aiSummary}
              kind="work_object"
              onGenerate={() => void handleGenerateAISummary()}
              onSaveToMemory={() => void handleSuggestWorkMemory()}
              saveToMemoryError={workMemoryError}
              saveToMemoryLabel="Suggest Memory"
              saveToMemoryMessage={workMemoryMessage}
            />

            <CommentsSection
              companyId={selectedCompanyId}
              employees={mentionEmployees}
              employeeNames={employeeNames}
              targetEntityId={detailWorkObject.id}
              targetEntityType="work_object"
              onChanged={() => void loadDetail(detailWorkObject.id)}
            />

            <section className="febgrid-surface overflow-hidden rounded-lg">
              <div className="border-b border-grid-200 bg-white/55 px-4 py-3">
                <h3 className="text-sm font-bold text-ink-950">Files</h3>
              </div>
              <form className="grid gap-3 border-b border-grid-100 p-4 lg:grid-cols-[1fr_1fr_auto]" onSubmit={handleUploadAttachment}>
                <FieldShell label="Attach file">
                  <input
                    key={fileInputKey}
                    accept=".png,.jpg,.jpeg,.webp,.pdf,.csv,.txt,.md,.json,.log,.doc,.docx,.xls,.xlsx,.mp3,.wav,.m4a,.webm,.ogg"
                    className="w-full rounded-lg border border-grid-200 bg-white px-3 py-2 text-sm font-semibold text-ink-700 file:mr-3 file:rounded-md file:border-0 file:bg-grid-100 file:px-3 file:py-1.5 file:text-xs file:font-bold file:text-ink-700 focus:border-brand-500 focus:outline-none focus:ring-4 focus:ring-brand-100"
                    type="file"
                    onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)}
                  />
                </FieldShell>
                <FieldShell label="Description">
                  <TextInput
                    placeholder="Optional file note"
                    value={fileDescription}
                    onChange={(event) => setFileDescription(event.target.value)}
                  />
                </FieldShell>
                <div className="flex items-end">
                  <Button
                    disabled={isUploading || !selectedFile}
                    type="submit"
                    variant="primary"
                    icon={<Upload className="size-4" aria-hidden="true" />}
                  >
                    {isUploading ? "Uploading..." : "Upload file"}
                  </Button>
                </div>
                {selectedFile ? <p className="text-xs font-semibold text-ink-500 lg:col-span-3">Selected: {selectedFile.name} ({formatBytes(selectedFile.size)})</p> : null}
                {uploadError ? <p className="text-sm font-semibold text-rose-700 lg:col-span-3">{uploadError}</p> : null}
              </form>
              {attachments.length === 0 ? (
                <EmptyState description="Files attached to your work will appear here." title="No files attached" />
              ) : (
                <div className="divide-y divide-grid-100">
                  {attachments.map((attachment) => (
                    <article key={attachment.id} className="flex flex-col gap-3 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
                      <div className="min-w-0">
                        <p className="truncate text-sm font-bold text-ink-950">{attachment.original_file_name}</p>
                        <p className="mt-1 text-xs font-semibold text-ink-500">{compactList([attachment.content_type ?? "Unknown type", formatBytes(attachment.file_size), formatDate(attachment.created_at)])}</p>
                      </div>
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
                        <Button
                          className="size-9 px-0"
                          aria-label={`Analyze document ${attachment.original_file_name}`}
                          icon={<FileSearch className="size-4" aria-hidden="true" />}
                          title={`Analyze document ${attachment.original_file_name}`}
                          onClick={() => void loadFileAIAnalysis(attachment)}
                        >
                          <span className="sr-only">Analyze document</span>
                        </Button>
                        {isSupportedImageAttachment(attachment) ? (
                          <Button
                            className="size-9 px-0"
                            aria-label={`Analyze image ${attachment.original_file_name}`}
                            icon={<ImageIcon className="size-4" aria-hidden="true" />}
                            title={`Analyze image ${attachment.original_file_name}`}
                            onClick={() => void loadFileAIImageAnalysis(attachment)}
                          >
                            <span className="sr-only">Analyze image</span>
                          </Button>
                        ) : null}
                        {isSupportedAudioAttachment(attachment) ? (
                          <Button
                            className="size-9 px-0"
                            aria-label={`Transcribe audio ${attachment.original_file_name}`}
                            icon={<Mic className="size-4" aria-hidden="true" />}
                            title={`Transcribe audio ${attachment.original_file_name}`}
                            onClick={() => void loadFileAITranscription(attachment)}
                          >
                            <span className="sr-only">Transcribe audio</span>
                          </Button>
                        ) : null}
                        <Button className="size-9 px-0" aria-label="Download file" icon={<Download className="size-4" aria-hidden="true" />} title="Download file" onClick={() => void handleDownloadAttachment(attachment)}>
                          <span className="sr-only">Download file</span>
                        </Button>
                      </div>
                    </article>
                  ))}
                </div>
              )}
              {fileSummaryAttachment ? (
                <div className="border-t border-grid-200 p-4">
                  <p className="mb-3 text-xs font-black uppercase tracking-normal text-ink-500">
                    {fileAIInsightMode === "audio" ? "Audio transcription" : fileAIInsightMode === "image" ? "Image analysis" : fileAIInsightMode === "analysis" ? "Document analysis" : "File summary"} / {fileSummaryAttachment.original_file_name}
                  </p>
                  <AISummaryPanel
                    error={fileAISummaryError}
                    generateLabel={fileAIInsightMode === "audio" ? "Transcribe Audio" : fileAIInsightMode === "image" ? "Analyze Image" : fileAIInsightMode === "analysis" ? "Analyze Document" : "Generate AI File Summary"}
                    isGenerating={isFileAISummaryGenerating}
                    isLoading={isFileAISummaryLoading}
                    isSavingToMemory={isSavingFileMemory}
                    job={fileAISummary}
                    kind={fileAIInsightMode === "audio" ? "audio" : fileAIInsightMode === "image" ? "image" : fileAIInsightMode === "analysis" ? "document" : "file"}
                    onGenerate={() => void handleGenerateFileAISummary()}
                    onSaveToMemory={() => void handleSuggestFileMemory()}
                    saveToMemoryError={fileMemoryError}
                    saveToMemoryLabel={fileAIInsightMode === "audio" ? "Suggest Transcription to Memory" : fileAIInsightMode === "image" || fileAIInsightMode === "analysis" ? "Suggest Analysis to Memory" : "Suggest Memory"}
                    saveToMemoryMessage={fileMemoryMessage}
                  />
                </div>
              ) : null}
            </section>

            {isDetailLoading ? <LoadingState label="Loading work details" /> : null}
            {detailError ? <ErrorState message={detailError} onRetry={() => loadDetail(detailWorkObject.id)} /> : null}
            {!isDetailLoading && !detailError ? (
              <section className="febgrid-surface overflow-hidden rounded-lg">
                <div className="border-b border-grid-200 bg-white/55 px-4 py-3">
                  <h3 className="text-sm font-bold text-ink-950">Recent activity</h3>
                </div>
                {detailEvents.length === 0 ? (
                  <EmptyState description="Work activity will appear here." title="No activity yet" />
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
    <div className="febgrid-muted-surface rounded-lg p-4">
      <p className="text-xs font-black uppercase tracking-normal text-ink-500">{label}</p>
      <div className="mt-2">{tone ? <Badge label={value} tone={tone} /> : <p className="text-sm font-bold text-ink-950">{value}</p>}</div>
    </div>
  );
}
