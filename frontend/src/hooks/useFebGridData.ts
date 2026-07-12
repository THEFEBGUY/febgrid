import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { getPageDataKeys, type FebGridModuleKey } from "../data/pageDataPlan";
import { markEntityInactive, prependEntity, replaceEntity, setNotificationReadState } from "../data/febGridState";
import { api, ApiError, cancelInFlightGetRequests } from "../services/api";
import type {
  AnnouncementCreatePayload,
  AnnouncementUpdatePayload,
  AttachmentUpdatePayload,
  AIJobCreatePayload,
  AISafetySettingsUpdatePayload,
  Company,
  CompanyCreatePayload,
  CompanyPlanUpdatePayload,
  CompanySettingsUpdatePayload,
  CustomFieldCreatePayload,
  CustomFieldUpdatePayload,
  DepartmentCreatePayload,
  EmployeeInvitationActionResult,
  EmployeeInvitationCreatePayload,
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
  UserRole,
  WorkObjectCreatePayload,
  WorkObjectTypeCreatePayload,
  WorkObjectTypeUpdatePayload,
  WorkObjectUpdatePayload,
} from "../types/api";
import type { PageKey } from "../types/domain";

const emptyData: FebGridData = {
  companies: [],
  aiCapabilities: null,
  aiProviderStatus: null,
  aiSafetySettings: null,
  aiJobQueueSummary: null,
  aiJobs: [],
  auditLogs: [],
  billingPlans: [],
  billingSummary: null,
  companySettings: null,
  industryTemplates: [],
  workObjectTypes: [],
  customFields: [],
  dashboardSummary: null,
  departments: [],
  employees: [],
  leaveApprovers: [],
  invitations: [],
  teams: [],
  projects: [],
  workObjects: [],
  leaves: [],
  events: [],
  notifications: [],
  notificationUnreadCount: 0,
  announcements: [],
  files: [],
};

type ModuleErrors = Partial<Record<FebGridModuleKey, string>>;

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
  createInvitation: (payload: Omit<EmployeeInvitationCreatePayload, "company_id">) => Promise<EmployeeInvitationActionResult | null>;
  resendInvitation: (invitationId: string) => Promise<EmployeeInvitationActionResult | null>;
  revokeInvitation: (invitationId: string) => Promise<void>;
  approveInvitation: (invitationId: string) => Promise<void>;
  rejectInvitation: (invitationId: string, rejectionReason?: string | null) => Promise<void>;
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
  updateCompanySettings: (payload: CompanySettingsUpdatePayload) => Promise<void>;
  updateCompanyPlan: (payload: CompanyPlanUpdatePayload) => Promise<void>;
  updateFile: (attachmentId: string, payload: AttachmentUpdatePayload) => Promise<void>;
  archiveFile: (attachmentId: string) => Promise<void>;
  restoreFile: (attachmentId: string) => Promise<void>;
  createAIJob: (payload: Omit<AIJobCreatePayload, "company_id">) => Promise<void>;
  runAIJob: (jobId: string) => Promise<void>;
  processNextAIJob: () => Promise<void>;
  retryAIJob: (jobId: string) => Promise<void>;
  recoverStaleAIJobs: () => Promise<void>;
  cancelAIJob: (jobId: string) => Promise<void>;
  updateAISafetySettings: (payload: AISafetySettingsUpdatePayload) => Promise<void>;
  applyIndustryTemplate: (templateKey: string) => Promise<void>;
  createWorkObjectType: (payload: Omit<WorkObjectTypeCreatePayload, "company_id">) => Promise<void>;
  updateWorkObjectType: (typeId: string, payload: WorkObjectTypeUpdatePayload) => Promise<void>;
  archiveWorkObjectType: (typeId: string) => Promise<void>;
  createCustomField: (payload: Omit<CustomFieldCreatePayload, "company_id">) => Promise<void>;
  updateCustomField: (fieldId: string, payload: CustomFieldUpdatePayload) => Promise<void>;
  archiveCustomField: (fieldId: string) => Promise<void>;
}

interface UseFebGridDataOptions {
  enabled?: boolean;
  role?: UserRole | null;
  page?: PageKey;
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

export function useFebGridData({ enabled = true, role = null, page = "dashboard" }: UseFebGridDataOptions = {}): FebGridDataState {
  const [data, setData] = useState<FebGridData>(emptyData);
  const [selectedCompanyId, setSelectedCompanyId] = useState<string | null>(() => getStoredCompanyId());
  const [isLoadingCompanies, setIsLoadingCompanies] = useState(true);
  const [isLoadingModules, setIsLoadingModules] = useState(false);
  const [isMutating, setIsMutating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [moduleErrors, setModuleErrors] = useState<ModuleErrors>({});
  const moduleRequestIdRef = useRef(0);
  const loadedCompanyIdRef = useRef<string | null>(null);
  const loadedModuleKeysRef = useRef<Set<FebGridModuleKey>>(new Set());
  const selectedCompanyIdRef = useRef<string | null>(selectedCompanyId);

  const selectedCompany = useMemo(
    () => data.companies.find((company) => company.id === selectedCompanyId) ?? null,
    [data.companies, selectedCompanyId],
  );

  const setSelectedCompanyIdOnce = useCallback((companyId: string | null): void => {
    if (selectedCompanyIdRef.current === companyId) return;

    selectedCompanyIdRef.current = companyId;
    moduleRequestIdRef.current += 1;
    loadedCompanyIdRef.current = null;
    loadedModuleKeysRef.current.clear();
    cancelInFlightGetRequests();
    setData((current) => ({ ...emptyData, companies: current.companies }));
    setModuleErrors({});

    if (companyId) storeCompanyId(companyId);
    else clearStoredCompanyId();

    setSelectedCompanyId(companyId);
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
      const currentCompanyId = selectedCompanyIdRef.current;
      if (!findCompany(companies, currentCompanyId)) {
        const storedCompanyId = getStoredCompanyId();
        const nextCompany = findCompany(companies, storedCompanyId) ?? companies[0] ?? null;
        setSelectedCompanyIdOnce(nextCompany?.id ?? null);
      }
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
      loadedCompanyIdRef.current = null;
      loadedModuleKeysRef.current.clear();
      cancelInFlightGetRequests();
      setData((current) => ({ ...emptyData, companies: current.companies }));
      setModuleErrors({});
      setIsLoadingModules(false);
      return;
    }

    const requestId = moduleRequestIdRef.current + 1;
    moduleRequestIdRef.current = requestId;

    if (loadedCompanyIdRef.current !== selectedCompanyId) {
      loadedCompanyIdRef.current = selectedCompanyId;
      loadedModuleKeysRef.current.clear();
      setData((current) => ({ ...emptyData, companies: current.companies }));
    }

    const dataLoaders: Record<FebGridModuleKey, () => Promise<unknown>> = {
      aiCapabilities: () => api.aiCapabilities(selectedCompanyId),
      aiProviderStatus: () => api.aiProviderStatus(selectedCompanyId),
      aiSafetySettings: () => api.aiSafetySettings(selectedCompanyId),
      aiJobQueueSummary: () => api.aiJobQueueSummary(selectedCompanyId),
      aiJobs: () => api.aiJobs(selectedCompanyId, { limit: 10 }),
      auditLogs: () => api.auditLogs(selectedCompanyId),
      billingPlans: () => api.billingPlans(),
      billingSummary: () => api.billingSummary(selectedCompanyId),
      companySettings: () => api.companySettings(selectedCompanyId),
      industryTemplates: () => api.industryTemplates(),
      workObjectTypes: () => api.workObjectTypes(selectedCompanyId, true),
      customFields: () => api.customFields(selectedCompanyId, undefined, true),
      dashboardSummary: () => api.dashboardSummary(selectedCompanyId),
      departments: () => api.departments(selectedCompanyId),
      employees: async () => (role === "employee" ? [await api.employeeMe()] : api.employees(selectedCompanyId)),
      leaveApprovers: () => api.leaveApprovers(selectedCompanyId),
      invitations: () => api.invitations(selectedCompanyId),
      teams: () => api.teams(selectedCompanyId),
      projects: () => api.projects(selectedCompanyId),
      workObjects: () => api.workObjects(selectedCompanyId),
      leaves: () => api.leaves(selectedCompanyId),
      events: () => api.events(selectedCompanyId),
      notifications: () => api.notifications(selectedCompanyId),
      notificationUnreadCount: async () => (await api.notificationUnreadCount(selectedCompanyId)).unread_count,
      announcements: () => api.announcements(selectedCompanyId),
      files: () => api.files(selectedCompanyId),
    };
    const keys = getPageDataKeys(page, role);
    setIsLoadingModules(keys.some((key) => !loadedModuleKeysRef.current.has(key)));
    setModuleErrors({});
    const results = await Promise.allSettled(keys.map((key) => dataLoaders[key]()));
    const nextData: Partial<FebGridData> = {};
    const nextErrors: ModuleErrors = {};
    const fulfilledKeys: FebGridModuleKey[] = [];
    results.forEach((result, index) => {
      const key = keys[index];
      if (result.status === "fulfilled") {
        Object.assign(nextData, { [key]: result.value });
        fulfilledKeys.push(key);
      }
      else if (!(result.reason instanceof ApiError && result.reason.status === 499)) nextErrors[key] = getErrorMessage(result.reason);
    });

    if (moduleRequestIdRef.current !== requestId) return;

    fulfilledKeys.forEach((key) => loadedModuleKeysRef.current.add(key));
    setData((current) => ({ ...current, ...nextData }));
    setModuleErrors(nextErrors);
    setIsLoadingModules(false);
  }, [enabled, page, role, selectedCompanyId]);

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
      const employee = await api.createEmployee({ ...payload, company_id: selectedCompanyId });
      setData((current) => prependEntity(current, "employees", employee));
    });
  }

  async function updateEmployee(employeeId: string, payload: EmployeeUpdatePayload): Promise<void> {
    if (!selectedCompanyId) return;
    await runMutation(async () => {
      const employee = await api.updateEmployee(employeeId, selectedCompanyId, payload);
      setData((current) => replaceEntity(current, "employees", employee));
    });
  }

  async function deactivateEmployee(employeeId: string): Promise<void> {
    if (!selectedCompanyId) return;
    setModuleErrors({});
    setError(null);
    await api.deactivateEmployee(employeeId, selectedCompanyId);
    setData((current) => markEntityInactive(current, "employees", employeeId));
  }

  async function updateEmployeeStatus(employeeId: string, currentStatus: string): Promise<void> {
    if (!selectedCompanyId) return;
    await runMutation(async () => {
      const employee = await api.updateEmployeeStatus(employeeId, { company_id: selectedCompanyId, current_status: currentStatus });
      setData((current) => replaceEntity(current, "employees", employee));
    });
  }

  async function createInvitation(payload: Omit<EmployeeInvitationCreatePayload, "company_id">): Promise<EmployeeInvitationActionResult | null> {
    if (!selectedCompanyId) return null;
    setIsMutating(true);
    setModuleErrors({});
    setError(null);
    try {
      const result = await api.createInvitation({ ...payload, company_id: selectedCompanyId });
      setData((current) => prependEntity(current, "invitations", result.invitation));
      return result;
    } finally {
      setIsMutating(false);
    }
  }

  async function resendInvitation(invitationId: string): Promise<EmployeeInvitationActionResult | null> {
    if (!selectedCompanyId) return null;
    setIsMutating(true);
    setModuleErrors({});
    setError(null);
    try {
      const result = await api.resendInvitation(invitationId, selectedCompanyId);
      setData((current) => replaceEntity(current, "invitations", result.invitation));
      return result;
    } finally {
      setIsMutating(false);
    }
  }

  async function revokeInvitation(invitationId: string): Promise<void> {
    if (!selectedCompanyId) return;
    await runMutation(async () => {
      const invitation = await api.revokeInvitation(invitationId, selectedCompanyId);
      setData((current) => replaceEntity(current, "invitations", invitation));
    });
  }

  async function approveInvitation(invitationId: string): Promise<void> {
    if (!selectedCompanyId) return;
    await runMutation(async () => {
      const invitation = await api.approveInvitation(invitationId, selectedCompanyId);
      const employees = await api.employees(selectedCompanyId);
      setData((current) => ({ ...replaceEntity(current, "invitations", invitation), employees }));
    });
  }

  async function rejectInvitation(invitationId: string, rejectionReason?: string | null): Promise<void> {
    if (!selectedCompanyId) return;
    await runMutation(async () => {
      const invitation = await api.rejectInvitation(invitationId, selectedCompanyId, rejectionReason);
      setData((current) => replaceEntity(current, "invitations", invitation));
    });
  }

  async function createDepartment(payload: Omit<DepartmentCreatePayload, "company_id">): Promise<void> {
    if (!selectedCompanyId) return;
    await runMutation(async () => {
      const department = await api.createDepartment({ ...payload, company_id: selectedCompanyId });
      setData((current) => prependEntity(current, "departments", department));
    });
  }

  async function createTeam(payload: Omit<TeamCreatePayload, "company_id">): Promise<void> {
    if (!selectedCompanyId) return;
    await runMutation(async () => {
      const team = await api.createTeam({ ...payload, company_id: selectedCompanyId });
      setData((current) => prependEntity(current, "teams", team));
    });
  }

  async function createProject(payload: Omit<ProjectCreatePayload, "company_id">): Promise<void> {
    if (!selectedCompanyId) return;
    await runMutation(async () => {
      const project = await api.createProject({ ...payload, company_id: selectedCompanyId });
      setData((current) => prependEntity(current, "projects", project));
    });
  }

  async function updateProject(projectId: string, payload: ProjectUpdatePayload): Promise<void> {
    if (!selectedCompanyId) return;
    await runMutation(async () => {
      const project = await api.updateProject(projectId, selectedCompanyId, payload);
      setData((current) => replaceEntity(current, "projects", project));
    });
  }

  async function deactivateProject(projectId: string): Promise<void> {
    if (!selectedCompanyId) return;
    await runMutation(async () => {
      await api.deactivateProject(projectId, selectedCompanyId);
      setData((current) => markEntityInactive(current, "projects", projectId));
    });
  }

  async function updateProjectStatus(projectId: string, statusValue: string): Promise<void> {
    if (!selectedCompanyId) return;
    await runMutation(async () => {
      const project = await api.updateProjectStatus(projectId, { company_id: selectedCompanyId, status: statusValue });
      setData((current) => replaceEntity(current, "projects", project));
    });
  }

  async function updateProjectPriority(projectId: string, priority: string): Promise<void> {
    if (!selectedCompanyId) return;
    await runMutation(async () => {
      const project = await api.updateProjectPriority(projectId, { company_id: selectedCompanyId, priority });
      setData((current) => replaceEntity(current, "projects", project));
    });
  }

  async function addProjectMember(projectId: string, payload: Omit<ProjectMemberCreatePayload, "company_id">): Promise<void> {
    if (!selectedCompanyId) return;
    await runMutation(async () => {
      await api.addProjectMember(projectId, { ...payload, company_id: selectedCompanyId });
    });
  }

  async function removeProjectMember(projectId: string, employeeId: string): Promise<void> {
    if (!selectedCompanyId) return;
    await runMutation(async () => {
      await api.removeProjectMember(projectId, selectedCompanyId, employeeId);
    });
  }

  async function createWorkObject(payload: Omit<WorkObjectCreatePayload, "company_id">): Promise<void> {
    if (!selectedCompanyId) return;
    await runMutation(async () => {
      const workObject = await api.createWorkObject({ ...payload, company_id: selectedCompanyId });
      setData((current) => prependEntity(current, "workObjects", workObject));
    });
  }

  async function updateWorkObject(workObjectId: string, payload: WorkObjectUpdatePayload): Promise<void> {
    if (!selectedCompanyId) return;
    await runMutation(async () => {
      const workObject = await api.updateWorkObject(workObjectId, selectedCompanyId, payload);
      setData((current) => replaceEntity(current, "workObjects", workObject));
    });
  }

  async function deactivateWorkObject(workObjectId: string): Promise<void> {
    if (!selectedCompanyId) return;
    await runMutation(async () => {
      await api.deactivateWorkObject(workObjectId, selectedCompanyId);
      setData((current) => markEntityInactive(current, "workObjects", workObjectId));
    });
  }

  async function assignWorkObject(workObjectId: string, assigneeEmployeeId: string | null): Promise<void> {
    if (!selectedCompanyId) return;
    await runMutation(async () => {
      const workObject = await api.assignWorkObject(workObjectId, { company_id: selectedCompanyId, assignee_employee_id: assigneeEmployeeId });
      setData((current) => replaceEntity(current, "workObjects", workObject));
    });
  }

  async function updateWorkObjectStatus(workObjectId: string, statusValue: string): Promise<void> {
    if (!selectedCompanyId) return;
    await runMutation(async () => {
      const workObject = await api.updateWorkObjectStatus(workObjectId, { company_id: selectedCompanyId, status: statusValue });
      setData((current) => replaceEntity(current, "workObjects", workObject));
    });
  }

  async function updateWorkObjectPriority(workObjectId: string, priority: string): Promise<void> {
    if (!selectedCompanyId) return;
    await runMutation(async () => {
      const workObject = await api.updateWorkObjectPriority(workObjectId, { company_id: selectedCompanyId, priority });
      setData((current) => replaceEntity(current, "workObjects", workObject));
    });
  }

  async function completeWorkObject(workObjectId: string): Promise<void> {
    if (!selectedCompanyId) return;
    await runMutation(async () => {
      const workObject = await api.completeWorkObject(workObjectId, { company_id: selectedCompanyId });
      setData((current) => replaceEntity(current, "workObjects", workObject));
    });
  }

  async function createLeave(payload: Omit<LeaveCreatePayload, "company_id">): Promise<void> {
    if (!selectedCompanyId) return;
    await runMutation(async () => {
      const leave = await api.createLeave({ ...payload, company_id: selectedCompanyId });
      setData((current) => prependEntity(current, "leaves", leave));
    });
  }

  async function updateLeave(leaveId: string, payload: LeaveUpdatePayload): Promise<void> {
    if (!selectedCompanyId) return;
    await runMutation(async () => {
      const leave = await api.updateLeave(leaveId, selectedCompanyId, payload);
      setData((current) => replaceEntity(current, "leaves", leave));
    });
  }

  async function approveLeave(leaveId: string, payload: Omit<LeaveDecisionPayload, "company_id">): Promise<void> {
    if (!selectedCompanyId) return;
    await runMutation(async () => {
      const leave = await api.approveLeave(leaveId, { ...payload, company_id: selectedCompanyId });
      setData((current) => replaceEntity(current, "leaves", leave));
    });
  }

  async function rejectLeave(leaveId: string, payload: Omit<LeaveDecisionPayload, "company_id">): Promise<void> {
    if (!selectedCompanyId) return;
    await runMutation(async () => {
      const leave = await api.rejectLeave(leaveId, { ...payload, company_id: selectedCompanyId });
      setData((current) => replaceEntity(current, "leaves", leave));
    });
  }

  async function cancelLeave(leaveId: string, payload: Omit<LeaveCancelPayload, "company_id">): Promise<void> {
    if (!selectedCompanyId) return;
    await runMutation(async () => {
      const leave = await api.cancelLeave(leaveId, { ...payload, company_id: selectedCompanyId });
      setData((current) => replaceEntity(current, "leaves", leave));
    });
  }

  async function deactivateLeave(leaveId: string): Promise<void> {
    if (!selectedCompanyId) return;
    await runMutation(async () => {
      await api.deactivateLeave(leaveId, selectedCompanyId);
      setData((current) => markEntityInactive(current, "leaves", leaveId));
    });
  }

  async function markNotificationRead(notificationId: string): Promise<void> {
    if (!selectedCompanyId) return;
    const previous = data.notifications.find((item) => item.id === notificationId);
    if (!previous || previous.is_read) return;
    setData((current) => setNotificationReadState(current, notificationId, true, new Date().toISOString()));
    try {
      const notification = await api.markNotificationRead(notificationId, selectedCompanyId);
      setData((current) => replaceEntity(current, "notifications", notification));
    } catch (caughtError) {
      setData((current) => setNotificationReadState(current, notificationId, previous.is_read, previous.read_at));
      throw caughtError;
    }
  }

  async function markNotificationUnread(notificationId: string): Promise<void> {
    if (!selectedCompanyId) return;
    const previous = data.notifications.find((item) => item.id === notificationId);
    if (!previous || !previous.is_read) return;
    setData((current) => setNotificationReadState(current, notificationId, false, null));
    try {
      const notification = await api.markNotificationUnread(notificationId, selectedCompanyId);
      setData((current) => replaceEntity(current, "notifications", notification));
    } catch (caughtError) {
      setData((current) => setNotificationReadState(current, notificationId, previous.is_read, previous.read_at));
      throw caughtError;
    }
  }

  async function markAllNotificationsRead(): Promise<void> {
    if (!selectedCompanyId) return;
    const previousNotifications = data.notifications;
    const previousUnreadCount = data.notificationUnreadCount;
    const readAt = new Date().toISOString();
    setData((current) => ({
      ...current,
      notificationUnreadCount: 0,
      notifications: current.notifications.map((item) => ({ ...item, is_read: true, read_at: item.read_at ?? readAt })),
    }));
    try {
      await api.markAllNotificationsRead(selectedCompanyId);
    } catch (caughtError) {
      setData((current) => ({ ...current, notifications: previousNotifications, notificationUnreadCount: previousUnreadCount }));
      throw caughtError;
    }
  }

  async function dismissNotification(notificationId: string): Promise<void> {
    if (!selectedCompanyId) return;
    await runMutation(async () => {
      const notification = await api.dismissNotification(notificationId, selectedCompanyId);
      setData((current) => ({
        ...current,
        notifications: current.notifications.map((item) => (item.id === notification.id ? notification : item)),
      }));
    });
  }

  async function createAnnouncement(payload: Omit<AnnouncementCreatePayload, "company_id">): Promise<void> {
    if (!selectedCompanyId) return;
    await runMutation(async () => {
      const announcement = await api.createAnnouncement({ ...payload, company_id: selectedCompanyId });
      setData((current) => prependEntity(current, "announcements", announcement));
    });
  }

  async function updateAnnouncement(announcementId: string, payload: AnnouncementUpdatePayload): Promise<void> {
    if (!selectedCompanyId) return;
    await runMutation(async () => {
      const announcement = await api.updateAnnouncement(announcementId, selectedCompanyId, payload);
      setData((current) => replaceEntity(current, "announcements", announcement));
    });
  }

  async function archiveAnnouncement(announcementId: string): Promise<void> {
    if (!selectedCompanyId) return;
    await runMutation(async () => {
      const announcement = await api.archiveAnnouncement(announcementId, selectedCompanyId);
      setData((current) => replaceEntity(current, "announcements", announcement));
    });
  }

  async function updateCompanySettings(payload: CompanySettingsUpdatePayload): Promise<void> {
    if (!selectedCompanyId) return;
    await runMutation(async () => {
      await api.updateCompanySettings(selectedCompanyId, payload);
      await Promise.all([refreshModules(), refreshCompanies()]);
    });
  }

  async function updateCompanyPlan(payload: CompanyPlanUpdatePayload): Promise<void> {
    if (!selectedCompanyId) return;
    await runMutation(async () => {
      await api.updateCompanyPlan(selectedCompanyId, payload);
      await refreshModules();
    });
  }

  async function updateFile(attachmentId: string, payload: AttachmentUpdatePayload): Promise<void> {
    if (!selectedCompanyId) return;
    await runMutation(async () => {
      await api.updateFile(attachmentId, selectedCompanyId, payload);
      await refreshModules();
    });
  }

  async function archiveFile(attachmentId: string): Promise<void> {
    if (!selectedCompanyId) return;
    await runMutation(async () => {
      await api.archiveFile(attachmentId, selectedCompanyId);
      await refreshModules();
    });
  }

  async function restoreFile(attachmentId: string): Promise<void> {
    if (!selectedCompanyId) return;
    await runMutation(async () => {
      await api.restoreFile(attachmentId, selectedCompanyId);
      await refreshModules();
    });
  }

  async function createAIJob(payload: Omit<AIJobCreatePayload, "company_id">): Promise<void> {
    if (!selectedCompanyId) return;
    await runMutation(async () => {
      await api.createAIJob({ ...payload, company_id: selectedCompanyId });
      await refreshModules();
    });
  }

  async function runAIJob(jobId: string): Promise<void> {
    if (!selectedCompanyId) return;
    await runMutation(async () => {
      await api.runAIJob(jobId, selectedCompanyId);
      await refreshModules();
    });
  }

  async function processNextAIJob(): Promise<void> {
    if (!selectedCompanyId) return;
    await runMutation(async () => {
      await api.processNextAIJob(selectedCompanyId);
      await refreshModules();
    });
  }

  async function retryAIJob(jobId: string): Promise<void> {
    if (!selectedCompanyId) return;
    await runMutation(async () => {
      await api.retryAIJob(jobId, selectedCompanyId);
      await refreshModules();
    });
  }

  async function recoverStaleAIJobs(): Promise<void> {
    if (!selectedCompanyId) return;
    await runMutation(async () => {
      await api.recoverStaleAIJobs(selectedCompanyId);
      await refreshModules();
    });
  }

  async function cancelAIJob(jobId: string): Promise<void> {
    if (!selectedCompanyId) return;
    await runMutation(async () => {
      await api.cancelAIJob(jobId, selectedCompanyId);
      await refreshModules();
    });
  }

  async function updateAISafetySettings(payload: AISafetySettingsUpdatePayload): Promise<void> {
    if (!selectedCompanyId) return;
    await runMutation(async () => {
      await api.updateAISafetySettings(selectedCompanyId, payload);
      await refreshModules();
    });
  }

  async function applyIndustryTemplate(templateKey: string): Promise<void> {
    if (!selectedCompanyId) return;
    await runMutation(async () => {
      await api.applyIndustryTemplate(selectedCompanyId, templateKey);
      await Promise.all([refreshModules(), refreshCompanies()]);
    });
  }

  async function createWorkObjectType(payload: Omit<WorkObjectTypeCreatePayload, "company_id">): Promise<void> {
    if (!selectedCompanyId) return;
    await runMutation(async () => {
      await api.createWorkObjectType({ ...payload, company_id: selectedCompanyId });
      await refreshModules();
    });
  }

  async function updateWorkObjectType(typeId: string, payload: WorkObjectTypeUpdatePayload): Promise<void> {
    if (!selectedCompanyId) return;
    await runMutation(async () => {
      await api.updateWorkObjectType(typeId, selectedCompanyId, payload);
      await refreshModules();
    });
  }

  async function archiveWorkObjectType(typeId: string): Promise<void> {
    if (!selectedCompanyId) return;
    await runMutation(async () => {
      await api.archiveWorkObjectType(typeId, selectedCompanyId);
      await refreshModules();
    });
  }

  async function createCustomField(payload: Omit<CustomFieldCreatePayload, "company_id">): Promise<void> {
    if (!selectedCompanyId) return;
    await runMutation(async () => {
      await api.createCustomField({ ...payload, company_id: selectedCompanyId });
      await refreshModules();
    });
  }

  async function updateCustomField(fieldId: string, payload: CustomFieldUpdatePayload): Promise<void> {
    if (!selectedCompanyId) return;
    await runMutation(async () => {
      await api.updateCustomField(fieldId, selectedCompanyId, payload);
      await refreshModules();
    });
  }

  async function archiveCustomField(fieldId: string): Promise<void> {
    if (!selectedCompanyId) return;
    await runMutation(async () => {
      await api.archiveCustomField(fieldId, selectedCompanyId);
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
    createInvitation,
    resendInvitation,
    revokeInvitation,
    approveInvitation,
    rejectInvitation,
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
    updateCompanySettings,
    updateCompanyPlan,
    updateFile,
    archiveFile,
    restoreFile,
    createAIJob,
    runAIJob,
    processNextAIJob,
    retryAIJob,
    recoverStaleAIJobs,
    cancelAIJob,
    updateAISafetySettings,
    applyIndustryTemplate,
    createWorkObjectType,
    updateWorkObjectType,
    archiveWorkObjectType,
    createCustomField,
    updateCustomField,
    archiveCustomField,
  };
}
