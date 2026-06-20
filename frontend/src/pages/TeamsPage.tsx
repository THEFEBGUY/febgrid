import { Plus } from "lucide-react";

import { Button } from "../components/ui/Button";
import { DataTable, type DataTableColumn } from "../components/ui/DataTable";
import { ModuleBoundary } from "../components/ui/ModuleBoundary";
import { SectionPanel } from "../components/ui/SectionPanel";
import type { Team } from "../types/api";
import type { ModulePageProps } from "../types/page";

const columns: DataTableColumn<Team>[] = [
  { key: "name", label: "Team", render: (team) => <span className="font-bold text-ink-950">{team.name}</span> },
  { key: "department", label: "Department", render: (team) => team.department ?? "Not set" },
  { key: "lead", label: "Lead", render: (team) => team.lead_employee_id ? "Assigned" : "No lead" },
  { key: "description", label: "Description", render: (team) => team.description ?? "No description" },
];

export function TeamsPage({ data, selectedCompany, isLoadingModules, moduleError, onRetry }: ModulePageProps): JSX.Element {
  return (
    <SectionPanel
      eyebrow={selectedCompany?.name ?? "Operating groups"}
      title="Teams"
      action={<Button disabled variant="primary" icon={<Plus className="size-4" aria-hidden="true" />}>Create team</Button>}
    >
      <ModuleBoundary
        emptyDescription="Teams will appear here after they are created through the backend API."
        emptyTitle="No teams yet"
        error={moduleError}
        isEmpty={data.teams.length === 0}
        isLoading={isLoadingModules}
        onRetry={onRetry}
      >
        <DataTable columns={columns} rows={data.teams} getRowKey={(team) => team.id} />
      </ModuleBoundary>
    </SectionPanel>
  );
}
