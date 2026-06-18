import { Plus } from "lucide-react";

import { leaves } from "../data/sampleData";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { DataTable, type DataTableColumn } from "../components/ui/DataTable";
import { SectionPanel } from "../components/ui/SectionPanel";
import { statusTone } from "../components/ui/tone";
import type { LeaveRecord } from "../types/domain";

const columns: DataTableColumn<LeaveRecord>[] = [
  { key: "employee", label: "Employee", render: (leave) => <span className="font-bold text-ink-950">{leave.employee}</span> },
  { key: "type", label: "Type", render: (leave) => leave.type },
  { key: "dates", label: "Dates", render: (leave) => leave.dates },
  { key: "status", label: "Status", render: (leave) => <Badge label={leave.status} tone={statusTone(leave.status)} /> },
  { key: "approver", label: "Approver", render: (leave) => leave.approver },
];

export function LeavesPage(): JSX.Element {
  return (
    <SectionPanel
      eyebrow="Availability"
      title="Leave Requests"
      action={<Button variant="primary" icon={<Plus className="size-4" aria-hidden="true" />}>Submit leave</Button>}
    >
      <DataTable columns={columns} rows={leaves} getRowKey={(leave) => leave.id} />
    </SectionPanel>
  );
}
