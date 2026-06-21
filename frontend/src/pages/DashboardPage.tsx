import { AlertTriangle, CalendarDays, CheckCircle2, Clock3, Users } from "lucide-react";
import { useMemo } from "react";

import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { MetricCard } from "../components/ui/MetricCard";
import { SectionPanel } from "../components/ui/SectionPanel";
import { EmptyState, ErrorState, LoadingState } from "../components/ui/States";
import { priorityTone, statusTone } from "../components/ui/tone";
import type { Metric } from "../types/domain";
import type { ModulePageProps } from "../types/page";
import { compactList, formatDate, formatLabel, formatTime } from "../utils/format";

const metricIcons = [Users, CheckCircle2, AlertTriangle, CalendarDays] as const;

export function DashboardPage({ data, selectedCompany, isLoadingCompanies, isLoadingModules, moduleError, onRetry }: ModulePageProps): JSX.Element {
  const metrics = useMemo<Metric[]>(() => {
    const activeEmployees = data.employees.filter((employee) => !["offline", "on_leave"].includes(employee.current_status)).length;
    const openWork = data.workObjects.filter((workObject) => !["completed", "archived", "rejected"].includes(workObject.status)).length;
    const blockedWork = data.workObjects.filter((workObject) => workObject.status === "blocked").length;
    const pendingLeaves = data.leaves.filter((leave) => leave.status === "pending").length;

    return [
      { label: "Active employees", value: activeEmployees.toString(), tone: "green", delta: `${data.employees.length} total employees` },
      { label: "Open work objects", value: openWork.toString(), tone: "blue", delta: `${data.workObjects.length} total objects` },
      { label: "Blocked work", value: blockedWork.toString(), tone: blockedWork > 0 ? "red" : "green", delta: blockedWork > 0 ? "Needs manager action" : "No blockers" },
      { label: "Pending leaves", value: pendingLeaves.toString(), tone: pendingLeaves > 0 ? "amber" : "green", delta: `${data.leaves.length} total leave requests` },
    ];
  }, [data.employees, data.leaves, data.workObjects]);

  const employeeNames = useMemo(
    () => Object.fromEntries(data.employees.map((employee) => [employee.id, employee.full_name])),
    [data.employees],
  );

  const priorityWork = data.workObjects
    .filter((workObject) => workObject.status !== "completed")
    .slice(0, 5);

  if (!selectedCompany && !isLoadingCompanies && !isLoadingModules) {
    return (
      <EmptyState
        description="Create a company tenant first. FebGrid will then load employees, work objects, leaves, events, and notifications from the backend."
        title="No active company"
      />
    );
  }

  if (isLoadingCompanies || isLoadingModules) {
    return <LoadingState label="Loading company operations" />;
  }

  if (moduleError) {
    return <ErrorState message={moduleError} onRetry={onRetry} />;
  }

  return (
    <div className="space-y-6">
      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {metrics.map((metric, index) => (
          <MetricCard key={metric.label} metric={metric} icon={metricIcons[index]} />
        ))}
      </section>

      <section className="grid gap-6 xl:grid-cols-[1.3fr_0.7fr]">
        <SectionPanel
          eyebrow="Mission control"
          title="Priority work"
          action={<Button disabled variant="primary" icon={<CheckCircle2 className="size-4" aria-hidden="true" />}>Create object</Button>}
        >
          {priorityWork.length === 0 ? (
            <EmptyState description="Created work objects will appear here for manager review." title="No priority work yet" />
          ) : (
            <div className="divide-y divide-grid-100">
              {priorityWork.map((workObject) => (
                <article key={workObject.id} className="flex flex-col gap-3 px-5 py-4 md:flex-row md:items-center md:justify-between">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-bold text-ink-950">{workObject.title}</p>
                    <p className="mt-1 truncate text-sm text-ink-500">
                      {compactList([
                        formatLabel(workObject.object_type),
                        workObject.assigned_to_employee_id ? employeeNames[workObject.assigned_to_employee_id] ?? "Assigned" : "Unassigned",
                        `Due ${formatDate(workObject.due_date)}`,
                      ])}
                    </p>
                  </div>
                  <div className="flex shrink-0 flex-wrap gap-2">
                    <Badge label={formatLabel(workObject.status)} tone={statusTone(workObject.status)} />
                    <Badge label={formatLabel(workObject.priority)} tone={priorityTone(workObject.priority)} />
                  </div>
                </article>
              ))}
            </div>
          )}
        </SectionPanel>

        <SectionPanel eyebrow="Activity" title="Live timeline">
          {data.events.length === 0 ? (
            <EmptyState description="Backend events generated by major actions will appear here." title="No events yet" />
          ) : (
            <div className="divide-y divide-grid-100">
              {data.events.slice(0, 6).map((event) => (
                <article key={event.id} className="flex gap-3 px-5 py-4">
                  <span className="mt-1 flex size-9 shrink-0 items-center justify-center rounded-md bg-grid-100 text-ink-700">
                    <Clock3 className="size-4" aria-hidden="true" />
                  </span>
                  <div className="min-w-0">
                    <p className="truncate text-sm font-bold text-ink-950">{event.title}</p>
                    <p className="mt-1 truncate text-xs font-semibold text-ink-500">
                      {formatTime(event.created_at)} / {event.target_entity_type ?? "company"}
                    </p>
                  </div>
                </article>
              ))}
            </div>
          )}
        </SectionPanel>
      </section>

      <SectionPanel eyebrow="Notifications" title="Action stream">
        {data.notifications.length === 0 ? (
          <EmptyState description="Work assignments and leave review notifications will appear here." title="No notifications yet" />
        ) : (
          <div className="grid gap-3 p-5 md:grid-cols-3">
            {data.notifications.slice(0, 3).map((notification) => (
              <article key={notification.id} className="rounded-lg border border-grid-200 bg-grid-50 p-4">
                <div className="flex items-start justify-between gap-3">
                  <p className="min-w-0 truncate text-sm font-bold text-ink-950">{notification.title}</p>
                  <Badge label={notification.is_read ? "Read" : "Open"} tone={notification.is_read ? "slate" : "blue"} />
                </div>
                <p className="mt-2 line-clamp-2 text-sm text-ink-500">{notification.message}</p>
              </article>
            ))}
          </div>
        )}
      </SectionPanel>
    </div>
  );
}
