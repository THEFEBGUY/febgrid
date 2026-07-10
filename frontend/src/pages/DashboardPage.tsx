import {
  Activity,
  AlertTriangle,
  Bell,
  Brain,
  BriefcaseBusiness,
  CalendarDays,
  CheckCircle2,
  Clock3,
  FolderKanban,
  Megaphone,
  Plus,
  RefreshCw,
  Sparkles,
  Users,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { AISummaryPanel } from "../components/ai/AISummaryPanel";
import { MagicBentoCard } from "../components/premium/MagicBento";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { MetricCard } from "../components/ui/MetricCard";
import { ProgressBar } from "../components/ui/ProgressBar";
import { SectionPanel } from "../components/ui/SectionPanel";
import { EmptyState, ErrorState, LoadingState } from "../components/ui/States";
import { priorityTone, statusTone } from "../components/ui/tone";
import { api } from "../services/api";
import type { AIJob, CompanyPulseSnapshot, DashboardSummary } from "../types/api";
import type { Metric } from "../types/domain";
import type { ModulePageProps } from "../types/page";
import { compactList, formatDate, formatLabel, formatTime } from "../utils/format";

const metricIcons = [Users, Users, BriefcaseBusiness, CheckCircle2, AlertTriangle, CalendarDays, Bell, FolderKanban] as const;

function navigateTo(page: string): void {
  window.location.hash = `/${page}`;
}

export function DashboardPage({
  currentUserRole,
  data,
  selectedCompany,
  isLoadingCompanies,
  isLoadingModules,
  moduleError,
  onRetry,
}: ModulePageProps): JSX.Element {
  const summary = data.dashboardSummary;
  const canUseCompanyBrief = currentUserRole === "company_owner" || currentUserRole === "admin";
  const canUseCompanyPulse = canUseCompanyBrief;
  const [companyPulse, setCompanyPulse] = useState<CompanyPulseSnapshot | null>(null);
  const [pulseError, setPulseError] = useState<string | null>(null);
  const [isPulseLoading, setIsPulseLoading] = useState(false);
  const [isPulseGenerating, setIsPulseGenerating] = useState(false);
  const [companyBrief, setCompanyBrief] = useState<AIJob | null>(null);
  const [briefError, setBriefError] = useState<string | null>(null);
  const [isBriefLoading, setIsBriefLoading] = useState(false);
  const [isBriefGenerating, setIsBriefGenerating] = useState(false);
  const [isSavingBriefMemory, setIsSavingBriefMemory] = useState(false);
  const [briefMemoryMessage, setBriefMemoryMessage] = useState<string | null>(null);
  const [briefMemoryError, setBriefMemoryError] = useState<string | null>(null);
  const employeeNames = useMemo(
    () => Object.fromEntries(data.employees.map((employee) => [employee.id, employee.full_name])),
    [data.employees],
  );

  useEffect(() => {
    const companyId = selectedCompany?.id;
    if (!companyId || !canUseCompanyPulse) {
      setCompanyPulse(null);
      setPulseError(null);
      setIsPulseLoading(false);
      return;
    }

    let isCurrent = true;
    setIsPulseLoading(true);
    setPulseError(null);
    api
      .latestCompanyPulse(companyId)
      .then((pulse) => {
        if (isCurrent) setCompanyPulse(pulse);
      })
      .catch((error: unknown) => {
        if (isCurrent) setPulseError(error instanceof Error ? error.message : "Unable to load Company Pulse.");
      })
      .finally(() => {
        if (isCurrent) setIsPulseLoading(false);
      });

    return () => {
      isCurrent = false;
    };
  }, [canUseCompanyPulse, selectedCompany?.id]);

  useEffect(() => {
    const companyId = selectedCompany?.id;
    if (!companyId || !canUseCompanyBrief) {
      setCompanyBrief(null);
      setBriefError(null);
      setIsBriefLoading(false);
      return;
    }

    let isCurrent = true;
    setIsBriefLoading(true);
    setBriefError(null);
    api
      .latestCompanyAIBrief(companyId)
      .then((job) => {
        if (isCurrent) setCompanyBrief(job);
      })
      .catch((error: unknown) => {
        if (isCurrent) setBriefError(error instanceof Error ? error.message : "Unable to load the latest company brief.");
      })
      .finally(() => {
        if (isCurrent) setIsBriefLoading(false);
      });

    return () => {
      isCurrent = false;
    };
  }, [canUseCompanyBrief, selectedCompany?.id]);

  async function handleGenerateCompanyBrief(): Promise<void> {
    const companyId = selectedCompany?.id;
    if (!companyId || !canUseCompanyBrief || isBriefGenerating) return;
    setIsBriefGenerating(true);
    setBriefError(null);
    try {
      const job = await api.generateCompanyAIBrief(companyId);
      setCompanyBrief(job);
    } catch (error) {
      setBriefError(error instanceof Error ? error.message : "Unable to generate the company brief.");
    } finally {
      setIsBriefGenerating(false);
    }
  }

  async function handleGenerateCompanyPulse(): Promise<void> {
    const companyId = selectedCompany?.id;
    if (!companyId || !canUseCompanyPulse || isPulseGenerating) return;
    setIsPulseGenerating(true);
    setPulseError(null);
    try {
      const pulse = await api.generateCompanyPulse(companyId);
      setCompanyPulse(pulse);
    } catch (error) {
      setPulseError(error instanceof Error ? error.message : "Unable to generate Company Pulse.");
    } finally {
      setIsPulseGenerating(false);
    }
  }

  async function handleSuggestBriefMemory(): Promise<void> {
    const companyId = selectedCompany?.id;
    if (!companyId || !companyBrief || isSavingBriefMemory) return;
    setIsSavingBriefMemory(true);
    setBriefMemoryError(null);
    setBriefMemoryMessage(null);
    try {
      await api.createCompanyMemoryFromAIJob(companyBrief.id, {
        company_id: companyId,
        memory_type: "company_brief",
        importance: "high",
        tags: ["company_brief", "ai_summary"],
      });
      setBriefMemoryMessage("Company brief saved as a memory suggestion.");
    } catch (error) {
      setBriefMemoryError(error instanceof Error ? error.message : "Unable to save company brief to memory.");
    } finally {
      setIsSavingBriefMemory(false);
    }
  }

  const metrics = useMemo<Metric[]>(() => {
    if (!summary) return [];
    return [
      {
        label: "Total employees",
        value: summary.employee_summary.total_employees.toString(),
        tone: "blue",
        delta: `${summary.employee_summary.inactive_employees} inactive`,
      },
      {
        label: "Active employees",
        value: summary.employee_summary.active_employees.toString(),
        tone: "green",
        delta: `${summary.employee_summary.available_employees} available`,
      },
      {
        label: "Pending work",
        value: summary.work_summary.pending_or_assigned.toString(),
        tone: "blue",
        delta: `${summary.work_summary.in_progress} in progress`,
      },
      {
        label: "Completed work",
        value: summary.work_summary.completed.toString(),
        tone: "green",
        delta: `${summary.work_summary.total_work_objects} total active objects`,
      },
      {
        label: "Blocked work",
        value: summary.work_summary.blocked.toString(),
        tone: summary.work_summary.blocked > 0 ? "red" : "green",
        delta: `${summary.work_summary.overdue} overdue`,
      },
      {
        label: "Pending leaves",
        value: summary.leave_summary.pending_leave_requests.toString(),
        tone: summary.leave_summary.pending_leave_requests > 0 ? "amber" : "green",
        delta: `${summary.leave_summary.upcoming_approved_leaves} upcoming approved`,
      },
      {
        label: "Unread notifications",
        value: summary.notification_summary.unread_notifications.toString(),
        tone: summary.notification_summary.unread_notifications > 0 ? "amber" : "green",
        delta: `${summary.notification_summary.important_notifications} important`,
      },
      {
        label: "Active projects",
        value: summary.project_summary.active_projects.toString(),
        tone: "teal",
        delta: `${summary.project_summary.average_progress}% avg progress`,
      },
    ];
  }, [summary]);

  if (!selectedCompany && !isLoadingCompanies && !isLoadingModules) {
    return (
      <EmptyState
        description="Create a company tenant first. FebGrid will then load the live operational dashboard for that workspace."
        title="No active company"
      />
    );
  }

  if (isLoadingCompanies || isLoadingModules) {
    return <LoadingState label="Loading live dashboard" />;
  }

  if (moduleError) {
    return <ErrorState message={moduleError} onRetry={onRetry} />;
  }

  if (!summary) {
    return <EmptyState description="Dashboard summary will appear after the selected company loads." title="No dashboard summary yet" />;
  }

  return (
    <div className="space-y-6">
      <MagicBentoCard className="animate-fade-up p-5" tone="blue">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div className="min-w-0">
            <p className="text-xs font-black uppercase tracking-normal text-brand-600">Live operational overview</p>
            <h2 className="mt-1 truncate text-2xl font-black text-ink-950">{summary.company_overview.company_name}</h2>
            <p className="mt-2 max-w-2xl text-sm font-semibold text-ink-500">
              Live command center for people, work, leaves, projects, notifications, files, and timeline activity. Last updated {formatTime(summary.company_overview.generated_at)}.
            </p>
          </div>
          <div className="flex flex-wrap gap-2 lg:justify-end">
            <Button title="Refresh dashboard" aria-label="Refresh dashboard" icon={<RefreshCw className="size-4" aria-hidden="true" />} onClick={() => void onRetry()}>
              Refresh
            </Button>
            <Button variant="primary" icon={<Plus className="size-4" aria-hidden="true" />} onClick={() => navigateTo("work-objects")}>
              Create work
            </Button>
          </div>
        </div>
      </MagicBentoCard>

      <section data-testid="dashboard-kpi-metrics" className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {metrics.map((metric, index) => (
          <MetricCard key={metric.label} metric={metric} icon={metricIcons[index]} />
        ))}
      </section>

      {canUseCompanyBrief ? (
        <div data-testid="dashboard-ai-executive-brief">
          <AISummaryPanel
            error={briefError}
            generateLabel="Generate Company Brief"
            isGenerating={isBriefGenerating}
            isLoading={isBriefLoading}
            isSavingToMemory={isSavingBriefMemory}
            job={companyBrief}
            kind="company"
            onGenerate={() => void handleGenerateCompanyBrief()}
            onSaveToMemory={() => void handleSuggestBriefMemory()}
            saveToMemoryError={briefMemoryError}
            saveToMemoryLabel="Suggest Memory"
            saveToMemoryMessage={briefMemoryMessage}
          />
        </div>
      ) : null}

      {canUseCompanyPulse ? (
        <div data-testid="dashboard-company-pulse">
          <CompanyPulsePanel
            error={pulseError}
            isGenerating={isPulseGenerating}
            isLoading={isPulseLoading}
            onGenerate={() => void handleGenerateCompanyPulse()}
            pulse={companyPulse}
          />
        </div>
      ) : null}

      {canUseCompanyBrief && summary.intelligence_summary ? (
        <IntelligenceReadinessPanel summary={summary} />
      ) : null}

      {summary.memory_summary ? (
        <SectionPanel
          eyebrow="Company Memory"
          title="Approved knowledge"
          description="Reviewable company knowledge created manually or from safe AI summary outputs."
          action={
            <Button icon={<Brain className="size-4" aria-hidden="true" />} onClick={() => navigateTo("memory")}>
              Open Memory
            </Button>
          }
        >
          <div className="grid gap-3 p-5 md:grid-cols-3">
            <StatusTile label="Approved" value={summary.memory_summary.approved_memories} tone="green" />
            <StatusTile label="Suggestions" value={summary.memory_summary.pending_suggestions} tone="amber" />
            <StatusTile label="Important" value={summary.memory_summary.important_memories} tone="red" />
          </div>
        </SectionPanel>
      ) : null}

      <section className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
        <SectionPanel
          eyebrow="Work overview"
          title="Status and priority"
          action={<Button icon={<BriefcaseBusiness className="size-4" aria-hidden="true" />} onClick={() => navigateTo("work-objects")}>Open work</Button>}
        >
          <div className="grid gap-4 p-5 md:grid-cols-2">
            <div className="grid grid-cols-2 gap-3">
              <StatusTile label="Assigned" value={summary.work_summary.pending_or_assigned} tone="blue" />
              <StatusTile label="In progress" value={summary.work_summary.in_progress} tone="teal" />
              <StatusTile label="Under review" value={summary.work_summary.under_review} tone="amber" />
              <StatusTile label="Completed" value={summary.work_summary.completed} tone="green" />
              <StatusTile label="Blocked" value={summary.work_summary.blocked} tone={summary.work_summary.blocked > 0 ? "red" : "green"} />
              <StatusTile label="High/Critical" value={summary.work_summary.high_or_critical_priority} tone="red" />
            </div>
            <div className="febgrid-muted-surface rounded-lg p-4">
              <div className="flex flex-wrap gap-2">
                <Badge label={`${summary.work_summary.due_today} due today`} tone={summary.work_summary.due_today > 0 ? "amber" : "green"} />
                <Badge label={`${summary.work_summary.overdue} overdue`} tone={summary.work_summary.overdue > 0 ? "red" : "green"} />
                <Badge label={`${summary.file_summary.recent_uploads_count} uploads this week`} tone="slate" />
              </div>
              <div className="mt-4 divide-y divide-grid-200">
                {summary.priority_work.length === 0 ? (
                  <EmptyState description="Blocked, high-priority, and due-soon work will appear here." title="No priority work" />
                ) : (
                  summary.priority_work.map((workObject) => (
                    <article key={workObject.id} className="py-3">
                      <p className="truncate text-sm font-bold text-ink-950">{workObject.title}</p>
                      <p className="mt-1 truncate text-xs font-semibold text-ink-500">
                        {compactList([
                          workObject.assignee_employee_id ? employeeNames[workObject.assignee_employee_id] ?? "Assigned" : "Unassigned",
                          workObject.due_date ? `Due ${formatDate(workObject.due_date)}` : null,
                        ])}
                      </p>
                      <div className="mt-2 flex flex-wrap gap-2">
                        <Badge label={formatLabel(workObject.status)} tone={statusTone(workObject.status)} />
                        <Badge label={formatLabel(workObject.priority)} tone={priorityTone(workObject.priority)} />
                      </div>
                    </article>
                  ))
                )}
              </div>
            </div>
          </div>
        </SectionPanel>

        <SectionPanel
          eyebrow="People"
          title="Employee availability"
          action={<Button icon={<Users className="size-4" aria-hidden="true" />} onClick={() => navigateTo("employees")}>Open employees</Button>}
        >
          <div className="grid gap-3 p-5 sm:grid-cols-2">
            <StatusTile label="Available" value={summary.employee_summary.available_employees} tone="green" />
            <StatusTile label="Busy" value={summary.employee_summary.busy_employees} tone="amber" />
            <StatusTile label="On leave" value={summary.employee_summary.on_leave_employees} tone="blue" />
            <StatusTile label="Inactive" value={summary.employee_summary.inactive_employees} tone="slate" />
          </div>
        </SectionPanel>
      </section>

      <section className="grid gap-6 xl:grid-cols-2">
        <SectionPanel
          eyebrow="Projects"
          title="Project health"
          action={<Button icon={<FolderKanban className="size-4" aria-hidden="true" />} onClick={() => navigateTo("projects")}>Open projects</Button>}
        >
          {summary.project_health_list.length === 0 ? (
            <EmptyState description="Active, delayed, and on-hold projects will appear here." title="No active projects" />
          ) : (
            <div className="divide-y divide-grid-100">
              {summary.project_health_list.map((project) => (
                <article key={project.id} className="px-5 py-4">
                  <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                    <div className="min-w-0">
                      <p className="truncate text-sm font-bold text-ink-950">{project.name}</p>
                      <p className="mt-1 truncate text-xs font-semibold text-ink-500">{project.risk_level ? `Risk ${formatLabel(project.risk_level)}` : "No risk level set"}</p>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <Badge label={formatLabel(project.status)} tone={statusTone(project.status)} />
                      <Badge label={formatLabel(project.priority)} tone={priorityTone(project.priority)} />
                    </div>
                  </div>
                  <div className="mt-3">
                    <ProgressBar value={project.progress_percent} />
                  </div>
                </article>
              ))}
            </div>
          )}
        </SectionPanel>

        <SectionPanel
          eyebrow="Leave"
          title="Leave attention"
          action={<Button icon={<CalendarDays className="size-4" aria-hidden="true" />} onClick={() => navigateTo("leaves")}>Open leaves</Button>}
        >
          {summary.leave_attention_list.length === 0 ? (
            <EmptyState description="Pending and upcoming approved leaves will appear here." title="No leaves need attention" />
          ) : (
            <div className="divide-y divide-grid-100">
              {summary.leave_attention_list.map((leave) => (
                <article key={leave.id} className="flex flex-col gap-3 px-5 py-4 md:flex-row md:items-center md:justify-between">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-bold text-ink-950">{leave.employee_id ? employeeNames[leave.employee_id] ?? "Employee" : "Employee"}</p>
                    <p className="mt-1 truncate text-xs font-semibold text-ink-500">
                      {compactList([formatLabel(leave.leave_type), `${formatDate(leave.start_date)} to ${formatDate(leave.end_date)}`])}
                    </p>
                  </div>
                  <Badge label={formatLabel(leave.status)} tone={statusTone(leave.status)} />
                </article>
              ))}
            </div>
          )}
        </SectionPanel>
      </section>

      <section className="grid gap-6 xl:grid-cols-[1fr_1fr_0.9fr]">
        <SectionPanel eyebrow="Activity" title="Recent events" action={<Button icon={<Clock3 className="size-4" aria-hidden="true" />} onClick={() => navigateTo("events")}>Open events</Button>}>
          {summary.recent_events.length === 0 ? (
            <EmptyState description="Major Phase 1 actions generate timeline events." title="No events yet" />
          ) : (
            <div className="divide-y divide-grid-100">
              {summary.recent_events.map((event) => (
                <article key={event.id} className="px-5 py-4">
                  <p className="truncate text-sm font-bold text-ink-950">{event.title}</p>
                  <p className="mt-1 truncate text-xs font-semibold text-ink-500">
                    {formatTime(event.created_at)} / {event.target_entity_type ? formatLabel(event.target_entity_type) : "Company"}
                  </p>
                  <div className="mt-2">
                    <Badge label={formatLabel(event.event_type)} tone="teal" />
                  </div>
                </article>
              ))}
            </div>
          )}
        </SectionPanel>

        <SectionPanel eyebrow="Action stream" title="Notifications" action={<Button icon={<Bell className="size-4" aria-hidden="true" />} onClick={() => navigateTo("notifications")}>Open notifications</Button>}>
          {summary.recent_notifications.length === 0 ? (
            <EmptyState description="Unread and important notifications will appear here." title="No open notifications" />
          ) : (
            <div className="divide-y divide-grid-100">
              {summary.recent_notifications.map((notification) => (
                <article key={notification.id} className="px-5 py-4">
                  <div className="flex items-start justify-between gap-3">
                    <p className="min-w-0 truncate text-sm font-bold text-ink-950">{notification.title}</p>
                    <Badge label={notification.is_read ? "Read" : "Unread"} tone={notification.is_read ? "slate" : "blue"} />
                  </div>
                  <p className="mt-1 line-clamp-2 text-sm text-ink-500">{notification.message}</p>
                  <div className="mt-2 flex flex-wrap gap-2">
                    <Badge label={formatLabel(notification.notification_type)} tone="teal" />
                    <Badge label={notification.priority} tone={priorityTone(notification.priority)} />
                  </div>
                </article>
              ))}
            </div>
          )}
        </SectionPanel>

        <SectionPanel eyebrow="Broadcast" title="Announcements" action={<Button icon={<Megaphone className="size-4" aria-hidden="true" />} onClick={() => navigateTo("announcements")}>Open announcements</Button>}>
          {summary.recent_announcements.length === 0 ? (
            <EmptyState description="Published internal announcements will appear here." title="No announcements yet" />
          ) : (
            <div className="divide-y divide-grid-100">
              {summary.recent_announcements.map((announcement) => (
                <article key={announcement.id} className="px-5 py-4">
                  <p className="truncate text-sm font-bold text-ink-950">{announcement.title}</p>
                  <p className="mt-1 line-clamp-2 text-sm text-ink-500">{announcement.body}</p>
                  <div className="mt-2 flex flex-wrap gap-2">
                    <Badge label={announcement.priority} tone={priorityTone(announcement.priority)} />
                    <Badge label={announcement.published_at ? formatTime(announcement.published_at) : "Draft"} tone="slate" />
                  </div>
                </article>
              ))}
            </div>
          )}
        </SectionPanel>
      </section>

      <SectionPanel eyebrow="Quick actions" title="Move work forward">
        <div className="grid gap-3 p-5 sm:grid-cols-2 lg:grid-cols-5">
          <Button icon={<Users className="size-4" aria-hidden="true" />} onClick={() => navigateTo("employees")}>Add employee</Button>
          <Button icon={<FolderKanban className="size-4" aria-hidden="true" />} onClick={() => navigateTo("projects")}>Create project</Button>
          <Button icon={<BriefcaseBusiness className="size-4" aria-hidden="true" />} onClick={() => navigateTo("work-objects")}>Create work object</Button>
          <Button icon={<CalendarDays className="size-4" aria-hidden="true" />} onClick={() => navigateTo("leaves")}>Submit leave</Button>
          <Button icon={<Megaphone className="size-4" aria-hidden="true" />} onClick={() => navigateTo("announcements")}>Create announcement</Button>
        </div>
      </SectionPanel>
    </div>
  );
}

function IntelligenceReadinessPanel({ summary }: { summary: DashboardSummary }): JSX.Element | null {
  const intelligence = summary.intelligence_summary;
  if (!intelligence) return null;

  const aiOpenJobs = intelligence.ai_queued_jobs + intelligence.ai_running_jobs + intelligence.ai_failed_jobs;
  const workDnaLabel = intelligence.latest_work_dna_scope
    ? `${formatLabel(intelligence.latest_work_dna_scope)} DNA`
    : "No Work DNA yet";
  const memorySuggestions = summary.memory_summary?.pending_suggestions ?? 0;

  return (
    <SectionPanel
      eyebrow="Layer 2 readiness"
      title="Operational intelligence links"
      description="A compact owner/admin view of Pulse, Work DNA, Digital Twin coverage, AI queue health, and Company Memory review state."
      action={
        <div className="flex flex-wrap justify-end gap-2">
          <Button
            aria-label="Open Company Memory"
            icon={<Brain className="size-4" aria-hidden="true" />}
            onClick={() => navigateTo("memory")}
            title="Open Company Memory"
          >
            Memory
          </Button>
          <Button
            aria-label="Open AI Foundation settings"
            icon={<Sparkles className="size-4" aria-hidden="true" />}
            onClick={() => navigateTo("settings")}
            title="Open AI Foundation settings"
            variant="secondary"
          >
            AI Foundation
          </Button>
        </div>
      }
    >
      <div className="grid gap-3 p-5 md:grid-cols-2 xl:grid-cols-4">
        <IntelligenceTile
          description={
            intelligence.latest_work_dna_generated_at
              ? `Last generated ${formatTime(intelligence.latest_work_dna_generated_at)}`
              : "Generate Work DNA to inspect repeatable work patterns."
          }
          icon={<Brain className="size-4" aria-hidden="true" />}
          label="Work DNA"
          metric={workDnaLabel}
          secondary={`${intelligence.latest_work_dna_bottlenecks} bottlenecks / ${intelligence.latest_work_dna_template_candidates} templates`}
          tone={intelligence.latest_work_dna_bottlenecks > 0 ? "amber" : "blue"}
          onClick={() => navigateTo("work-dna")}
        />
        <IntelligenceTile
          description="Recent safe employee context snapshots; no ranking or surveillance score."
          icon={<Users className="size-4" aria-hidden="true" />}
          label="Digital Twin coverage"
          metric={`${intelligence.employee_twins_recent_count}/${summary.employee_summary.active_employees}`}
          secondary={`${intelligence.employee_twins_missing_recent_count} active employees without a recent snapshot`}
          tone={intelligence.employee_twins_missing_recent_count > 0 ? "amber" : "green"}
          onClick={() => navigateTo("employees")}
        />
        <IntelligenceTile
          description="Queue visibility for summaries, analysis jobs, memory suggestions, and provider readiness."
          icon={<Activity className="size-4" aria-hidden="true" />}
          label="AI job queue"
          metric={`${aiOpenJobs} open`}
          secondary={`${intelligence.ai_failed_jobs} failed / ${intelligence.ai_running_jobs} running / ${intelligence.ai_queued_jobs} queued`}
          tone={intelligence.ai_failed_jobs > 0 ? "red" : aiOpenJobs > 0 ? "amber" : "green"}
          onClick={() => navigateTo("settings")}
        />
        <IntelligenceTile
          description="Review AI-suggested and manually captured operational knowledge before approval."
          icon={<Sparkles className="size-4" aria-hidden="true" />}
          label="Memory review"
          metric={`${memorySuggestions} pending`}
          secondary={`${summary.memory_summary?.approved_memories ?? 0} approved / ${summary.memory_summary?.important_memories ?? 0} important`}
          tone={memorySuggestions > 0 ? "amber" : "green"}
          onClick={() => navigateTo("memory")}
        />
      </div>
    </SectionPanel>
  );
}

function IntelligenceTile({
  description,
  icon,
  label,
  metric,
  onClick,
  secondary,
  tone,
}: {
  description: string;
  icon: JSX.Element;
  label: string;
  metric: string;
  onClick: () => void;
  secondary: string;
  tone: "blue" | "green" | "amber" | "red";
}): JSX.Element {
  return (
    <button
      className="group rounded-lg border border-grid-200 bg-white/70 p-4 text-left shadow-sm transition hover:-translate-y-0.5 hover:border-brand-300 hover:bg-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
      onClick={onClick}
      title={`Open ${label}`}
      type="button"
    >
      <div className="flex items-center justify-between gap-3">
        <Badge label={label} tone={tone} />
        <span className="rounded-lg border border-grid-200 bg-white/80 p-2 text-ink-500 transition group-hover:text-brand-600">{icon}</span>
      </div>
      <p className="mt-4 text-2xl font-black text-ink-950">{metric}</p>
      <p className="mt-1 text-xs font-black uppercase tracking-normal text-ink-500">{secondary}</p>
      <p className="mt-3 text-sm font-semibold leading-6 text-ink-500">{description}</p>
    </button>
  );
}

function CompanyPulsePanel({
  pulse,
  error,
  isLoading,
  isGenerating,
  onGenerate,
}: {
  pulse: CompanyPulseSnapshot | null;
  error: string | null;
  isLoading: boolean;
  isGenerating: boolean;
  onGenerate: () => void;
}): JSX.Element {
  const sectionEntries = Object.entries(pulse?.section_scores ?? {});
  const hasPulse = Boolean(pulse);

  return (
    <SectionPanel
      eyebrow="Operational intelligence"
      title="Company Pulse"
      description="Rule-based company health from people, work, projects, leaves, events, AI jobs, files, and Company Memory."
      action={
        <div className="flex flex-wrap justify-end gap-2">
          <Button
            aria-label="Open Work DNA"
            icon={<Brain className="size-4" aria-hidden="true" />}
            onClick={() => navigateTo("work-dna")}
            title="Open Work DNA"
            variant="secondary"
          >
            Open Work DNA
          </Button>
          <Button
            aria-label={hasPulse ? "Refresh Company Pulse" : "Generate Company Pulse"}
            disabled={isGenerating || isLoading}
            icon={isGenerating ? <RefreshCw className="size-4 animate-spin" aria-hidden="true" /> : <Activity className="size-4" aria-hidden="true" />}
            onClick={onGenerate}
            title={hasPulse ? "Refresh Company Pulse" : "Generate Company Pulse"}
            variant={hasPulse ? "secondary" : "primary"}
          >
            {isGenerating ? "Generating" : hasPulse ? "Refresh Pulse" : "Generate Pulse"}
          </Button>
        </div>
      }
    >
      <div className="space-y-5 p-5">
        {isLoading ? (
          <LoadingState label="Loading Company Pulse" />
        ) : error ? (
          <ErrorState message={error} onRetry={onGenerate} />
        ) : !pulse ? (
          <EmptyState
            description="Generate a rule-based snapshot to see company health, risks, and recommended operational actions."
            title="No Company Pulse yet"
          />
        ) : (
          <>
            <div className="grid gap-4 xl:grid-cols-[0.55fr_1fr]">
              <MagicBentoCard className="p-5" tone={pulseTone(pulse.pulse_status)}>
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <p className="text-xs font-black uppercase tracking-normal text-ink-500">Overall pulse</p>
                    <div className="mt-2 flex items-end gap-2">
                      <span className="text-5xl font-black leading-none text-ink-950">{pulse.overall_score}</span>
                      <span className="pb-1 text-sm font-black text-ink-500">/100</span>
                    </div>
                  </div>
                  <div className="rounded-lg border border-grid-200 bg-white/70 p-3 shadow-sm">
                    <Sparkles className="size-5 text-brand-600" aria-hidden="true" />
                  </div>
                </div>
                <div className="mt-4 flex flex-wrap gap-2">
                  <Badge label={formatLabel(pulse.pulse_status)} tone={pulseTone(pulse.pulse_status)} />
                  <Badge label={`Trend ${formatLabel(pulse.trend)}`} tone={trendTone(pulse.trend)} />
                  <Badge label={pulse.is_rule_based ? "Rule based" : "AI assisted"} tone="slate" />
                </div>
                <p className="mt-3 text-xs font-semibold text-ink-500">Generated {formatTime(pulse.created_at)}</p>
              </MagicBentoCard>

              <div className="febgrid-muted-surface rounded-lg p-4">
                <p className="text-sm font-bold text-ink-950">{pulse.summary}</p>
                <div className="mt-4 grid gap-3 md:grid-cols-2">
                  {sectionEntries.map(([key, value]) => (
                    <div key={key} className="rounded-lg border border-grid-200 bg-white/70 p-3 shadow-sm">
                      <div className="mb-2 flex items-center justify-between gap-3">
                        <p className="truncate text-xs font-black uppercase tracking-normal text-ink-500">{sectionLabel(key)}</p>
                        <Badge label={`${value}/100`} tone={scoreTone(value)} />
                      </div>
                      <ProgressBar value={value} />
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <div className="grid gap-4 xl:grid-cols-3">
              <PulseList title="Key signals" items={pulse.key_signals} emptyLabel="No positive or neutral signals yet." tone="green" />
              <PulseList title="Risks" items={pulse.risks} emptyLabel="No major risks visible from current signals." tone="red" />
              <PulseList title="Recommended actions" items={pulse.recommended_actions} emptyLabel="No recommended actions yet." tone="blue" />
            </div>
          </>
        )}
      </div>
    </SectionPanel>
  );
}

function PulseList({
  title,
  items,
  emptyLabel,
  tone,
}: {
  title: string;
  items: string[];
  emptyLabel: string;
  tone: "blue" | "green" | "red";
}): JSX.Element {
  return (
    <div className="rounded-lg border border-grid-200 bg-white/70 p-4 shadow-sm">
      <div className="mb-3 flex items-center gap-2">
        <Badge label={title} tone={tone} />
      </div>
      {items.length === 0 ? (
        <p className="text-sm font-semibold text-ink-500">{emptyLabel}</p>
      ) : (
        <ul className="space-y-2">
          {items.slice(0, 5).map((item, index) => (
            <li key={`${title}-${index}-${item}`} className="text-sm font-semibold leading-6 text-ink-700">
              {item}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function pulseTone(statusValue: string): "blue" | "green" | "amber" | "red" | "teal" | "slate" {
  switch (statusValue) {
    case "excellent":
      return "teal";
    case "healthy":
      return "green";
    case "watch":
      return "amber";
    case "at_risk":
    case "critical":
      return "red";
    default:
      return "slate";
  }
}

function trendTone(trend: string): "blue" | "green" | "amber" | "red" | "teal" | "slate" {
  if (trend === "improving") return "green";
  if (trend === "declining") return "red";
  if (trend === "stable") return "blue";
  return "slate";
}

function scoreTone(value: number): "blue" | "green" | "amber" | "red" | "teal" | "slate" {
  if (value >= 85) return "teal";
  if (value >= 70) return "green";
  if (value >= 50) return "amber";
  return "red";
}

function sectionLabel(key: string): string {
  return formatLabel(key.replace(/_health$/, ""));
}

function StatusTile({ label, value, tone }: { label: string; value: number; tone: "blue" | "green" | "amber" | "red" | "teal" | "slate" }): JSX.Element {
  return (
    <MagicBentoCard className="p-4" tone={tone}>
      <p className="text-xs font-black uppercase tracking-normal text-ink-500">{label}</p>
      <div className="mt-2 flex items-end justify-between gap-3">
        <p className="text-2xl font-black text-ink-950">{value}</p>
        <Badge label={value === 1 ? "item" : "items"} tone={tone} />
      </div>
    </MagicBentoCard>
  );
}
