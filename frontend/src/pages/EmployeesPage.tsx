import { Plus, UserRoundCheck } from "lucide-react";

import { employees } from "../data/sampleData";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { DataTable, type DataTableColumn } from "../components/ui/DataTable";
import { SectionPanel } from "../components/ui/SectionPanel";
import { statusTone } from "../components/ui/tone";
import type { EmployeeRecord } from "../types/domain";

const columns: DataTableColumn<EmployeeRecord>[] = [
  {
    key: "name",
    label: "Employee",
    render: (employee) => (
      <span className="flex min-w-48 items-center gap-3">
        <span className="flex size-9 shrink-0 items-center justify-center rounded-md bg-grid-100 text-ink-700">
          <UserRoundCheck className="size-4" aria-hidden="true" />
        </span>
        <span className="min-w-0">
          <span className="block truncate font-bold text-ink-950">{employee.name}</span>
          <span className="block truncate text-xs text-ink-500">{employee.role}</span>
        </span>
      </span>
    ),
  },
  { key: "team", label: "Team", render: (employee) => employee.team },
  { key: "status", label: "Status", render: (employee) => <Badge label={employee.status} tone={statusTone(employee.status)} /> },
  { key: "work", label: "Active work", render: (employee) => employee.workCount.toString(), className: "text-right" },
];

export function EmployeesPage(): JSX.Element {
  return (
    <SectionPanel
      eyebrow="People directory"
      title="Employees"
      action={<Button variant="primary" icon={<Plus className="size-4" aria-hidden="true" />}>Add employee</Button>}
    >
      <DataTable columns={columns} rows={employees} getRowKey={(employee) => employee.id} />
    </SectionPanel>
  );
}
