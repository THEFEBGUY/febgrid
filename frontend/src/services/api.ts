import type {
  Company,
  CompanyCreatePayload,
  Employee,
  EmployeeCreatePayload,
  Event,
  LeaveCreatePayload,
  LeaveRequest,
  Notification,
  Project,
  Team,
  WorkObject,
  WorkObjectCreatePayload,
} from "../types/api";

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, "") ?? "http://127.0.0.1:8000";

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
  companies: () => request<Company[]>("/companies"),
  createCompany: (payload: CompanyCreatePayload) => request<Company>("/companies", jsonInit("POST", payload)),
  employees: (companyId: string) => request<Employee[]>(companyPath("/employees", companyId)),
  createEmployee: (payload: EmployeeCreatePayload) => request<Employee>("/employees", jsonInit("POST", payload)),
  teams: (companyId: string) => request<Team[]>(companyPath("/teams", companyId)),
  projects: (companyId: string) => request<Project[]>(companyPath("/projects", companyId)),
  workObjects: (companyId: string) => request<WorkObject[]>(companyPath("/work-objects", companyId)),
  createWorkObject: (payload: WorkObjectCreatePayload) => request<WorkObject>("/work-objects", jsonInit("POST", payload)),
  leaves: (companyId: string) => request<LeaveRequest[]>(companyPath("/leaves", companyId)),
  createLeave: (payload: LeaveCreatePayload) => request<LeaveRequest>("/leaves", jsonInit("POST", payload)),
  events: (companyId: string) => request<Event[]>(companyPath("/timeline", companyId)),
  notifications: (companyId: string) => request<Notification[]>(companyPath("/notifications", companyId)),
};
