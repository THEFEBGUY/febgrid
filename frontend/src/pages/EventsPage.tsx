import { Clock3, Filter, RotateCcw } from "lucide-react";
import { useMemo, useState } from "react";

import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { ModuleBoundary } from "../components/ui/ModuleBoundary";
import { SectionPanel } from "../components/ui/SectionPanel";
import type { Event } from "../types/api";
import type { ModulePageProps } from "../types/page";
import { compactList, formatLabel, formatTime } from "../utils/format";

function eventActor(event: Event, employeeNames: Record<string, string>): string {
  if (event.actor_employee_id) return employeeNames[event.actor_employee_id] ?? "Employee";
  if (event.actor_user_id) return "User";
  return "System";
}

function eventTarget(event: Event): string {
  return compactList([
    event.target_entity_type ? formatLabel(event.target_entity_type) : "Company",
    event.target_entity_id ? event.target_entity_id.slice(0, 8) : null,
  ]);
}

export function EventsPage({ data, selectedCompany, isLoadingModules, moduleError, onRetry }: ModulePageProps): JSX.Element {
  const [eventTypeFilter, setEventTypeFilter] = useState("");
  const [targetFilter, setTargetFilter] = useState("");

  const employeeNames = useMemo(
    () => Object.fromEntries(data.employees.map((employee) => [employee.id, employee.full_name])),
    [data.employees],
  );

  const eventTypes = useMemo(() => Array.from(new Set(data.events.map((event) => event.event_type))).sort(), [data.events]);
  const targetTypes = useMemo(
    () => Array.from(new Set(data.events.map((event) => event.target_entity_type).filter(Boolean) as string[])).sort(),
    [data.events],
  );

  const filteredEvents = useMemo(
    () =>
      data.events.filter((event) => {
        if (eventTypeFilter && event.event_type !== eventTypeFilter) return false;
        if (targetFilter && event.target_entity_type !== targetFilter) return false;
        return true;
      }),
    [data.events, eventTypeFilter, targetFilter],
  );

  return (
    <SectionPanel
      eyebrow={selectedCompany?.name ?? "Universal timeline"}
      title="Events"
      action={
        <Button
          disabled={!eventTypeFilter && !targetFilter}
          icon={<RotateCcw className="size-4" aria-hidden="true" />}
          onClick={() => {
            setEventTypeFilter("");
            setTargetFilter("");
          }}
        >
          Reset
        </Button>
      }
    >
      <ModuleBoundary
        emptyDescription="Important backend actions will appear here as company memory events."
        emptyTitle="No events yet"
        error={moduleError}
        isEmpty={data.events.length === 0}
        isLoading={isLoadingModules}
        onRetry={onRetry}
      >
        <div className="flex flex-col gap-3 border-b border-grid-100 px-5 py-4 lg:flex-row lg:items-center">
          <div className="flex items-center gap-2 text-sm font-bold text-ink-700">
            <Filter className="size-4" aria-hidden="true" />
            Filters
          </div>
          <label className="block min-w-0 lg:w-72">
            <span className="sr-only">Filter by event type</span>
            <select
              className="h-10 w-full rounded-md border border-grid-200 bg-white px-3 text-sm font-semibold text-ink-900"
              value={eventTypeFilter}
              onChange={(event) => setEventTypeFilter(event.target.value)}
            >
              <option value="">All event types</option>
              {eventTypes.map((eventType) => (
                <option key={eventType} value={eventType}>
                  {formatLabel(eventType)}
                </option>
              ))}
            </select>
          </label>
          <label className="block min-w-0 lg:w-60">
            <span className="sr-only">Filter by target type</span>
            <select
              className="h-10 w-full rounded-md border border-grid-200 bg-white px-3 text-sm font-semibold text-ink-900"
              value={targetFilter}
              onChange={(event) => setTargetFilter(event.target.value)}
            >
              <option value="">All targets</option>
              {targetTypes.map((targetType) => (
                <option key={targetType} value={targetType}>
                  {formatLabel(targetType)}
                </option>
              ))}
            </select>
          </label>
        </div>

        {filteredEvents.length === 0 ? (
          <div className="px-5 py-10 text-center">
            <p className="text-sm font-bold text-ink-950">No events match these filters</p>
            <p className="mt-1 text-sm font-medium text-ink-500">Reset filters to return to the full company timeline.</p>
          </div>
        ) : (
          <div className="divide-y divide-grid-100">
            {filteredEvents.map((event) => (
              <article key={event.id} className="flex flex-col gap-3 px-5 py-4 lg:flex-row lg:items-center lg:justify-between">
                <div className="flex min-w-0 items-start gap-3">
                  <span className="flex size-10 shrink-0 items-center justify-center rounded-md bg-grid-100 text-ink-700">
                    <Clock3 className="size-4" aria-hidden="true" />
                  </span>
                  <div className="min-w-0">
                    <p className="text-sm font-bold text-ink-950">{event.title}</p>
                    {event.description ? <p className="mt-1 line-clamp-2 text-sm text-ink-500">{event.description}</p> : null}
                    <p className="mt-2 text-xs font-semibold text-ink-500">
                      {formatTime(event.created_at)} / {eventActor(event, employeeNames)} / {eventTarget(event)}
                    </p>
                  </div>
                </div>
                <div className="flex shrink-0 flex-wrap gap-2">
                  <Badge label={formatLabel(event.event_type)} tone="teal" />
                  <Badge label={event.target_entity_type ? formatLabel(event.target_entity_type) : "Company"} tone="slate" />
                </div>
              </article>
            ))}
          </div>
        )}
      </ModuleBoundary>
    </SectionPanel>
  );
}
