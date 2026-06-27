import { Bell, BriefcaseBusiness, CalendarDays, CheckCircle2, UserCircle } from "lucide-react";
import { useMemo } from "react";

import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { MetricCard } from "../components/ui/MetricCard";
import { ModuleBoundary } from "../components/ui/ModuleBoundary";
import { SectionPanel } from "../components/ui/SectionPanel";
import { statusTone } from "../components/ui/tone";
import type { ModulePageProps } from "../types/page";
import type { PageKey } from "../types/domain";
import { formatDate, formatLabel, formatTime } from "../utils/format";

interface EmployeeDashboardPageProps extends ModulePageProps {
  onNavigate: (page: PageKey) => void;
}

export function EmployeeDashboardPage({
  data,
  selectedCompany,
  isLoadingModules,
  moduleError,
  onRetry,
  onNavigate,
}: EmployeeDashboardPageProps): JSX.Element {
  const profile = data.employees[0] ?? null;
  const activeWork = useMemo(
    () => data.workObjects.filter((workObject) => workObject.is_active && !["completed", "cancelled"].includes(workObject.status)),
    [data.workObjects],
  );
  const completedWork = data.workObjects.filter((workObject) => workObject.status === "completed").length;
  const pendingLeaves = data.leaves.filter((leave) => leave.status === "pending").length;
  const unreadNotifications = data.notifications.filter((notification) => !notification.is_read && !notification.is_dismissed).length;

  const metrics = [
    {
      metric: {
        label: "Open work",
        value: activeWork.length.toString(),
        tone: "blue" as const,
        delta: `${completedWork} completed`,
      },
      icon: BriefcaseBusiness,
    },
    {
      metric: {
        label: "Completed work",
        value: completedWork.toString(),
        tone: "green" as const,
        delta: `${data.workObjects.length} total assigned`,
      },
      icon: CheckCircle2,
    },
    {
      metric: {
        label: "Pending leaves",
        value: pendingLeaves.toString(),
        tone: "amber" as const,
        delta: `${data.leaves.length} leave records`,
      },
      icon: CalendarDays,
    },
    {
      metric: {
        label: "Unread notifications",
        value: unreadNotifications.toString(),
        tone: "teal" as const,
        delta: "Personal action stream",
      },
      icon: Bell,
    },
  ];

  return (
    <div className="space-y-6">
      <SectionPanel
        eyebrow={selectedCompany?.name ?? "Your company"}
        title="My Dashboard"
        action={<Button variant="primary" onClick={() => onNavigate("my-work")}>Open my work</Button>}
      >
        <ModuleBoundary
          emptyDescription="Your profile, work, leave, and notifications will appear here after onboarding is complete."
          emptyTitle="Your employee workspace is ready"
          error={moduleError}
          isEmpty={!profile && data.workObjects.length === 0 && data.leaves.length === 0}
          isLoading={isLoadingModules}
          onRetry={onRetry}
        >
          <div className="grid gap-4 p-5 lg:grid-cols-[1.2fr_0.8fr]">
            <div className="rounded-lg border border-grid-200 bg-grid-50 p-5">
              <p className="text-xs font-bold uppercase tracking-normal text-ink-500">Company</p>
              <h2 className="mt-2 text-2xl font-black text-ink-950">{selectedCompany?.name ?? "FebGrid workspace"}</h2>
              <p className="mt-2 text-sm font-medium text-ink-600">{selectedCompany?.description ?? "Your personal operating view inside the company."}</p>
            </div>
            <div className="rounded-lg border border-grid-200 bg-grid-50 p-5">
              <div className="flex items-start gap-3">
                <span className="flex size-11 shrink-0 items-center justify-center rounded-md bg-white text-ink-700 ring-1 ring-grid-200">
                  <UserCircle className="size-5" aria-hidden="true" />
                </span>
                <div className="min-w-0">
                  <p className="truncate text-sm font-black text-ink-950">{profile?.full_name ?? "Employee profile"}</p>
                  <p className="mt-1 truncate text-xs font-semibold text-ink-500">{profile?.email ?? "Account email"}</p>
                  <div className="mt-3 flex flex-wrap gap-2">
                    <Badge label={formatLabel(profile?.profile_completion_status)} tone="blue" />
                    <Badge label={formatLabel(profile?.activation_status)} tone={profile?.activation_status === "activated" ? "green" : "amber"} />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </ModuleBoundary>
      </SectionPanel>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {metrics.map((item) => (
          <MetricCard key={item.metric.label} metric={item.metric} icon={item.icon} />
        ))}
      </div>

      <div className="grid gap-6 xl:grid-cols-2">
        <SectionPanel title="My Work" action={<Button onClick={() => onNavigate("my-work")}>View all</Button>}>
          {activeWork.length === 0 ? (
            <div className="px-5 py-8 text-sm font-medium text-ink-500">No active work is assigned to you right now.</div>
          ) : (
            <div className="divide-y divide-grid-100">
              {activeWork.slice(0, 5).map((workObject) => (
                <article key={workObject.id} className="px-5 py-4">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div className="min-w-0">
                      <p className="truncate text-sm font-bold text-ink-950">{workObject.title}</p>
                      <p className="mt-1 text-xs font-semibold text-ink-500">Due {formatDate(workObject.due_date)}</p>
                    </div>
                    <div className="flex gap-2">
                      <Badge label={formatLabel(workObject.status)} tone={statusTone(workObject.status)} />
                      <Badge label={formatLabel(workObject.priority)} tone={workObject.priority === "critical" ? "red" : workObject.priority === "high" ? "amber" : "slate"} />
                    </div>
                  </div>
                </article>
              ))}
            </div>
          )}
        </SectionPanel>

        <SectionPanel title="My Leave" action={<Button onClick={() => onNavigate("my-leave")}>Submit leave</Button>}>
          {data.leaves.length === 0 ? (
            <div className="px-5 py-8 text-sm font-medium text-ink-500">No leave requests submitted yet.</div>
          ) : (
            <div className="divide-y divide-grid-100">
              {data.leaves.slice(0, 5).map((leave) => (
                <article key={leave.id} className="px-5 py-4">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <p className="text-sm font-bold text-ink-950">{formatLabel(leave.leave_type)}</p>
                      <p className="mt-1 text-xs font-semibold text-ink-500">
                        {formatDate(leave.start_date)} - {formatDate(leave.end_date)}
                      </p>
                    </div>
                    <Badge label={formatLabel(leave.status)} tone={statusTone(leave.status)} />
                  </div>
                </article>
              ))}
            </div>
          )}
        </SectionPanel>

        <SectionPanel title="Notifications" action={<Button onClick={() => onNavigate("notifications")}>Open</Button>}>
          {data.notifications.length === 0 ? (
            <div className="px-5 py-8 text-sm font-medium text-ink-500">No personal notifications yet.</div>
          ) : (
            <div className="divide-y divide-grid-100">
              {data.notifications.slice(0, 5).map((notification) => (
                <article key={notification.id} className="px-5 py-4">
                  <p className="text-sm font-bold text-ink-950">{notification.title}</p>
                  <p className="mt-1 line-clamp-2 text-sm text-ink-600">{notification.message}</p>
                  <p className="mt-2 text-xs font-semibold text-ink-500">{formatTime(notification.created_at)}</p>
                </article>
              ))}
            </div>
          )}
        </SectionPanel>

        <SectionPanel title="Announcements" action={<Button onClick={() => onNavigate("announcements")}>Open</Button>}>
          {data.announcements.length === 0 ? (
            <div className="px-5 py-8 text-sm font-medium text-ink-500">No published company announcements yet.</div>
          ) : (
            <div className="divide-y divide-grid-100">
              {data.announcements.slice(0, 5).map((announcement) => (
                <article key={announcement.id} className="px-5 py-4">
                  <p className="text-sm font-bold text-ink-950">{announcement.title}</p>
                  <p className="mt-1 line-clamp-2 text-sm text-ink-600">{announcement.body}</p>
                  <p className="mt-2 text-xs font-semibold text-ink-500">
                    {announcement.published_at ? formatTime(announcement.published_at) : formatTime(announcement.created_at)}
                  </p>
                </article>
              ))}
            </div>
          )}
        </SectionPanel>
      </div>
    </div>
  );
}
