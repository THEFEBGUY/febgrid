import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { api, ApiError } from "../services/api";
import type {
  Company,
  CompanyCreatePayload,
  DepartmentCreatePayload,
  EmployeeCreatePayload,
  EmployeeUpdatePayload,
  FebGridData,
  LeaveCreatePayload,
  ProjectCreatePayload,
  ProjectMemberCreatePayload,
  ProjectUpdatePayload,
  TeamCreatePayload,
  WorkObjectCreatePayload,
} from "../types/api";

const emptyData: FebGridData = {
  companies: [],
  departments: [],
  employees: [],
  teams: [],
  projects: [],
  workObjects: [],
  leaves: [],
  events: [],
  notifications: [],
};

type ModuleDataKey = Exclude<keyof FebGridData, "companies">;
type ModuleErrors = Partial<Record<ModuleDataKey, string>>;

interface FebGridDataState {
  data: FebGridData;
  selectedCompanyId: string | null;
  selectedCompany: Company | null;
  isLoadingCompanies: boolean;
  isLoadingModules: boolean;
  isMutating: boolean;
  error: string | null;
  moduleErrors: ModuleErrors;
  selectCompany: (companyId: string) => void;
  refreshCompanies: () => Promise<void>;
  refreshModules: () => Promise<void>;
  createCompany: (payload: CompanyCreatePayload) => Promise<void>;
  createEmployee: (payload: Omit<EmployeeCreatePayload, "company_id">) => Promise<void>;
  updateEmployee: (employeeId: string, payload: EmployeeUpdatePayload) => Promise<void>;
  deactivateEmployee: (employeeId: string) => Promise<void>;
  updateEmployeeStatus: (employeeId: string, currentStatus: string) => Promise<void>;
  createDepartment: (payload: Omit<DepartmentCreatePayload, "company_id">) => Promise<void>;
  createTeam: (payload: Omit<TeamCreatePayload, "company_id">) => Promise<void>;
  createProject: (payload: Omit<ProjectCreatePayload, "company_id">) => Promise<void>;
  updateProject: (projectId: string, payload: ProjectUpdatePayload) => Promise<void>;
  deactivateProject: (projectId: string) => Promise<void>;
  updateProjectStatus: (projectId: string, status: string) => Promise<void>;
  updateProjectPriority: (projectId: string, priority: string) => Promise<void>;
  addProjectMember: (projectId: string, payload: Omit<ProjectMemberCreatePayload, "company_id">) => Promise<void>;
  removeProjectMember: (projectId: string, employeeId: string) => Promise<void>;
  createWorkObject: (payload: Omit<WorkObjectCreatePayload, "company_id">) => Promise<void>;
  createLeave: (payload: Omit<LeaveCreatePayload, "company_id">) => Promise<void>;
}

interface UseFebGridDataOptions {
  enabled?: boolean;
}

function getErrorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  if (error instanceof Error) return error.message;
  return "Something went wrong while contacting the backend.";
}

function getStoredCompanyId(): string | null {
  try {
    return window.localStorage.getItem("febgrid.activeCompanyId");
  } catch {
    return null;
  }
}

function storeCompanyId(companyId: string): void {
  try {
    window.localStorage.setItem("febgrid.activeCompanyId", companyId);
  } catch {
    // Non-critical: the selector still works for the current session.
  }
}

function clearStoredCompanyId(): void {
  try {
    window.localStorage.removeItem("febgrid.activeCompanyId");
  } catch {
    // Non-critical: the selector still works for the current session.
  }
}

function findCompany(companies: Company[], companyId: string | null): Company | undefined {
  if (!companyId) return undefined;
  return companies.find((company) => company.id === companyId);
}

export function useFebGridData({ enabled = true }: UseFebGridDataOptions = {}): FebGridDataState {
  const [data, setData] = useState<FebGridData>(emptyData);
  const [selectedCompanyId, setSelectedCompanyId] = useState<string | null>(() => getStoredCompanyId());
  const [isLoadingCompanies, setIsLoadingCompanies] = useState(true);
  const [isLoadingModules, setIsLoadingModules] = useState(false);
  const [isMutating, setIsMutating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [moduleErrors, setModuleErrors] = useState<ModuleErrors>({});
  const moduleRequestIdRef = useRef(0);

  const selectedCompany = useMemo(
    () => data.companies.find((company) => company.id === selectedCompanyId) ?? null,
    [data.companies, selectedCompanyId],
  );

  const setSelectedCompanyIdOnce = useCallback((companyId: string | null): void => {
    setSelectedCompanyId((currentCompanyId) => {
      if (currentCompanyId === companyId) return currentCompanyId;

      moduleRequestIdRef.current += 1;

      if (companyId) {
        storeCompanyId(companyId);
      } else {
        clearStoredCompanyId();
      }

      return companyId;
    });
  }, []);

  const refreshCompanies = useCallback(async (): Promise<void> => {
    if (!enabled) {
      setData(emptyData);
      setModuleErrors({});
      setError(null);
      setIsLoadingCompanies(false);
      setIsLoadingModules(false);
      setSelectedCompanyIdOnce(null);
      return;
    }

    setIsLoadingCompanies(true);
    setError(null);
    try {
      const companies = await api.companies();
      setData((current) => ({ ...current, companies }));

      setSelectedCompanyId((currentCompanyId) => {
        if (findCompany(companies, currentCompanyId)) return currentCompanyId;

        const storedCompanyId = getStoredCompanyId();
        const nextCompany = findCompany(companies, storedCompanyId) ?? companies[0] ?? null;
        const nextCompanyId = nextCompany?.id ?? null;

        if (nextCompanyId === currentCompanyId) return currentCompanyId;
        if (nextCompanyId) storeCompanyId(nextCompanyId);
        else clearStoredCompanyId();

        return nextCompanyId;
      });
    } catch (caughtError) {
      setError(getErrorMessage(caughtError));
      setModuleErrors({});
      setData(emptyData);
      setSelectedCompanyIdOnce(null);
    } finally {
      setIsLoadingCompanies(false);
    }
  }, [enabled, setSelectedCompanyIdOnce]);

  const refreshModules = useCallback(async (): Promise<void> => {
    if (!enabled || !selectedCompanyId) {
      moduleRequestIdRef.current += 1;
      setData((current) => ({ ...emptyData, companies: current.companies }));
      setModuleErrors({});
      setIsLoadingModules(false);
      return;
    }

    const requestId = moduleRequestIdRef.current + 1;
    moduleRequestIdRef.current = requestId;

    setIsLoadingModules(true);
    setModuleErrors({});
    setData((current) => ({ ...current, ...emptyData, companies: current.companies }));

    const [departments, employees, teams, projects, workObjects, leaves, events, notifications] = await Promise.allSettled([
      api.departments(selectedCompanyId),
      api.employees(selectedCompanyId),
      api.teams(selectedCompanyId),
      api.projects(selectedCompanyId),
      api.workObjects(selectedCompanyId),
      api.leaves(selectedCompanyId),
      api.events(selectedCompanyId),
      api.notifications(selectedCompanyId),
    ]);

    const nextData: Partial<FebGridData> = {};
    const nextErrors: ModuleErrors = {};

    if (departments.status === "fulfilled") nextData.departments = departments.value;
    else nextErrors.departments = getErrorMessage(departments.reason);

    if (employees.status === "fulfilled") nextData.employees = employees.value;
    else nextErrors.employees = getErrorMessage(employees.reason);

    if (teams.status === "fulfilled") nextData.teams = teams.value;
    else nextErrors.teams = getErrorMessage(teams.reason);

    if (projects.status === "fulfilled") nextData.projects = projects.value;
    else nextErrors.projects = getErrorMessage(projects.reason);

    if (workObjects.status === "fulfilled") nextData.workObjects = workObjects.value;
    else nextErrors.workObjects = getErrorMessage(workObjects.reason);

    if (leaves.status === "fulfilled") nextData.leaves = leaves.value;
    else nextErrors.leaves = getErrorMessage(leaves.reason);

    if (events.status === "fulfilled") nextData.events = events.value;
    else nextErrors.events = getErrorMessage(events.reason);

    if (notifications.status === "fulfilled") nextData.notifications = notifications.value;
    else nextErrors.notifications = getErrorMessage(notifications.reason);

    if (moduleRequestIdRef.current !== requestId) return;

    setData((current) => ({ ...current, ...nextData }));
    setModuleErrors(nextErrors);
    setIsLoadingModules(false);
  }, [enabled, selectedCompanyId]);

  useEffect(() => {
    void refreshCompanies();
  }, [refreshCompanies]);

  useEffect(() => {
    void refreshModules();
  }, [refreshModules]);

  function selectCompany(companyId: string): void {
    if (!companyId) return;
    setSelectedCompanyIdOnce(companyId);
  }

  async function runMutation(action: () => Promise<void>): Promise<void> {
    setIsMutating(true);
    setModuleErrors({});
    setError(null);
    try {
      await action();
    } finally {
      setIsMutating(false);
    }
  }

  async function createCompany(payload: CompanyCreatePayload): Promise<void> {
    await runMutation(async () => {
      const company = await api.createCompany(payload);
      setData((current) => ({
        ...current,
        companies: current.companies.some((existingCompany) => existingCompany.id === company.id)
          ? current.companies.map((existingCompany) => (existingCompany.id === company.id ? company : existingCompany))
          : [...current.companies, company],
      }));
      setSelectedCompanyIdOnce(company.id);
      await refreshCompanies();
    });
  }

  async function createEmployee(payload: Omit<EmployeeCreatePayload, "company_id">): Promise<void> {
    if (!selectedCompanyId) return;
    await runMutation(async () => {
      await api.createEmployee({ ...payload, company_id: selectedCompanyId });
      await Promise.all([refreshModules(), refreshCompanies()]);
    });
  }

  async function updateEmployee(employeeId: string, payload: EmployeeUpdatePayload): Promise<void> {
    if (!selectedCompanyId) return;
    await runMutation(async () => {
      await api.updateEmployee(employeeId, selectedCompanyId, payload);
      await refreshModules();
    });
  }

  async function deactivateEmployee(employeeId: string): Promise<void> {
    if (!selectedCompanyId) return;
    await runMutation(async () => {
      await api.deactivateEmployee(employeeId, selectedCompanyId);
      await refreshModules();
    });
  }

  async function updateEmployeeStatus(employeeId: string, currentStatus: string): Promise<void> {
    if (!selectedCompanyId) return;
    await runMutation(async () => {
      await api.updateEmployeeStatus(employeeId, { company_id: selectedCompanyId, current_status: currentStatus });
      await refreshModules();
    });
  }

  async function createDepartment(payload: Omit<DepartmentCreatePayload, "company_id">): Promise<void> {
    if (!selectedCompanyId) return;
    await runMutation(async () => {
      await api.createDepartment({ ...payload, company_id: selectedCompanyId });
      await refreshModules();
    });
  }

  async function createTeam(payload: Omit<TeamCreatePayload, "company_id">): Promise<void> {
    if (!selectedCompanyId) return;
    await runMutation(async () => {
      await api.createTeam({ ...payload, company_id: selectedCompanyId });
      await refreshModules();
    });
  }

  async function createProject(payload: Omit<ProjectCreatePayload, "company_id">): Promise<void> {
    if (!selectedCompanyId) return;
    await runMutation(async () => {
      await api.createProject({ ...payload, company_id: selectedCompanyId });
      await refreshModules();
    });
  }

  async function updateProject(projectId: string, payload: ProjectUpdatePayload): Promise<void> {
    if (!selectedCompanyId) return;
    await runMutation(async () => {
      await api.updateProject(projectId, selectedCompanyId, payload);
      await refreshModules();
    });
  }

  async function deactivateProject(projectId: string): Promise<void> {
    if (!selectedCompanyId) return;
    await runMutation(async () => {
      await api.deactivateProject(projectId, selectedCompanyId);
      await refreshModules();
    });
  }

  async function updateProjectStatus(projectId: string, statusValue: string): Promise<void> {
    if (!selectedCompanyId) return;
    await runMutation(async () => {
      await api.updateProjectStatus(projectId, { company_id: selectedCompanyId, status: statusValue });
      await refreshModules();
    });
  }

  async function updateProjectPriority(projectId: string, priority: string): Promise<void> {
    if (!selectedCompanyId) return;
    await runMutation(async () => {
      await api.updateProjectPriority(projectId, { company_id: selectedCompanyId, priority });
      await refreshModules();
    });
  }

  async function addProjectMember(projectId: string, payload: Omit<ProjectMemberCreatePayload, "company_id">): Promise<void> {
    if (!selectedCompanyId) return;
    await runMutation(async () => {
      await api.addProjectMember(projectId, { ...payload, company_id: selectedCompanyId });
      await refreshModules();
    });
  }

  async function removeProjectMember(projectId: string, employeeId: string): Promise<void> {
    if (!selectedCompanyId) return;
    await runMutation(async () => {
      await api.removeProjectMember(projectId, selectedCompanyId, employeeId);
      await refreshModules();
    });
  }

  async function createWorkObject(payload: Omit<WorkObjectCreatePayload, "company_id">): Promise<void> {
    if (!selectedCompanyId) return;
    await runMutation(async () => {
      await api.createWorkObject({ ...payload, company_id: selectedCompanyId });
      await refreshModules();
    });
  }

  async function createLeave(payload: Omit<LeaveCreatePayload, "company_id">): Promise<void> {
    if (!selectedCompanyId) return;
    await runMutation(async () => {
      await api.createLeave({ ...payload, company_id: selectedCompanyId });
      await refreshModules();
    });
  }

  return {
    data,
    selectedCompanyId,
    selectedCompany,
    isLoadingCompanies,
    isLoadingModules,
    isMutating,
    error,
    moduleErrors,
    selectCompany,
    refreshCompanies,
    refreshModules,
    createCompany,
    createEmployee,
    updateEmployee,
    deactivateEmployee,
    updateEmployeeStatus,
    createDepartment,
    createTeam,
    createProject,
    updateProject,
    deactivateProject,
    updateProjectStatus,
    updateProjectPriority,
    addProjectMember,
    removeProjectMember,
    createWorkObject,
    createLeave,
  };
}
