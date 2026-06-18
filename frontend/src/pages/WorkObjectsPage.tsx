import { Plus } from "lucide-react";

import { workObjects } from "../data/sampleData";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { DataTable, type DataTableColumn } from "../components/ui/DataTable";
import { SectionPanel } from "../components/ui/SectionPanel";
import { priorityTone, statusTone } from "../components/ui/tone";
import type { WorkObjectRecord } from "../types/domain";

const columns: DataTableColumn<WorkObjectRecord>[] = [
  { key: "title", label: "Work object", render: (workObject) => <span className="font-bold text-ink-950">{workObject.title}</span> },
  { key: "type", label: "Type", render: (workObject) => workObject.type },
  { key: "assignee", label: "Assignee", render: (workObject) => workObject.assignee },
  { key: "status", label: "Status", render: (workObject) => <Badge label={workObject.status} tone={statusTone(workObject.status)} /> },
  { key: "priority", label: "Priority", render: (workObject) => <Badge label={workObject.priority} tone={priorityTone(workObject.priority)} /> },
  { key: "due", label: "Due", render: (workObject) => workObject.due },
];

export function WorkObjectsPage(): JSX.Element {
  return (
    <SectionPanel
      eyebrow="Core work engine"
      title="Work Objects"
      action={<Button variant="primary" icon={<Plus className="size-4" aria-hidden="true" />}>New object</Button>}
    >
      <DataTable columns={columns} rows={workObjects} getRowKey={(workObject) => workObject.id} />
    </SectionPanel>
  );
}
