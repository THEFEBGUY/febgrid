import { Plus } from "lucide-react";

import { teams } from "../data/sampleData";
import { Button } from "../components/ui/Button";
import { DataTable, type DataTableColumn } from "../components/ui/DataTable";
import { SectionPanel } from "../components/ui/SectionPanel";
import type { TeamRecord } from "../types/domain";

const columns: DataTableColumn<TeamRecord>[] = [
  { key: "name", label: "Team", render: (team) => <span className="font-bold text-ink-950">{team.name}</span> },
  { key: "department", label: "Department", render: (team) => team.department },
  { key: "lead", label: "Lead", render: (team) => team.lead },
  { key: "members", label: "Members", render: (team) => team.members.toString(), className: "text-right" },
  { key: "workload", label: "Workload", render: (team) => <span className="font-bold text-ink-950">{team.workload}</span>, className: "text-right" },
];

export function TeamsPage(): JSX.Element {
  return (
    <SectionPanel
      eyebrow="Operating groups"
      title="Teams"
      action={<Button variant="primary" icon={<Plus className="size-4" aria-hidden="true" />}>Create team</Button>}
    >
      <DataTable columns={columns} rows={teams} getRowKey={(team) => team.id} />
    </SectionPanel>
  );
}
