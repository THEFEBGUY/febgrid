import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { api, ApiError } from "../services/api";
import type {
  AnnouncementCreatePayload,
  AnnouncementUpdatePayload,
  Company,
  CompanyCreatePayload,
  DepartmentCreatePayload,
  EmployeeCreatePayload,
  EmployeeUpdatePayload,
  FebGridData,
  LeaveCancelPayload,
  LeaveCreatePayload,
  LeaveDecisionPayload,
  LeaveUpdatePayload,
  ProjectCreatePayload,
  ProjectMemberCreatePayload,
  ProjectUpdatePayload,
  TeamCreatePayload,
  WorkObjectCreatePayload,
  WorkObjectUpdatePayload,
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
  announcements: [],
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
  updateWorkObject: (workObjectId: string, payload: WorkObjectUpdatePayload) => Promise<void>;
  deactivateWorkObject: (workObjectId: string) => Promise<void>;
  assignWorkObject: (workObjectId: string, assigneeEmployeeId: string | null) => Promise<void>;
  updateWorkObjectStatus: (workObjectId: string, status: string) => Promise<void>;
  updateWorkObjectPriority: (workObjectId: string, priority: string) => Promise<void>;
  completeWorkObject: (workObjectId: string) => Promise<void>;
  createLeave: (payload: Omit<LeaveCreatePayload, "company_id">) => Promise<void>;
  updateLeave: (leaveId: string, payload: LeaveUpdatePayload) => Promise<void>;
  approveLeave: (leaveId: string, payload: Omit<LeaveDecisionPayload, "company_id">) => Promise<void>;
  rejectLeave: (leaveId: string, payload: Omit<LeaveDecisionPayload, "company_id">) => Promise<void>;
  cancelLeave: (leaveId: string, payload: Omit<LeaveCancelPayload, "company_id">) => Promise<void>;
  deactivateLeave: (leaveId: string) => Promise<void>;
  markNotificationRead: (notificationId: string) => Promise<void>;
  markNotificationUnread: (notificationId: string) => Promise<void>;
  markAllNotificationsRead: () => Promise<void>;
  dismissNotification: (notificationId: string) => Promise<void>;
  createAnnouncement: (payload: Omit<AnnouncementCreatePayload, "company_id">) => Promise<void>;
  updateAnnouncement: (announcementId: string, payload: AnnouncementUpdatePayload) => Promise<void>;
  archiveAnnouncement: (announcementId: string) => Promise<void>;
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

    const [departments, employees, teams, projects, workObjects, leaves, events, notifications, announcements] = await Promise.allSettled([
      api.departments(selectedCompanyId),
      api.employees(selectedCompanyId),
      api.teams(selectedCompanyId),
      api.projects(selectedCompanyId),
      api.workObjects(selectedCompanyId),
      api.leaves(selectedCompanyId),
      api.events(selectedCompanyId),
      api.notifications(selectedCompanyId),
      api.announcements(selectedCompanyId),
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

    if (announcements.status === "fulfilled") nextData.announcements = announcements.value;
    else nextErrors.announcements = getErrorMessage(announcements.reason);

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

  async function updateWorkObject(workObjectId: string, payload: WorkObjectUpdatePayload): Promise<void> {
    if (!selectedCompanyId) return;
    await runMutation(async () => {
      await api.updateWorkObject(workObjectId, selectedCompanyId, payload);
      await refreshModules();
    });
  }

  async function deactivateWorkObject(workObjectId: string): Promise<void> {
    if (!selectedCompanyId) return;
    await runMutation(async () => {
      await api.deactivateWorkObject(workObjectId, selectedCompanyId);
      await refreshModules();
    });
  }

  async function assignWorkObject(workObjectId: string, assigneeEmployeeId: string | null): Promise<void> {
    if (!selectedCompanyId) return;
    await runMutation(async () => {
      await api.assignWorkObject(workObjectId, { company_id: selectedCompanyId, assignee_employee_id: assigneeEmployeeId });
      await refreshModules();
    });
  }

  async function updateWorkObjectStatus(workObjectId: string, statusValue: string): Promise<void> {
    if (!selectedCompanyId) return;
    await runMutation(async () => {
      await api.updateWorkObjectStatus(workObjectId, { company_id: selectedCompanyId, status: statusValue });
      await refreshModules();
    });
  }

  async function updateWorkObjectPriority(workObjectId: string, priority: string): Promise<void> {
    if (!selectedCompanyId) return;
    await runMutation(async () => {
      await api.updateWorkObjectPriority(workObjectId, { company_id: selectedCompanyId, priority });
      await refreshModules();
    });
  }

  async function completeWorkObject(workObjectId: string): Promise<void> {
    if (!selectedCompanyId) return;
    await runMutation(async () => {
      await api.completeWorkObject(workObjectId, { company_id: selectedCompanyId });
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

  async function updateLeave(leaveId: string, payload: LeaveUpdatePayload): Promise<void> {
    if (!selectedCompanyId) return;
    await runMutation(async () => {
      await api.updateLeave(leaveId, selectedCompanyId, payload);
      await refreshModules();
    });
  }

  async function approveLeave(leaveId: string, payload: Omit<LeaveDecisionPayload, "company_id">): Promise<void> {
    if (!selectedCompanyId) return;
    await runMutation(async () => {
      await api.approveLeave(leaveId, { ...payload, company_id: selectedCompanyId });
      await refreshModules();
    });
  }

  async function rejectLeave(leaveId: string, payload: Omit<LeaveDecisionPayload, "company_id">): Promise<void> {
    if (!selectedCompanyId) return;
    await runMutation(async () => {
      await api.rejectLeave(leaveId, { ...payload, company_id: selectedCompanyId });
      await refreshModules();
    });
  }

  async function cancelLeave(leaveId: string, payload: Omit<LeaveCancelPayload, "company_id">): Promise<void> {
    if (!selectedCompanyId) return;
    await runMutation(async () => {
      await api.cancelLeave(leaveId, { ...payload, company_id: selectedCompanyId });
      await refreshModules();
    });
  }

  async function deactivateLeave(leaveId: string): Promise<void> {
    if (!selectedCompanyId) return;
    await runMutation(async () => {
      await api.deactivateLeave(leaveId, selectedCompanyId);
      await refreshModules();
    });
  }

  async function markNotificationRead(notificationId: string): Promise<void> {
    if (!selectedCompanyId) return;
    await runMutation(async () => {
      await api.markNotificationRead(notificationId, selectedCompanyId);
      await refreshModules();
    });
  }

  async function markNotificationUnread(notificationId: string): Promise<void> {
    if (!selectedCompanyId) return;
    await runMutation(async () => {
      await api.markNotificationUnread(notificationId, selectedCompanyId);
      await refreshModules();
    });
  }

  async function markAllNotificationsRead(): Promise<void> {
    if (!selectedCompanyId) return;
    await runMutation(async () => {
      await api.markAllNotificationsRead(selectedCompanyId);
      await refreshModules();
    });
  }

  async function dismissNotification(notificationId: string): Promise<void> {
    if (!selectedCompanyId) return;
    await runMutation(async () => {
      await api.dismissNotification(notificationId, selectedCompanyId);
      await refreshModules();
    });
  }

  async function createAnnouncement(payload: Omit<AnnouncementCreatePayload, "company_id">): Promise<void> {
    if (!selectedCompanyId) return;
    await runMutation(async () => {
      await api.createAnnouncement({ ...payload, company_id: selectedCompanyId });
      await refreshModules();
    });
  }

  async function updateAnnouncement(announcementId: string, payload: AnnouncementUpdatePayload): Promise<void> {
    if (!selectedCompanyId) return;
    await runMutation(async () => {
      await api.updateAnnouncement(announcementId, selectedCompanyId, payload);
      await refreshModules();
    });
  }

  async function archiveAnnouncement(announcementId: string): Promise<void> {
    if (!selectedCompanyId) return;
    await runMutation(async () => {
      await api.archiveAnnouncement(announcementId, selectedCompanyId);
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
    updateWorkObject,
    deactivateWorkObject,
    assignWorkObject,
    updateWorkObjectStatus,
    updateWorkObjectPriority,
    completeWorkObject,
    createLeave,
    updateLeave,
    approveLeave,
    rejectLeave,
    cancelLeave,
    deactivateLeave,
    markNotificationRead,
    markNotificationUnread,
    markAllNotificationsRead,
    dismissNotification,
    createAnnouncement,
    updateAnnouncement,
    archiveAnnouncement,
  };
}
