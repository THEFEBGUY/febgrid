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
  manager_id: string | null;
  full_name: string;
  email: string;
  phone: string | null;
  role: string;
  department: string | null;
  employment_type: string;
  status: string;
  location: string | null;
  profile_image_url: string | null;
  skills: string[];
  metadata: Record<string, unknown>;
}

export interface EmployeeCreatePayload {
  company_id: string;
  manager_id?: string | null;
  full_name: string;
  email: string;
  phone?: string | null;
  role: string;
  department?: string | null;
  employment_type: string;
  status: string;
  location?: string | null;
  profile_image_url?: string | null;
  skills: string[];
  metadata: Record<string, unknown>;
}

export interface Team extends Timestamped {
  id: string;
  company_id: string;
  lead_employee_id: string | null;
  name: string;
  department: string | null;
  description: string | null;
}

export interface Project extends Timestamped {
  id: string;
  company_id: string;
  owner_employee_id: string | null;
  name: string;
  description: string | null;
  status: string;
  priority: string;
  start_date: string | null;
  due_date: string | null;
  progress_percent: number;
  tags: string[];
}

export interface WorkObject extends Timestamped {
  id: string;
  company_id: string;
  project_id: string | null;
  created_by_employee_id: string | null;
  assigned_to_employee_id: string | null;
  title: string;
  description: string | null;
  object_type: string;
  status: string;
  priority: string;
  due_date: string | null;
  tags: string[];
  custom_fields: Record<string, unknown>;
  ai_summary: string | null;
}

export interface WorkObjectCreatePayload {
  company_id: string;
  project_id?: string | null;
  created_by_employee_id?: string | null;
  assigned_to_employee_id?: string | null;
  title: string;
  description?: string | null;
  object_type: string;
  status: string;
  priority: string;
  due_date?: string | null;
  tags: string[];
  custom_fields: Record<string, unknown>;
  ai_summary?: string | null;
}

export interface LeaveRequest extends Timestamped {
  id: string;
  company_id: string;
  employee_id: string;
  approver_employee_id: string | null;
  start_date: string;
  end_date: string;
  leave_type: string;
  reason: string | null;
  status: string;
  decision_note: string | null;
}

export interface LeaveCreatePayload {
  company_id: string;
  employee_id: string;
  approver_employee_id?: string | null;
  start_date: string;
  end_date: string;
  leave_type: string;
  reason?: string | null;
  status: string;
  decision_note?: string | null;
}

export interface Event {
  id: string;
  company_id: string;
  actor_employee_id: string | null;
  target_entity_type: string | null;
  target_entity_id: string | null;
  event_type: string;
  title: string;
  description: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface Notification {
  id: string;
  company_id: string;
  recipient_employee_id: string;
  title: string;
  message: string;
  notification_type: string;
  related_entity_type: string | null;
  related_entity_id: string | null;
  is_read: boolean;
  created_at: string;
  read_at: string | null;
}

export interface FebGridData {
  companies: Company[];
  employees: Employee[];
  teams: Team[];
  projects: Project[];
  workObjects: WorkObject[];
  leaves: LeaveRequest[];
  events: Event[];
  notifications: Notification[];
}
