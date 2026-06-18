export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, "") ?? "http://127.0.0.1:8000";

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
    throw new ApiError(`Request failed for ${path}`, response.status);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

export const api = {
  health: () => request<{ status: string; service: string; environment: string }>("/health"),
  companies: () => request<unknown[]>("/companies"),
  employees: (companyId: string) => request<unknown[]>(`/employees?company_id=${companyId}`),
  teams: (companyId: string) => request<unknown[]>(`/teams?company_id=${companyId}`),
  projects: (companyId: string) => request<unknown[]>(`/projects?company_id=${companyId}`),
  workObjects: (companyId: string) => request<unknown[]>(`/work-objects?company_id=${companyId}`),
  leaves: (companyId: string) => request<unknown[]>(`/leaves?company_id=${companyId}`),
  events: (companyId: string) => request<unknown[]>(`/timeline?company_id=${companyId}`),
  notifications: (companyId: string) => request<unknown[]>(`/notifications?company_id=${companyId}`),
};
