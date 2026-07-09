import { Brain, Fingerprint, RefreshCw, Sparkles } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";

import { MagicBentoCard } from "../components/premium/MagicBento";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { FieldShell, SelectInput } from "../components/ui/FormControls";
import { SectionPanel } from "../components/ui/SectionPanel";
import { EmptyState, ErrorState, LoadingState } from "../components/ui/States";
import { api } from "../services/api";
import type { CompanyMemoryCreatePayload, WorkDNAScopeType, WorkDNASnapshot } from "../types/api";
import type { ModulePageProps } from "../types/page";
import { formatLabel, formatTime } from "../utils/format";

const periodOptions = [7, 30, 90];
const scopeOptions: WorkDNAScopeType[] = ["company", "project", "department", "team"];

function text(value: unknown, fallback = "Not enough data yet"): string {
  if (typeof value === "string" && value.trim()) return value;
  if (typeof value === "number") return value.toString();
  return fallback;
}

function numberValue(value: unknown): number {
  return typeof value === "number" && Number.isFinite(value) ? value : 0;
}

function recordValue(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : {};
}

function listValue<T = unknown>(value: unknown): T[] {
  return Array.isArray(value) ? (value as T[]) : [];
}

function pickScopeId(snapshot: WorkDNASnapshot | null): string | null {
  return snapshot?.scope_id ?? null;
}

export function WorkDNAPage({ data, selectedCompany, currentUserRole }: ModulePageProps): JSX.Element {
  const [scopeType, setScopeType] = useState<WorkDNAScopeType>("company");
  const [scopeId, setScopeId] = useState<string | null>(null);
  const [periodDays, setPeriodDays] = useState(30);
  const [latest, setLatest] = useState<WorkDNASnapshot | null>(null);
  const [history, setHistory] = useState<WorkDNASnapshot[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isSavingMemory, setIsSavingMemory] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const canUseWorkDNA = currentUserRole === "company_owner" || currentUserRole === "admin";
  const scopeIdOptions = useMemo(() => {
    if (scopeType === "project") return data.projects.map((project) => ({ id: project.id, label: project.name }));
    if (scopeType === "department") return data.departments.map((department) => ({ id: department.id, label: department.name }));
    if (scopeType === "team") return data.teams.map((team) => ({ id: team.id, label: team.name }));
    return [];
  }, [data.departments, data.projects, data.teams, scopeType]);

  useEffect(() => {
    if (scopeType === "company") {
      setScopeId(null);
      return;
    }
    if (!scopeIdOptions.some((option) => option.id === scopeId)) {
      setScopeId(scopeIdOptions[0]?.id ?? null);
    }
  }, [scopeId, scopeIdOptions, scopeType]);

  const loadWorkDNA = useCallback(async (): Promise<void> => {
    if (!selectedCompany || !canUseWorkDNA) return;
    if (scopeType !== "company" && !scopeId) {
      setLatest(null);
      setHistory([]);
      return;
    }
    setIsLoading(true);
    setError(null);
    try {
      const params = { scope_type: scopeType, scope_id: scopeId };
      const [nextLatest, nextHistory] = await Promise.all([
        api.latestWorkDNA(selectedCompany.id, params),
        api.workDNAHistory(selectedCompany.id, { ...params, limit: 12 }),
      ]);
      setLatest(nextLatest);
      setHistory(nextHistory);
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Unable to load Work DNA.");
    } finally {
      setIsLoading(false);
    }
  }, [canUseWorkDNA, scopeId, scopeType, selectedCompany]);

  useEffect(() => {
    void loadWorkDNA();
  }, [loadWorkDNA]);

  async function handleGenerate(): Promise<void> {
    if (!selectedCompany || isGenerating || !canUseWorkDNA) return;
    if (scopeType !== "company" && !scopeId) {
      setError(`Choose a ${formatLabel(scopeType)} before generating Work DNA.`);
      return;
    }
    setIsGenerating(true);
    setError(null);
    setNotice(null);
    try {
      const snapshot = await api.generateWorkDNA(selectedCompany.id, {
        scope_type: scopeType,
        scope_id: scopeId,
        period_days: periodDays,
      });
      setLatest(snapshot);
      const nextHistory = await api.workDNAHistory(selectedCompany.id, { scope_type: scopeType, scope_id: pickScopeId(snapshot), limit: 12 });
      setHistory(nextHistory);
      setNotice("Work DNA generated.");
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Unable to generate Work DNA.");
    } finally {
      setIsGenerating(false);
    }
  }

  async function handleSuggestMemory(): Promise<void> {
    if (!selectedCompany || !latest || isSavingMemory) return;
    setIsSavingMemory(true);
    setError(null);
    setNotice(null);
    try {
      const payload: CompanyMemoryCreatePayload = {
        company_id: selectedCompany.id,
        title: `${formatLabel(latest.scope_type)} Work DNA insight`,
        memory_type: "process",
        scope_type: latest.scope_type === "company" ? "company" : latest.scope_type,
        scope_id: latest.scope_id,
        source_type: "work_dna",
        source_id: latest.id,
        content: [
          latest.overall_summary,
          ...latest.recommended_improvements.slice(0, 5).map((item) => `- ${item}`),
          ...latest.limitations.slice(0, 3).map((item) => `Limitation: ${item}`),
        ].join("\n"),
        summary: latest.overall_summary,
        tags: ["work_dna", "process", "operational_intelligence"],
        importance: latest.risks.length > 0 ? "high" : "normal",
        status: "suggested",
        visibility: "owner_admin",
        metadata: {
          source: "work_dna_page",
          snapshot_id: latest.id,
          period_days: latest.period_days,
          scope_type: latest.scope_type,
        },
      };
      await api.createCompanyMemory(payload);
      setNotice("Work DNA insight suggested to Company Memory.");
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Unable to suggest Work DNA to memory.");
    } finally {
      setIsSavingMemory(false);
    }
  }

  if (!selectedCompany) {
    return <EmptyState title="No company selected" description="Select a company before opening Work DNA." />;
  }

  if (!canUseWorkDNA) {
    return <ErrorState message="Company Work DNA is currently limited to owner/admin users." />;
  }

  const hasScopedOptions = scopeType === "company" || scopeIdOptions.length > 0;
  const workVolume = recordValue(latest?.work_volume);
  const coverage = recordValue(latest?.data_coverage);
  const sourceCounts = recordValue(latest?.source_counts);

  return (
    <div className="space-y-6">
      <SectionPanel
        eyebrow={selectedCompany.name}
        title="Work DNA"
        description="Explainable work-system intelligence for recurring work, workflow bottlenecks, overdue pressure, templates, and process improvements."
        action={
          <div className="flex flex-wrap gap-2">
            <Button
              title="Refresh Work DNA"
              aria-label="Refresh Work DNA"
              icon={<RefreshCw className="size-4" aria-hidden="true" />}
              disabled={isLoading}
              onClick={() => void loadWorkDNA()}
            >
              Refresh
            </Button>
            <Button
              title="Generate Work DNA"
              aria-label="Generate Work DNA"
              icon={isGenerating ? <RefreshCw className="size-4 animate-spin" aria-hidden="true" /> : <Sparkles className="size-4" aria-hidden="true" />}
              variant="primary"
              disabled={isGenerating || !hasScopedOptions}
              onClick={() => void handleGenerate()}
            >
              {isGenerating ? "Generating" : latest ? "Regenerate" : "Generate"}
            </Button>
          </div>
        }
      >
        <div className="grid gap-4 border-b border-grid-200 p-5 lg:grid-cols-[1fr_1fr_1fr_auto]">
          <FieldShell label="Scope">
            <SelectInput value={scopeType} onChange={(event) => setScopeType(event.target.value as WorkDNAScopeType)}>
              {scopeOptions.map((option) => (
                <option key={option} value={option}>
                  {formatLabel(option)}
                </option>
              ))}
            </SelectInput>
          </FieldShell>
          <FieldShell label="Scope target">
            <SelectInput disabled={scopeType === "company" || scopeIdOptions.length === 0} value={scopeId ?? ""} onChange={(event) => setScopeId(event.target.value || null)}>
              {scopeType === "company" ? <option value="">Whole company</option> : null}
              {scopeType !== "company" && scopeIdOptions.length === 0 ? <option value="">No {formatLabel(scopeType)} available</option> : null}
              {scopeIdOptions.map((option) => (
                <option key={option.id} value={option.id}>
                  {option.label}
                </option>
              ))}
            </SelectInput>
          </FieldShell>
          <FieldShell label="Period">
            <SelectInput value={periodDays} onChange={(event) => setPeriodDays(Number(event.target.value))}>
              {periodOptions.map((option) => (
                <option key={option} value={option}>
                  {option} days
                </option>
              ))}
            </SelectInput>
          </FieldShell>
          <div className="flex items-end">
            <Button
              title="Suggest latest Work DNA to Company Memory"
              aria-label="Suggest latest Work DNA to Company Memory"
              icon={<Brain className="size-4" aria-hidden="true" />}
              disabled={!latest || isSavingMemory}
              onClick={() => void handleSuggestMemory()}
            >
              {isSavingMemory ? "Suggesting" : "Suggest Memory"}
            </Button>
          </div>
        </div>

        {notice ? <p className="mx-5 mt-5 rounded-lg border border-green-200 bg-green-50 px-4 py-3 text-sm font-bold text-green-700">{notice}</p> : null}
        {error ? <ErrorState message={error} onRetry={() => void loadWorkDNA()} /> : null}
        {isLoading ? <LoadingState label="Loading Work DNA" /> : null}
        {!isLoading && !error && !latest ? (
          <EmptyState
            title="No Work DNA snapshot yet"
            description="Generate a rule-based snapshot to identify recurring work, bottlenecks, template candidates, and advisory process improvements."
            action={
              <Button title="Generate Work DNA" aria-label="Generate Work DNA" icon={<Fingerprint className="size-4" aria-hidden="true" />} onClick={() => void handleGenerate()}>
                Generate Work DNA
              </Button>
            }
          />
        ) : null}

        {!isLoading && latest ? (
          <div className="space-y-5 p-5">
            <div className="grid gap-4 xl:grid-cols-[0.7fr_1fr]">
              <MagicBentoCard className="p-5" tone="blue">
                <div className="flex flex-wrap gap-2">
                  <Badge label={latest.is_rule_based ? "Rule based" : "AI assisted"} tone="blue" />
                  <Badge label={formatLabel(latest.scope_type)} tone="teal" />
                  <Badge label={`${latest.period_days} days`} tone="slate" />
                  {latest.ai_narrative_used ? <Badge label="Groq narrative" tone="green" /> : null}
                </div>
                <h3 className="mt-4 text-lg font-black text-ink-950">Work-system snapshot</h3>
                <p className="mt-2 text-sm font-semibold leading-6 text-ink-600">{latest.overall_summary}</p>
                <p className="mt-3 text-xs font-bold text-ink-500">Generated {formatTime(latest.created_at)}</p>
              </MagicBentoCard>

              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                <MetricTile label="Analyzed work" value={numberValue(workVolume.total_analyzed)} />
                <MetricTile label="Open work" value={numberValue(workVolume.current_open)} />
                <MetricTile label="Bottlenecks" value={latest.bottlenecks.length} tone={latest.bottlenecks.length ? "amber" : "green"} />
                <MetricTile label="Recurring patterns" value={latest.recurring_patterns.length} />
                <MetricTile label="Templates" value={latest.template_candidates.length} />
                <MetricTile label="Automation ideas" value={latest.automation_candidates.length} />
                <MetricTile label="Coverage" value={text(coverage.coverage_level, "Minimal")} isText />
                <MetricTile label="Source events" value={numberValue(sourceCounts.events_in_period)} />
              </div>
            </div>

            <div className="grid gap-4 xl:grid-cols-3">
              <InsightList title="Operational strengths" items={latest.operational_strengths} tone="green" />
              <InsightList title="Attention areas" items={latest.attention_areas} tone="amber" />
              <InsightList title="Risks" items={latest.risks} tone="red" />
            </div>

            <div className="grid gap-4 xl:grid-cols-3">
              <DistributionCard title="Work types" rows={latest.work_type_distribution} />
              <DistributionCard title="Statuses" rows={latest.status_distribution} />
              <DistributionCard title="Priorities" rows={latest.priority_distribution} />
              <DistributionCard title="Projects" rows={latest.project_patterns} />
              <DistributionCard title="Departments" rows={latest.department_patterns} />
              <DistributionCard title="Teams" rows={latest.team_patterns} />
            </div>

            <div className="grid gap-4 xl:grid-cols-2">
              <PatternCard title="Recurring work patterns" rows={latest.recurring_patterns} primaryKey="pattern_name" />
              <PatternCard title="Workflow bottlenecks" rows={latest.bottlenecks} primaryKey="type" />
              <PatternCard title="Deadline patterns" rows={latest.deadline_patterns} primaryKey="pattern" />
              <PatternCard title="Template candidates" rows={latest.template_candidates} primaryKey="name" />
              <PatternCard title="Automation candidates" rows={latest.automation_candidates} primaryKey="name" />
              <InsightList title="Recommended improvements" items={latest.recommended_improvements} tone="blue" />
            </div>

            <div className="grid gap-4 xl:grid-cols-2">
              <InsightList title="Limitations" items={latest.limitations} tone="slate" />
              <SectionPanel eyebrow="History" title="Recent snapshots">
                {history.length === 0 ? (
                  <EmptyState title="No history yet" description="Work DNA history will appear after snapshots are generated." />
                ) : (
                  <div className="divide-y divide-grid-200">
                    {history.map((snapshot) => (
                      <article key={snapshot.id} className="px-5 py-4">
                        <div className="flex flex-wrap items-center justify-between gap-3">
                          <p className="text-sm font-black text-ink-950">{formatLabel(snapshot.scope_type)} / {snapshot.period_days} days</p>
                          <Badge label={formatTime(snapshot.created_at)} tone="slate" />
                        </div>
                        <p className="mt-2 line-clamp-2 text-sm font-semibold text-ink-500">{snapshot.overall_summary}</p>
                      </article>
                    ))}
                  </div>
                )}
              </SectionPanel>
            </div>
          </div>
        ) : null}
      </SectionPanel>
    </div>
  );
}

function MetricTile({ label, value, tone = "blue", isText = false }: { label: string; value: number | string; tone?: "blue" | "green" | "amber"; isText?: boolean }): JSX.Element {
  return (
    <MagicBentoCard className="p-4" tone={tone}>
      <p className="text-xs font-black uppercase tracking-normal text-ink-500">{label}</p>
      <p className={`${isText ? "text-lg" : "text-3xl"} mt-2 font-black text-ink-950`}>{value}</p>
    </MagicBentoCard>
  );
}

function InsightList({ title, items, tone }: { title: string; items: string[]; tone: "blue" | "green" | "amber" | "red" | "slate" }): JSX.Element {
  return (
    <div className="rounded-lg border border-grid-200 bg-white/70 p-4 shadow-sm">
      <Badge label={title} tone={tone} />
      {items.length === 0 ? (
        <p className="mt-3 text-sm font-semibold text-ink-500">Not enough evidence yet.</p>
      ) : (
        <ul className="mt-3 space-y-2">
          {items.slice(0, 7).map((item, index) => (
            <li key={`${title}-${index}-${item}`} className="text-sm font-semibold leading-6 text-ink-700">
              {item}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function DistributionCard({ title, rows }: { title: string; rows: Record<string, unknown>[] }): JSX.Element {
  return (
    <div className="rounded-lg border border-grid-200 bg-white/70 p-4 shadow-sm">
      <p className="text-sm font-black text-ink-950">{title}</p>
      {rows.length === 0 ? (
        <p className="mt-3 text-sm font-semibold text-ink-500">Not enough data yet.</p>
      ) : (
        <div className="mt-3 space-y-3">
          {rows.slice(0, 6).map((row, index) => (
            <div key={`${title}-${index}-${text(row.label)}`}>
              <div className="flex items-center justify-between gap-3 text-sm font-bold">
                <span className="truncate text-ink-800">{text(row.label, "Unknown")}</span>
                <span className="text-ink-500">{numberValue(row.count)} / {numberValue(row.percentage)}%</span>
              </div>
              <div className="mt-2 h-2 overflow-hidden rounded-full bg-grid-100">
                <div className="h-full rounded-full bg-brand-600" style={{ width: `${Math.min(numberValue(row.percentage), 100)}%` }} />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function PatternCard({ title, rows, primaryKey }: { title: string; rows: Record<string, unknown>[]; primaryKey: string }): JSX.Element {
  return (
    <div className="rounded-lg border border-grid-200 bg-white/70 p-4 shadow-sm">
      <p className="text-sm font-black text-ink-950">{title}</p>
      {rows.length === 0 ? (
        <p className="mt-3 text-sm font-semibold text-ink-500">Not enough data yet.</p>
      ) : (
        <div className="mt-3 space-y-3">
          {rows.slice(0, 6).map((rawRow, index) => {
            const row = recordValue(rawRow);
            const evidence = text(row.evidence, text(row.recommended_action, ""));
            return (
              <article key={`${title}-${index}-${text(row[primaryKey])}`} className="rounded-lg border border-grid-200 bg-grid-50 p-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <p className="text-sm font-black text-ink-950">{formatLabel(text(row[primaryKey], "Pattern"))}</p>
                  {row.count || row.occurrence_count ? <Badge label={`${numberValue(row.count ?? row.occurrence_count)} signals`} tone="blue" /> : null}
                </div>
                {evidence ? <p className="mt-2 text-sm font-semibold leading-6 text-ink-600">{evidence}</p> : null}
                {listValue(row.common_tags).length > 0 ? (
                  <div className="mt-3 flex flex-wrap gap-2">
                    {listValue(row.common_tags).map((tag) => (
                      <Badge key={String(tag)} label={String(tag)} tone="teal" />
                    ))}
                  </div>
                ) : null}
              </article>
            );
          })}
        </div>
      )}
    </div>
  );
}
