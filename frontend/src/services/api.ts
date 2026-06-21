import type {
  AuthMe,
  AuthSession,
  Company,
  CompanyCreatePayload,
  Department,
  DepartmentCreatePayload,
  Employee,
  EmployeeCreatePayload,
  EmployeeUpdatePayload,
  Event,
  LeaveCreatePayload,
  LeaveRequest,
  LoginPayload,
  Notification,
  Project,
  ProjectCreatePayload,
  ProjectMember,
  ProjectMemberCreatePayload,
  ProjectUpdatePayload,
  RegisterPayload,
  Team,
  TeamCreatePayload,
  WorkObject,
  WorkObjectCreatePayload,
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
  const response = await fetch(`${API_BASE_URL}/api/v1${path}`, {
    headers: {
      "Content-Type": "application/json",
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

export const api = {
  health: () => request<{ status: string; service: string; environment: string }>("/health"),
  register: (payload: RegisterPayload) => request<AuthSession>("/auth/register", jsonInit("POST", payload)),
  login: (payload: LoginPayload) => request<AuthSession>("/auth/login", jsonInit("POST", payload)),
  logout: () => request<{ status: string }>("/auth/logout", { method: "POST" }),
  me: () => request<AuthMe>("/auth/me"),
  companies: () => request<Company[]>("/companies"),
  createCompany: (payload: CompanyCreatePayload) => request<Company>("/companies", jsonInit("POST", payload)),
  departments: (companyId: string) => request<Department[]>(companyPath("/departments", companyId)),
  createDepartment: (payload: DepartmentCreatePayload) => request<Department>("/departments", jsonInit("POST", payload)),
  employees: (companyId: string) => request<Employee[]>(companyPath("/employees", companyId)),
  createEmployee: (payload: EmployeeCreatePayload) => request<Employee>("/employees", jsonInit("POST", payload)),
  updateEmployee: (employeeId: string, companyId: string, payload: EmployeeUpdatePayload) => request<Employee>(companyPath(`/employees/${employeeId}`, companyId), jsonInit("PUT", payload)),
  deactivateEmployee: (employeeId: string, companyId: string) => request<void>(companyPath(`/employees/${employeeId}`, companyId), { method: "DELETE" }),
  updateEmployeeStatus: (employeeId: string, payload: { company_id: string; current_status: string }) => request<Employee>(`/employees/${employeeId}/status`, jsonInit("PATCH", payload)),
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
  createWorkObject: (payload: WorkObjectCreatePayload) => request<WorkObject>("/work-objects", jsonInit("POST", payload)),
  leaves: (companyId: string) => request<LeaveRequest[]>(companyPath("/leaves", companyId)),
  createLeave: (payload: LeaveCreatePayload) => request<LeaveRequest>("/leaves", jsonInit("POST", payload)),
  events: (companyId: string) => request<Event[]>(companyPath("/timeline", companyId)),
  notifications: (companyId: string) => request<Notification[]>(companyPath("/notifications", companyId)),
};
