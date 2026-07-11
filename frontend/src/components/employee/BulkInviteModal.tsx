import { AlertTriangle, CheckCircle2, Clipboard, Download, FileSpreadsheet, Send, Upload } from "lucide-react";
import { type ChangeEvent, type DragEvent, useEffect, useMemo, useState } from "react";

import { api, ApiError } from "../../services/api";
import type { BulkInviteConfirmResult, BulkInvitePreview, BulkInvitePreviewRow } from "../../types/api";
import { Button } from "../ui/Button";
import { Modal } from "../ui/Modal";
import { Badge } from "../ui/Badge";

type Step = "upload" | "preview" | "results";
type PreviewFilter = "all" | "ready" | "attention";

interface BulkInviteModalProps {
  companyId: string | null;
  isOpen: boolean;
  onClose: () => void;
  onCompleted: () => Promise<void>;
}

function createIdempotencyKey(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") return crypto.randomUUID();
  return `bulk-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

function safeCsvCell(value: string | number): string {
  const text = String(value).replace(/\r?\n/g, " ");
  const neutralized = /^[=+\-@]/.test(text) ? `'${text}` : text;
  return `"${neutralized.replace(/"/g, '""')}"`;
}

function downloadBlob(blob: Blob, fileName: string): void {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = fileName;
  anchor.click();
  window.setTimeout(() => URL.revokeObjectURL(url), 0);
}

function errorMessage(error: unknown): string {
  if (!(error instanceof ApiError)) return "Bulk invitation could not be completed. Please try again.";
  const messages: Record<string, string> = {
    BULK_INVITE_SERVICE_UNAVAILABLE: "The local CSV validation service is not available. Start it and try again.",
    BULK_INVITE_SERVICE_ERROR: "The CSV validation service could not validate this file. Please try again.",
    BULK_INVITE_PREVIEW_MISMATCH: "This preview is no longer valid. Upload the CSV again to refresh it.",
    BULK_INVITE_CONFIRMATION_IN_PROGRESS: "This CSV confirmation is already being processed. Please wait a moment.",
    BULK_INVITE_INTERNAL_ERROR: "FebGrid could not safely finish this bulk invite request. No result was confirmed; please try again.",
    BULK_INVITE_FILE_TOO_LARGE: "This CSV is larger than the supported upload limit.",
    BULK_INVITE_UNSUPPORTED_FILE: "Upload a UTF-8 CSV file using the FebGrid template.",
  };
  return messages[error.message] ?? "Bulk invitation could not be completed. Please review the CSV and try again.";
}

function statusTone(status: string): "green" | "blue" | "amber" | "red" | "slate" {
  if (status === "VALID" || status === "INVITED") return "green";
  if (status.startsWith("SKIPPED") || status === "EXISTING_EMPLOYEE" || status === "EXISTING_INVITATION") return "amber";
  if (status === "DUPLICATE" || status.startsWith("FAILED") || status === "INVALID") return "red";
  return "slate";
}

function rowMessage(row: BulkInvitePreviewRow): string {
  return [...row.errors, ...row.warnings].map((issue) => issue.message).join(" ") || "Ready to invite";
}

export function BulkInviteModal({ companyId, isOpen, onClose, onCompleted }: BulkInviteModalProps): JSX.Element {
  const [step, setStep] = useState<Step>("upload");
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<BulkInvitePreview | null>(null);
  const [result, setResult] = useState<BulkInviteConfirmResult | null>(null);
  const [approvalRequired, setApprovalRequired] = useState(false);
  const [filter, setFilter] = useState<PreviewFilter>("all");
  const [isBusy, setIsBusy] = useState(false);
  const [isConfirmationReady, setIsConfirmationReady] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [idempotencyKey, setIdempotencyKey] = useState(createIdempotencyKey);

  const eligibleRows = useMemo(() => preview?.rows.filter((row) => row.status === "VALID") ?? [], [preview]);
  const visibleRows = useMemo(() => {
    if (!preview) return [];
    if (filter === "ready") return preview.rows.filter((row) => row.status === "VALID");
    if (filter === "attention") return preview.rows.filter((row) => row.status !== "VALID");
    return preview.rows;
  }, [filter, preview]);

  useEffect(() => {
    if (!isOpen) return;
    setStep("upload");
    setFile(null);
    setPreview(null);
    setResult(null);
    setApprovalRequired(false);
    setFilter("all");
    setError(null);
    setIsConfirmationReady(false);
    setIdempotencyKey(createIdempotencyKey());
  }, [companyId, isOpen]);

  function close(): void {
    if (!isBusy) onClose();
  }

  function selectFile(event: ChangeEvent<HTMLInputElement>): void {
    setFile(event.target.files?.[0] ?? null);
    setError(null);
  }

  function dropFile(event: DragEvent<HTMLDivElement>): void {
    event.preventDefault();
    setFile(event.dataTransfer.files?.[0] ?? null);
    setError(null);
  }

  async function downloadTemplate(): Promise<void> {
    if (!companyId) return;
    setError(null);
    setIsBusy(true);
    try {
      downloadBlob(await api.bulkInviteTemplate(companyId), "febgrid-bulk-invite-template.csv");
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setIsBusy(false);
    }
  }

  async function previewFile(): Promise<void> {
    if (!companyId || !file) {
      setError("Choose a CSV file before validating it.");
      return;
    }
    setError(null);
    setIsBusy(true);
    try {
      const nextPreview = await api.previewBulkInvites(companyId, file);
      setPreview(nextPreview);
      setIsConfirmationReady(false);
      setStep("preview");
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setIsBusy(false);
    }
  }

  async function confirm(): Promise<void> {
    if (!companyId || !preview) return;
    setError(null);
    setIsBusy(true);
    try {
      const nextResult = await api.confirmBulkInvites(companyId, {
        preview_token: preview.preview_token,
        idempotency_key: idempotencyKey,
        file_name: preview.file_name,
        approval_required: approvalRequired,
        rows: preview.rows,
      });
      setResult(nextResult);
      setStep("results");
      try {
        await onCompleted();
      } catch {
        setError("Invitations were created, but the employee list could not refresh yet. Refresh the page to see the latest queue.");
      }
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setIsBusy(false);
    }
  }

  function downloadErrorReport(): void {
    if (!result) return;
    const failedRows = result.rows.filter((row) => row.status !== "INVITED");
    const csv = ["row_number,email,status,message", ...failedRows.map((row) => [row.row_number, row.email, row.status, row.message].map(safeCsvCell).join(","))].join("\r\n");
    downloadBlob(new Blob([csv], { type: "text/csv;charset=utf-8" }), "febgrid-bulk-invite-results.csv");
  }

  function retryFailures(): void {
    setResult(null);
    setIdempotencyKey(createIdempotencyKey());
    setIsConfirmationReady(false);
    setStep("preview");
  }

  return (
    <Modal description="Validate a CSV first, then send only the eligible invitations through FebGrid's existing onboarding flow." isOpen={isOpen} title="Bulk invite employees" onClose={close}>
      <div className="space-y-5 p-5">
        <div className="grid gap-2 sm:grid-cols-3" aria-label="Bulk invite progress">
          {(["upload", "preview", "results"] as Step[]).map((item, index) => (
            <div key={item} className={`rounded-md border px-3 py-2 text-xs font-bold ${step === item ? "border-brand-300 bg-brand-50 text-brand-700" : "border-grid-200 bg-grid-50 text-ink-500"}`}>
              {index + 1}. {item === "upload" ? "Upload" : item === "preview" ? "Review" : "Results"}
            </div>
          ))}
        </div>

        {error ? <div className="rounded-md border border-rose-200 bg-rose-50 px-4 py-3 text-sm font-semibold text-rose-700" role="alert">{error}</div> : null}

        {step === "upload" ? (
          <div className="space-y-4">
            <div className="rounded-lg border border-dashed border-grid-300 bg-grid-50 px-5 py-7 text-center" onDragOver={(event) => event.preventDefault()} onDrop={dropFile}>
              <FileSpreadsheet className="mx-auto size-7 text-brand-600" aria-hidden="true" />
              <p className="mt-3 text-sm font-bold text-ink-950">Upload a UTF-8 employee CSV</p>
              <p className="mt-1 text-sm font-medium text-ink-500">Required columns: email, full name, job title, and role. Maximum 500 rows.</p>
              <label className="mt-4 inline-flex cursor-pointer items-center justify-center gap-2 rounded-md border border-grid-200 bg-white px-3.5 py-2.5 text-sm font-bold text-ink-900 shadow-sm transition hover:border-grid-300 hover:bg-grid-50">
                <Upload className="size-4" aria-hidden="true" />
                Choose CSV
                <input accept=".csv,text/csv" className="sr-only" type="file" onChange={selectFile} />
              </label>
              {file ? <p className="mt-3 text-sm font-semibold text-ink-700">Selected: {file.name}</p> : null}
            </div>
            <div className="flex flex-wrap justify-between gap-3 border-t border-grid-200 pt-4">
              <Button disabled={isBusy} icon={<Download className="size-4" aria-hidden="true" />} variant="secondary" onClick={() => void downloadTemplate()}>
                Download CSV template
              </Button>
              <Button disabled={isBusy || !file} icon={<Clipboard className="size-4" aria-hidden="true" />} onClick={() => void previewFile()}>
                {isBusy ? "Validating CSV" : "Validate and preview"}
              </Button>
            </div>
          </div>
        ) : null}

        {step === "preview" && preview ? (
          <div className="space-y-4">
            <div className="grid gap-3 sm:grid-cols-4">
              <div className="rounded-md border border-grid-200 bg-grid-50 p-3"><p className="text-xs font-bold uppercase tracking-wide text-ink-500">Rows</p><p className="mt-1 text-xl font-black text-ink-950">{preview.total_rows}</p></div>
              <div className="rounded-md border border-emerald-200 bg-emerald-50 p-3"><p className="text-xs font-bold uppercase tracking-wide text-emerald-700">Ready</p><p className="mt-1 text-xl font-black text-emerald-800">{eligibleRows.length}</p></div>
              <div className="rounded-md border border-amber-200 bg-amber-50 p-3"><p className="text-xs font-bold uppercase tracking-wide text-amber-700">Existing</p><p className="mt-1 text-xl font-black text-amber-800">{preview.existing_employee_count + preview.existing_invitation_count}</p></div>
              <div className="rounded-md border border-rose-200 bg-rose-50 p-3"><p className="text-xs font-bold uppercase tracking-wide text-rose-700">Needs attention</p><p className="mt-1 text-xl font-black text-rose-800">{preview.invalid_row_count + preview.duplicate_row_count}</p></div>
            </div>
            <div className="rounded-md border border-grid-200 bg-grid-50 px-4 py-3 text-sm font-medium text-ink-700">
              <label className="flex cursor-pointer items-start gap-3">
                <input checked={approvalRequired} className="mt-0.5 size-4 rounded border-grid-300 text-brand-600 focus:ring-brand-600" type="checkbox" onChange={(event) => setApprovalRequired(event.target.checked)} />
                <span><strong className="font-bold text-ink-950">Require approval after profile completion</strong><br />{approvalRequired ? "Each invitee must submit a profile and wait for an authorized reviewer." : "Invitees can join after completing their profile."}</span>
              </label>
            </div>
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="flex flex-wrap gap-2" role="group" aria-label="Preview row filter">
                {(["all", "ready", "attention"] as PreviewFilter[]).map((item) => <Button key={item} className="h-8 px-3 text-xs" variant={filter === item ? "primary" : "secondary"} onClick={() => setFilter(item)}>{item === "all" ? "All rows" : item === "ready" ? "Ready to invite" : "Needs attention"}</Button>)}
              </div>
              <p className="text-xs font-medium text-ink-500">Preview expires {new Date(preview.preview_expires_at).toLocaleTimeString()}</p>
            </div>
            <div className="max-h-64 overflow-auto rounded-md border border-grid-200">
              <table className="min-w-full text-left text-sm"><thead className="sticky top-0 bg-grid-50 text-xs uppercase tracking-wide text-ink-500"><tr><th className="px-3 py-2">Row</th><th className="px-3 py-2">Employee</th><th className="px-3 py-2">Status</th><th className="px-3 py-2">Details</th></tr></thead><tbody className="divide-y divide-grid-200 bg-white">{visibleRows.map((row) => <tr key={row.row_number}><td className="px-3 py-3 font-semibold text-ink-700">{row.row_number}</td><td className="px-3 py-3"><p className="font-bold text-ink-950">{row.normalized.full_name || "Unnamed"}</p><p className="text-xs text-ink-500">{row.normalized.email}</p></td><td className="px-3 py-3"><Badge label={row.status.replaceAll("_", " ")} tone={statusTone(row.status)} /></td><td className="px-3 py-3 text-xs font-medium text-ink-600">{rowMessage(row)}</td></tr>)}</tbody></table>
            </div>
            {eligibleRows.length === 0 ? <div className="flex gap-3 rounded-md border border-amber-200 bg-amber-50 px-4 py-3 text-sm font-semibold text-amber-800"><AlertTriangle className="mt-0.5 size-4 shrink-0" aria-hidden="true" />No rows are currently eligible. Update the CSV and upload it again.</div> : null}
            {isConfirmationReady ? (
              <div className="rounded-md border border-brand-200 bg-brand-50 px-4 py-4">
                <p className="font-bold text-ink-950">Confirm {eligibleRows.length} invitation{eligibleRows.length === 1 ? "" : "s"}</p>
                <p className="mt-1 text-sm font-medium text-ink-700">Only the rows marked Ready will be sent. Existing and invalid rows will remain skipped, and each successful row uses the standard FebGrid invitation flow.</p>
                <div className="mt-4 flex flex-wrap justify-end gap-2"><Button disabled={isBusy} variant="secondary" onClick={() => setIsConfirmationReady(false)}>Back</Button><Button disabled={isBusy} icon={<Send className="size-4" aria-hidden="true" />} onClick={() => void confirm()}>{isBusy ? "Sending invitations" : `Confirm and send ${eligibleRows.length}`}</Button></div>
              </div>
            ) : (
              <div className="flex flex-wrap justify-between gap-3 border-t border-grid-200 pt-4"><Button disabled={isBusy} variant="secondary" onClick={() => setStep("upload")}>Choose another file</Button><Button disabled={isBusy || eligibleRows.length === 0} icon={<Send className="size-4" aria-hidden="true" />} onClick={() => setIsConfirmationReady(true)}>Continue to confirmation</Button></div>
            )}
          </div>
        ) : null}

        {step === "results" && result ? (
          <div className="space-y-4">
            <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-4"><div className="flex gap-3"><CheckCircle2 className="mt-0.5 size-5 text-emerald-700" aria-hidden="true" /><div><p className="font-bold text-emerald-900">Bulk invitation processing completed</p><p className="mt-1 text-sm font-medium text-emerald-800">{result.idempotent_replay ? "This confirmation was already completed; no invitations were duplicated." : "Eligible rows were sent through the existing FebGrid invitation and activation flow."}</p></div></div></div>
            <div className="grid gap-3 sm:grid-cols-3"><div className="rounded-md border border-emerald-200 bg-emerald-50 p-3"><p className="text-xs font-bold uppercase text-emerald-700">Invited</p><p className="mt-1 text-xl font-black text-emerald-800">{result.invited_rows}</p></div><div className="rounded-md border border-amber-200 bg-amber-50 p-3"><p className="text-xs font-bold uppercase text-amber-700">Skipped</p><p className="mt-1 text-xl font-black text-amber-800">{result.skipped_rows}</p></div><div className="rounded-md border border-rose-200 bg-rose-50 p-3"><p className="text-xs font-bold uppercase text-rose-700">Failed</p><p className="mt-1 text-xl font-black text-rose-800">{result.failed_rows}</p></div></div>
            {result.rows.length > 0 ? <div className="max-h-52 overflow-auto rounded-md border border-grid-200"><table className="min-w-full text-left text-sm"><thead className="sticky top-0 bg-grid-50 text-xs uppercase tracking-wide text-ink-500"><tr><th className="px-3 py-2">Row</th><th className="px-3 py-2">Email</th><th className="px-3 py-2">Outcome</th><th className="px-3 py-2">Details</th></tr></thead><tbody className="divide-y divide-grid-200 bg-white">{result.rows.map((row) => <tr key={`${row.row_number}-${row.status}`}><td className="px-3 py-3 font-semibold text-ink-700">{row.row_number}</td><td className="px-3 py-3 text-ink-700">{row.email}</td><td className="px-3 py-3"><Badge label={row.status.replaceAll("_", " ")} tone={statusTone(row.status)} /></td><td className="px-3 py-3 text-xs font-medium text-ink-600">{row.message}</td></tr>)}</tbody></table></div> : null}
            <div className="flex flex-wrap justify-between gap-3 border-t border-grid-200 pt-4"><Button disabled={result.rows.length === 0} icon={<Download className="size-4" aria-hidden="true" />} variant="secondary" onClick={downloadErrorReport}>Download results CSV</Button><div className="flex flex-wrap gap-2">{result.failed_rows > 0 ? <Button variant="secondary" onClick={retryFailures}>Retry unresolved rows</Button> : null}<Button onClick={close}>Done</Button></div></div>
          </div>
        ) : null}
      </div>
    </Modal>
  );
}
