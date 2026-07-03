import type {
  Announcement,
  AnnouncementCreatePayload,
  AnnouncementUpdatePayload,
  Attachment,
  AttachmentUpdatePayload,
  AICapabilities,
  AIProviderStatus,
  AISafetySettings,
  AISafetySettingsUpdatePayload,
  AIJob,
  AIJobCreatePayload,
  AuditLog,
  AuthMe,
  AuthSession,
  BillingSummary,
  Company,
  CompanyCreatePayload,
  CompanyPlanUpdatePayload,
  CompanySettings,
  CompanySettingsUpdatePayload,
  Comment,
  CommentCreatePayload,
  CommentUpdatePayload,
  CustomFieldCreatePayload,
  CustomFieldDefinition,
  CustomFieldUpdatePayload,
  DashboardSummary,
  Department,
  DepartmentCreatePayload,
  Employee,
  EmployeeCreatePayload,
  EmployeeInvitation,
  EmployeeInvitationActionResult,
  EmployeeInvitationCreatePayload,
  EmployeeSelfUpdatePayload,
  EmployeeUpdatePayload,
  Event,
  ApplyIndustryTemplateResult,
  IndustryTemplate,
  InvitationAcceptPayload,
  InvitationAcceptResult,
  InvitationPreview,
  InvitationProfileCompletePayload,
  InvitationProfileCompleteResult,
  LeaveCancelPayload,
  LeaveCreatePayload,
  LeaveDecisionPayload,
  LeaveRequest,
  LeaveSummary,
  LeaveUpdatePayload,
  LoginPayload,
  Notification,
  NotificationUnreadCount,
  PlanDefinition,
  Project,
  ProjectCreatePayload,
  ProjectMember,
  ProjectMemberCreatePayload,
  ProjectUpdatePayload,
  RegisterPayload,
  SearchResponse,
  Team,
  TeamCreatePayload,
  WorkObject,
  WorkObjectCreatePayload,
  WorkObjectSummary,
  WorkObjectTypeCreatePayload,
  WorkObjectTypeDefinition,
  WorkObjectTypeUpdatePayload,
  WorkObjectUpdatePayload,
} from "../types/api";

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, "") ?? "http://127.0.0.1:8000";
let authToken: string | null = null;

export function setApiAuthToken(token: string | null): void {
  authToken = token;
}

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const isFormData = init?.body instanceof FormData;
  const response = await fetch(`${API_BASE_URL}/api/v1${path}`, {
    headers: {
      ...(isFormData ? {} : { "Content-Type": "application/json" }),
      ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}),
      ...init?.headers,
    },
    ...init,
  });

  if (!response.ok) {
    let message = `Request failed for ${path}`;
    try {
      const body = (await response.json()) as { detail?: unknown };
      if (typeof body.detail === "string") {
        message = body.detail;
      }
    } catch {
      message = response.statusText || message;
    }
    throw new ApiError(message, response.status);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

async function requestBlob(path: string, init?: RequestInit): Promise<Blob> {
  const response = await fetch(`${API_BASE_URL}/api/v1${path}`, {
    headers: {
      ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}),
      ...init?.headers,
    },
    ...init,
  });

  if (!response.ok) {
    throw new ApiError(response.statusText || `Request failed for ${path}`, response.status);
  }

  return response.blob();
}

function jsonInit(method: "POST" | "PUT" | "PATCH", body: unknown): RequestInit {
  return {
    method,
    body: JSON.stringify(body),
  };
}

function companyPath(path: string, companyId: string): string {
  const separator = path.includes("?") ? "&" : "?";
  return `${path}${separator}company_id=${encodeURIComponent(companyId)}`;
}

function attachmentFormData(file: File, companyId: string, description?: string | null): FormData {
  const formData = new FormData();
  formData.append("company_id", companyId);
  formData.append("file", file);
  if (description) formData.append("description", description);
  return formData;
}

export const api = {
  health: () => request<{ status: string; service: string; environment: string }>("/health"),
  register: (payload: RegisterPayload) => request<AuthSession>("/auth/register", jsonInit("POST", payload)),
  login: (payload: LoginPayload) => request<AuthSession>("/auth/login", jsonInit("POST", payload)),
  logout: () => request<{ status: string }>("/auth/logout", { method: "POST" }),
  markPresenceOnline: () => request<Employee>("/auth/presence/online", { method: "POST" }),
  markPresenceOffline: (keepalive = false) => request<Employee>("/auth/presence/offline", { method: "POST", keepalive }),
  me: () => request<AuthMe>("/auth/me"),
  companies: () => request<Company[]>("/companies"),
  createCompany: (payload: CompanyCreatePayload) => request<Company>("/companies", jsonInit("POST", payload)),
  companySettings: (companyId: string) => request<CompanySettings>(companyPath("/company-settings", companyId)),
  billingPlans: () => request<PlanDefinition[]>("/billing/plans"),
  billingSummary: (companyId: string) => request<BillingSummary>(companyPath("/billing/summary", companyId)),
  updateCompanyPlan: (companyId: string, payload: CompanyPlanUpdatePayload) =>
    request<BillingSummary["plan"]>(companyPath("/billing/company-plan", companyId), jsonInit("PUT", payload)),
  updateCompanySettings: (companyId: string, payload: CompanySettingsUpdatePayload) => request<CompanySettings>(companyPath("/company-settings", companyId), jsonInit("PUT", payload)),
  industryTemplates: () => request<IndustryTemplate[]>("/industry-templates"),
  industryTemplate: (templateKey: string) => request<IndustryTemplate>(`/industry-templates/${encodeURIComponent(templateKey)}`),
  applyIndustryTemplate: (companyId: string, templateKey: string) =>
    request<ApplyIndustryTemplateResult>(companyPath("/company-settings/apply-template", companyId), jsonInit("POST", { template_key: templateKey })),
  workObjectTypes: (companyId: string, includeInactive = false) =>
    request<WorkObjectTypeDefinition[]>(companyPath(`/work-object-types?include_inactive=${includeInactive ? "true" : "false"}`, companyId)),
  createWorkObjectType: (payload: WorkObjectTypeCreatePayload) => request<WorkObjectTypeDefinition>("/work-object-types", jsonInit("POST", payload)),
  updateWorkObjectType: (typeId: string, companyId: string, payload: WorkObjectTypeUpdatePayload) =>
    request<WorkObjectTypeDefinition>(companyPath(`/work-object-types/${typeId}`, companyId), jsonInit("PATCH", payload)),
  archiveWorkObjectType: (typeId: string, companyId: string) => request<WorkObjectTypeDefinition>(companyPath(`/work-object-types/${typeId}/archive`, companyId), jsonInit("POST", {})),
  customFields: (companyId: string, typeKey?: string, includeInactive = false) => {
    const searchParams = new URLSearchParams({ include_inactive: includeInactive ? "true" : "false" });
    if (typeKey) searchParams.set("type_key", typeKey);
    return request<CustomFieldDefinition[]>(companyPath(`/custom-fields?${searchParams.toString()}`, companyId));
  },
  createCustomField: (payload: CustomFieldCreatePayload) => request<CustomFieldDefinition>("/custom-fields", jsonInit("POST", payload)),
  updateCustomField: (fieldId: string, companyId: string, payload: CustomFieldUpdatePayload) =>
    request<CustomFieldDefinition>(companyPath(`/custom-fields/${fieldId}`, companyId), jsonInit("PATCH", payload)),
  archiveCustomField: (fieldId: string, companyId: string) => request<CustomFieldDefinition>(companyPath(`/custom-fields/${fieldId}/archive`, companyId), jsonInit("POST", {})),
  dashboardSummary: (companyId: string) => request<DashboardSummary>(companyPath("/dashboard/summary", companyId)),
  departments: (companyId: string) => request<Department[]>(companyPath("/departments", companyId)),
  createDepartment: (payload: DepartmentCreatePayload) => request<Department>("/departments", jsonInit("POST", payload)),
  employees: (companyId: string) => request<Employee[]>(companyPath("/employees", companyId)),
  createEmployee: (payload: EmployeeCreatePayload) => request<Employee>("/employees", jsonInit("POST", payload)),
  employeeMe: () => request<Employee>("/employees/me"),
  updateEmployeeMe: (payload: EmployeeSelfUpdatePayload) => request<Employee>("/employees/me", jsonInit("PATCH", payload)),
  updateEmployee: (employeeId: string, companyId: string, payload: EmployeeUpdatePayload) => request<Employee>(companyPath(`/employees/${employeeId}`, companyId), jsonInit("PUT", payload)),
  deactivateEmployee: (employeeId: string, companyId: string) => request<void>(companyPath(`/employees/${employeeId}`, companyId), { method: "DELETE" }),
  updateEmployeeStatus: (employeeId: string, payload: { company_id: string; current_status: string }) => request<Employee>(`/employees/${employeeId}/status`, jsonInit("PATCH", payload)),
  invitations: (companyId: string, statusFilter?: string) => {
    const searchParams = new URLSearchParams({ company_id: companyId });
    if (statusFilter) searchParams.set("status", statusFilter);
    return request<EmployeeInvitation[]>(`/invitations?${searchParams.toString()}`);
  },
  createInvitation: (payload: EmployeeInvitationCreatePayload) => request<EmployeeInvitationActionResult>("/invitations", jsonInit("POST", payload)),
  resendInvitation: (invitationId: string, companyId: string) =>
    request<EmployeeInvitationActionResult>(`/invitations/${invitationId}/resend`, jsonInit("POST", { company_id: companyId })),
  revokeInvitation: (invitationId: string, companyId: string) =>
    request<EmployeeInvitation>(`/invitations/${invitationId}/revoke`, jsonInit("POST", { company_id: companyId })),
  approveInvitation: (invitationId: string, companyId: string) =>
    request<EmployeeInvitation>(`/invitations/${invitationId}/approve`, jsonInit("POST", { company_id: companyId })),
  rejectInvitation: (invitationId: string, companyId: string, rejectionReason?: string | null) =>
    request<EmployeeInvitation>(`/invitations/${invitationId}/reject`, jsonInit("POST", { company_id: companyId, rejection_reason: rejectionReason ?? null })),
  previewInvitation: (token: string) => request<InvitationPreview>(`/invitations/preview/${encodeURIComponent(token)}`),
  acceptInvitation: (payload: InvitationAcceptPayload) => request<InvitationAcceptResult>("/invitations/accept", jsonInit("POST", payload)),
  completeInvitationProfile: (payload: InvitationProfileCompletePayload) =>
    request<InvitationProfileCompleteResult>("/invitations/complete-profile", jsonInit("POST", payload)),
  teams: (companyId: string) => request<Team[]>(companyPath("/teams", companyId)),
  createTeam: (payload: TeamCreatePayload) => request<Team>("/teams", jsonInit("POST", payload)),
  projects: (companyId: string) => request<Project[]>(companyPath("/projects", companyId)),
  project: (projectId: string, companyId: string) => request<Project>(companyPath(`/projects/${projectId}`, companyId)),
  createProject: (payload: ProjectCreatePayload) => request<Project>("/projects", jsonInit("POST", payload)),
  updateProject: (projectId: string, companyId: string, payload: ProjectUpdatePayload) => request<Project>(companyPath(`/projects/${projectId}`, companyId), jsonInit("PUT", payload)),
  deactivateProject: (projectId: string, companyId: string) => request<void>(companyPath(`/projects/${projectId}`, companyId), { method: "DELETE" }),
  updateProjectStatus: (projectId: string, payload: { company_id: string; status: string }) => request<Project>(`/projects/${projectId}/status`, jsonInit("PATCH", payload)),
  updateProjectPriority: (projectId: string, payload: { company_id: string; priority: string }) => request<Project>(`/projects/${projectId}/priority`, jsonInit("PATCH", payload)),
  updateProjectOwner: (projectId: string, payload: { company_id: string; owner_employee_id?: string | null; owner_user_id?: string | null }) => request<Project>(`/projects/${projectId}/owner`, jsonInit("PATCH", payload)),
  projectMembers: (projectId: string, companyId: string) => request<ProjectMember[]>(companyPath(`/projects/${projectId}/members`, companyId)),
  addProjectMember: (projectId: string, payload: ProjectMemberCreatePayload) => request<ProjectMember>(`/projects/${projectId}/members`, jsonInit("POST", payload)),
  removeProjectMember: (projectId: string, companyId: string, employeeId: string) => request<void>(companyPath(`/projects/${projectId}/members/${employeeId}`, companyId), { method: "DELETE" }),
  projectTimeline: (projectId: string, companyId: string) => request<Event[]>(companyPath(`/projects/${projectId}/timeline`, companyId)),
  projectWorkObjects: (projectId: string, companyId: string) => request<WorkObject[]>(companyPath(`/projects/${projectId}/work-objects`, companyId)),
  workObjects: (companyId: string) => request<WorkObject[]>(companyPath("/work-objects", companyId)),
  workObject: (workObjectId: string, companyId: string) => request<WorkObject>(companyPath(`/work-objects/${workObjectId}`, companyId)),
  workObjectSummary: (companyId: string) => request<WorkObjectSummary>(companyPath("/work-objects/summary", companyId)),
  createWorkObject: (payload: WorkObjectCreatePayload) => request<WorkObject>("/work-objects", jsonInit("POST", payload)),
  updateWorkObject: (workObjectId: string, companyId: string, payload: WorkObjectUpdatePayload) => request<WorkObject>(companyPath(`/work-objects/${workObjectId}`, companyId), jsonInit("PUT", payload)),
  deactivateWorkObject: (workObjectId: string, companyId: string) => request<void>(companyPath(`/work-objects/${workObjectId}`, companyId), { method: "DELETE" }),
  assignWorkObject: (workObjectId: string, payload: { company_id: string; assignee_employee_id?: string | null }) => request<WorkObject>(`/work-objects/${workObjectId}/assignee`, jsonInit("PATCH", payload)),
  updateWorkObjectStatus: (workObjectId: string, payload: { company_id: string; status: string }) => request<WorkObject>(`/work-objects/${workObjectId}/status`, jsonInit("PATCH", payload)),
  updateWorkObjectPriority: (workObjectId: string, payload: { company_id: string; priority: string }) => request<WorkObject>(`/work-objects/${workObjectId}/priority`, jsonInit("PATCH", payload)),
  completeWorkObject: (workObjectId: string, payload: { company_id: string }) => request<WorkObject>(`/work-objects/${workObjectId}/complete`, jsonInit("POST", payload)),
  workObjectTimeline: (workObjectId: string, companyId: string) => request<Event[]>(companyPath(`/work-objects/${workObjectId}/timeline`, companyId)),
  workObjectAttachments: (workObjectId: string, companyId: string) => request<Attachment[]>(companyPath(`/work-objects/${workObjectId}/attachments`, companyId)),
  uploadWorkObjectAttachment: (workObjectId: string, companyId: string, file: File, description?: string | null) =>
    request<Attachment>(`/work-objects/${workObjectId}/attachments`, { method: "POST", body: attachmentFormData(file, companyId, description) }),
  comments: (targetEntityType: "work_object" | "project", targetEntityId: string, companyId: string) =>
    request<Comment[]>(companyPath(`/comments?target_entity_type=${encodeURIComponent(targetEntityType)}&target_entity_id=${encodeURIComponent(targetEntityId)}`, companyId)),
  createComment: (payload: CommentCreatePayload) => request<Comment>("/comments", jsonInit("POST", payload)),
  updateComment: (commentId: string, companyId: string, payload: CommentUpdatePayload) => request<Comment>(companyPath(`/comments/${commentId}`, companyId), jsonInit("PATCH", payload)),
  archiveComment: (commentId: string, companyId: string) => request<void>(companyPath(`/comments/${commentId}`, companyId), { method: "DELETE" }),
  attachment: (attachmentId: string, companyId: string) => request<Attachment>(companyPath(`/attachments/${attachmentId}`, companyId)),
  updateAttachment: (attachmentId: string, companyId: string, payload: AttachmentUpdatePayload) => request<Attachment>(companyPath(`/attachments/${attachmentId}`, companyId), jsonInit("PATCH", payload)),
  deleteAttachment: (attachmentId: string, companyId: string) => request<void>(companyPath(`/attachments/${attachmentId}`, companyId), { method: "DELETE" }),
  downloadAttachment: (attachmentId: string, companyId: string) => requestBlob(companyPath(`/attachments/${attachmentId}/download`, companyId)),
  files: (companyId: string, params: { q?: string; content_type?: string; include_archived?: boolean; include_deleted?: boolean } = {}) => {
    const searchParams = new URLSearchParams({ company_id: companyId });
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== "") searchParams.set(key, String(value));
    });
    return request<Attachment[]>(`/files?${searchParams.toString()}`);
  },
  updateFile: (attachmentId: string, companyId: string, payload: AttachmentUpdatePayload) =>
    request<Attachment>(companyPath(`/files/${attachmentId}`, companyId), jsonInit("PATCH", payload)),
  archiveFile: (attachmentId: string, companyId: string) => request<Attachment>(companyPath(`/files/${attachmentId}/archive`, companyId), jsonInit("POST", {})),
  restoreFile: (attachmentId: string, companyId: string) => request<Attachment>(companyPath(`/files/${attachmentId}/restore`, companyId), jsonInit("POST", {})),
  generateFileAISummary: (attachmentId: string, companyId: string) =>
    request<AIJob>(companyPath(`/files/${attachmentId}/ai-summary`, companyId), jsonInit("POST", {})),
  latestFileAISummary: (attachmentId: string, companyId: string) =>
    request<AIJob | null>(companyPath(`/files/${attachmentId}/ai-summary/latest`, companyId)),
  aiCapabilities: (companyId: string) => request<AICapabilities>(companyPath("/ai/capabilities", companyId)),
  aiProviderStatus: (companyId: string) => request<AIProviderStatus>(companyPath("/ai/provider-status", companyId)),
  aiSafetySettings: (companyId: string) => request<AISafetySettings>(companyPath("/ai/safety-settings", companyId)),
  updateAISafetySettings: (companyId: string, payload: AISafetySettingsUpdatePayload) =>
    request<AISafetySettings>(companyPath("/ai/safety-settings", companyId), jsonInit("PUT", payload)),
  aiJobs: (companyId: string, params: { status?: string; job_type?: string; limit?: number } = {}) => {
    const searchParams = new URLSearchParams({ company_id: companyId });
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== "") searchParams.set(key, String(value));
    });
    return request<AIJob[]>(`/ai/jobs?${searchParams.toString()}`);
  },
  generateWorkObjectAISummary: (workObjectId: string, companyId: string) =>
    request<AIJob>(companyPath(`/work-objects/${workObjectId}/ai-summary`, companyId), jsonInit("POST", {})),
  latestWorkObjectAISummary: (workObjectId: string, companyId: string) =>
    request<AIJob | null>(companyPath(`/work-objects/${workObjectId}/ai-summary/latest`, companyId)),
  generateProjectAISummary: (projectId: string, companyId: string) =>
    request<AIJob>(companyPath(`/projects/${projectId}/ai-summary`, companyId), jsonInit("POST", {})),
  latestProjectAISummary: (projectId: string, companyId: string) =>
    request<AIJob | null>(companyPath(`/projects/${projectId}/ai-summary/latest`, companyId)),
  generateCompanyAIBrief: (companyId: string) =>
    request<AIJob>(companyPath(`/companies/${companyId}/ai-brief`, companyId), jsonInit("POST", {})),
  latestCompanyAIBrief: (companyId: string) =>
    request<AIJob | null>(companyPath(`/companies/${companyId}/ai-brief/latest`, companyId)),
  createAIJob: (payload: AIJobCreatePayload) => request<AIJob>("/ai/jobs", jsonInit("POST", payload)),
  runAIJob: (jobId: string, companyId: string) => request<AIJob>(companyPath(`/ai/jobs/${jobId}/run`, companyId), jsonInit("POST", {})),
  cancelAIJob: (jobId: string, companyId: string) => request<AIJob>(companyPath(`/ai/jobs/${jobId}/cancel`, companyId), jsonInit("POST", {})),
  leaves: (companyId: string) => request<LeaveRequest[]>(companyPath("/leaves", companyId)),
  leaveApprovers: (companyId: string) => request<Employee[]>(companyPath("/leaves/approvers", companyId)),
  leave: (leaveId: string, companyId: string) => request<LeaveRequest>(companyPath(`/leaves/${leaveId}`, companyId)),
  leaveSummary: (companyId: string) => request<LeaveSummary>(companyPath("/leaves/summary", companyId)),
  createLeave: (payload: LeaveCreatePayload) => request<LeaveRequest>("/leaves", jsonInit("POST", payload)),
  updateLeave: (leaveId: string, companyId: string, payload: LeaveUpdatePayload) => request<LeaveRequest>(companyPath(`/leaves/${leaveId}`, companyId), jsonInit("PUT", payload)),
  approveLeave: (leaveId: string, payload: LeaveDecisionPayload) => request<LeaveRequest>(`/leaves/${leaveId}/approve`, jsonInit("POST", payload)),
  rejectLeave: (leaveId: string, payload: LeaveDecisionPayload) => request<LeaveRequest>(`/leaves/${leaveId}/reject`, jsonInit("POST", payload)),
  cancelLeave: (leaveId: string, payload: LeaveCancelPayload) => request<LeaveRequest>(`/leaves/${leaveId}/cancel`, jsonInit("POST", payload)),
  deactivateLeave: (leaveId: string, companyId: string) => request<void>(companyPath(`/leaves/${leaveId}`, companyId), { method: "DELETE" }),
  leaveTimeline: (leaveId: string, companyId: string) => request<Event[]>(companyPath(`/leaves/${leaveId}/timeline`, companyId)),
  events: (companyId: string) => request<Event[]>(companyPath("/timeline", companyId)),
  auditLogs: (companyId: string) => request<AuditLog[]>(companyPath("/audit-log", companyId)),
  notifications: (companyId: string) => request<Notification[]>(companyPath("/notifications", companyId)),
  announcements: (companyId: string) => request<Announcement[]>(companyPath("/announcements", companyId)),
  createAnnouncement: (payload: AnnouncementCreatePayload) => request<Announcement>("/announcements", jsonInit("POST", payload)),
  updateAnnouncement: (announcementId: string, companyId: string, payload: AnnouncementUpdatePayload) => request<Announcement>(companyPath(`/announcements/${announcementId}`, companyId), jsonInit("PATCH", payload)),
  archiveAnnouncement: (announcementId: string, companyId: string) => request<Announcement>(companyPath(`/announcements/${announcementId}/archive`, companyId), { method: "PATCH" }),
  notificationUnreadCount: (companyId: string) => request<NotificationUnreadCount>(companyPath("/notifications/unread-count", companyId)),
  search: (companyId: string, params: { q?: string; types?: string[]; limit?: number }) => {
    const searchParams = new URLSearchParams({ company_id: companyId });
    if (params.q !== undefined) searchParams.set("q", params.q);
    if (params.types?.length) searchParams.set("types", params.types.join(","));
    if (params.limit !== undefined) searchParams.set("limit", params.limit.toString());
    return request<SearchResponse>(`/search?${searchParams.toString()}`);
  },
  markNotificationRead: (notificationId: string, companyId: string) => request<Notification>(companyPath(`/notifications/${notificationId}/read`, companyId), { method: "PATCH" }),
  markNotificationUnread: (notificationId: string, companyId: string) => request<Notification>(companyPath(`/notifications/${notificationId}/unread`, companyId), { method: "PATCH" }),
  markAllNotificationsRead: (companyId: string) => request<void>(companyPath("/notifications/read-all", companyId), { method: "PATCH" }),
  dismissNotification: (notificationId: string, companyId: string) => request<Notification>(companyPath(`/notifications/${notificationId}/dismiss`, companyId), { method: "PATCH" }),
};
