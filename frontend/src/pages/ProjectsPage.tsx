import { Plus } from "lucide-react";

import { projects } from "../data/sampleData";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { DataTable, type DataTableColumn } from "../components/ui/DataTable";
import { ProgressBar } from "../components/ui/ProgressBar";
import { SectionPanel } from "../components/ui/SectionPanel";
import { priorityTone, statusTone } from "../components/ui/tone";
import type { ProjectRecord } from "../types/domain";

const columns: DataTableColumn<ProjectRecord>[] = [
  { key: "name", label: "Project", render: (project) => <span className="font-bold text-ink-950">{project.name}</span> },
  { key: "owner", label: "Owner", render: (project) => project.owner },
  { key: "status", label: "Status", render: (project) => <Badge label={project.status} tone={statusTone(project.status)} /> },
  { key: "priority", label: "Priority", render: (project) => <Badge label={project.priority} tone={priorityTone(project.priority)} /> },
  { key: "progress", label: "Progress", render: (project) => <ProgressBar value={project.progress} /> },
];

export function ProjectsPage(): JSX.Element {
  return (
    <SectionPanel
      eyebrow="Delivery tracking"
      title="Projects"
      action={<Button variant="primary" icon={<Plus className="size-4" aria-hidden="true" />}>New project</Button>}
    >
      <DataTable columns={columns} rows={projects} getRowKey={(project) => project.id} />
    </SectionPanel>
  );
}
