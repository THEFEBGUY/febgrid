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

export interface CompanySettings {
  company_id: string;
  name: string;
  industry: string | null;
  size: string | null;
  timezone: string;
  description: string | null;
  settings: Record<string, unknown>;
  work_week: string[];
  default_work_object_type: string;
  default_priority: string;
  file_upload_max_mb: number;
  template_key: string | null;
  metadata: Record<string, unknown>;
}

export interface CompanySettingsUpdatePayload {
  name?: string;
  industry?: string | null;
  size?: string | null;
  timezone?: string;
  description?: string | null;
  work_week?: string[];
  default_work_object_type?: string;
  default_priority?: string;
  file_upload_max_mb?: number;
  dashboard_flags?: Record<string, unknown>;
  notification_defaults?: Record<string, unknown>;
  metadata?: Record<string, unknown>;
}

export interface IndustryTemplateWorkObjectType {
  key: string;
  name: string;
  description: string | null;
  icon: string | null;
  color: string | null;
  is_default: boolean;
  sort_order: number;
}

export interface IndustryTemplateCustomField {
  type_key: string;
  field_key: string;
  label: string;
  field_type: CustomFieldType;
  required: boolean;
  options: string[];
  default_value: unknown;
  help_text: string | null;
  sort_order: number;
}

export interface IndustryTemplate {
  key: string;
  name: string;
  description: string;
  industry: string;
  work_object_types: IndustryTemplateWorkObjectType[];
  custom_fields: IndustryTemplateCustomField[];
  metadata: Record<string, unknown>;
}

export interface ApplyIndustryTemplateResult {
  company_id: string;
  template_key: string;
  created_type_count: number;
  created_custom_field_count: number;
  skipped_type_count: number;
  skipped_custom_field_count: number;
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
  account_status: string;
  activation_status: string;
  profile_completion_status: string;
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

export interface EmployeeSelfUpdatePayload {
  full_name?: string;
  phone?: string | null;
  location?: string | null;
  profile_image_url?: string | null;
  skills?: string[];
  metadata?: Record<string, unknown>;
}

export interface EmployeeInvitation extends Timestamped {
  id: string;
  company_id: string;
  employee_id: string | null;
  invited_email: string;
  normalized_email: string;
  invited_role: string;
  department_id: string | null;
  team_id: string | null;
  manager_employee_id: string | null;
  job_title: string | null;
  employment_type: string | null;
  joining_date: string | null;
  invite_source: string;
  approval_required: boolean;
  status: string;
  expires_at: string;
  sent_at: string;
  accepted_at: string | null;
  revoked_at: string | null;
  revoked_by_user_id: string | null;
  approved_at: string | null;
  approved_by_user_id: string | null;
  rejected_at: string | null;
  rejected_by_user_id: string | null;
  rejection_reason: string | null;
  invited_by_user_id: string | null;
  metadata: Record<string, unknown>;
}

export interface EmployeeInvitationCreatePayload {
  company_id: string;
  invited_email: string;
  invited_role: UserRole;
  full_name?: string | null;
  department_id?: string | null;
  team_id?: string | null;
  manager_employee_id?: string | null;
  job_title?: string | null;
  employment_type?: string | null;
  joining_date?: string | null;
  approval_required: boolean;
  expires_in_hours?: number;
  note?: string | null;
  metadata?: Record<string, unknown>;
}

export interface EmployeeInvitationActionResult {
  invitation: EmployeeInvitation;
  acceptance_url: string;
  email_delivery: Record<string, unknown>;
}

export interface InvitationPreview {
  company_id: string;
  company_name: string;
  employee_id: string | null;
  employee_name: string | null;
  invited_email: string;
  invited_role: string;
  invite_source: string;
  approval_required: boolean;
  status: string;
  expires_at: string;
  inviter_name: string | null;
  job_title: string | null;
  employment_type: string | null;
  joining_date: string | null;
  department_name: string | null;
  team_name: string | null;
  manager_name: string | null;
  account_status: string | null;
  activation_status: string | null;
  profile_completion_status: string | null;
  metadata: Record<string, unknown>;
}

export interface InvitationAcceptPayload {
  token: string;
  email: string;
  password: string;
  full_name?: string | null;
}

export interface InvitationAcceptResult {
  invitation: EmployeeInvitation;
  employee: Employee;
  user: AuthUser;
  requires_profile: boolean;
  approval_required: boolean;
  message: string;
}

export interface InvitationProfileCompletePayload {
  token: string;
  email: string;
  full_name?: string | null;
  phone?: string | null;
  location?: string | null;
  profile_image_url?: string | null;
  skills?: string[];
  bio?: string | null;
  emergency_contact_name?: string | null;
  emergency_contact_phone?: string | null;
  metadata?: Record<string, unknown>;
}

export interface InvitationProfileCompleteResult {
  invitation: EmployeeInvitation;
  employee: Employee;
  session: AuthSession | null;
  approval_required: boolean;
  message: string;
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

export interface WorkObjectTypeDefinition extends Timestamped {
  id: string;
  company_id: string;
  key: string;
  name: string;
  description: string | null;
  icon: string | null;
  color: string | null;
  is_default: boolean;
  is_active: boolean;
  sort_order: number;
  metadata: Record<string, unknown>;
}

export interface WorkObjectTypeCreatePayload {
  company_id: string;
  key: string;
  name: string;
  description?: string | null;
  icon?: string | null;
  color?: string | null;
  is_default?: boolean;
  is_active?: boolean;
  sort_order?: number;
  metadata?: Record<string, unknown>;
}

export interface WorkObjectTypeUpdatePayload {
  name?: string;
  description?: string | null;
  icon?: string | null;
  color?: string | null;
  is_default?: boolean;
  is_active?: boolean;
  sort_order?: number;
  metadata?: Record<string, unknown>;
}

export type CustomFieldType = "text" | "textarea" | "number" | "date" | "checkbox" | "select" | "multiselect";

export interface CustomFieldDefinition extends Timestamped {
  id: string;
  company_id: string;
  work_object_type_id: string | null;
  type_key: string;
  field_key: string;
  label: string;
  field_type: CustomFieldType;
  required: boolean;
  options: string[];
  default_value: unknown;
  help_text: string | null;
  sort_order: number;
  is_active: boolean;
  metadata: Record<string, unknown>;
}

export interface CustomFieldCreatePayload {
  company_id: string;
  work_object_type_id?: string | null;
  type_key: string;
  field_key: string;
  label: string;
  field_type: CustomFieldType;
  required?: boolean;
  options?: string[];
  default_value?: unknown;
  help_text?: string | null;
  sort_order?: number;
  is_active?: boolean;
  metadata?: Record<string, unknown>;
}

export interface CustomFieldUpdatePayload {
  work_object_type_id?: string | null;
  label?: string;
  field_type?: CustomFieldType;
  required?: boolean;
  options?: string[];
  default_value?: unknown;
  help_text?: string | null;
  sort_order?: number;
  is_active?: boolean;
  metadata?: Record<string, unknown>;
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

export interface CommentMention {
  id: string;
  company_id: string;
  comment_id: string;
  mentioned_user_id: string | null;
  mentioned_employee_id: string | null;
  created_at: string;
}

export interface Comment extends Timestamped {
  id: string;
  company_id: string;
  author_user_id: string | null;
  author_employee_id: string | null;
  target_entity_type: "work_object" | "project";
  target_entity_id: string;
  parent_comment_id: string | null;
  body: string;
  metadata: Record<string, unknown>;
  is_edited: boolean;
  edited_at: string | null;
  is_archived: boolean;
  mentions: CommentMention[];
}

export interface CommentCreatePayload {
  company_id: string;
  target_entity_type: "work_object" | "project";
  target_entity_id: string;
  parent_comment_id?: string | null;
  body: string;
  metadata?: Record<string, unknown>;
  mentioned_user_ids?: string[];
  mentioned_employee_ids?: string[];
}

export interface CommentUpdatePayload {
  body?: string;
  metadata?: Record<string, unknown>;
  mentioned_user_ids?: string[];
  mentioned_employee_ids?: string[];
}

export interface Announcement extends Timestamped {
  id: string;
  company_id: string;
  author_user_id: string | null;
  title: string;
  body: string;
  priority: "low" | "normal" | "high" | "urgent";
  metadata: Record<string, unknown>;
  is_published: boolean;
  published_at: string | null;
  is_archived: boolean;
}

export interface AnnouncementCreatePayload {
  company_id: string;
  title: string;
  body: string;
  priority: "low" | "normal" | "high" | "urgent";
  metadata?: Record<string, unknown>;
  is_published?: boolean;
}

export interface AnnouncementUpdatePayload {
  title?: string;
  body?: string;
  priority?: "low" | "normal" | "high" | "urgent";
  metadata?: Record<string, unknown>;
  is_published?: boolean;
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

export interface SearchResultItem {
  id: string;
  type: string;
  title: string;
  subtitle: string | null;
  description: string | null;
  status: string | null;
  priority: string | null;
  related_entity_type: string | null;
  related_entity_id: string | null;
  created_at: string | null;
  updated_at: string | null;
  href: string | null;
  metadata: Record<string, unknown>;
}

export interface SearchResponse {
  query: string;
  company_id: string;
  total: number;
  groups: Record<string, SearchResultItem[]>;
  results: SearchResultItem[];
}

export interface DashboardSummary {
  company_overview: {
    company_id: string;
    company_name: string;
    generated_at: string;
  };
  employee_summary: {
    total_employees: number;
    active_employees: number;
    available_employees: number;
    on_leave_employees: number;
    busy_employees: number;
    inactive_employees: number;
  };
  work_summary: {
    total_work_objects: number;
    pending_or_assigned: number;
    in_progress: number;
    blocked: number;
    under_review: number;
    completed: number;
    overdue: number;
    due_today: number;
    high_or_critical_priority: number;
  };
  project_summary: {
    total_projects: number;
    active_projects: number;
    on_hold_projects: number;
    delayed_projects: number;
    completed_projects: number;
    high_priority_projects: number;
    average_progress: number;
  };
  leave_summary: {
    total_leave_requests: number;
    pending_leave_requests: number;
    approved_leave_requests: number;
    rejected_leave_requests: number;
    cancelled_leave_requests: number;
    upcoming_approved_leaves: number;
  };
  file_summary: {
    total_attachments: number;
    recent_uploads_count: number;
  };
  notification_summary: {
    unread_notifications: number;
    important_notifications: number;
  };
  announcement_summary: {
    active_announcements: number;
    urgent_announcements: number;
  };
  recent_events: Event[];
  recent_notifications: Notification[];
  recent_announcements: Announcement[];
  priority_work: WorkObject[];
  project_health_list: Project[];
  leave_attention_list: LeaveRequest[];
}

export interface FebGridData {
  companies: Company[];
  companySettings: CompanySettings | null;
  industryTemplates: IndustryTemplate[];
  workObjectTypes: WorkObjectTypeDefinition[];
  customFields: CustomFieldDefinition[];
  dashboardSummary: DashboardSummary | null;
  departments: Department[];
  employees: Employee[];
  leaveApprovers: Employee[];
  invitations: EmployeeInvitation[];
  teams: Team[];
  projects: Project[];
  workObjects: WorkObject[];
  leaves: LeaveRequest[];
  events: Event[];
  notifications: Notification[];
  announcements: Announcement[];
}
