import { RefreshCw, ShieldCheck, Sparkles } from "lucide-react";

import { Badge } from "../ui/Badge";
import { Button } from "../ui/Button";
import { EmptyState, ErrorState, LoadingState } from "../ui/States";
import type { EmployeeDigitalTwinSignals, EmployeeDigitalTwinSnapshot } from "../../types/api";
import { formatDateTime, formatLabel } from "../../utils/format";

type TwinPayload = EmployeeDigitalTwinSnapshot | EmployeeDigitalTwinSignals | null;

interface DigitalTwinPanelProps {
  twin: TwinPayload;
  history?: EmployeeDigitalTwinSnapshot[];
  isLoading?: boolean;
  isGenerating?: boolean;
  error?: string | null;
  onGenerate: () => void;
  periodDays: number;
  onPeriodChange?: (periodDays: number) => void;
  title?: string;
}

const workloadTone: Record<string, "blue" | "green" | "amber" | "red" | "slate" | "teal"> = {
  light: "blue",
  balanced: "green",
  elevated: "amber",
  overloaded: "red",
  unknown: "slate",
};

function readNumber(source: Record<string, unknown> | undefined, key: string): number {
  const value = source?.[key];
  return typeof value === "number" ? value : 0;
}

function readString(source: Record<string, unknown> | undefined, key: string): string | null {
  const value = source?.[key];
  return typeof value === "string" && value.trim() ? value : null;
}

function readProjectNames(source: Record<string, unknown> | undefined): string[] {
  const values = source?.projects;
  if (!Array.isArray(values)) return [];
  return values.map((value) => String(value)).filter(Boolean).slice(0, 6);
}

function generatedAt(twin: TwinPayload): string | null {
  if (!twin) return null;
  if ("created_at" in twin) return twin.created_at;
  return twin.generated_at;
}

function providerMode(twin: TwinPayload): string | null {
  if (!twin || !("provider_mode" in twin)) return null;
  return twin.provider_mode;
}

export function DigitalTwinPanel({
  twin,
  history = [],
  isLoading = false,
  isGenerating = false,
  error,
  onGenerate,
  periodDays,
  onPeriodChange,
  title = "Employee Digital Twin",
}: DigitalTwinPanelProps): JSX.Element {
  const profile = twin?.profile ?? {};
  const work = twin?.work_metrics ?? {};
  const projects = twin?.project_metrics ?? {};
  const coverage = twin?.data_coverage ?? {};
  const methodology = readString(twin?.metadata, "methodology");
  const workloadLevel = twin?.workload_level ?? "unknown";

  return (
    <section className="overflow-hidden rounded-xl border border-grid-200 bg-grid-50/90 shadow-premium">
      <div className="flex flex-col gap-4 border-b border-grid-200 p-5 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <p className="text-xs font-black uppercase text-brand-600">Operational profile</p>
          <h3 className="mt-1 flex items-center gap-2 text-xl font-black text-ink-950">
            <Sparkles className="size-5 text-brand-500" aria-hidden="true" />
            {title}
          </h3>
          <p className="mt-2 max-w-3xl text-sm font-semibold text-ink-500">
            This summarizes FebGrid work data to help with workload and priorities. It is not an employment or performance score.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {onPeriodChange ? (
            <select
              className="min-h-10 rounded-lg border border-grid-200 bg-white px-3 text-sm font-bold text-ink-800 shadow-sm focus:border-brand-400 focus:outline-none focus:ring-2 focus:ring-brand-200"
              aria-label="Digital Twin period"
              value={periodDays}
              onChange={(event) => onPeriodChange(Number(event.target.value))}
            >
              <option value={7}>7 days</option>
              <option value={30}>30 days</option>
              <option value={90}>90 days</option>
            </select>
          ) : null}
          <Button
            aria-label="Generate Employee Digital Twin"
            title="Generate Employee Digital Twin"
            disabled={isGenerating}
            icon={<RefreshCw className="size-4" aria-hidden="true" />}
            onClick={onGenerate}
            variant={twin ? "secondary" : "primary"}
          >
            {isGenerating ? "Generating" : twin ? "Refresh twin" : "Generate twin"}
          </Button>
        </div>
      </div>

      {isLoading ? <LoadingState label="Loading Digital Twin" /> : null}
      {error ? <ErrorState message={error} onRetry={onGenerate} /> : null}
      {!isLoading && !error && !twin ? (
        <EmptyState
          title="No Digital Twin snapshot yet"
          description="Generate a safe rule-based operational snapshot for this employee."
          action={
            <Button variant="primary" icon={<Sparkles className="size-4" aria-hidden="true" />} onClick={onGenerate}>
              Generate twin
            </Button>
          }
        />
      ) : null}

      {twin ? (
        <div className="space-y-5 p-5">
          <div className="grid gap-4 xl:grid-cols-[0.9fr_1.4fr]">
            <div className="magic-bento-card rounded-xl border border-grid-200 p-5">
              <p className="text-xs font-black uppercase text-ink-500">Workload level</p>
              <div className="mt-3 flex flex-wrap items-center gap-2">
                <Badge label={formatLabel(workloadLevel)} tone={workloadTone[workloadLevel] ?? "slate"} />
                <Badge label={twin.is_rule_based ? "Rule based" : "AI assisted"} tone="blue" />
                {twin.ai_narrative_used ? <Badge label={providerMode(twin) ?? "AI narrative"} tone="teal" /> : <Badge label="No employee score" tone="slate" />}
              </div>
              <p className="mt-4 text-sm font-semibold leading-6 text-ink-700">{twin.summary}</p>
              <p className="mt-4 text-xs font-bold text-ink-500">
                Period: {formatDateTime(twin.period_start)} - {formatDateTime(twin.period_end)}
              </p>
              {generatedAt(twin) ? <p className="mt-1 text-xs font-bold text-ink-500">Generated {formatDateTime(generatedAt(twin) ?? "")}</p> : null}
            </div>

            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
              <Metric label="Open work" value={readNumber(work, "current_open_work_count")} />
              <Metric label="Completed" value={readNumber(work, "completed_work_count")} />
              <Metric label="Overdue" value={readNumber(work, "overdue_work_count")} tone="red" />
              <Metric label="Active projects" value={readNumber(projects, "active_project_count")} tone="teal" />
              <Metric label="Blocked" value={readNumber(work, "blocked_work_count")} tone="amber" />
              <Metric label="High priority" value={readNumber(work, "high_priority_open_work_count")} tone="amber" />
              <Metric label="Upcoming due" value={readNumber(work, "upcoming_due_work_count")} tone="blue" />
              <Metric label="Coverage" value={formatLabel(readString(coverage, "coverage_level") ?? "unknown")} tone="green" />
            </div>
          </div>

          <div className="grid gap-4 lg:grid-cols-3">
            <InfoList title="Operational strengths" items={twin.strengths} emptyLabel="Not enough operational data yet." tone="green" />
            <InfoList title="Attention areas" items={twin.attention_areas} emptyLabel="No attention areas visible." tone="amber" />
            <InfoList title="Risks" items={twin.risks} emptyLabel="No major operational risks visible." tone="red" />
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <InfoList title="Recommended actions" items={twin.recommended_actions} emptyLabel="No recommended actions yet." tone="blue" />
            <div className="rounded-xl border border-grid-200 bg-white/70 p-4">
              <p className="text-xs font-black uppercase text-ink-500">Profile and projects</p>
              <div className="mt-3 grid gap-2 text-sm font-semibold text-ink-700 sm:grid-cols-2">
                <p>Role: {readString(profile, "role") ?? "Not set"}</p>
                <p>Department: {readString(profile, "department") ?? "Not assigned"}</p>
                <p>Team: {readString(profile, "team") ?? "Not assigned"}</p>
                <p>Manager: {readString(profile, "manager") ?? "Not assigned"}</p>
              </div>
              <div className="mt-4 flex flex-wrap gap-2">
                {readProjectNames(projects).length ? readProjectNames(projects).map((project) => <Badge key={project} label={project} tone="teal" />) : <Badge label="No active project data" tone="slate" />}
              </div>
              <div className="mt-4 flex flex-wrap gap-2">
                {twin.skills.length ? twin.skills.slice(0, 12).map((skill) => <Badge key={skill} label={skill} tone="blue" />) : <Badge label="No skills/tags yet" tone="slate" />}
              </div>
            </div>
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <InfoList title="Data coverage" items={[`Coverage: ${formatLabel(readString(coverage, "coverage_level") ?? "unknown")}`, ...(Array.isArray(coverage.source_categories) ? coverage.source_categories.map(String) : [])]} tone="teal" />
            <InfoList title="Limitations" items={twin.limitations} tone="slate" />
          </div>

          <div className="rounded-xl border border-grid-200 bg-white/70 p-4">
            <p className="flex items-center gap-2 text-xs font-black uppercase text-ink-500">
              <ShieldCheck className="size-4 text-brand-500" aria-hidden="true" />
              How this is calculated
            </p>
            <p className="mt-2 text-sm font-semibold leading-6 text-ink-600">
              {methodology ??
                "Workload is calculated from current assigned work, due dates, priorities, blocked items, project involvement, availability, and approved leave. FebGrid does not create an employee performance score."}
            </p>
          </div>

          {history.length ? (
            <div className="rounded-xl border border-grid-200 bg-white/70 p-4">
              <p className="text-xs font-black uppercase text-ink-500">Snapshot history</p>
              <div className="mt-3 grid gap-2">
                {history.slice(0, 5).map((item) => (
                  <div key={item.id} className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-grid-200 px-3 py-2 text-sm font-bold text-ink-700">
                    <span>{formatDateTime(item.created_at)}</span>
                    <Badge label={formatLabel(item.workload_level)} tone={workloadTone[item.workload_level] ?? "slate"} />
                  </div>
                ))}
              </div>
            </div>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}

function Metric({ label, value, tone = "blue" }: { label: string; value: string | number; tone?: "blue" | "green" | "amber" | "red" | "teal" | "slate" }): JSX.Element {
  return (
    <div className="rounded-xl border border-grid-200 bg-white/70 p-4">
      <p className="text-xs font-black uppercase text-ink-500">{label}</p>
      <p className="mt-2 text-2xl font-black text-ink-950">{value}</p>
      <div className="mt-3">
        <Badge label="operational" tone={tone} />
      </div>
    </div>
  );
}

function InfoList({
  title,
  items,
  emptyLabel = "No data yet.",
  tone,
}: {
  title: string;
  items: string[];
  emptyLabel?: string;
  tone: "blue" | "green" | "amber" | "red" | "teal" | "slate";
}): JSX.Element {
  const visibleItems = items.length ? items : [emptyLabel];
  return (
    <div className="rounded-xl border border-grid-200 bg-white/70 p-4">
      <Badge label={title} tone={tone} />
      <ul className="mt-3 space-y-2">
        {visibleItems.map((item, index) => (
          <li key={`${title}-${index}`} className="text-sm font-semibold leading-6 text-ink-700">
            {item}
          </li>
        ))}
      </ul>
    </div>
  );
}
