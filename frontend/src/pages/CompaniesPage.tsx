import { Plus } from "lucide-react";

import { companies } from "../data/sampleData";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { DataTable, type DataTableColumn } from "../components/ui/DataTable";
import { SectionPanel } from "../components/ui/SectionPanel";
import { statusTone } from "../components/ui/tone";
import type { CompanyRecord } from "../types/domain";

const columns: DataTableColumn<CompanyRecord>[] = [
  { key: "name", label: "Company", render: (company) => <span className="font-bold text-ink-950">{company.name}</span> },
  { key: "industry", label: "Industry", render: (company) => company.industry },
  { key: "region", label: "Region", render: (company) => company.region },
  { key: "employees", label: "Employees", render: (company) => company.employees.toString(), className: "text-right" },
  { key: "status", label: "Status", render: (company) => <Badge label={company.status} tone={statusTone(company.status)} /> },
];

export function CompaniesPage(): JSX.Element {
  return (
    <SectionPanel
      eyebrow="Tenant foundation"
      title="Companies"
      action={<Button variant="primary" icon={<Plus className="size-4" aria-hidden="true" />}>New company</Button>}
    >
      <DataTable columns={columns} rows={companies} getRowKey={(company) => company.id} />
    </SectionPanel>
  );
}
