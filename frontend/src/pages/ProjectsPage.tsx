import { Plus } from "lucide-react";

import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { DataTable, type DataTableColumn } from "../components/ui/DataTable";
import { ModuleBoundary } from "../components/ui/ModuleBoundary";
import { ProgressBar } from "../components/ui/ProgressBar";
import { SectionPanel } from "../components/ui/SectionPanel";
import { priorityTone, statusTone } from "../components/ui/tone";
import type { Project } from "../types/api";
import type { ModulePageProps } from "../types/page";
import { formatLabel } from "../utils/format";

const columns: DataTableColumn<Project>[] = [
  { key: "name", label: "Project", render: (project) => <span className="font-bold text-ink-950">{project.name}</span> },
  { key: "owner", label: "Owner", render: (project) => project.owner_employee_id ? "Assigned" : "No owner" },
  { key: "status", label: "Status", render: (project) => <Badge label={formatLabel(project.status)} tone={statusTone(project.status)} /> },
  { key: "priority", label: "Priority", render: (project) => <Badge label={formatLabel(project.priority)} tone={priorityTone(project.priority)} /> },
  { key: "progress", label: "Progress", render: (project) => <ProgressBar value={project.progress_percent} /> },
];

export function ProjectsPage({ data, selectedCompany, isLoadingModules, moduleError, onRetry }: ModulePageProps): JSX.Element {
  return (
    <SectionPanel
      eyebrow={selectedCompany?.name ?? "Delivery tracking"}
      title="Projects"
      action={<Button disabled variant="primary" icon={<Plus className="size-4" aria-hidden="true" />}>New project</Button>}
    >
      <ModuleBoundary
        emptyDescription="Projects created through the backend API will show here with status, priority, and progress."
        emptyTitle="No projects yet"
        error={moduleError}
        isEmpty={data.projects.length === 0}
        isLoading={isLoadingModules}
        onRetry={onRetry}
      >
        <DataTable columns={columns} rows={data.projects} getRowKey={(project) => project.id} />
      </ModuleBoundary>
    </SectionPanel>
  );
}
