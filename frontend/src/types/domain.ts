import type { LucideIcon } from "lucide-react";

export type PageKey =
  | "dashboard"
  | "companies"
  | "employees"
  | "teams"
  | "projects"
  | "work-objects"
  | "leaves"
  | "events"
  | "announcements"
  | "notifications"
  | "settings";

export interface NavigationItem {
  key: PageKey;
  label: string;
  description: string;
  icon: LucideIcon;
}

export interface Metric {
  label: string;
  value: string;
  tone: "blue" | "green" | "amber" | "red" | "teal" | "slate";
  delta: string;
}

export interface CompanyRecord {
  id: string;
  name: string;
  industry: string;
  region: string;
  employees: number;
  status: "Active" | "Onboarding" | "Paused";
}

export interface EmployeeRecord {
  id: string;
  name: string;
  role: string;
  team: string;
  status: "Working" | "Available" | "Busy" | "On Leave" | "Offline";
  workCount: number;
}

export interface TeamRecord {
  id: string;
  name: string;
  department: string;
  lead: string;
  members: number;
  workload: string;
}

export interface ProjectRecord {
  id: string;
  name: string;
  owner: string;
  status: "Active" | "On Hold" | "Not Started" | "Completed" | "Delayed";
  priority: "Low" | "Medium" | "High" | "Critical";
  progress: number;
}

export interface WorkObjectRecord {
  id: string;
  title: string;
  type: string;
  assignee: string;
  status: "Draft" | "Assigned" | "In Progress" | "Blocked" | "Under Review" | "Completed";
  priority: "Low" | "Medium" | "High" | "Critical";
  due: string;
}

export interface LeaveRecord {
  id: string;
  employee: string;
  type: string;
  dates: string;
  status: "Pending" | "Approved" | "Rejected" | "Cancelled";
  approver: string;
}

export interface EventRecord {
  id: string;
  time: string;
  title: string;
  entity: string;
  type: string;
}

export interface NotificationRecord {
  id: string;
  title: string;
  message: string;
  type: string;
  read: boolean;
  createdAt: string;
}
