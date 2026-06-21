import { Building2, Plus, UsersRound } from "lucide-react";
import { type FormEvent, useMemo, useState } from "react";

import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { DataTable, type DataTableColumn } from "../components/ui/DataTable";
import { FieldShell, SelectInput, TextArea, TextInput } from "../components/ui/FormControls";
import { Modal } from "../components/ui/Modal";
import { ModuleBoundary } from "../components/ui/ModuleBoundary";
import { SectionPanel } from "../components/ui/SectionPanel";
import type { Department, DepartmentCreatePayload, Team, TeamCreatePayload } from "../types/api";
import type { ModulePageProps } from "../types/page";

interface TeamsPageProps extends ModulePageProps {
  onCreateDepartment: (payload: Omit<DepartmentCreatePayload, "company_id">) => Promise<void>;
  onCreateTeam: (payload: Omit<TeamCreatePayload, "company_id">) => Promise<void>;
}

const initialDepartmentForm = {
  name: "",
  description: "",
};

const initialTeamForm = {
  name: "",
  department_id: "",
  lead_employee_id: "",
  description: "",
};

export function TeamsPage({
  data,
  selectedCompany,
  isLoadingModules,
  moduleError,
  onRetry,
  onCreateDepartment,
  onCreateTeam,
  isMutating,
}: TeamsPageProps): JSX.Element {
  const [departmentForm, setDepartmentForm] = useState(initialDepartmentForm);
  const [teamForm, setTeamForm] = useState(initialTeamForm);
  const [departmentError, setDepartmentError] = useState<string | null>(null);
  const [teamError, setTeamError] = useState<string | null>(null);
  const [isDepartmentModalOpen, setIsDepartmentModalOpen] = useState(false);
  const [isTeamModalOpen, setIsTeamModalOpen] = useState(false);

  const departmentNames = useMemo(
    () => Object.fromEntries(data.departments.map((department) => [department.id, department.name])),
    [data.departments],
  );
  const employeeNames = useMemo(() => Object.fromEntries(data.employees.map((employee) => [employee.id, employee.full_name])), [data.employees]);

  const departmentColumns: DataTableColumn<Department>[] = [
    {
      key: "name",
      label: "Department",
      render: (department) => (
        <span className="flex min-w-56 items-center gap-3">
          <span className="flex size-9 shrink-0 items-center justify-center rounded-md bg-grid-100 text-ink-700">
            <Building2 className="size-4" aria-hidden="true" />
          </span>
          <span className="min-w-0">
            <span className="block truncate font-bold text-ink-950">{department.name}</span>
            <span className="block truncate text-xs text-ink-500">{department.description ?? "No description"}</span>
          </span>
        </span>
      ),
    },
    {
      key: "employees",
      label: "Employees",
      render: (department) => data.employees.filter((employee) => employee.department_id === department.id).length,
    },
    {
      key: "teams",
      label: "Teams",
      render: (department) => data.teams.filter((team) => team.department_id === department.id).length,
    },
    { key: "active", label: "Status", render: (department) => <Badge label={department.is_active ? "Active" : "Inactive"} tone={department.is_active ? "green" : "slate"} /> },
  ];

  const teamColumns: DataTableColumn<Team>[] = [
    {
      key: "name",
      label: "Team",
      render: (team) => (
        <span className="flex min-w-56 items-center gap-3">
          <span className="flex size-9 shrink-0 items-center justify-center rounded-md bg-grid-100 text-ink-700">
            <UsersRound className="size-4" aria-hidden="true" />
          </span>
          <span className="min-w-0">
            <span className="block truncate font-bold text-ink-950">{team.name}</span>
            <span className="block truncate text-xs text-ink-500">{team.description ?? "No description"}</span>
          </span>
        </span>
      ),
    },
    { key: "department", label: "Department", render: (team) => team.department_id ? departmentNames[team.department_id] ?? "Assigned" : team.department ?? "Not set" },
    { key: "lead", label: "Lead", render: (team) => team.lead_employee_id ? employeeNames[team.lead_employee_id] ?? "Assigned" : "No lead" },
    {
      key: "members",
      label: "Members",
      render: (team) => data.employees.filter((employee) => employee.team_id === team.id).length,
    },
    { key: "active", label: "Status", render: (team) => <Badge label={team.is_active ? "Active" : "Inactive"} tone={team.is_active ? "green" : "slate"} /> },
  ];

  function openDepartmentModal(): void {
    setDepartmentForm(initialDepartmentForm);
    setDepartmentError(null);
    setIsDepartmentModalOpen(true);
  }

  function openTeamModal(): void {
    setTeamForm(initialTeamForm);
    setTeamError(null);
    setIsTeamModalOpen(true);
  }

  async function handleDepartmentSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    setDepartmentError(null);

    const name = departmentForm.name.trim();
    if (!name) {
      setDepartmentError("Department name is required.");
      return;
    }

    try {
      await onCreateDepartment({
        name,
        description: departmentForm.description.trim() || null,
        is_active: true,
      });
      setIsDepartmentModalOpen(false);
    } catch {
      setDepartmentError("Department could not be created. Check the name and try again.");
    }
  }

  async function handleTeamSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    setTeamError(null);

    const name = teamForm.name.trim();
    if (!name) {
      setTeamError("Team name is required.");
      return;
    }

    const departmentName = teamForm.department_id ? departmentNames[teamForm.department_id] ?? null : null;

    try {
      await onCreateTeam({
        name,
        department_id: teamForm.department_id || null,
        department: departmentName,
        lead_employee_id: teamForm.lead_employee_id || null,
        description: teamForm.description.trim() || null,
        is_active: true,
      });
      setIsTeamModalOpen(false);
    } catch {
      setTeamError("Team could not be created. Check the details and try again.");
    }
  }

  return (
    <>
      <div className="space-y-6">
        <SectionPanel
          eyebrow={selectedCompany?.name ?? "Org structure"}
          title="Departments"
          action={<Button disabled={!selectedCompany} variant="primary" icon={<Plus className="size-4" aria-hidden="true" />} onClick={openDepartmentModal}>Create department</Button>}
        >
          <ModuleBoundary
            emptyDescription={selectedCompany ? "Create departments to group employees and teams." : "Create or select a company before adding departments."}
            emptyTitle="No departments yet"
            error={moduleError}
            isEmpty={data.departments.length === 0}
            isLoading={isLoadingModules}
            onRetry={onRetry}
            emptyAction={selectedCompany ? <Button variant="primary" icon={<Plus className="size-4" aria-hidden="true" />} onClick={openDepartmentModal}>Create department</Button> : undefined}
          >
            <DataTable columns={departmentColumns} rows={data.departments} getRowKey={(department) => department.id} />
          </ModuleBoundary>
        </SectionPanel>

        <SectionPanel
          eyebrow="Delivery groups"
          title="Teams"
          action={<Button disabled={!selectedCompany} variant="primary" icon={<Plus className="size-4" aria-hidden="true" />} onClick={openTeamModal}>Create team</Button>}
        >
          <ModuleBoundary
            emptyDescription={selectedCompany ? "Create teams and optionally assign a department and lead." : "Create or select a company before adding teams."}
            emptyTitle="No teams yet"
            error={moduleError}
            isEmpty={data.teams.length === 0}
            isLoading={isLoadingModules}
            onRetry={onRetry}
            emptyAction={selectedCompany ? <Button variant="primary" icon={<Plus className="size-4" aria-hidden="true" />} onClick={openTeamModal}>Create team</Button> : undefined}
          >
            <DataTable columns={teamColumns} rows={data.teams} getRowKey={(team) => team.id} />
          </ModuleBoundary>
        </SectionPanel>
      </div>

      <Modal description="Departments belong to the authenticated company workspace." isOpen={isDepartmentModalOpen} title="Create department" onClose={() => setIsDepartmentModalOpen(false)}>
        <form className="space-y-4 p-5" onSubmit={handleDepartmentSubmit}>
          <FieldShell label="Department name">
            <TextInput required value={departmentForm.name} onChange={(event) => setDepartmentForm((current) => ({ ...current, name: event.target.value }))} />
          </FieldShell>
          <FieldShell label="Description">
            <TextArea value={departmentForm.description} onChange={(event) => setDepartmentForm((current) => ({ ...current, description: event.target.value }))} />
          </FieldShell>
          {departmentError ? <p className="text-sm font-semibold text-rose-700">{departmentError}</p> : null}
          <div className="flex justify-end gap-2 border-t border-grid-200 pt-4">
            <Button onClick={() => setIsDepartmentModalOpen(false)}>Cancel</Button>
            <Button disabled={isMutating} type="submit" variant="primary">
              {isMutating ? "Saving..." : "Create department"}
            </Button>
          </div>
        </form>
      </Modal>

      <Modal description="Teams can link to a department and an employee lead." isOpen={isTeamModalOpen} title="Create team" onClose={() => setIsTeamModalOpen(false)}>
        <form className="space-y-4 p-5" onSubmit={handleTeamSubmit}>
          <div className="grid gap-4 sm:grid-cols-2">
            <FieldShell label="Team name">
              <TextInput required value={teamForm.name} onChange={(event) => setTeamForm((current) => ({ ...current, name: event.target.value }))} />
            </FieldShell>
            <FieldShell label="Department">
              <SelectInput value={teamForm.department_id} onChange={(event) => setTeamForm((current) => ({ ...current, department_id: event.target.value }))}>
                <option value="">No department</option>
                {data.departments.map((department) => (
                  <option key={department.id} value={department.id}>
                    {department.name}
                  </option>
                ))}
              </SelectInput>
            </FieldShell>
            <FieldShell label="Lead employee">
              <SelectInput value={teamForm.lead_employee_id} onChange={(event) => setTeamForm((current) => ({ ...current, lead_employee_id: event.target.value }))}>
                <option value="">No lead</option>
                {data.employees.map((employee) => (
                  <option key={employee.id} value={employee.id}>
                    {employee.full_name}
                  </option>
                ))}
              </SelectInput>
            </FieldShell>
          </div>
          <FieldShell label="Description">
            <TextArea value={teamForm.description} onChange={(event) => setTeamForm((current) => ({ ...current, description: event.target.value }))} />
          </FieldShell>
          {teamError ? <p className="text-sm font-semibold text-rose-700">{teamError}</p> : null}
          <div className="flex justify-end gap-2 border-t border-grid-200 pt-4">
            <Button onClick={() => setIsTeamModalOpen(false)}>Cancel</Button>
            <Button disabled={isMutating} type="submit" variant="primary">
              {isMutating ? "Saving..." : "Create team"}
            </Button>
          </div>
        </form>
      </Modal>
    </>
  );
}
