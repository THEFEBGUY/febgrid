import type { FebGridData, UserRole } from "../types/api";
import type { PageKey } from "../types/domain";


export type FebGridModuleKey = Exclude<keyof FebGridData, "companies">;

const ADMIN_PAGE_DATA: Record<PageKey, FebGridModuleKey[]> = {
  dashboard: ["dashboardSummary"],
  companies: [],
  employees: ["employees", "invitations", "departments", "teams"],
  teams: ["teams", "departments", "employees"],
  projects: ["projects", "employees", "departments", "teams"],
  "work-objects": ["workObjects", "employees", "projects", "departments", "teams", "workObjectTypes", "customFields"],
  leaves: ["leaves", "employees"],
  events: [],
  announcements: ["announcements"],
  notifications: ["notifications"],
  memory: [],
  "work-dna": ["projects", "departments", "teams"],
  settings: [
    "companySettings",
    "billingPlans",
    "billingSummary",
    "industryTemplates",
    "workObjectTypes",
    "customFields",
    "files",
    "aiCapabilities",
    "aiProviderStatus",
    "aiSafetySettings",
    "aiJobQueueSummary",
    "aiJobs",
  ],
  "my-dashboard": [],
  "my-work": [],
  "my-projects": [],
  "my-digital-twin": [],
  "my-leave": [],
  "my-profile": [],
};

const EMPLOYEE_PAGE_DATA: Partial<Record<PageKey, FebGridModuleKey[]>> = {
  "my-dashboard": ["employees", "workObjects", "leaves", "notifications", "announcements"],
  "my-work": ["employees", "leaveApprovers", "workObjects"],
  "my-projects": ["projects"],
  "my-digital-twin": ["employees"],
  "my-leave": ["employees", "leaveApprovers", "leaves"],
  "my-profile": [],
  notifications: ["notifications"],
  announcements: ["announcements"],
};

export function getPageDataKeys(page: PageKey, role: UserRole | null): FebGridModuleKey[] {
  const pageKeys = role === "employee" ? EMPLOYEE_PAGE_DATA[page] ?? [] : ADMIN_PAGE_DATA[page];
  return Array.from(new Set<FebGridModuleKey>([...pageKeys, "notificationUnreadCount"]));
}
