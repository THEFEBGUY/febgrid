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
  extension: string | null;
  checksum_sha256: string | null;
  storage_provider: string;
  storage_path: string;
  public_url: string | null;
  description: string | null;
  tags: string[];
  processing_status: string;
  scan_status: string;
  ai_processing_status: string;
  metadata: Record<string, unknown>;
  is_active: boolean;
  is_deleted: boolean;
  archived_at: string | null;
  deleted_at: string | null;
}

export interface AttachmentUpdatePayload {
  description?: string | null;
  tags?: string[];
  processing_status?: string;
  scan_status?: string;
  metadata?: Record<string, unknown>;
}

export type AIJobStatus = "queued" | "running" | "succeeded" | "failed" | "cancelled" | "skipped";
export type AIJobType =
  | "work_object_summary_mock"
  | "project_summary_mock"
  | "employee_workload_mock"
  | "file_summary_mock"
  | "company_brief_mock"
  | "work_object_summary_safe"
  | "project_summary_safe"
  | "company_brief_safe"
  | "file_summary_safe"
  | "document_analysis_safe"
  | "image_analysis_safe"
  | "audio_transcription_safe";

export interface AIJob extends Timestamped {
  id: string;
  company_id: string;
  requested_by_user_id: string | null;
  requested_by_employee_id: string | null;
  job_type: AIJobType | string;
  status: AIJobStatus | string;
  priority: "low" | "normal" | "high" | "urgent" | string;
  input_entity_type: string | null;
  input_entity_id: string | null;
  input_payload: Record<string, unknown>;
  output_payload: Record<string, unknown>;
  error_message: string | null;
  provider_key: string;
  provider_mode: AIProviderMode | string;
  attempts: number;
  max_attempts: number;
  queued_at: string | null;
  locked_at: string | null;
  locked_by: string | null;
  next_attempt_at: string | null;
  last_attempt_at: string | null;
  timeout_seconds: number;
  error_code: string | null;
  retryable: boolean;
  cancelled_by_user_id: string | null;
  cancellation_reason: string | null;
  run_mode: string;
  scheduled_at: string | null;
  started_at: string | null;
  completed_at: string | null;
  failed_at: string | null;
  cancelled_at: string | null;
  metadata: Record<string, unknown>;
}

export interface AIJobQueueSummary {
  company_id: string;
  queued: number;
  running: number;
  succeeded: number;
  failed: number;
  cancelled: number;
  skipped: number;
  retryable_failed: number;
  stale_running: number;
}

export interface AIJobProcessResult {
  processed: boolean;
  message: string;
  job: AIJob | null;
}

export interface AIJobRecoveryResult {
  recovered: number;
  message: string;
}

export interface AIJobCreatePayload {
  company_id: string;
  job_type: AIJobType | string;
  priority?: "low" | "normal" | "high" | "urgent";
  input_entity_type?: string | null;
  input_entity_id?: string | null;
  input_payload?: Record<string, unknown>;
  max_attempts?: number;
  scheduled_at?: string | null;
  metadata?: Record<string, unknown>;
}

export interface AICapability {
  job_type: AIJobType | string;
  label: string;
  description: string;
  mock_only: boolean;
}

export interface AICapabilities {
  company_id: string;
  provider_key: string;
  provider_mode: AIProviderMode | string;
  real_ai_connected: boolean;
  external_calls_enabled: boolean;
  capabilities: AICapability[];
  message: string;
}

export type AIProviderMode = "disabled" | "mock" | "groq" | "openai_future" | "custom_openai_compatible_future";

export interface AIProviderStatus {
  company_id: string;
  provider_key: string;
  provider_mode: AIProviderMode | string;
  configured: boolean;
  model_name: string | null;
  external_processing_enabled: boolean;
  external_processing_allowed: boolean;
  ai_enabled: boolean;
  real_ai_connected: boolean;
  supported_real_job_types: string[];
  supported_mock_job_types: string[];
  message: string;
}

export interface AISafetySettings {
  company_id: string;
  ai_enabled: boolean;
  external_ai_processing_allowed: boolean;
  default_provider_mode: AIProviderMode | string;
  allowed_ai_job_types: string[];
  max_monthly_ai_jobs: number | null;
  metadata: Record<string, unknown>;
}

export interface AISafetySettingsUpdatePayload {
  ai_enabled?: boolean;
  external_ai_processing_allowed?: boolean;
  default_provider_mode?: AIProviderMode | string;
  allowed_ai_job_types?: string[];
  max_monthly_ai_jobs?: number | null;
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

export interface AuditLog extends Event {
  actor_name: string | null;
  actor_role: string | null;
  actor_employee_name: string | null;
  target_label: string | null;
  company_name: string | null;
  summary: string | null;
  is_audit_relevant: boolean;
}

export interface PlanDefinition {
  key: string;
  name: string;
  description: string;
  seat_limit: number;
  storage_limit_mb: number;
  work_object_limit: number;
  project_limit: number;
  employee_limit: number;
  notification_limit: number | null;
  file_upload_limit_mb: number;
  metadata: Record<string, unknown>;
}

export interface CompanyBillingPlan extends Timestamped {
  id: string;
  company_id: string;
  plan_key: string;
  billing_status: string;
  trial_start_at: string | null;
  trial_ends_at: string | null;
  current_period_start: string | null;
  current_period_end: string | null;
  seat_limit: number;
  storage_limit_mb: number;
  work_object_limit: number;
  project_limit: number;
  employee_limit: number;
  notification_limit: number | null;
  file_upload_limit_mb: number;
  is_trial: boolean;
  is_active: boolean;
  metadata: Record<string, unknown>;
}

export interface BillingUsage {
  company_id: string;
  active_employees: number;
  active_projects: number;
  active_work_objects: number;
  uploaded_file_count: number;
  storage_used_mb: number;
  active_departments: number;
  active_teams: number;
  notifications_count: number;
  monthly_events_count: number;
}

export interface UsageWarning {
  code: string;
  message: string;
  current: number;
  limit: number;
  severity: "warning" | "critical";
}

export interface BillingSummary {
  company_id: string;
  company_name: string;
  generated_at: string;
  plan: CompanyBillingPlan;
  usage: BillingUsage;
  warnings: UsageWarning[];
  payment_provider_enabled: boolean;
  payment_provider_note: string;
}

export interface CompanyPlanUpdatePayload {
  plan_key?: string | null;
  billing_status?: string | null;
  trial_start_at?: string | null;
  trial_ends_at?: string | null;
  current_period_start?: string | null;
  current_period_end?: string | null;
  seat_limit?: number | null;
  storage_limit_mb?: number | null;
  work_object_limit?: number | null;
  project_limit?: number | null;
  employee_limit?: number | null;
  notification_limit?: number | null;
  file_upload_limit_mb?: number | null;
  is_trial?: boolean | null;
  is_active?: boolean | null;
  metadata?: Record<string, unknown> | null;
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

export type CompanyMemoryStatus = "draft" | "suggested" | "approved" | "rejected" | "archived";
export type CompanyMemoryImportance = "low" | "normal" | "high" | "critical";
export type CompanyMemoryVisibility = "owner_admin" | "manager_hr" | "team" | "project_members" | "employee_self" | "company";

export interface CompanyMemory {
  id: string;
  company_id: string;
  title: string;
  memory_type: string;
  scope_type: string;
  scope_id: string | null;
  source_type: string | null;
  source_id: string | null;
  source_ai_job_id: string | null;
  content: string;
  summary: string | null;
  tags: string[];
  importance: CompanyMemoryImportance;
  confidence: number | null;
  status: CompanyMemoryStatus;
  visibility: CompanyMemoryVisibility;
  created_by_user_id: string | null;
  created_by_employee_id: string | null;
  approved_by_user_id: string | null;
  approved_at: string | null;
  rejected_by_user_id: string | null;
  rejected_at: string | null;
  archived_by_user_id: string | null;
  archived_at: string | null;
  last_used_at: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface CompanyMemoryCreatePayload {
  company_id: string;
  title: string;
  memory_type: string;
  scope_type: string;
  scope_id?: string | null;
  source_type?: string | null;
  source_id?: string | null;
  source_ai_job_id?: string | null;
  content: string;
  summary?: string | null;
  tags?: string[];
  importance?: CompanyMemoryImportance;
  confidence?: number | null;
  status?: CompanyMemoryStatus;
  visibility?: CompanyMemoryVisibility;
  metadata?: Record<string, unknown>;
}

export interface CompanyMemoryUpdatePayload {
  title?: string;
  memory_type?: string;
  scope_type?: string;
  scope_id?: string | null;
  content?: string;
  summary?: string | null;
  tags?: string[];
  importance?: CompanyMemoryImportance;
  confidence?: number | null;
  visibility?: CompanyMemoryVisibility;
  metadata?: Record<string, unknown>;
}

export interface CompanyMemoryFromAIJobPayload {
  company_id: string;
  title?: string | null;
  memory_type?: string | null;
  importance?: CompanyMemoryImportance;
  visibility?: CompanyMemoryVisibility;
  approve_now?: boolean;
  tags?: string[];
  metadata?: Record<string, unknown>;
}

export type CompanyPulseStatus = "excellent" | "healthy" | "watch" | "at_risk" | "critical";
export type CompanyPulseTrend = "improving" | "stable" | "declining" | "unknown";

export interface CompanyPulseSnapshot extends Timestamped {
  id: string;
  company_id: string;
  overall_score: number;
  pulse_status: CompanyPulseStatus | string;
  trend: CompanyPulseTrend | string;
  summary: string;
  section_scores: Record<string, number>;
  key_signals: string[];
  risks: string[];
  recommended_actions: string[];
  source_counts: Record<string, unknown>;
  generated_by_user_id: string | null;
  generated_by_ai_job_id: string | null;
  is_rule_based: boolean;
  metadata: Record<string, unknown>;
}

export interface CompanyPulseSignals {
  company_id: string;
  overall_score: number;
  pulse_status: CompanyPulseStatus | string;
  trend: CompanyPulseTrend | string;
  summary: string;
  section_scores: Record<string, number>;
  key_signals: string[];
  risks: string[];
  recommended_actions: string[];
  source_counts: Record<string, unknown>;
  generated_at: string;
  is_rule_based: boolean;
  metadata: Record<string, unknown>;
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
  memory_summary?: {
    approved_memories: number;
    pending_suggestions: number;
    important_memories: number;
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
  aiCapabilities: AICapabilities | null;
  aiProviderStatus: AIProviderStatus | null;
  aiSafetySettings: AISafetySettings | null;
  aiJobQueueSummary: AIJobQueueSummary | null;
  aiJobs: AIJob[];
  auditLogs: AuditLog[];
  billingPlans: PlanDefinition[];
  billingSummary: BillingSummary | null;
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
  files: Attachment[];
}
