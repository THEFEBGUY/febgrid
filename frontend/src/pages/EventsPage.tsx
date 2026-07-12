import { Clock3, ExternalLink } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";

import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { FilterBar, FilterField } from "../components/ui/FilterBar";
import { SelectInput, TextInput } from "../components/ui/FormControls";
import { ModuleBoundary } from "../components/ui/ModuleBoundary";
import { SectionPanel } from "../components/ui/SectionPanel";
import { api, ApiError } from "../services/api";
import type { AuditLog, Employee, Event, Project } from "../types/api";
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

export function EventsPage({ currentUserRole, selectedCompany }: ModulePageProps): JSX.Element {
  const [searchFilter, setSearchFilter] = useState("");
  const [eventTypeFilter, setEventTypeFilter] = useState("");
  const [targetFilter, setTargetFilter] = useState("");
  const [actorFilter, setActorFilter] = useState("");
  const [projectFilter, setProjectFilter] = useState("");
  const [dateFromFilter, setDateFromFilter] = useState("");
  const [dateToFilter, setDateToFilter] = useState("");
  const [auditOnly, setAuditOnly] = useState(false);
  const [events, setEvents] = useState<Event[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [isLoadingEvents, setIsLoadingEvents] = useState(false);
  const [isLoadingAudit, setIsLoadingAudit] = useState(false);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [timelineError, setTimelineError] = useState<string | null>(null);
  const [auditError, setAuditError] = useState<string | null>(null);
  const [hasMore, setHasMore] = useState(false);
  const [timelineRetry, setTimelineRetry] = useState(0);
  const [auditRetry, setAuditRetry] = useState(0);
  const canViewAudit = currentUserRole === "company_owner" || currentUserRole === "admin";
  const activeCompanyIdRef = useRef<string | null>(selectedCompany?.id ?? null);
  activeCompanyIdRef.current = selectedCompany?.id ?? null;

  const serverFilters = useMemo(() => ({
    actor_employee_id: actorFilter || undefined,
    audit_only: auditOnly || undefined,
    date_from: dateFromFilter ? `${dateFromFilter}T00:00:00Z` : undefined,
    date_to: dateToFilter ? `${dateToFilter}T23:59:59Z` : undefined,
    event_type: eventTypeFilter || undefined,
    project_id: projectFilter || undefined,
    q: searchFilter.trim() || undefined,
    target_entity_type: targetFilter || undefined,
    limit: 50,
  }), [actorFilter, auditOnly, dateFromFilter, dateToFilter, eventTypeFilter, projectFilter, searchFilter, targetFilter]);

  useEffect(() => {
    if (!selectedCompany) {
      setEvents([]);
      return;
    }
    const controller = new AbortController();
    let active = true;
    setEvents([]);
    setHasMore(false);
    const timer = globalThis.setTimeout(() => {
      setIsLoadingEvents(true);
      setTimelineError(null);
      void api.events(selectedCompany.id, serverFilters, controller.signal)
        .then((result) => {
          if (!active) return;
          setEvents(result);
          setHasMore(result.length === 50);
        })
        .catch((error: unknown) => {
          if (!active) return;
          if (error instanceof ApiError && error.status === 499) return;
          setTimelineError(error instanceof ApiError ? error.message : "Unable to load the company timeline.");
        })
        .finally(() => { if (active) setIsLoadingEvents(false); });
    }, searchFilter ? 250 : 0);
    return () => {
      globalThis.clearTimeout(timer);
      active = false;
      controller.abort();
    };
  }, [searchFilter, selectedCompany, serverFilters, timelineRetry]);

  useEffect(() => {
    if (!selectedCompany) {
      setAuditLogs([]);
      setEmployees([]);
      setProjects([]);
      return;
    }
    let active = true;
    setAuditLogs([]);
    setEmployees([]);
    setProjects([]);
    setIsLoadingAudit(true);
    setAuditError(null);
    void Promise.allSettled([
      canViewAudit ? api.auditLogs(selectedCompany.id, 50) : Promise.resolve([]),
      api.employees(selectedCompany.id),
      api.projects(selectedCompany.id),
    ]).then(([auditResult, employeeResult, projectResult]) => {
      if (!active) return;
      if (auditResult.status === "fulfilled") setAuditLogs(auditResult.value);
      else if (!(auditResult.reason instanceof ApiError && auditResult.reason.status === 499)) {
        setAuditError(auditResult.reason instanceof ApiError ? auditResult.reason.message : "Unable to load audit entries.");
      }
      if (employeeResult.status === "fulfilled") setEmployees(employeeResult.value);
      if (projectResult.status === "fulfilled") setProjects(projectResult.value);
      setIsLoadingAudit(false);
    });
    return () => { active = false; };
  }, [auditRetry, canViewAudit, selectedCompany]);

  async function loadMore(): Promise<void> {
    if (!selectedCompany || isLoadingMore || events.length === 0) return;
    const lastEvent = events[events.length - 1];
    const companyId = selectedCompany.id;
    setIsLoadingMore(true);
    setTimelineError(null);
    try {
      const next = await api.events(companyId, {
        ...serverFilters,
        before_created_at: lastEvent.created_at,
        before_id: lastEvent.id,
      });
      if (activeCompanyIdRef.current !== companyId) return;
      setEvents((current) => {
        const known = new Set(current.map((event) => event.id));
        return [...current, ...next.filter((event) => !known.has(event.id))];
      });
      setHasMore(next.length === 50);
    } catch (error) {
      if (!(error instanceof ApiError && error.status === 499)) {
        setTimelineError(error instanceof ApiError ? error.message : "Unable to load more events.");
      }
    } finally {
      setIsLoadingMore(false);
    }
  }

  const employeeNames = useMemo(
    () => Object.fromEntries(employees.map((employee) => [employee.id, employee.full_name])),
    [employees],
  );

  const eventTypes = useMemo(() => Array.from(new Set(events.map((event) => event.event_type))).sort(), [events]);
  const targetTypes = useMemo(
    () => Array.from(new Set(events.map((event) => event.target_entity_type).filter(Boolean) as string[])).sort(),
    [events],
  );

  const groupedEvents = useMemo(() => {
    const groups: Record<string, Event[]> = { Today: [], Yesterday: [], Older: [] };
    events.forEach((event) => {
      groups[timelineBucket(event)].push(event);
    });
    return Object.entries(groups).filter(([, events]) => events.length > 0);
  }, [events]);

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
        error={timelineError}
        isEmpty={events.length === 0}
        isLoading={isLoadingEvents}
        onRetry={async () => { setTimelineRetry((value) => value + 1); }}
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
              {employees.map((employee) => (
                <option key={employee.id} value={employee.id}>
                  {employee.full_name}
                </option>
              ))}
            </SelectInput>
          </FilterField>
          <FilterField label="Project">
            <SelectInput value={projectFilter} onChange={(event) => setProjectFilter(event.target.value)}>
              <option value="">All projects</option>
              {projects.map((project) => (
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
                <div className="febgrid-table-head px-5 py-2">
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
        {hasMore ? (
          <div className="flex justify-center border-t border-grid-100 px-5 py-4">
            <Button disabled={isLoadingMore} onClick={() => void loadMore()}>
              {isLoadingMore ? "Loading more..." : "Load more"}
            </Button>
          </div>
        ) : null}
      </ModuleBoundary>
    </SectionPanel>

    {canViewAudit ? <div className="mt-6">
      <SectionPanel eyebrow="Audit trail" title="Strong Audit Log">
        <ModuleBoundary
          emptyDescription="Audit-relevant events such as billing, settings, employee, file, project, work, leave, and announcement changes will appear here."
          emptyTitle="No audit log entries"
          error={auditError}
          isEmpty={auditLogs.length === 0}
          isLoading={isLoadingAudit}
          onRetry={async () => { setAuditRetry((value) => value + 1); }}
        >
          <div className="divide-y divide-grid-100">
            {auditLogs.map((entry) => (
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
    </div> : null}
    </>
  );
}
