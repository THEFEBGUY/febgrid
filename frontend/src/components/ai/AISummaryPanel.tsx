import { Sparkles } from "lucide-react";

import type { AIJob } from "../../types/api";
import { formatLabel, formatTime } from "../../utils/format";
import { displayAIModel, displayAIProvider } from "../../utils/aiDisplay";
import { Badge } from "../ui/Badge";
import { Button } from "../ui/Button";
import { LoadingState } from "../ui/States";

type SummaryKind = "work_object" | "project" | "company" | "file" | "document" | "image" | "audio";

interface AISummaryPanelProps {
  error: string | null;
  generateLabel: string;
  isGenerating: boolean;
  isLoading: boolean;
  isSavingToMemory?: boolean;
  job: AIJob | null;
  kind: SummaryKind;
  onGenerate: () => void;
  onSaveToMemory?: () => void;
  saveToMemoryError?: string | null;
  saveToMemoryLabel?: string;
  saveToMemoryMessage?: string | null;
}

function text(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : null;
}

function list(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value.map((item) => String(item).trim()).filter(Boolean).slice(0, 6);
}

function providerLabel(job: AIJob | null): string {
  if (!job) return "AI summary";
  return displayAIProvider(job.provider_mode || "mock");
}

function summaryTitle(kind: SummaryKind): string {
  if (kind === "company") return "AI executive brief";
  if (kind === "project") return "AI project summary";
  if (kind === "audio") return "AI audio transcription";
  if (kind === "image") return "AI image analysis";
  if (kind === "document") return "AI document analysis";
  if (kind === "file") return "AI file summary";
  return "AI work summary";
}

function entityLabel(kind: SummaryKind): string {
  if (kind === "company") return "company";
  if (kind === "project") return "project";
  if (kind === "audio") return "audio";
  if (kind === "image") return "image";
  if (kind === "document") return "document";
  if (kind === "file") return "file";
  return "work object";
}

function statusTone(status: string): "blue" | "green" | "amber" | "red" | "slate" {
  if (status === "succeeded") return "green";
  if (status === "failed") return "red";
  if (status === "running") return "blue";
  if (status === "queued") return "amber";
  return "slate";
}

export function AISummaryPanel({
  error,
  generateLabel,
  isGenerating,
  isLoading,
  isSavingToMemory = false,
  job,
  kind,
  onGenerate,
  onSaveToMemory,
  saveToMemoryError = null,
  saveToMemoryLabel = "Suggest Memory",
  saveToMemoryMessage = null,
}: AISummaryPanelProps): JSX.Element {
  const output = job?.output_payload ?? {};
  const summary =
    kind === "company"
      ? text(output.executive_summary) ?? text(output.summary)
      : kind === "audio"
        ? text(output.transcript_summary) ?? text(output.summary)
      : kind === "image"
        ? text(output.image_overview) ?? text(output.summary)
      : kind === "document"
        ? text(output.document_overview) ?? text(output.summary)
        : text(output.summary);
  const generatedAt = text(output.generated_at) ?? job?.completed_at ?? job?.created_at ?? null;
  const isMock = output.is_mock === true || output.mock === true || job?.provider_mode === "mock";
  const modelName = text(output.model_name) ?? text(output.model) ?? text(job?.metadata.model_name);
  const primaryPoints =
    kind === "company" ? list(output.operational_highlights) : kind === "project" ? list(output.risks_or_blockers) : list(output.key_points);
  const blockers = kind === "project" || kind === "company" ? list(output.risks_or_blockers) : list(output.blockers_or_risks);
  const fileRisks = list(output.risks_or_concerns);
  const importantFileSignals = list(output.important_dates_or_numbers);
  const decisionsOrCommitments = list(output.decisions_or_commitments);
  const actionItems = list(output.action_items);
  const importantDates = list(output.important_dates);
  const importantNumbers = list(output.important_numbers);
  const mentionedPeople = list(output.people_or_teams_mentioned);
  const relatedWorkSuggestions = list(output.related_work_suggestions);
  const visibleElements = list(output.visible_objects_or_elements);
  const possibleContext = list(output.possible_context);
  const operationalRelevance = text(output.operational_relevance);
  const transcript = text(output.transcript);
  const languageDetected = text(output.language_detected);
  const durationSeconds = typeof output.duration_seconds === "number" ? output.duration_seconds : null;
  const limitations = list(output.limitations);
  const nextSteps = kind === "company" ? list(output.suggested_next_actions) : list(output.suggested_next_steps);
  const currentStatus = kind === "project" ? text(output.status_explanation) : text(output.current_status_explanation);
  const attentionItems = list(output.attention_items);
  const isTruncated = output.truncated === true;
  const unsupportedReason = text(output.unsupported_reason);

  return (
    <section className="febgrid-surface overflow-hidden rounded-lg">
      <div className="flex flex-col gap-3 border-b border-grid-200 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <Sparkles className="size-4 text-brand-600" aria-hidden="true" />
            <h3 className="text-sm font-black text-ink-950">{summaryTitle(kind)}</h3>
            {job ? <Badge label={providerLabel(job)} tone={job.provider_mode === "groq" ? "teal" : "blue"} /> : null}
            {job ? <Badge label={formatLabel(job.status)} tone={statusTone(job.status)} /> : null}
            {isMock && job ? <Badge label="Mock output" tone="slate" /> : null}
          </div>
          <p className="mt-1 text-xs font-semibold text-ink-500">
            Server-owned prompt, safe{" "}
            {kind === "company"
              ? "aggregated company"
              : kind === "audio"
                ? "supported audio metadata"
                : kind === "image"
                  ? "supported image metadata"
                  : kind === "file" || kind === "document"
                    ? "supported text-document"
                    : "entity"}{" "}
            context, no raw paths, no secrets.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {onSaveToMemory && job?.status === "succeeded" ? (
            <Button
              aria-label={saveToMemoryLabel}
              disabled={isSavingToMemory}
              title={saveToMemoryLabel}
              onClick={onSaveToMemory}
            >
              {isSavingToMemory ? "Saving..." : saveToMemoryLabel}
            </Button>
          ) : null}
          <Button
            aria-label={generateLabel}
            disabled={isGenerating}
            icon={<Sparkles className="size-4" aria-hidden="true" />}
            title={generateLabel}
            variant="primary"
            onClick={onGenerate}
          >
            {isGenerating ? "Generating..." : generateLabel}
          </Button>
        </div>
      </div>

      {isLoading ? <LoadingState label="Loading latest AI summary" /> : null}
      {error ? <p className="m-4 rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm font-bold text-rose-700">{error}</p> : null}
      {saveToMemoryError ? (
        <p className="mx-4 mt-4 rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm font-bold text-rose-700">{saveToMemoryError}</p>
      ) : null}
      {saveToMemoryMessage ? (
        <p className="mx-4 mt-4 rounded-lg border border-green-200 bg-green-50 px-4 py-3 text-sm font-bold text-green-700">{saveToMemoryMessage}</p>
      ) : null}

      {!isLoading && !job && !error ? (
        <div className="px-4 py-5">
          <p className="text-sm font-bold text-ink-950">No summary generated yet.</p>
          <p className="mt-1 text-sm font-semibold text-ink-500">
            Generate one when you want a concise operational readout for this {entityLabel(kind)}.
          </p>
        </div>
      ) : null}

      {!isLoading && job ? (
        <div className="space-y-4 p-4">
          {job.status === "queued" || job.status === "running" ? (
            <div className="rounded-lg border border-brand-200 bg-brand-50 px-4 py-3">
              <p className="text-sm font-black text-brand-800">
                {job.status === "queued" ? "Queued for secure processing" : "Generating summary"}
              </p>
              <p className="mt-1 text-xs font-semibold text-brand-700">
                {job.status === "queued"
                  ? "FebGrid will start this job automatically and update this panel when processing begins."
                  : "The result will appear here automatically when processing finishes."}
              </p>
            </div>
          ) : null}
          {job.status === "failed" ? (
            <p className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm font-bold text-rose-700">
              {job.error_message ?? "AI summary failed safely."}
            </p>
          ) : null}
          {(kind === "file" || kind === "document") && isTruncated ? <Badge label="Content truncated" tone="amber" /> : null}
          {(kind === "file" || kind === "document" || kind === "image" || kind === "audio") && unsupportedReason ? <Badge label={formatLabel(unsupportedReason)} tone="red" /> : null}
          {summary ? (
            <div className="rounded-lg border border-grid-200 bg-grid-50 p-4">
              <p className="text-xs font-black uppercase tracking-normal text-ink-500">
                {kind === "company" ? "Executive summary" : "Summary"}
              </p>
              <p className="mt-2 text-sm font-semibold leading-6 text-ink-700">{summary}</p>
            </div>
          ) : null}
          {kind === "company" ? (
            <div className="grid gap-3 md:grid-cols-2">
              <SummaryStat label="Work overview" value={text(output.work_overview) ?? "Not enough data yet"} />
              <SummaryStat label="Project overview" value={text(output.project_overview) ?? "Not enough data yet"} />
              <SummaryStat label="People overview" value={text(output.people_overview) ?? "Not enough data yet"} />
              <SummaryStat label="Leave overview" value={text(output.leave_overview) ?? "Not enough data yet"} />
            </div>
          ) : null}
          {kind === "project" ? (
            <div className="grid gap-3 md:grid-cols-3">
              <SummaryStat label="Health" value={text(output.project_health) ?? "Unknown"} />
              <SummaryStat label="Progress" value={text(output.progress_overview) ?? "Not enough data yet"} />
              <SummaryStat label="Open work" value={text(output.open_work_overview) ?? "Not enough data yet"} />
            </div>
          ) : kind === "file" || kind === "document" ? (
            <div className="grid gap-3 md:grid-cols-2">
              <SummaryStat label="Document type" value={text(output.document_type_guess) ?? "Unknown"} />
              <SummaryStat label="Extraction" value={isTruncated ? "Text-only, truncated" : "Text-only"} />
            </div>
          ) : kind === "image" ? (
            <div className="grid gap-3 md:grid-cols-2">
              <SummaryStat label="Image type" value={text(output.document_type_guess) ?? "Supported image"} />
              <SummaryStat label="Safety" value="No identity, biometric, or sensitive-trait analysis" />
            </div>
          ) : kind === "audio" ? (
            <div className="grid gap-3 md:grid-cols-2">
              <SummaryStat label="Language" value={languageDetected ?? "Unknown"} />
              <SummaryStat label="Duration" value={durationSeconds !== null ? `${Math.round(durationSeconds)} seconds` : "Not detected"} />
              <SummaryStat label="Safety" value="No speaker identity, emotion, or sensitive-trait analysis" />
              <SummaryStat label="Mode" value="Uploaded audio only" />
            </div>
          ) : currentStatus ? (
            <SummaryBlock items={[currentStatus]} title="Status explanation" />
          ) : null}
          {kind === "project" && currentStatus ? <SummaryBlock items={[currentStatus]} title="Status explanation" /> : null}
          {kind === "work_object" && primaryPoints.length > 0 ? <SummaryBlock items={primaryPoints} title="Key points" /> : null}
          {kind === "file" && list(output.key_points).length > 0 ? <SummaryBlock items={list(output.key_points)} title="Key points" /> : null}
          {kind === "file" && importantFileSignals.length > 0 ? <SummaryBlock items={importantFileSignals} title="Important dates or numbers" /> : null}
          {kind === "document" && list(output.key_points).length > 0 ? <SummaryBlock items={list(output.key_points)} title="Key points" /> : null}
          {kind === "document" && decisionsOrCommitments.length > 0 ? <SummaryBlock items={decisionsOrCommitments} title="Decisions or commitments" /> : null}
          {kind === "document" && actionItems.length > 0 ? <SummaryBlock items={actionItems} title="Action items" /> : null}
          {kind === "document" && importantDates.length > 0 ? <SummaryBlock items={importantDates} title="Important dates" /> : null}
          {kind === "document" && importantNumbers.length > 0 ? <SummaryBlock items={importantNumbers} title="Important numbers" /> : null}
          {kind === "image" && visibleElements.length > 0 ? <SummaryBlock items={visibleElements} title="Visible objects or elements" /> : null}
          {kind === "image" && possibleContext.length > 0 ? <SummaryBlock items={possibleContext} title="Possible context" /> : null}
          {kind === "image" && operationalRelevance ? <SummaryBlock items={[operationalRelevance]} title="Operational relevance" /> : null}
          {kind === "audio" && list(output.key_points).length > 0 ? <SummaryBlock items={list(output.key_points)} title="Key points" /> : null}
          {kind === "audio" && actionItems.length > 0 ? <SummaryBlock items={actionItems} title="Action items" /> : null}
          {kind === "audio" && decisionsOrCommitments.length > 0 ? <SummaryBlock items={decisionsOrCommitments} title="Decisions or commitments" /> : null}
          {kind === "audio" && importantFileSignals.length > 0 ? <SummaryBlock items={importantFileSignals} title="Important dates or numbers" /> : null}
          {kind === "audio" && transcript ? <TranscriptBlock transcript={transcript} /> : null}
          {kind === "company" && primaryPoints.length > 0 ? <SummaryBlock items={primaryPoints} title="Operational highlights" /> : null}
          {kind === "company" && attentionItems.length > 0 ? <SummaryBlock items={attentionItems} title="Attention items" /> : null}
          {blockers.length > 0 ? <SummaryBlock items={blockers} title="Blockers or risks" /> : null}
          {(kind === "file" || kind === "document" || kind === "image" || kind === "audio") && fileRisks.length > 0 ? <SummaryBlock items={fileRisks} title="Risks or concerns" /> : null}
          {kind === "document" && mentionedPeople.length > 0 ? <SummaryBlock items={mentionedPeople} title="People or teams mentioned" /> : null}
          {kind === "document" && relatedWorkSuggestions.length > 0 ? <SummaryBlock items={relatedWorkSuggestions} title="Related work suggestions" /> : null}
          {nextSteps.length > 0 ? <SummaryBlock items={nextSteps} title="Suggested next steps" /> : null}
          {(kind === "file" || kind === "document" || kind === "image" || kind === "audio") && limitations.length > 0 ? <SummaryBlock items={limitations} title="Limitations" /> : null}
          <p className="text-xs font-semibold text-ink-500">
            {generatedAt ? `Generated ${formatTime(generatedAt)}` : "Generated time unavailable"}
            {modelName ? ` / ${displayAIModel(modelName)}` : ""}
          </p>
        </div>
      ) : null}
    </section>
  );
}

function SummaryBlock({ items, title }: { items: string[]; title: string }): JSX.Element {
  return (
    <div className="rounded-lg border border-grid-200 bg-grid-50 p-4">
      <p className="text-xs font-black uppercase tracking-normal text-ink-500">{title}</p>
      <ul className="mt-2 space-y-2 text-sm font-semibold leading-6 text-ink-700">
        {items.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </div>
  );
}

function TranscriptBlock({ transcript }: { transcript: string }): JSX.Element {
  return (
    <details className="rounded-lg border border-grid-200 bg-grid-50 p-4">
      <summary className="cursor-pointer text-xs font-black uppercase tracking-normal text-ink-500">
        Transcript text
      </summary>
      <p className="mt-3 whitespace-pre-wrap text-sm font-semibold leading-6 text-ink-700">{transcript}</p>
    </details>
  );
}

function SummaryStat({ label, value }: { label: string; value: string }): JSX.Element {
  return (
    <div className="rounded-lg border border-grid-200 bg-grid-50 p-4">
      <p className="text-xs font-black uppercase tracking-normal text-ink-500">{label}</p>
      <p className="mt-2 text-sm font-bold leading-6 text-ink-950">{value}</p>
    </div>
  );
}
