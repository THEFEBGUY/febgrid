import type {
  CompanyRecord,
  EmployeeRecord,
  EventRecord,
  LeaveRecord,
  Metric,
  NotificationRecord,
  ProjectRecord,
  TeamRecord,
  WorkObjectRecord,
} from "../types/domain";

export const metrics: Metric[] = [
  { label: "Active employees", value: "42", tone: "green", delta: "+6 this month" },
  { label: "Open work objects", value: "128", tone: "blue", delta: "18 under review" },
  { label: "Blocked work", value: "7", tone: "red", delta: "3 need manager action" },
  { label: "Pending leaves", value: "5", tone: "amber", delta: "2 begin this week" },
];

export const companies: CompanyRecord[] = [
  { id: "cmp-001", name: "Northstar Operations", industry: "Field Services", region: "Pune", employees: 42, status: "Active" },
  { id: "cmp-002", name: "BluePeak Retail", industry: "Retail", region: "Mumbai", employees: 18, status: "Onboarding" },
  { id: "cmp-003", name: "UrbanWorks Studio", industry: "Agency", region: "Bengaluru", employees: 26, status: "Active" },
];

export const employees: EmployeeRecord[] = [
  { id: "emp-001", name: "Rahul Patil", role: "Site Manager", team: "Operations", status: "Working", workCount: 5 },
  { id: "emp-002", name: "Neha Shah", role: "HR Admin", team: "People", status: "Available", workCount: 2 },
  { id: "emp-003", name: "Aman Verma", role: "Project Owner", team: "Engineering", status: "Busy", workCount: 8 },
  { id: "emp-004", name: "Sara Khan", role: "Designer", team: "Creative", status: "On Leave", workCount: 1 },
];

export const teams: TeamRecord[] = [
  { id: "team-001", name: "Operations Grid", department: "Operations", lead: "Rahul Patil", members: 14, workload: "72%" },
  { id: "team-002", name: "People Desk", department: "HR", lead: "Neha Shah", members: 5, workload: "48%" },
  { id: "team-003", name: "Product Build", department: "Engineering", lead: "Aman Verma", members: 11, workload: "81%" },
];

export const projects: ProjectRecord[] = [
  { id: "prj-001", name: "Warehouse Audit", owner: "Rahul Patil", status: "Active", priority: "High", progress: 68 },
  { id: "prj-002", name: "Employee Directory Rollout", owner: "Neha Shah", status: "Active", priority: "Medium", progress: 52 },
  { id: "prj-003", name: "Store Opening Checklist", owner: "Aman Verma", status: "On Hold", priority: "Critical", progress: 34 },
];

export const workObjects: WorkObjectRecord[] = [
  { id: "wo-001", title: "Upload Site 12 inspection photos", type: "Site Visit", assignee: "Rahul Patil", status: "In Progress", priority: "High", due: "Today" },
  { id: "wo-002", title: "Approve leave handover plan", type: "Approval Request", assignee: "Neha Shah", status: "Under Review", priority: "Medium", due: "Tomorrow" },
  { id: "wo-003", title: "Resolve vendor invoice mismatch", type: "Invoice", assignee: "Aman Verma", status: "Blocked", priority: "Critical", due: "Today" },
  { id: "wo-004", title: "Draft campaign proofing checklist", type: "Document Review", assignee: "Sara Khan", status: "Assigned", priority: "Low", due: "Friday" },
];

export const leaves: LeaveRecord[] = [
  { id: "lv-001", employee: "Sara Khan", type: "Paid Leave", dates: "18 Jun - 20 Jun", status: "Approved", approver: "Neha Shah" },
  { id: "lv-002", employee: "Rahul Patil", type: "Half Day", dates: "21 Jun", status: "Pending", approver: "Aman Verma" },
  { id: "lv-003", employee: "Aman Verma", type: "Sick Leave", dates: "24 Jun", status: "Pending", approver: "Neha Shah" },
];

export const events: EventRecord[] = [
  { id: "evt-001", time: "09:05", title: "Site Visit work object created", entity: "Warehouse Audit", type: "work_object.created" },
  { id: "evt-002", time: "09:18", title: "Rahul status changed to Working", entity: "Rahul Patil", type: "employee.status_changed" },
  { id: "evt-003", time: "10:10", title: "Leave request submitted", entity: "Sara Khan", type: "leave.requested" },
  { id: "evt-004", time: "10:32", title: "Notification sent for blocked invoice", entity: "Invoice WO-003", type: "notification.sent" },
];

export const notifications: NotificationRecord[] = [
  { id: "ntf-001", title: "Work assigned", message: "Vendor invoice mismatch needs review.", type: "work_assigned", read: false, createdAt: "10:32" },
  { id: "ntf-002", title: "Leave approval needed", message: "Rahul submitted a half-day request.", type: "leave_request_submitted", read: false, createdAt: "09:50" },
  { id: "ntf-003", title: "File uploaded", message: "Site inspection images were attached.", type: "file_uploaded", read: true, createdAt: "Yesterday" },
];
