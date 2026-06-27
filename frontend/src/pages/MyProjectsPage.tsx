import { BriefcaseBusiness, Eye } from "lucide-react";
import { useCallback, useMemo, useState } from "react";

import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { DataTable, type DataTableColumn } from "../components/ui/DataTable";
import { Modal } from "../components/ui/Modal";
import { ModuleBoundary } from "../components/ui/ModuleBoundary";
import { SectionPanel } from "../components/ui/SectionPanel";
import { EmptyState, ErrorState, LoadingState } from "../components/ui/States";
import { priorityTone, statusTone } from "../components/ui/tone";
import { api } from "../services/api";
import type { Event as FebGridEvent, Project, WorkObject } from "../types/api";
import type { ModulePageProps } from "../types/page";
import { compactList, formatDate, formatLabel, formatTime } from "../utils/format";

export function MyProjectsPage({
  data,
  selectedCompany,
  isLoadingModules,
  moduleError,
  onRetry,
}: ModulePageProps): JSX.Element {
  const selectedCompanyId = selectedCompany?.id ?? null;
  const [detailProject, setDetailProject] = useState<Project | null>(null);
  const [projectWorkObjects, setProjectWorkObjects] = useState<WorkObject[]>([]);
  const [projectEvents, setProjectEvents] = useState<FebGridEvent[]>([]);
  const [isDetailLoading, setIsDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);

  const visibleProjects = useMemo(() => data.projects.filter((project) => project.is_active), [data.projects]);

  const loadDetail = useCallback(
    async (projectId: string): Promise<void> => {
      if (!selectedCompanyId) return;
      setIsDetailLoading(true);
      setDetailError(null);
      try {
        const [workObjects, events] = await Promise.all([
          api.projectWorkObjects(projectId, selectedCompanyId),
          api.projectTimeline(projectId, selectedCompanyId),
        ]);
        setProjectWorkObjects(workObjects);
        setProjectEvents(events);
      } catch {
        setDetailError("Unable to load this project.");
      } finally {
        setIsDetailLoading(false);
      }
    },
    [selectedCompanyId],
  );

  function openDetail(project: Project): void {
    setDetailProject(project);
    setProjectWorkObjects([]);
    setProjectEvents([]);
    setDetailError(null);
    void loadDetail(project.id);
  }

  const columns: DataTableColumn<Project>[] = [
    {
      key: "project",
      label: "Project",
      render: (project) => (
        <span className="min-w-56">
          <span className="block truncate font-bold text-ink-950">{project.name}</span>
          <span className="block truncate text-xs text-ink-500">{project.code ?? "Assigned project"}</span>
        </span>
      ),
    },
    { key: "status", label: "Status", render: (project) => <Badge label={formatLabel(project.status)} tone={statusTone(project.status)} /> },
    { key: "priority", label: "Priority", render: (project) => <Badge label={formatLabel(project.priority)} tone={priorityTone(project.priority)} /> },
    {
      key: "progress",
      label: "Progress",
      render: (project) => (
        <div className="min-w-40">
          <div className="h-2 rounded-full bg-grid-100">
            <div className="h-2 rounded-full bg-brand-500" style={{ width: `${Math.min(100, Math.max(0, project.progress_percent))}%` }} />
          </div>
          <p className="mt-2 text-xs font-semibold text-ink-500">{project.progress_percent}%</p>
        </div>
      ),
    },
    { key: "due", label: "Due", render: (project) => formatDate(project.due_date) },
    {
      key: "actions",
      label: "Actions",
      render: (project) => (
        <div className="flex justify-end">
          <Button
            aria-label="View project details"
            className="size-9 px-0"
            icon={<Eye className="size-4" aria-hidden="true" />}
            title="View project details"
            onClick={() => openDetail(project)}
          >
            <span className="sr-only">View project details</span>
          </Button>
        </div>
      ),
      className: "text-right",
    },
  ];

  return (
    <>
      <SectionPanel eyebrow={selectedCompany?.name ?? "My projects"} title="My Projects">
        <ModuleBoundary
          emptyDescription="You do not have any assigned projects yet. Projects will appear here when you are added as an owner or member."
          emptyTitle="No projects assigned"
          error={moduleError}
          isEmpty={visibleProjects.length === 0}
          isLoading={isLoadingModules}
          onRetry={onRetry}
        >
          <DataTable columns={columns} rows={visibleProjects} getRowKey={(project) => project.id} />
        </ModuleBoundary>
      </SectionPanel>

      <Modal
        description="Your project context, linked work, and recent activity."
        isOpen={Boolean(detailProject)}
        title={detailProject?.name ?? "Project details"}
        onClose={() => setDetailProject(null)}
      >
        {detailProject ? (
          <div className="space-y-5 p-5">
            <div className="grid gap-4 sm:grid-cols-2">
              <DetailItem label="Status" value={formatLabel(detailProject.status)} tone={statusTone(detailProject.status)} />
              <DetailItem label="Priority" value={formatLabel(detailProject.priority)} tone={priorityTone(detailProject.priority)} />
              <DetailItem label="Progress" value={`${detailProject.progress_percent}%`} />
              <DetailItem label="Dates" value={compactList([formatDate(detailProject.start_date), `Due ${formatDate(detailProject.due_date)}`])} />
            </div>

            {detailProject.description ? (
              <p className="rounded-lg border border-grid-200 bg-grid-50 p-4 text-sm font-medium leading-6 text-ink-600">{detailProject.description}</p>
            ) : null}

            {isDetailLoading ? <LoadingState label="Loading project details" /> : null}
            {detailError ? <ErrorState message={detailError} onRetry={() => loadDetail(detailProject.id)} /> : null}

            {!isDetailLoading && !detailError ? (
              <>
                <section className="rounded-lg border border-grid-200">
                  <div className="flex items-center gap-2 border-b border-grid-200 px-4 py-3">
                    <BriefcaseBusiness className="size-4 text-ink-500" aria-hidden="true" />
                    <h3 className="text-sm font-bold text-ink-950">Linked work</h3>
                  </div>
                  {projectWorkObjects.length === 0 ? (
                    <EmptyState description="Linked project work will appear here." title="No linked work yet" />
                  ) : (
                    <div className="divide-y divide-grid-100">
                      {projectWorkObjects.slice(0, 8).map((workObject) => (
                        <article key={workObject.id} className="px-4 py-3">
                          <p className="text-sm font-bold text-ink-950">{workObject.title}</p>
                          <p className="mt-1 text-xs font-semibold text-ink-500">
                            {compactList([formatLabel(workObject.status), formatLabel(workObject.priority), `Due ${formatDate(workObject.due_date)}`])}
                          </p>
                        </article>
                      ))}
                    </div>
                  )}
                </section>

                <section className="rounded-lg border border-grid-200">
                  <div className="border-b border-grid-200 px-4 py-3">
                    <h3 className="text-sm font-bold text-ink-950">Recent activity</h3>
                  </div>
                  {projectEvents.length === 0 ? (
                    <EmptyState description="Project activity will appear here." title="No activity yet" />
                  ) : (
                    <div className="divide-y divide-grid-100">
                      {projectEvents.slice(0, 8).map((event) => (
                        <article key={event.id} className="px-4 py-3">
                          <p className="text-sm font-bold text-ink-950">{event.title}</p>
                          <p className="mt-1 text-xs font-semibold text-ink-500">
                            {formatTime(event.created_at)} / {formatLabel(event.event_type)}
                          </p>
                        </article>
                      ))}
                    </div>
                  )}
                </section>
              </>
            ) : null}
          </div>
        ) : null}
      </Modal>
    </>
  );
}

function DetailItem({ label, value, tone }: { label: string; value: string; tone?: "blue" | "green" | "amber" | "red" | "teal" | "slate" }): JSX.Element {
  return (
    <div className="rounded-lg border border-grid-200 bg-grid-50 p-4">
      <p className="text-xs font-bold uppercase tracking-normal text-ink-500">{label}</p>
      <div className="mt-2">{tone ? <Badge label={value} tone={tone} /> : <p className="text-sm font-bold text-ink-950">{value}</p>}</div>
    </div>
  );
}
