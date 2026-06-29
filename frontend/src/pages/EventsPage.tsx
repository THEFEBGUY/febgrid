import { Clock3, ExternalLink } from "lucide-react";
import { useMemo, useState } from "react";

import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { FilterBar, FilterField } from "../components/ui/FilterBar";
import { SelectInput, TextInput } from "../components/ui/FormControls";
import { ModuleBoundary } from "../components/ui/ModuleBoundary";
import { SectionPanel } from "../components/ui/SectionPanel";
import type { AuditLog, Event } from "../types/api";
import type { ModulePageProps } from "../types/page";
import { compactList, formatDate, formatLabel, formatTime } from "../utils/format";

const auditPrefixes = [
  "auth.",
  "billing.",
  "company.",
  "custom_field.",
  "user.",
  "employee.",
  "employee_account.",
  "employee_invite.",
  "employee_profile.",
  "department.",
  "team.",
  "project.",
  "work_object.",
  "work_object_type.",
  "leave.",
  "file.",
  "industry_template.",
  "manual_employee.",
  "notification.",
  "comment.",
  "announcement.",
];

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

function isAuditRelevant(event: Event): boolean {
  return auditPrefixes.some((prefix) => event.event_type.startsWith(prefix));
}

function eventRoute(event: Event): string | null {
  const entityType = event.target_entity_type ?? event.related_entity_type;
  switch (entityType) {
    case "employee":
      return "/employees";
    case "department":
    case "team":
      return "/teams";
    case "project":
      return "/projects";
    case "work_object":
      return "/work-objects";
    case "leave_request":
      return "/leaves";
    case "attachment":
      return "/work-objects";
    case "notification":
      return "/notifications";
    case "announcement":
      return "/announcements";
    default:
      return null;
  }
}

function timelineBucket(event: Event): string {
  const createdAt = new Date(event.created_at);
  if (Number.isNaN(createdAt.getTime())) return "Older";
  const today = new Date();
  const startOfToday = new Date(today.getFullYear(), today.getMonth(), today.getDate());
  const startOfYesterday = new Date(startOfToday);
  startOfYesterday.setDate(startOfToday.getDate() - 1);
  if (createdAt >= startOfToday) return "Today";
  if (createdAt >= startOfYesterday) return "Yesterday";
  return "Older";
}

function auditActor(entry: AuditLog, employeeNames: Record<string, string>): string {
  return entry.actor_name ?? entry.actor_employee_name ?? (entry.actor_employee_id ? employeeNames[entry.actor_employee_id] : null) ?? "System";
}

export function EventsPage({ data, selectedCompany, isLoadingModules, moduleError, onRetry }: ModulePageProps): JSX.Element {
  const [searchFilter, setSearchFilter] = useState("");
  const [eventTypeFilter, setEventTypeFilter] = useState("");
  const [targetFilter, setTargetFilter] = useState("");
  const [actorFilter, setActorFilter] = useState("");
  const [projectFilter, setProjectFilter] = useState("");
  const [dateFromFilter, setDateFromFilter] = useState("");
  const [dateToFilter, setDateToFilter] = useState("");
  const [auditOnly, setAuditOnly] = useState(false);

  const employeeNames = useMemo(
    () => Object.fromEntries(data.employees.map((employee) => [employee.id, employee.full_name])),
    [data.employees],
  );

  const eventTypes = useMemo(() => Array.from(new Set(data.events.map((event) => event.event_type))).sort(), [data.events]);
  const targetTypes = useMemo(
    () => Array.from(new Set(data.events.map((event) => event.target_entity_type).filter(Boolean) as string[])).sort(),
    [data.events],
  );

  const filteredEvents = useMemo(() => {
    const query = searchFilter.trim().toLowerCase();
    return data.events.filter((event) => {
      const searchable = [
        event.title,
        event.description,
        event.event_type,
        event.target_entity_type,
        event.related_entity_type,
        eventActor(event, employeeNames),
        eventTarget(event),
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();
      const eventDate = event.created_at.slice(0, 10);
      if (query && !searchable.includes(query)) return false;
      if (eventTypeFilter && event.event_type !== eventTypeFilter) return false;
      if (targetFilter && event.target_entity_type !== targetFilter) return false;
      if (actorFilter && event.actor_employee_id !== actorFilter) return false;
      if (
        projectFilter &&
        !(
          (event.target_entity_type === "project" && event.target_entity_id === projectFilter) ||
          (event.related_entity_type === "project" && event.related_entity_id === projectFilter)
        )
      ) {
        return false;
      }
      if (dateFromFilter && eventDate < dateFromFilter) return false;
      if (dateToFilter && eventDate > dateToFilter) return false;
      if (auditOnly && !isAuditRelevant(event)) return false;
      return true;
    });
  }, [actorFilter, auditOnly, data.events, dateFromFilter, dateToFilter, employeeNames, eventTypeFilter, projectFilter, searchFilter, targetFilter]);

  const groupedEvents = useMemo(() => {
    const groups: Record<string, Event[]> = { Today: [], Yesterday: [], Older: [] };
    filteredEvents.forEach((event) => {
      groups[timelineBucket(event)].push(event);
    });
    return Object.entries(groups).filter(([, events]) => events.length > 0);
  }, [filteredEvents]);

  const hasActiveFilters = Boolean(searchFilter || eventTypeFilter || targetFilter || actorFilter || projectFilter || dateFromFilter || dateToFilter || auditOnly);

  return (
    <>
    <SectionPanel
      eyebrow={selectedCompany?.name ?? "Universal timeline"}
      title="Events"
    >
      <ModuleBoundary
        emptyDescription="Important backend actions will appear here as company memory events."
        emptyTitle="No events yet"
        error={moduleError}
        isEmpty={data.events.length === 0}
        isLoading={isLoadingModules}
        onRetry={onRetry}
      >
        <FilterBar
          isResetDisabled={!hasActiveFilters}
          onReset={() => {
            setSearchFilter("");
            setEventTypeFilter("");
            setTargetFilter("");
            setActorFilter("");
            setProjectFilter("");
            setDateFromFilter("");
            setDateToFilter("");
            setAuditOnly(false);
          }}
        >
          <FilterField label="Search">
            <TextInput placeholder="Title, actor, target" value={searchFilter} onChange={(event) => setSearchFilter(event.target.value)} />
          </FilterField>
          <FilterField label="Event type">
            <SelectInput value={eventTypeFilter} onChange={(event) => setEventTypeFilter(event.target.value)}>
              <option value="">All event types</option>
              {eventTypes.map((eventType) => (
                <option key={eventType} value={eventType}>
                  {formatLabel(eventType)}
                </option>
              ))}
            </SelectInput>
          </FilterField>
          <FilterField label="Actor">
            <SelectInput value={actorFilter} onChange={(event) => setActorFilter(event.target.value)}>
              <option value="">All actors</option>
              {data.employees.map((employee) => (
                <option key={employee.id} value={employee.id}>
                  {employee.full_name}
                </option>
              ))}
            </SelectInput>
          </FilterField>
          <FilterField label="Project">
            <SelectInput value={projectFilter} onChange={(event) => setProjectFilter(event.target.value)}>
              <option value="">All projects</option>
              {data.projects.map((project) => (
                <option key={project.id} value={project.id}>
                  {project.name}
                </option>
              ))}
            </SelectInput>
          </FilterField>
          <FilterField label="Target">
            <SelectInput value={targetFilter} onChange={(event) => setTargetFilter(event.target.value)}>
              <option value="">All targets</option>
              {targetTypes.map((targetType) => (
                <option key={targetType} value={targetType}>
                  {formatLabel(targetType)}
                </option>
              ))}
            </SelectInput>
          </FilterField>
          <FilterField label="From">
            <TextInput type="date" value={dateFromFilter} onChange={(event) => setDateFromFilter(event.target.value)} />
          </FilterField>
          <FilterField label="To">
            <TextInput type="date" value={dateToFilter} onChange={(event) => setDateToFilter(event.target.value)} />
          </FilterField>
          <label className="flex min-h-10 items-center gap-3 rounded-md border border-grid-200 bg-white px-3 text-sm font-bold text-ink-700 xl:col-span-2">
            <input
              checked={auditOnly}
              className="size-4 rounded border-grid-300"
              type="checkbox"
              onChange={(event) => setAuditOnly(event.target.checked)}
            />
            Audit relevant only
          </label>
        </FilterBar>

        {groupedEvents.length === 0 ? (
          <div className="px-5 py-10 text-center">
            <p className="text-sm font-bold text-ink-950">No events match these filters</p>
            <p className="mt-1 text-sm font-medium text-ink-500">Reset filters to return to the full company timeline.</p>
          </div>
        ) : (
          <div className="divide-y divide-grid-100">
            {groupedEvents.map(([bucket, events]) => (
              <section key={bucket}>
                <div className="bg-grid-50 px-5 py-2">
                  <p className="text-xs font-bold uppercase tracking-normal text-ink-500">{bucket}</p>
                </div>
                <div className="divide-y divide-grid-100">
                  {events.map((event) => {
                    const route = eventRoute(event);
                    return (
                      <article key={event.id} className="flex flex-col gap-3 px-5 py-4 lg:flex-row lg:items-center lg:justify-between">
                        <div className="flex min-w-0 items-start gap-3">
                          <span className="flex size-10 shrink-0 items-center justify-center rounded-md bg-grid-100 text-ink-700">
                            <Clock3 className="size-4" aria-hidden="true" />
                          </span>
                          <div className="min-w-0">
                            <p className="text-sm font-bold text-ink-950">{event.title}</p>
                            {event.description ? <p className="mt-1 line-clamp-2 text-sm text-ink-500">{event.description}</p> : null}
                            <p className="mt-2 text-xs font-semibold text-ink-500">
                              {formatTime(event.created_at)} / {formatDate(event.created_at)} / {eventActor(event, employeeNames)} / {eventTarget(event)}
                            </p>
                            {event.related_entity_type ? (
                              <p className="mt-1 text-xs font-semibold text-ink-500">
                                Related: {formatLabel(event.related_entity_type)}
                                {event.related_entity_id ? ` ${event.related_entity_id.slice(0, 8)}` : ""}
                              </p>
                            ) : null}
                          </div>
                        </div>
                        <div className="flex shrink-0 flex-wrap items-center gap-2">
                          <Badge label={formatLabel(event.event_type)} tone="teal" />
                          <Badge label={event.target_entity_type ? formatLabel(event.target_entity_type) : "Company"} tone="slate" />
                          {isAuditRelevant(event) ? <Badge label="Audit" tone="amber" /> : null}
                          {route ? (
                            <Button
                              className="size-9 px-0"
                              aria-label="Open related page"
                              icon={<ExternalLink className="size-4" aria-hidden="true" />}
                              onClick={() => {
                                window.location.hash = route;
                              }}
                            >
                              <span className="sr-only">Open related page</span>
                            </Button>
                          ) : null}
                        </div>
                      </article>
                    );
                  })}
                </div>
              </section>
            ))}
          </div>
        )}
      </ModuleBoundary>
    </SectionPanel>

    <div className="mt-6">
      <SectionPanel eyebrow="Audit trail" title="Strong Audit Log">
        <ModuleBoundary
          emptyDescription="Audit-relevant events such as billing, settings, employee, file, project, work, leave, and announcement changes will appear here."
          emptyTitle="No audit log entries"
          error={moduleError}
          isEmpty={data.auditLogs.length === 0}
          isLoading={isLoadingModules}
          onRetry={onRetry}
        >
          <div className="divide-y divide-grid-100">
            {data.auditLogs.slice(0, 50).map((entry) => (
              <article key={entry.id} className="grid gap-3 px-5 py-4 lg:grid-cols-[1.2fr_0.7fr_0.7fr_120px] lg:items-center">
                <div className="min-w-0">
                  <p className="text-sm font-bold text-ink-950">{entry.title}</p>
                  <p className="mt-1 line-clamp-2 text-sm font-medium text-ink-500">{entry.summary ?? entry.description ?? "Audit event recorded."}</p>
                </div>
                <div>
                  <p className="text-xs font-bold uppercase tracking-normal text-ink-500">Actor</p>
                  <p className="mt-1 text-sm font-semibold text-ink-800">{auditActor(entry, employeeNames)}</p>
                  {entry.actor_role ? <p className="text-xs font-semibold text-ink-500">{formatLabel(entry.actor_role)}</p> : null}
                </div>
                <div>
                  <p className="text-xs font-bold uppercase tracking-normal text-ink-500">Target</p>
                  <p className="mt-1 text-sm font-semibold text-ink-800">{entry.target_label ? formatLabel(entry.target_label) : eventTarget(entry)}</p>
                </div>
                <div className="flex flex-col items-start gap-2 lg:items-end">
                  <Badge label={formatLabel(entry.event_type)} tone="amber" />
                  <span className="text-xs font-semibold text-ink-500">{formatTime(entry.created_at)}</span>
                </div>
              </article>
            ))}
          </div>
        </ModuleBoundary>
      </SectionPanel>
    </div>
    </>
  );
}
