export interface Timestamped {
  created_at: string;
  updated_at: string;
}

export interface Company extends Timestamped {
  id: string;
  name: string;
  slug: string;
  industry: string | null;
  size: string | null;
  timezone: string;
  description: string | null;
  settings: Record<string, unknown>;
  is_active: boolean;
}

export interface CompanyCreatePayload {
  name: string;
  slug: string;
  industry?: string | null;
  size?: string | null;
  timezone: string;
  description?: string | null;
  settings: Record<string, unknown>;
}

export type UserRole = "company_owner" | "admin" | "manager" | "employee";

export interface AuthUser extends Timestamped {
  id: string;
  company_id: string;
  full_name: string;
  email: string;
  role: UserRole;
  auth_provider: string;
  is_active: boolean;
  last_login_at: string | null;
}

export interface AuthSession {
  access_token: string;
  token_type: "bearer";
  user: AuthUser;
  company: Company;
}

export interface AuthMe {
  user: AuthUser;
  company: Company;
}

export interface LoginPayload {
  email: string;
  password: string;
}

export interface RegisterPayload {
  full_name: string;
  email: string;
  password: string;
  company_name: string;
  company_slug: string;
  industry?: string | null;
  size?: string | null;
  timezone: string;
}

export interface Employee extends Timestamped {
  id: string;
  company_id: string;
  user_id: string | null;
  department_id: string | null;
  team_id: string | null;
  manager_id: string | null;
  full_name: string;
  email: string | null;
  phone: string | null;
  role_title: string;
  department: string | null;
  employment_type: string;
  current_status: string;
  location: string | null;
  profile_image_url: string | null;
  skills: string[];
  metadata: Record<string, unknown>;
  joined_at: string | null;
  is_active: boolean;
}

export interface EmployeeCreatePayload {
  company_id: string;
  user_id?: string | null;
  department_id?: string | null;
  team_id?: string | null;
  manager_id?: string | null;
  full_name: string;
  email?: string | null;
  phone?: string | null;
  role_title: string;
  department?: string | null;
  employment_type: string;
  current_status: string;
  location?: string | null;
  profile_image_url?: string | null;
  skills: string[];
  metadata: Record<string, unknown>;
  joined_at?: string | null;
  is_active?: boolean;
}

export interface EmployeeUpdatePayload {
  user_id?: string | null;
  department_id?: string | null;
  team_id?: string | null;
  manager_id?: string | null;
  full_name?: string;
  email?: string | null;
  phone?: string | null;
  role_title?: string;
  department?: string | null;
  employment_type?: string;
  current_status?: string;
  location?: string | null;
  profile_image_url?: string | null;
  skills?: string[];
  metadata?: Record<string, unknown>;
  joined_at?: string | null;
  is_active?: boolean;
}

export interface Department extends Timestamped {
  id: string;
  company_id: string;
  name: string;
  description: string | null;
  is_active: boolean;
}

export interface DepartmentCreatePayload {
  company_id: string;
  name: string;
  description?: string | null;
  is_active?: boolean;
}

export interface Team extends Timestamped {
  id: string;
  company_id: string;
  department_id: string | null;
  lead_employee_id: string | null;
  name: string;
  department: string | null;
  description: string | null;
  is_active: boolean;
}

export interface TeamCreatePayload {
  company_id: string;
  department_id?: string | null;
  lead_employee_id?: string | null;
  name: string;
  department?: string | null;
  description?: string | null;
  is_active?: boolean;
}

export interface Project extends Timestamped {
  id: string;
  company_id: string;
  owner_employee_id: string | null;
  owner_user_id: string | null;
  department_id: string | null;
  team_id: string | null;
  name: string;
  code: string | null;
  description: string | null;
  status: string;
  priority: string;
  start_date: string | null;
  due_date: string | null;
  progress_percent: number;
  risk_level: string | null;
  is_active: boolean;
  tags: string[];
}

export interface ProjectCreatePayload {
  company_id: string;
  owner_employee_id?: string | null;
  owner_user_id?: string | null;
  department_id?: string | null;
  team_id?: string | null;
  name: string;
  code?: string | null;
  description?: string | null;
  status: string;
  priority: string;
  start_date?: string | null;
  due_date?: string | null;
  progress_percent: number;
  risk_level?: string | null;
  is_active?: boolean;
  tags: string[];
}

export interface ProjectUpdatePayload {
  owner_employee_id?: string | null;
  owner_user_id?: string | null;
  department_id?: string | null;
  team_id?: string | null;
  name?: string;
  code?: string | null;
  description?: string | null;
  status?: string;
  priority?: string;
  start_date?: string | null;
  due_date?: string | null;
  progress_percent?: number;
  risk_level?: string | null;
  is_active?: boolean;
  tags?: string[];
}

export interface ProjectMember extends Timestamped {
  id: string;
  project_id: string;
  company_id: string;
  employee_id: string;
  role_on_project: string | null;
  is_active: boolean;
}

export interface ProjectMemberCreatePayload {
  company_id: string;
  employee_id: string;
  role_on_project?: string | null;
}

export interface WorkObject extends Timestamped {
  id: string;
  company_id: string;
  project_id: string | null;
  department_id: string | null;
  team_id: string | null;
  creator_employee_id: string | null;
  creator_user_id: string | null;
  assignee_employee_id: string | null;
  title: string;
  description: string | null;
  object_type: string;
  status: string;
  priority: string;
  due_date: string | null;
  start_date: string | null;
  completed_at: string | null;
  tags: string[];
  metadata: Record<string, unknown>;
  custom_fields: Record<string, unknown>;
  ai_summary: string | null;
  is_active: boolean;
}

export interface WorkObjectCreatePayload {
  company_id: string;
  project_id?: string | null;
  department_id?: string | null;
  team_id?: string | null;
  creator_employee_id?: string | null;
  creator_user_id?: string | null;
  assignee_employee_id?: string | null;
  title: string;
  description?: string | null;
  object_type: string;
  status: string;
  priority: string;
  due_date?: string | null;
  start_date?: string | null;
  completed_at?: string | null;
  tags: string[];
  metadata: Record<string, unknown>;
  custom_fields: Record<string, unknown>;
  ai_summary?: string | null;
  is_active?: boolean;
}

export interface WorkObjectUpdatePayload {
  project_id?: string | null;
  department_id?: string | null;
  team_id?: string | null;
  creator_employee_id?: string | null;
  creator_user_id?: string | null;
  assignee_employee_id?: string | null;
  title?: string;
  description?: string | null;
  object_type?: string;
  status?: string;
  priority?: string;
  due_date?: string | null;
  start_date?: string | null;
  completed_at?: string | null;
  tags?: string[];
  metadata?: Record<string, unknown>;
  custom_fields?: Record<string, unknown>;
  ai_summary?: string | null;
  is_active?: boolean;
}

export interface WorkObjectSummary {
  company_id: string;
  total: number;
  open: number;
  blocked: number;
  completed: number;
  due_soon: number;
  overdue: number;
}

export interface Attachment extends Timestamped {
  id: string;
  company_id: string;
  work_object_id: string | null;
  project_id: string | null;
  uploaded_by_user_id: string | null;
  uploaded_by_employee_id: string | null;
  linked_entity_type: string;
  linked_entity_id: string;
  file_name: string;
  original_file_name: string;
  content_type: string | null;
  file_size: number | null;
  storage_provider: string;
  storage_path: string;
  public_url: string | null;
  description: string | null;
  ai_processing_status: string;
  metadata: Record<string, unknown>;
  is_active: boolean;
}

export interface AttachmentUpdatePayload {
  description?: string | null;
  metadata?: Record<string, unknown>;
}

export interface LeaveRequest extends Timestamped {
  id: string;
  company_id: string;
  employee_id: string;
  approver_employee_id: string | null;
  requested_by_user_id: string | null;
  start_date: string;
  end_date: string;
  total_days: number;
  leave_type: string;
  reason: string | null;
  status: string;
  manager_note: string | null;
  submitted_at: string;
  approved_at: string | null;
  rejected_at: string | null;
  cancelled_at: string | null;
  metadata: Record<string, unknown>;
  is_active: boolean;
}

export interface LeaveCreatePayload {
  company_id: string;
  employee_id: string;
  approver_employee_id?: string | null;
  requested_by_user_id?: string | null;
  start_date: string;
  end_date: string;
  leave_type: string;
  reason?: string | null;
  status?: string;
  manager_note?: string | null;
  metadata?: Record<string, unknown>;
}

export interface LeaveUpdatePayload {
  employee_id?: string | null;
  approver_employee_id?: string | null;
  start_date?: string;
  end_date?: string;
  leave_type?: string;
  reason?: string | null;
  manager_note?: string | null;
  metadata?: Record<string, unknown>;
}

export interface LeaveDecisionPayload {
  company_id: string;
  approver_employee_id?: string | null;
  manager_note?: string | null;
}

export interface LeaveCancelPayload {
  company_id: string;
  actor_employee_id?: string | null;
  manager_note?: string | null;
}

export interface LeaveSummary {
  company_id: string;
  total: number;
  pending: number;
  approved: number;
  rejected: number;
  cancelled: number;
  this_week: number;
  this_month: number;
}

export interface Event {
  id: string;
  company_id: string;
  actor_user_id: string | null;
  actor_employee_id: string | null;
  target_entity_type: string | null;
  target_entity_id: string | null;
  related_entity_type: string | null;
  related_entity_id: string | null;
  event_type: string;
  title: string;
  description: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface Notification {
  id: string;
  company_id: string;
  recipient_user_id: string | null;
  recipient_employee_id: string | null;
  actor_user_id: string | null;
  actor_employee_id: string | null;
  event_id: string | null;
  target_entity_type: string | null;
  target_entity_id: string | null;
  title: string;
  message: string;
  notification_type: string;
  priority: "low" | "normal" | "high" | "urgent";
  action_url: string | null;
  metadata: Record<string, unknown>;
  is_read: boolean;
  created_at: string;
  updated_at: string;
  read_at: string | null;
  is_dismissed: boolean;
  dismissed_at: string | null;
}

export interface NotificationUnreadCount {
  company_id: string;
  unread_count: number;
}

export interface FebGridData {
  companies: Company[];
  departments: Department[];
  employees: Employee[];
  teams: Team[];
  projects: Project[];
  workObjects: WorkObject[];
  leaves: LeaveRequest[];
  events: Event[];
  notifications: Notification[];
}
