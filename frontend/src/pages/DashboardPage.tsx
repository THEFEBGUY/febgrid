import { AlertTriangle, CalendarDays, CheckCircle2, Clock3, Users } from "lucide-react";

import { events, metrics, notifications, workObjects } from "../data/sampleData";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { MetricCard } from "../components/ui/MetricCard";
import { SectionPanel } from "../components/ui/SectionPanel";
import { priorityTone, statusTone } from "../components/ui/tone";

const metricIcons = [Users, CheckCircle2, AlertTriangle, CalendarDays] as const;

export function DashboardPage(): JSX.Element {
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
          action={<Button variant="primary" icon={<CheckCircle2 className="size-4" aria-hidden="true" />}>Create object</Button>}
        >
          <div className="divide-y divide-grid-100">
            {workObjects.slice(0, 4).map((workObject) => (
              <article key={workObject.id} className="flex flex-col gap-3 px-5 py-4 md:flex-row md:items-center md:justify-between">
                <div className="min-w-0">
                  <p className="truncate text-sm font-bold text-ink-950">{workObject.title}</p>
                  <p className="mt-1 truncate text-sm text-ink-500">{workObject.type} / {workObject.assignee} / Due {workObject.due}</p>
                </div>
                <div className="flex shrink-0 flex-wrap gap-2">
                  <Badge label={workObject.status} tone={statusTone(workObject.status)} />
                  <Badge label={workObject.priority} tone={priorityTone(workObject.priority)} />
                </div>
              </article>
            ))}
          </div>
        </SectionPanel>

        <SectionPanel eyebrow="Activity" title="Live timeline">
          <div className="divide-y divide-grid-100">
            {events.map((event) => (
              <article key={event.id} className="flex gap-3 px-5 py-4">
                <span className="mt-1 flex size-9 shrink-0 items-center justify-center rounded-md bg-grid-100 text-ink-700">
                  <Clock3 className="size-4" aria-hidden="true" />
                </span>
                <div className="min-w-0">
                  <p className="truncate text-sm font-bold text-ink-950">{event.title}</p>
                  <p className="mt-1 truncate text-xs font-semibold text-ink-500">{event.time} / {event.entity}</p>
                </div>
              </article>
            ))}
          </div>
        </SectionPanel>
      </section>

      <SectionPanel eyebrow="Notifications" title="Action stream">
        <div className="grid gap-3 p-5 md:grid-cols-3">
          {notifications.map((notification) => (
            <article key={notification.id} className="rounded-lg border border-grid-200 bg-grid-50 p-4">
              <div className="flex items-start justify-between gap-3">
                <p className="min-w-0 truncate text-sm font-bold text-ink-950">{notification.title}</p>
                <Badge label={notification.read ? "Read" : "Open"} tone={notification.read ? "slate" : "blue"} />
              </div>
              <p className="mt-2 line-clamp-2 text-sm text-ink-500">{notification.message}</p>
            </article>
          ))}
        </div>
      </SectionPanel>
    </div>
  );
}
