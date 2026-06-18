# FebGrid Product Requirements Document (PRD)

**Product Name:** FebGrid  
**Full Title:** FebGrid: The Unified Workspace with Automated AI Work Review by TheFebGuy  
**Creator:** TheFebGuy(Pranav Amble)  
**Document Type:** Product Requirements Document  
**Version:** v1.0  
**Date:** 18 June 2026  
**Target Launch Direction:** 2026 and future  
**Target Sectors:** Cross-industry: technology, non-technology, retail, construction, field operations, logistics, agencies, offices, small businesses, and enterprise companies  

---

## 1. Product Vision

FebGrid is a **Business Operating System** that converts company activity into operational intelligence.

FebGrid is not only an employee management system, HRMS, project management app, communication app, or AI assistant. It is a unified system where work, employees, communication, files, leave management, AI review, company memory, and executive intelligence exist in one live operational layer.

The core belief behind FebGrid is:

> **Better System = Better Product**

Instead of building disconnected features, FebGrid is built around engines:

- **Work Object Engine** — every type of work becomes a flexible object.
- **Event Engine** — every action generates an event.
- **Knowledge Engine** — everything becomes searchable.
- **AI Intelligence Engine** — everything becomes AI-readable.
- **Company Memory Engine** — every decision, document, and outcome becomes long-term company knowledge.

---

## 2. Product Positioning

### 2.1 One-Line Positioning

FebGrid is a unified business operating system that helps companies manage people, work, communication, files, and intelligence from one live operational dashboard.

### 2.2 Extended Positioning

FebGrid replaces the need for multiple disconnected subscriptions such as task tools, HRMS tools, team communication apps, document storage systems, and manual reporting workflows. It gives owners, managers, and employees one central grid where all business activity can be created, tracked, reviewed, searched, and summarized.

### 2.3 Category Definition

FebGrid should not be positioned as only:

- Project management software
- Employee management software
- HRMS software
- AI chatbot
- Task management software
- Communication tool

FebGrid should be positioned as:

> **The Central Nervous System of Business Operations**

or

> **A Business Operating System for modern teams**

---

## 3. Problem Statement

Companies suffer from operational fragmentation. A single company may use:

- Jira, ClickUp, Trello, or Asana for task management
- Slack, WhatsApp, or Microsoft Teams for communication
- Zoho, Keka, or spreadsheets for HR and leave tracking
- Google Drive or Dropbox for files
- Emails for approvals
- Manual reporting for leadership updates
- Separate AI tools for writing, code review, document analysis, or summarization

This creates several problems:

1. **Tool fatigue** — employees must switch between too many apps.
2. **Data fragmentation** — work information is spread across chats, files, emails, and spreadsheets.
3. **Low visibility** — leadership cannot see company operations clearly in real time.
4. **Manual reporting burden** — managers spend time collecting updates instead of acting on them.
5. **Weak accountability** — tasks, proof, files, and decisions are not always connected.
6. **No company memory** — important decisions disappear in chats, emails, or employee memory.
7. **Limited cross-industry flexibility** — many tools are designed mainly for software teams or office teams, not field, retail, construction, or mixed businesses.

FebGrid solves this by unifying business operations into one intelligent system.

---

## 4. Target Users

### 4.1 Primary User Groups

#### Company Owners / Founders

Need quick visibility into what is happening across the company without reading long reports.

Key needs:

- Company health overview
- Daily executive brief
- Team performance visibility
- Risk detection
- Cost and work progress awareness
- Reduced dependency on manual reporting

#### Managers / Team Leads

Need to assign, track, review, and coordinate work efficiently.

Key needs:

- Assign tasks
- Track employees
- Manage leaves
- Review work evidence
- Detect blockers
- Receive AI recommendations
- Coordinate backups when employees are unavailable

#### Employees / Field Workers

Need a simple way to receive work, update status, upload evidence, and communicate.

Key needs:

- Clear task list
- Simple status update
- Voice memo updates
- Photo/document upload
- Leave request submission
- Notifications
- Minimal complexity

#### HR / Admins

Need centralized employee records, leave records, roles, permissions, and company structure.

Key needs:

- Employee profiles
- Leave management
- Attendance/status tracking
- Role-based permissions
- Department/team structure
- Audit logs

#### Executives / Enterprise Leadership

Need high-level operational intelligence and governance.

Key needs:

- Executive dashboard
- Department health
- Risk radar
- Company memory
- Compliance controls
- Custom reports

---

## 5. Target Sectors

FebGrid must be designed for both tech and non-tech companies.

### 5.1 Technology Companies

Use cases:

- Task tracking
- Bug tracking
- Sprint management
- Pull request/code review tracking
- Documentation
- AI code pre-review
- Team workload monitoring

### 5.2 Construction / Field Operations

Use cases:

- Site visit updates
- Voice memos
- Site photos
- Material usage logs
- Attendance and shift status
- Safety issue reporting
- Contractor coordination

### 5.3 Retail / Small Businesses

Use cases:

- Stock checks
- Staff management
- Store tasks
- Supplier orders
- Receipts and invoices
- Daily sales notes
- Leave management

### 5.4 Logistics

Use cases:

- Delivery tracking
- Route issue reports
- Vehicle reports
- Driver status
- Proof of delivery
- Incident reporting

### 5.5 Agencies / Creative Teams

Use cases:

- Design reviews
- Client approvals
- Media uploads
- Campaign tasks
- Copy review
- UI mockup review

### 5.6 Offices / Professional Services

Use cases:

- Employee management
- Document workflows
- Client work tracking
- Internal communication
- Approval workflows
- Executive summaries

---

## 6. Product Principles

### 6.1 Core System Philosophy

FebGrid must follow these principles:

1. **Everything is a Work Object.**
2. **Every action generates an Event.**
3. **Everything is searchable.**
4. **Everything is AI-readable.**
5. **Everything contributes to Company Memory.**
6. **The system should work for tech and non-tech companies.**
7. **The user experience should feel simple even if the system is powerful.**
8. **AI should support operations, not replace managerial judgment.**
9. **The product should work in weak network environments.**
10. **The foundation must be flexible enough for future modules.**

### 6.2 Design Philosophy

The UI should feel:

- Clean
- Fast
- Premium
- Calm
- Trustworthy
- Operationally serious
- Easy for non-technical users
- Powerful for managers

The UI should avoid:

- Too many animations
- Flashy effects
- Confusing dashboards
- Overcrowded screens
- Complex setup flows
- Overuse of AI chatbot styling

---

## 7. Product Layers

FebGrid will be designed in four major product layers, with one hidden technical foundation layer.

---

## 8. Layer 0: Event Engine

Layer 0 is the hidden foundation of FebGrid.

Most systems store records. FebGrid stores records and events.

Every important action in the system should create an event.

### 8.1 Purpose

The Event Engine powers:

- Universal Timeline
- Activity logs
- Audit trail
- Notifications
- AI summaries
- Company Memory
- Analytics
- Risk detection
- Work history

### 8.2 Example Events

- Company created
- Employee invited
- Employee status changed
- Task created
- Task assigned
- Task completed
- Comment added
- File uploaded
- Voice note submitted
- Leave requested
- Leave approved
- Leave rejected
- AI review completed
- Project delayed
- Risk alert generated
- Notification sent

### 8.3 Event Requirements

Each event should store:

- Event ID
- Company ID
- Actor ID
- Target entity type
- Target entity ID
- Event type
- Event title
- Event description
- Metadata JSON
- Created timestamp

### 8.4 Event Design Rule

No important action should happen silently.

If the action matters to the business, it must generate an event.

---

## 9. Layer 1: Operational Foundation

Layer 1 includes the basic operational modules that every company needs.

### 9.1 People Management

#### Features

- Company employee directory
- Employee profile creation
- Employee invitation
- Role assignment
- Department assignment
- Team assignment
- Skill tagging
- Contact details
- Work status
- Availability status
- Joining date
- Employment type
- Manager mapping
- Employee activity history

#### Employee Status Values

- Working
- On Break
- Offline
- On Leave
- Done for the Day
- Busy
- Available

#### Employee Profile Fields

- Full name
- Email
- Phone number
- Role
- Department
- Team
- Skills
- Employment type
- Current status
- Manager
- Location/branch/site, optional
- Profile image, optional
- Created date
- Updated date

---

### 9.2 Teams and Departments

#### Features

- Create departments
- Create teams
- Assign employees to teams
- Assign team leads
- Team-level workload view
- Department-level activity view
- Team performance summaries

#### Example Departments

- Operations
- Sales
- Marketing
- Engineering
- HR
- Finance
- Construction Site Team
- Retail Store Team
- Logistics Team

---

### 9.3 Project Management

#### Features

- Create projects
- Assign project owner
- Add team members
- Link work objects
- Add files
- Track progress
- View timeline
- View project risks
- Project status
- Project priority

#### Project Status Values

- Not Started
- Active
- On Hold
- Completed
- Cancelled
- Delayed

---

### 9.4 Work Object Engine

The Work Object Engine is the heart of FebGrid.

Every type of work should be stored as a Work Object.

#### Work Object Examples

- Task
- Bug
- Feature
- Site Visit
- Inspection
- Delivery
- Invoice
- Receipt
- Purchase Order
- Voice Update
- Document Review
- Design Review
- Meeting
- Approval Request
- Maintenance Issue
- Customer Complaint
- Stock Check
- Safety Report

#### Core Work Object Fields

- Work object ID
- Company ID
- Project ID, optional
- Created by
- Assigned to
- Title
- Description
- Object type
- Status
- Priority
- Due date
- Tags
- Attachments
- Custom fields
- AI summary
- Created timestamp
- Updated timestamp

#### Work Object Status Values

- Draft
- Pending
- Assigned
- In Progress
- Blocked
- Under Review
- Completed
- Rejected
- Archived

#### Priority Values

- Low
- Medium
- High
- Critical

#### Work Object Requirements

- Work objects must support custom fields.
- Work objects must support file attachments.
- Work objects must support comments.
- Work objects must generate events.
- Work objects must be searchable.
- Work objects must be AI-readable.
- Work objects must support industry-specific labels.

---

### 9.5 Leave Management

#### Features

- Submit leave request
- Approve leave
- Reject leave
- Cancel leave request
- View employee leave history
- View company leave calendar
- Show leave impact on assigned work
- Generate leave-related events

#### Leave Request Fields

- Leave ID
- Employee ID
- Company ID
- Start date
- End date
- Leave type
- Reason
- Status
- Approver ID
- Created timestamp
- Updated timestamp

#### Leave Types

- Sick Leave
- Casual Leave
- Paid Leave
- Unpaid Leave
- Emergency Leave
- Half Day
- Work From Home, optional depending on company

#### Leave Status Values

- Pending
- Approved
- Rejected
- Cancelled

---

### 9.6 Communication Layer

#### Phase 1 Communication Features

- Comments on work objects
- Internal announcements
- Mentions
- In-app notifications
- Team messages, optional for later Phase 1 or Phase 2

#### Future Communication Features

- Channels
- Direct messages
- WhatsApp alerts
- SMS alerts
- Email alerts
- Voice note updates

---

### 9.7 File Pipeline

Files should not be treated as random uploads. Every file should connect to a work object, employee, project, or event.

#### Supported File Types

- Images
- PDFs
- Documents
- Audio files
- Video files
- Spreadsheets
- Receipts
- Screenshots
- UI mockups

#### File Metadata

- File ID
- Company ID
- Uploaded by
- Linked entity type
- Linked entity ID
- File name
- File type
- File size
- Storage URL
- AI processing status
- Created timestamp

#### File Requirements

- Files must be searchable by metadata.
- Files must be connected to work context.
- Files should be ready for future AI analysis.
- Files should support permissions.

---

### 9.8 Notifications

#### Notification Types

- Task assigned
- Task updated
- Comment mention
- Leave request submitted
- Leave request approved
- Leave request rejected
- File uploaded
- AI review completed
- Risk alert
- System announcement

#### Notification Fields

- Notification ID
- Company ID
- Recipient employee ID
- Title
- Message
- Type
- Is read
- Related entity type
- Related entity ID
- Created timestamp

---

## 10. Layer 2: Operational Intelligence

Layer 2 makes FebGrid unique. It turns raw operations into intelligence.

---

### 10.1 Employee Digital Twin

The Employee Digital Twin is a live operational profile of an employee.

It is not personal surveillance. It is work intelligence.

#### Purpose

To help managers understand:

- What the employee is working on
- What the employee is good at
- How much workload they have
- Whether they are available
- Which work they can handle next
- Whether they may become overloaded

#### Digital Twin Metrics

- Current workload percentage
- Assigned work count
- Completed work count
- Delayed work count
- Reliability score
- Capacity score
- Skill match score
- Recent activity
- Leave impact
- Project involvement

#### Example Employee Digital Twin Card

```text
Employee: Rahul Patil
Status: Working
Current Capacity: 68%
Active Work: 5 items
Strengths: Site Supervision, Vendor Coordination
Risk: Low
Recommended Next Assignment: Warehouse Audit
```

#### Requirements

- Should be visible to managers and admins.
- Should not expose sensitive private information unnecessarily.
- Should explain score reasons.
- Should avoid unfair automated decisions.
- Should support manual override by managers.

---

### 10.2 Company Pulse Score

Company Pulse is a live health score for the company.

#### Purpose

To help leadership understand the company in one glance.

#### Suggested Score Components

- Operations Health
- Project Health
- People Availability
- Work Completion Rate
- Risk Level
- Blocker Level
- Communication Responsiveness
- Leave Impact

#### Example

```text
Company Health: 84/100
Operations: 88
Projects: 81
People: 79
Risk Level: Medium
Recommended Action: Review 3 blocked tasks today.
```

#### Requirements

- Should be simple enough for owners to understand.
- Should show reasons behind the score.
- Should not be a black-box number.
- Should update based on events and work state.

---

### 10.3 Universal Timeline

The Universal Timeline shows everything important happening in the company.

#### Timeline Inputs

- Task events
- Project events
- Employee status updates
- Leave events
- File uploads
- Comments
- AI reviews
- Risk alerts
- Announcements

#### Timeline Filters

- Company-wide
- Employee-specific
- Project-specific
- Team-specific
- Work-object-specific
- Date range
- Event type

#### Example Timeline

```text
09:00 — Rahul checked in
09:15 — Site photo uploaded for Mall Project
09:30 — Inventory update added
10:00 — Leave request submitted by Neha
10:05 — Task assigned to Aman
10:20 — AI risk alert generated for Site B
```

---

### 10.4 Operational Search

Operational Search is one search box for the entire company.

#### Searchable Items

- Employees
- Projects
- Work objects
- Comments
- Events
- Files
- Voice transcripts
- AI summaries
- Leave requests
- Notifications
- Company memory records

#### Example Searches

- `cement`
- `Rahul site update`
- `leave requests last month`
- `blocked tasks`
- `invoice vendor A`
- `project delay reason`
- `photos from Site 12`

#### Requirements

- Search should work across structured and unstructured data.
- Search results should show context.
- Search should respect user permissions.
- Future AI search should allow natural language questions.

---

### 10.5 Work DNA Engine

Work DNA helps the company learn from repeated work patterns.

#### Purpose

To understand how work usually happens and where delays commonly occur.

#### Example Insights

```text
Work Type: Site Inspection
Average Completion Time: 2.3 days
Common Delay Reason: Missing site photos
Best Performing Team: Team B
Risk Pattern: Delays increase when more than 2 employees are on leave
```

#### Work DNA Inputs

- Historical work objects
- Events
- Completion times
- Comments
- Delay reasons
- Assigned employees
- Project outcomes
- AI summaries

---

### 10.6 Company Memory

Company Memory stores long-term business knowledge.

#### Purpose

To prevent important company knowledge from disappearing in chats, emails, files, and employee memory.

#### Memory Items

- Decisions
- Discussions
- Project learnings
- Vendor choices
- Meeting outcomes
- Important documents
- Repeated issues
- Policy notes
- Historical reasons

#### Example Questions

- Why did we choose Vendor A?
- What caused the last project delay?
- Who handled the previous warehouse audit?
- What was decided in the last client meeting?
- Which supplier gave the best rate last year?

#### Requirements

- Memory should be generated from important events and documents.
- Users should be able to manually save memory items.
- AI should summarize and retrieve memory later.
- Memory must respect company permissions.

---

## 11. Layer 3: Industry Adaptation Engine

FebGrid must not be hard-coded for one type of company.

The Industry Adaptation Engine allows companies to configure work object types and workflows based on their industry.

---

### 11.1 Configurable Work Object Types

Admins should be able to create custom work types.

#### Examples

##### Software Company

- Bug
- Feature
- Pull Request Review
- Sprint Task
- Deployment Checklist

##### Construction Company

- Site Visit
- Material Request
- Inspection
- Safety Report
- Contractor Update

##### Retail Business

- Stock Check
- Supplier Order
- Customer Complaint
- Store Opening Checklist
- Cash Reconciliation

##### Logistics Company

- Delivery
- Vehicle Issue
- Route Report
- Proof of Delivery
- Fuel Receipt

##### Agency

- Design Review
- Copy Review
- Client Approval
- Campaign Task
- Social Media Asset

---

### 11.2 Custom Fields

Each work object type should support custom fields.

#### Example: Construction Site Visit

- Site name
- Location
- Materials used
- Photos required
- Contractor name
- Safety issue present

#### Example: Bug Report

- Severity
- Environment
- Steps to reproduce
- Affected module
- Screenshot

#### Example: Delivery

- Pickup location
- Drop location
- Driver
- Vehicle number
- Delivery proof

---

### 11.3 Workflow Templates

Companies should be able to select templates during onboarding.

#### Template Examples

- Startup Team Template
- Construction Site Template
- Retail Store Template
- Software Development Template
- Agency Operations Template
- Logistics Operations Template
- Office Admin Template

---

## 12. Layer 4: FebGuyAI Intelligence Layer

FebGuyAI is the AI layer behind FebGrid.

The AI should not be only a chatbot. It should be an operational intelligence engine.

---

### 12.1 AI Service Architecture

FebGrid should use a decoupled AI abstraction layer.

#### File

```text
ai_service.py
```

#### Purpose

The AI provider should be replaceable without changing the entire application.

#### Development Mode

Use free or low-cost AI providers and open-source models where possible.

Examples:

- Gemini free tiers
- Groq small models
- Hugging Face models
- Local/open-source models where practical

#### Production Mode

Use enterprise-grade AI providers when paying customers justify the cost.

#### Requirement

Changing AI provider should mainly require environment variable changes and service-level updates, not frontend/backend rewrites.

---

### 12.2 AI Job Queue

AI tasks should not block normal app usage.

All AI work should go through an AI job queue.

#### AI Job Types

- Voice transcription
- Voice-to-work parsing
- Image analysis
- Document analysis
- Work review
- Task summarization
- Risk analysis
- Executive brief generation
- Company memory extraction

#### AI Job Status Values

- Queued
- Processing
- Completed
- Failed
- Cancelled

---

### 12.3 Voice-to-Work

Employees can submit voice updates.

Example voice note:

> “Pillar work completed. Used 4 cement bags. Need more steel rods tomorrow.”

FebGuyAI should convert this into:

- Task update
- Inventory note
- Material usage record
- Possible follow-up task
- Timeline event
- Manager summary

#### Requirements

- Accept audio upload
- Transcribe audio
- Extract useful work details
- Link update to work object or project
- Ask for manager confirmation where needed
- Store transcript
- Store structured output

---

### 12.4 Photo-to-Work

Employees can upload photos as evidence.

FebGuyAI can analyze photos for:

- Progress evidence
- Safety issues
- Visual defects
- Missing proof
- UI layout issues for design teams
- Receipt/invoice extraction

#### Requirements

- Image upload support
- AI analysis job creation
- Result displayed in work object
- Human confirmation before critical decisions

---

### 12.5 Document Intelligence

FebGuyAI can analyze:

- Invoices
- Receipts
- Contracts
- Reports
- Spreadsheets
- Business emails
- Policy documents

#### Possible Outputs

- Summary
- Extracted fields
- Risk flags
- Amounts
- Dates
- Vendor names
- Action items
- Tone review
- Compliance notes

---

### 12.6 Omni-Work Pre-Review

FebGuyAI should review different work types before manager intervention.

#### Examples

- Code flaws
- UI accessibility or spacing issues
- Legal tone in business emails
- Logic errors in financial spreadsheets
- Missing photos in field reports
- Incomplete task evidence
- Delay risks

---

### 12.7 Executive Translation Layer

This converts company activity into simple executive summaries.

#### Example Daily Brief

```text
47 employees are active today.
Project Alpha is behind schedule because 3 key tasks are blocked.
Recommended action: assign Rohit to Site B and review pending material approval.
```

#### Requirements

- Summarize by company
- Summarize by project
- Summarize by department
- Summarize by risk
- Show important recommendations
- Avoid unnecessary details

---

### 12.8 AI Risk Radar

AI Risk Radar predicts operational problems.

#### Risk Types

- Project delay risk
- Employee overload risk
- Leave impact risk
- Material shortage risk
- Work dependency risk
- Low activity risk
- Blocked task risk
- Cost leakage risk, future

#### Example Alert

```text
Risk: Site B may be delayed by 2 days.
Reason: 3 workers are absent and material delivery is pending.
Suggested action: move Aman from Team C to Site B for one day.
```

---

## 13. Core User Roles and Permissions

### 13.1 Roles

#### Super Admin

Platform-level owner, internal FebGrid role.

Can:

- Manage all platform data
- View system health
- Manage plans
- Handle support

#### Company Owner

Main company account owner.

Can:

- Manage company
- Manage billing
- Manage all employees
- View all dashboards
- Access executive briefs
- Configure company settings

#### Admin

Company admin.

Can:

- Add employees
- Manage teams
- Approve leaves
- Manage work objects
- View reports

#### Manager

Team or project manager.

Can:

- Assign work
- Review work
- View team members
- Approve team-specific items, if permitted
- View team analytics

#### Employee

Regular user.

Can:

- View assigned work
- Update status
- Submit leave request
- Upload files
- Comment
- View relevant notifications

#### Guest / Client, Future

Limited access user.

Can:

- View shared project/work items
- Comment or approve specific items
- Upload files if allowed

---

## 14. Main User Journeys

### 14.1 Company Onboarding

1. User creates company account.
2. User enters company name, industry, size, and plan.
3. User selects industry template.
4. User creates departments and teams.
5. User invites employees.
6. User creates first project.
7. User creates first work object.
8. FebGrid shows the first operational dashboard.

### 14.2 Manager Assigns Work

1. Manager opens dashboard.
2. Manager creates work object.
3. Manager selects type, priority, due date, and assignee.
4. System creates work object.
5. Event is generated.
6. Notification is sent to employee.
7. Work appears on employee dashboard.

### 14.3 Employee Updates Work

1. Employee opens assigned work.
2. Employee changes status or adds update.
3. Employee may upload photo, file, or voice memo.
4. Event is generated.
5. Manager receives notification.
6. Timeline updates.
7. AI job may be created if file/voice analysis is enabled.

### 14.4 Leave Request Flow

1. Employee submits leave request.
2. System checks assigned work and availability impact.
3. Manager receives notification.
4. Manager approves or rejects.
5. Employee status updates if approved.
6. Leave event is generated.
7. Backup recommendation is generated in AI-enabled plans.

### 14.5 Executive Daily Brief Flow

1. System reads recent events, work state, leaves, and risks.
2. FebGuyAI generates brief.
3. Owner sees 3-line summary.
4. Owner can expand details.
5. Owner can take action from recommendations.

---

## 15. MVP Scope

The MVP must prove that FebGrid can operate as a unified company workspace.

### 15.1 MVP Must-Have Features

#### Authentication

- Sign up
- Login
- Logout
- Password reset, optional for early MVP
- Company account creation

#### Company Management

- Create company
- Update company details
- View company dashboard

#### Employee Management

- Add employee
- Edit employee
- Delete/deactivate employee
- Assign role
- Assign team/department
- View employee profile
- Update employee status

#### Team and Department Management

- Create department
- Create team
- Assign employees
- View team list

#### Project Management

- Create project
- Edit project
- Assign project owner
- Add members
- View project work objects

#### Work Object Engine

- Create work object
- Assign work object
- Update status
- Add due date
- Add priority
- Add comments
- View work object list
- Filter work objects

#### Leave Management

- Submit leave request
- Approve leave
- Reject leave
- View leave list
- View employee leave history

#### File Uploads

- Upload file to work object
- View attachments
- Store file metadata

#### Event Engine

- Generate events for major actions
- View universal timeline
- Filter timeline by project/employee/work object

#### Notifications

- In-app notifications
- Mark as read
- Notification list

#### Basic Dashboard

- Total employees
- Active employees
- Pending tasks
- Completed tasks
- Leave requests
- Recent events

---

### 15.2 MVP Exclusions

These should not be built in the first MVP unless extra time is available:

- Full AI reviews
- Advanced voice memo parsing
- WhatsApp integration
- SMS integration
- Billing automation
- Advanced analytics
- Enterprise compliance dashboard
- Complex custom workflow builder
- Mobile native apps
- Payroll
- Biometric attendance
- Video meetings

---

## 16. Phase Roadmap

### Phase 1: Base Level Core Matrix

Goal: Build the operational foundation.

Includes:

- React frontend setup
- FastAPI backend setup
- PostgreSQL/Supabase setup
- Authentication
- Company module
- Employee module
- Team/department module
- Project module
- Work Object Engine v1
- Leave module
- File upload v1
- Notification v1
- Event Engine v1
- Basic dashboard

Success criteria:

- A company can onboard and manage employees.
- Managers can create and assign work.
- Employees can update work and submit leave.
- Files can be uploaded to work objects.
- Important actions create events.
- Dashboard shows live operational overview.

---

### Phase 2: Decoupled Data and Notification Stream

Goal: Improve operational flow and prepare for scale.

Includes:

- Advanced notifications
- Mentions
- Email alerts
- Search v1
- Better filters
- File pipeline improvements
- Activity feed improvements
- Company settings
- Industry templates v1
- Billing preparation
- Audit logs

Success criteria:

- Company data is easier to search and filter.
- Notifications are reliable.
- Industry-specific work objects can be configured.
- System is ready for AI job integration.

---

### Phase 3: FebGuyAI Brain Activation

Goal: Add AI intelligence behind the grid.

Includes:

- ai_service.py abstraction
- AI job queue
- Voice transcription
- Voice-to-work parsing
- File summarization
- Document analysis
- Image analysis v1
- Work summary
- Executive brief v1
- Company Memory v1

Success criteria:

- AI can analyze uploaded content.
- AI can summarize work updates.
- AI can generate owner/manager briefs.
- AI results are stored and searchable.

---

### Phase 4: Operational Intelligence Expansion

Goal: Make FebGrid feel one-of-a-kind.

Includes:

- Employee Digital Twin v1
- Company Pulse Score v1
- Work DNA Engine v1
- AI Risk Radar v1
- Leave impact engine
- Smart backup recommendation
- Advanced operational search

Success criteria:

- Managers get intelligent recommendations.
- Owners get live company health.
- FebGrid becomes more than a management tool.

---

### Phase 5: Enterprise and Global Scale

Goal: Prepare for larger companies and global market.

Includes:

- Advanced permissions
- Custom compliance policies
- Enterprise dashboards
- API integrations
- WhatsApp/SMS wallet
- Custom AI model routing
- Advanced reports
- Data export
- SSO, future
- Multi-branch/company hierarchy

Success criteria:

- FebGrid can support larger companies.
- Enterprise buyers can trust data control and reporting.
- Communication costs are passed through wallet system.

---

## 17. Pricing and Monetization

### 17.1 Pricing Philosophy

FebGrid should use per-company pricing instead of per-user pricing for price-sensitive markets.

This reduces adoption friction and makes the product attractive for Indian businesses and small companies.

---

### 17.2 Tier 1: Base Level

**Price:** ₹999/month  
**Target:** Startups and small businesses up to 15-20 employees  

Includes:

- Employee management
- Task/work object management
- Projects
- Leaves
- Basic files
- Notifications
- Basic dashboard
- Manual operations

AI strategy:

- Minimal or free-tier AI only
- No costly automation by default

Goal:

- High-margin entry product
- Strong user experience
- Create FOMO and habit formation

---

### 17.3 Tier 2: Growth Level

**Price:** ₹2,999/month  
**Target:** Mid-sized businesses up to 50 employees  

Includes:

- Everything in Base Level
- FebGuyAI Pre-Review
- Voice memo processing
- Smart task updates
- Leave impact engine
- Backup suggestions
- Company Pulse
- Basic executive briefs
- Advanced search

Goal:

- Sell autonomous value, not just more features

---

### 17.4 Tier 3: Enterprise Level

**Price:** ₹9,999+/month  
**Target:** Large companies, infrastructure firms, tech export firms, multi-branch companies  

Includes:

- Everything in Growth Level
- Custom data policies
- Advanced permissions
- Custom AI workflows
- Executive monitoring dashboards
- Audit logs
- API access
- Dedicated support
- Custom onboarding

---

### 17.5 Utility Add-Ons

#### Communication Wallet

For WhatsApp/SMS alerts:

- Admin adds prepaid balance.
- Each alert deducts small amount.
- FebGrid never pays communication cost out-of-pocket.

#### Micro-Upsell Triggers

Examples:

- Locked AI voice summary button
- Locked risk radar card
- Locked executive brief
- Locked smart backup suggestion

Example UI text:

```text
Auto-Summarize Voice Update with FebGuyAI — Upgrade to Unlock
```

---

## 18. Functional Requirements

### 18.1 Authentication

- Users must be able to sign up.
- Users must be able to log in.
- Users must be connected to a company.
- Users must have role-based access.
- Sessions must be secure.

### 18.2 Multi-Tenancy

- Every major record must belong to a company.
- Users should only access data from their company unless they are platform admins.
- Company ID must be included in core tables.

### 18.3 Employee Management

- Admins can create employees.
- Admins can edit employees.
- Admins can deactivate employees.
- Managers can view team employees.
- Employees can view their own profile.

### 18.4 Work Object Management

- Users with permission can create work objects.
- Work objects can be assigned.
- Work objects can have due dates.
- Work objects can have priorities.
- Work objects can have statuses.
- Work objects can have comments and files.
- Updating work objects generates events.

### 18.5 Leave Management

- Employees can submit leave requests.
- Managers/admins can approve or reject.
- Leave approvals update availability.
- Leave actions generate events and notifications.

### 18.6 File Upload

- Users can upload supported files.
- Files are linked to an entity.
- File metadata is stored.
- Upload actions generate events.

### 18.7 Timeline

- System displays company activity timeline.
- Timeline can be filtered.
- Timeline must be permission-aware.

### 18.8 Notifications

- System creates notifications for important events.
- Users can mark notifications as read.
- Users can open related entity from notification.

### 18.9 AI Jobs

- AI jobs must be stored separately.
- AI processing should be asynchronous.
- AI results should be linked to source work/file/event.
- Failed AI jobs should be visible for debugging.

---

## 19. Non-Functional Requirements

### 19.1 Performance

- Dashboard should load quickly.
- Core pages should not depend on AI completion.
- File uploads should not block the interface.
- Timeline should support pagination.
- Search should support indexing in later phases.

### 19.2 Reliability

- Critical actions should generate events reliably.
- Failed AI jobs should not break work management.
- Notifications should be retryable.
- File metadata should not be lost even if AI analysis fails.

### 19.3 Security

- Role-based access control is required.
- Company data isolation is required.
- File access must be permission-controlled.
- Sensitive actions should be logged.
- API endpoints must validate company ownership.

### 19.4 Scalability

- Database design must support many companies.
- Work object types must be extensible.
- AI provider must be replaceable.
- Event table may grow large, so pagination and indexing are required.

### 19.5 Usability

- Employees should be able to update work with minimum clicks.
- Managers should see important information quickly.
- Owners should not need to understand technical dashboards.
- Non-tech users should understand the product without training-heavy onboarding.

### 19.6 Low Network Support

- Avoid heavy animations.
- Optimize dashboard data loading.
- Use lazy loading for files and timelines.
- Allow basic actions to complete with minimal bandwidth.

---

## 20. Data Model Overview

### 20.1 Core Entities

- Company
- User
- Employee
- Department
- Team
- Project
- WorkObject
- WorkObjectType
- WorkUpdate
- FileAttachment
- LeaveRequest
- Event
- Notification
- AIJob
- CompanyMemory
- Skill
- EmployeeSkill

---

## 21. Initial Database Schema Draft

The following schema is a starting point. It should be refined during engineering.

```sql
-- Companies
CREATE TABLE companies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    industry TEXT,
    plan_type TEXT DEFAULT 'base',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Users
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID REFERENCES companies(id),
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Employees
CREATE TABLE employees (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID REFERENCES companies(id) NOT NULL,
    user_id UUID REFERENCES users(id),
    full_name TEXT NOT NULL,
    phone TEXT,
    role_title TEXT,
    department_id UUID,
    team_id UUID,
    manager_id UUID,
    employment_type TEXT,
    current_status TEXT DEFAULT 'offline',
    joined_at DATE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Departments
CREATE TABLE departments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID REFERENCES companies(id) NOT NULL,
    name TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Teams
CREATE TABLE teams (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID REFERENCES companies(id) NOT NULL,
    department_id UUID REFERENCES departments(id),
    name TEXT NOT NULL,
    lead_employee_id UUID REFERENCES employees(id),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Skills
CREATE TABLE skills (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID REFERENCES companies(id),
    name TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Employee Skills
CREATE TABLE employee_skills (
    employee_id UUID REFERENCES employees(id) ON DELETE CASCADE,
    skill_id UUID REFERENCES skills(id) ON DELETE CASCADE,
    PRIMARY KEY (employee_id, skill_id)
);

-- Projects
CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID REFERENCES companies(id) NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    owner_employee_id UUID REFERENCES employees(id),
    status TEXT DEFAULT 'active',
    priority TEXT DEFAULT 'medium',
    start_date DATE,
    due_date DATE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Work Object Types
CREATE TABLE work_object_types (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID REFERENCES companies(id),
    name TEXT NOT NULL,
    description TEXT,
    custom_schema JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Work Objects
CREATE TABLE work_objects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID REFERENCES companies(id) NOT NULL,
    project_id UUID REFERENCES projects(id),
    work_object_type_id UUID REFERENCES work_object_types(id),
    created_by UUID REFERENCES employees(id),
    assigned_to UUID REFERENCES employees(id),
    title TEXT NOT NULL,
    description TEXT,
    status TEXT DEFAULT 'pending',
    priority TEXT DEFAULT 'medium',
    due_date TIMESTAMP,
    tags TEXT[],
    custom_fields JSONB DEFAULT '{}',
    ai_summary TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Work Updates / Comments
CREATE TABLE work_updates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID REFERENCES companies(id) NOT NULL,
    work_object_id UUID REFERENCES work_objects(id) ON DELETE CASCADE,
    employee_id UUID REFERENCES employees(id),
    message TEXT,
    update_type TEXT DEFAULT 'comment',
    created_at TIMESTAMP DEFAULT NOW()
);

-- File Attachments
CREATE TABLE file_attachments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID REFERENCES companies(id) NOT NULL,
    uploaded_by UUID REFERENCES employees(id),
    linked_entity_type TEXT NOT NULL,
    linked_entity_id UUID NOT NULL,
    file_name TEXT NOT NULL,
    file_type TEXT,
    mime_type TEXT,
    file_size BIGINT,
    storage_url TEXT NOT NULL,
    ai_processing_status TEXT DEFAULT 'not_started',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Leave Requests
CREATE TABLE leave_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID REFERENCES companies(id) NOT NULL,
    employee_id UUID REFERENCES employees(id) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    leave_type TEXT,
    reason TEXT,
    status TEXT DEFAULT 'pending',
    approver_employee_id UUID REFERENCES employees(id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Events
CREATE TABLE events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID REFERENCES companies(id) NOT NULL,
    actor_employee_id UUID REFERENCES employees(id),
    event_type TEXT NOT NULL,
    target_entity_type TEXT,
    target_entity_id UUID,
    title TEXT NOT NULL,
    description TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Notifications
CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID REFERENCES companies(id) NOT NULL,
    recipient_employee_id UUID REFERENCES employees(id) NOT NULL,
    title TEXT NOT NULL,
    message TEXT,
    notification_type TEXT,
    related_entity_type TEXT,
    related_entity_id UUID,
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- AI Jobs
CREATE TABLE ai_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID REFERENCES companies(id) NOT NULL,
    source_entity_type TEXT NOT NULL,
    source_entity_id UUID NOT NULL,
    job_type TEXT NOT NULL,
    status TEXT DEFAULT 'queued',
    input_json JSONB DEFAULT '{}',
    result_json JSONB DEFAULT '{}',
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);

-- Company Memory
CREATE TABLE company_memory (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID REFERENCES companies(id) NOT NULL,
    source_entity_type TEXT,
    source_entity_id UUID,
    memory_type TEXT,
    title TEXT NOT NULL,
    summary TEXT,
    content TEXT,
    tags TEXT[],
    importance_score INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

---

## 22. Backend Architecture

### 22.1 Technology Stack

- Language: Python
- Framework: FastAPI
- Database: PostgreSQL / Supabase
- ORM: SQLAlchemy
- Authentication: Supabase Auth
- File Storage: Supabase Storage
- Background Jobs: Celery, RQ, FastAPI BackgroundTasks, or a simple queue for early MVP
- AI Layer: `ai_service.py`

---

### 22.2 Backend Folder Structure

```text
backend/
│
├── app/
│   ├── main.py
│   │
│   ├── api/
│   │   ├── auth.py
│   │   ├── companies.py
│   │   ├── employees.py
│   │   ├── departments.py
│   │   ├── teams.py
│   │   ├── projects.py
│   │   ├── work_objects.py
│   │   ├── leaves.py
│   │   ├── uploads.py
│   │   ├── events.py
│   │   ├── notifications.py
│   │   └── ai_jobs.py
│   │
│   ├── models/
│   │   ├── company.py
│   │   ├── user.py
│   │   ├── employee.py
│   │   ├── project.py
│   │   ├── work_object.py
│   │   ├── leave.py
│   │   ├── event.py
│   │   ├── notification.py
│   │   └── ai_job.py
│   │
│   ├── schemas/
│   │   ├── company.py
│   │   ├── employee.py
│   │   ├── project.py
│   │   ├── work_object.py
│   │   ├── leave.py
│   │   ├── event.py
│   │   └── notification.py
│   │
│   ├── services/
│   │   ├── event_service.py
│   │   ├── notification_service.py
│   │   ├── file_service.py
│   │   ├── ai_service.py
│   │   ├── search_service.py
│   │   └── pulse_service.py
│   │
│   ├── core/
│   │   ├── config.py
│   │   ├── security.py
│   │   └── permissions.py
│   │
│   └── db/
│       ├── database.py
│       └── migrations/
│
└── requirements.txt
```

---

## 23. API Requirements

### 23.1 Auth APIs

```http
POST /auth/register
POST /auth/login
POST /auth/logout
GET  /auth/me
```

### 23.2 Company APIs

```http
POST /companies
GET  /companies/me
PUT  /companies/me
GET  /companies/me/dashboard
```

### 23.3 Employee APIs

```http
POST   /employees
GET    /employees
GET    /employees/{employee_id}
PUT    /employees/{employee_id}
DELETE /employees/{employee_id}
PATCH  /employees/{employee_id}/status
GET    /employees/{employee_id}/activity
GET    /employees/{employee_id}/digital-twin
```

### 23.4 Department APIs

```http
POST   /departments
GET    /departments
PUT    /departments/{department_id}
DELETE /departments/{department_id}
```

### 23.5 Team APIs

```http
POST   /teams
GET    /teams
GET    /teams/{team_id}
PUT    /teams/{team_id}
DELETE /teams/{team_id}
POST   /teams/{team_id}/members
DELETE /teams/{team_id}/members/{employee_id}
```

### 23.6 Project APIs

```http
POST   /projects
GET    /projects
GET    /projects/{project_id}
PUT    /projects/{project_id}
DELETE /projects/{project_id}
GET    /projects/{project_id}/timeline
GET    /projects/{project_id}/work-objects
```

### 23.7 Work Object APIs

```http
POST   /work-objects
GET    /work-objects
GET    /work-objects/{work_object_id}
PUT    /work-objects/{work_object_id}
DELETE /work-objects/{work_object_id}
PATCH  /work-objects/{work_object_id}/status
POST   /work-objects/{work_object_id}/comments
GET    /work-objects/{work_object_id}/comments
POST   /work-objects/{work_object_id}/attachments
GET    /work-objects/{work_object_id}/timeline
```

### 23.8 Leave APIs

```http
POST  /leaves
GET   /leaves
GET   /leaves/{leave_id}
PUT   /leaves/{leave_id}
POST  /leaves/{leave_id}/approve
POST  /leaves/{leave_id}/reject
GET   /employees/{employee_id}/leaves
```

### 23.9 File APIs

```http
POST /uploads
GET  /files/{file_id}
GET  /files
```

### 23.10 Event APIs

```http
GET /events
GET /events/{event_id}
GET /timeline
```

### 23.11 Notification APIs

```http
GET   /notifications
PATCH /notifications/{notification_id}/read
PATCH /notifications/read-all
```

### 23.12 Search APIs

```http
GET /search?q={query}
```

### 23.13 AI APIs

```http
POST /ai-jobs
GET  /ai-jobs
GET  /ai-jobs/{ai_job_id}
POST /ai/executive-brief
POST /ai/work-objects/{work_object_id}/summarize
POST /ai/files/{file_id}/analyze
```

---

## 24. Frontend Architecture

### 24.1 Technology Stack

- React
- TypeScript
- Vite or Next.js depending on routing needs
- Tailwind CSS
- API client using Axios or Fetch
- State management: Zustand, Redux Toolkit, or React Query
- Forms: React Hook Form
- Tables/grids: custom or lightweight grid library

---

### 24.2 Frontend Folder Structure

```text
frontend/
│
├── src/
│   ├── app/
│   │   ├── routes/
│   │   └── providers/
│   │
│   ├── pages/
│   │   ├── Dashboard/
│   │   ├── Employees/
│   │   ├── EmployeeProfile/
│   │   ├── Projects/
│   │   ├── WorkObjects/
│   │   ├── Leaves/
│   │   ├── Timeline/
│   │   ├── Notifications/
│   │   ├── Search/
│   │   └── Settings/
│   │
│   ├── components/
│   │   ├── Layout/
│   │   ├── Grid/
│   │   ├── Cards/
│   │   ├── EmployeeCard/
│   │   ├── WorkObjectCard/
│   │   ├── StatusBadge/
│   │   ├── PriorityBadge/
│   │   ├── FileUploader/
│   │   ├── NotificationPanel/
│   │   ├── TimelineItem/
│   │   └── AIInsightBox/
│   │
│   ├── services/
│   │   ├── api.ts
│   │   ├── authService.ts
│   │   ├── employeeService.ts
│   │   ├── workObjectService.ts
│   │   └── notificationService.ts
│   │
│   ├── hooks/
│   │   ├── useAuth.ts
│   │   ├── useEmployees.ts
│   │   ├── useWorkObjects.ts
│   │   └── useNotifications.ts
│   │
│   ├── types/
│   └── utils/
│
└── package.json
```

---

## 25. Main Screens

### 25.1 Login / Signup

Purpose:

- Allow users to enter FebGrid.
- Company owner can create company.

Required elements:

- Email
- Password
- Login button
- Signup flow
- Forgot password, optional

---

### 25.2 Main Dashboard / Mission Control

Purpose:

Give a live overview of the company.

Required cards:

- Company Pulse, future
- Active employees
- Employees on leave
- Pending work objects
- Completed work objects
- Blocked work objects
- Recent events
- Pending leave approvals
- Notifications
- AI brief, future

---

### 25.3 Employee Directory

Purpose:

Show all employees in one place.

Features:

- Employee list
- Status badges
- Role/department/team filters
- Search employee
- Add employee
- View profile

---

### 25.4 Employee Profile / Digital Twin

Phase 1 profile:

- Basic details
- Role
- Team
- Status
- Assigned work
- Leave history
- Activity timeline

Future Digital Twin:

- Capacity score
- Reliability score
- Skill summary
- Recommended assignments
- Risk indicators

---

### 25.5 Work Grid

Purpose:

Show all work objects.

Features:

- Grid/list view
- Filters by status, assignee, project, priority
- Create work object
- Update status
- Open work details
- Attach files
- Add comments

---

### 25.6 Work Object Detail Page

Required sections:

- Title
- Status
- Priority
- Assignee
- Due date
- Description
- Comments
- Attachments
- Timeline
- AI summary, future

---

### 25.7 Projects Page

Features:

- Project list
- Project status
- Project owner
- Progress
- Linked work objects
- Timeline

---

### 25.8 Leave Management Page

Features:

- Submit leave
- Leave list
- Pending approvals
- Approved leaves
- Rejected leaves
- Leave calendar, future
- Leave impact, future

---

### 25.9 Universal Timeline Page

Features:

- Company-wide event feed
- Filter by employee
- Filter by project
- Filter by event type
- Filter by date

---

### 25.10 Operational Search Page

Features:

- Search input
- Results grouped by type
- Permission-aware results
- Search history, future
- AI answer mode, future

---

### 25.11 Settings Page

Features:

- Company settings
- Roles and permissions
- Work object types
- Industry template
- Billing, future
- AI settings, future

---

## 26. UX Requirements

### 26.1 Dashboard UX

- Should show important data without overwhelming the user.
- Should prioritize action items.
- Should allow manager to move from alert to action quickly.
- Should avoid too many charts in early MVP.

### 26.2 Employee UX

- Employee should see only what matters.
- Main employee screen should show:
  - My work
  - My status
  - My leaves
  - Notifications
- Updating work should be fast.

### 26.3 Manager UX

- Manager should see team capacity and blockers.
- Manager should assign work quickly.
- Manager should approve leave quickly.
- Manager should get recommendations without losing control.

### 26.4 Owner UX

- Owner should see the company health quickly.
- Owner should not need to read every task.
- Executive brief should be simple, direct, and action-oriented.

---

## 27. AI Safety and Human Control

FebGuyAI should assist, not blindly control operations.

### 27.1 Rules

- AI recommendations should be explainable.
- AI should not approve leave automatically in early versions.
- AI should not make irreversible decisions without human confirmation.
- AI should show confidence where relevant.
- AI outputs should be editable.
- Managers should be able to override AI suggestions.

### 27.2 Sensitive Areas

Be careful with:

- Employee scoring
- Performance ratings
- Attrition predictions
- Automated disciplinary recommendations
- Personal data
- Location data

### 27.3 Recommended Approach

Use AI as:

- Assistant
- Reviewer
- Summarizer
- Risk detector
- Recommendation engine

Do not position AI as:

- Judge
- Surveillance tool
- Fully autonomous manager

---

## 28. Analytics and Metrics

### 28.1 Product Usage Metrics

- Daily active companies
- Daily active users
- Work objects created per company
- Work objects completed per company
- Files uploaded
- Leave requests submitted
- Events generated
- Notifications opened
- Search usage
- AI jobs completed

### 28.2 Business Metrics

- Monthly recurring revenue
- Free-to-paid conversion
- Base-to-Growth upgrade rate
- Churn rate
- Average revenue per company
- Activation rate
- Retention rate

### 28.3 Operational Metrics for Customers

- Work completion rate
- Average completion time
- Blocked work count
- Employee availability
- Leave impact
- Project delay risk
- Team workload balance

---

## 29. Success Criteria

### 29.1 MVP Success

MVP is successful if:

- A company can manage employees, work, files, leaves, notifications, and events in one place.
- Managers use FebGrid daily to track work.
- Employees can update work without training-heavy onboarding.
- Owners can understand company activity faster than before.

### 29.2 Product Differentiation Success

FebGrid becomes differentiated when:

- Company Pulse gives useful live health visibility.
- Employee Digital Twin helps assign work better.
- Universal Timeline becomes the company activity source of truth.
- Company Memory answers historical business questions.
- FebGuyAI reduces manual review and reporting.

---

## 30. Risks and Mitigation

### 30.1 Risk: Too Many Features Too Early

Mitigation:

- Build engines first.
- Keep MVP focused.
- Delay advanced AI until foundation is stable.

### 30.2 Risk: Product Feels Complex

Mitigation:

- Simple dashboard.
- Role-based UI.
- Progressive feature reveal.
- Clean navigation.

### 30.3 Risk: AI Costs Become High

Mitigation:

- Use AI abstraction layer.
- Use free/low-cost models in dev.
- Use paid models only for paid plans.
- Queue AI jobs.
- Limit AI usage by plan.

### 30.4 Risk: Employee Scoring Feels Like Surveillance

Mitigation:

- Explain scores.
- Focus on workload and support, not punishment.
- Allow company settings.
- Avoid sensitive personal inferences.

### 30.5 Risk: Database Becomes Rigid

Mitigation:

- Use work object types.
- Use custom fields JSONB.
- Use event-driven design.
- Keep AI results decoupled.

---

## 31. Initial Engineering Sprint Plan

### Sprint 1: Project Setup

- Create FastAPI backend
- Create React frontend
- Setup PostgreSQL/Supabase
- Setup environment variables
- Setup basic auth
- Setup project structure

### Sprint 2: Company and User Foundation

- Company model
- User model
- Auth APIs
- Company dashboard base
- Role-based access base

### Sprint 3: Employee Management

- Employee model
- Departments
- Teams
- Employee CRUD APIs
- Employee directory UI
- Employee profile UI

### Sprint 4: Work Object Engine

- Work object types
- Work object CRUD
- Assignment
- Status updates
- Work grid UI
- Work detail page

### Sprint 5: Event Engine

- Event model
- Event service
- Generate events for employee/work/leave actions
- Timeline API
- Timeline UI

### Sprint 6: Leave Management

- Leave request model
- Leave APIs
- Leave approval flow
- Leave UI
- Leave notifications

### Sprint 7: File Pipeline

- File upload API
- Storage integration
- File attachment model
- Attach files to work objects
- File UI

### Sprint 8: Notifications

- Notification model
- Notification service
- Notification UI
- Mark as read

### Sprint 9: Dashboard Polish

- Dashboard cards
- Recent events
- Work summary
- Employee summary
- Leave summary
- UI polish

### Sprint 10: AI Foundation Preparation

- AI job table
- ai_service.py
- AI job APIs
- Mock AI provider
- Prepare for Phase 3

---

## 32. Development Rules

### 32.1 Backend Rules

- Every major endpoint must validate company access.
- Every important action must call EventService.
- Notifications should be created through NotificationService.
- AI should be called only through AIService.
- File uploads should be handled through FileService.
- Avoid mixing business logic directly inside route files.

### 32.2 Frontend Rules

- Keep components reusable.
- Use consistent status badges.
- Use consistent empty states.
- Use loading states.
- Avoid heavy animations.
- Make employee actions simple.
- Keep manager dashboards action-oriented.

### 32.3 Database Rules

- Every company-owned table must include company_id.
- Use UUIDs for primary keys.
- Use timestamps consistently.
- Add indexes for company_id, status, created_at, assigned_to, and project_id.
- Use JSONB only where flexibility is required, not for everything.

---

## 33. Suggested Indexes

```sql
CREATE INDEX idx_employees_company_id ON employees(company_id);
CREATE INDEX idx_work_objects_company_id ON work_objects(company_id);
CREATE INDEX idx_work_objects_assigned_to ON work_objects(assigned_to);
CREATE INDEX idx_work_objects_project_id ON work_objects(project_id);
CREATE INDEX idx_work_objects_status ON work_objects(status);
CREATE INDEX idx_events_company_id_created_at ON events(company_id, created_at DESC);
CREATE INDEX idx_notifications_recipient ON notifications(recipient_employee_id, is_read);
CREATE INDEX idx_leave_requests_company_status ON leave_requests(company_id, status);
CREATE INDEX idx_ai_jobs_company_status ON ai_jobs(company_id, status);
```

---

## 34. Acceptance Criteria for Phase 1

Phase 1 is complete when:

1. A user can create a company account.
2. A company can add employees.
3. Employees can be assigned to teams/departments.
4. Managers can create projects.
5. Managers can create and assign work objects.
6. Employees can update work status.
7. Employees can submit leave requests.
8. Managers can approve or reject leaves.
9. Files can be uploaded to work objects.
10. Events are generated for major actions.
11. Universal Timeline displays events.
12. Notifications are generated and visible.
13. Dashboard shows company activity summary.
14. Permissions prevent users from seeing another company's data.

---

## 35. Future Expansion Ideas

### 35.1 Mobile App

- Employee mobile app
- Voice update capture
- Photo upload
- Push notifications
- Offline mode

### 35.2 WhatsApp/SMS Integration

- Task alerts
- Leave approval alerts
- Daily summaries
- Field worker updates
- Wallet-based charging

### 35.3 Advanced Company Memory

- Ask questions from historical data
- Decision tracing
- Vendor history
- Project lessons
- Policy memory

### 35.4 AI Operations Consultant

- Suggest cost savings
- Predict workforce needs
- Recommend resource allocation
- Detect process inefficiencies

### 35.5 Marketplace / Templates

- Industry templates
- Workflow templates
- Report templates
- Automation templates

---

## 36. Final Product Direction

FebGrid should not be built as a random collection of features.

It should be built as a system of connected engines:

```text
Company
  -> Employees
  -> Teams
  -> Projects
  -> Work Objects
  -> Events
  -> Files
  -> Notifications
  -> Search
  -> AI Jobs
  -> Company Memory
  -> Executive Intelligence
```

The long-term power of FebGrid will come from the fact that every business action becomes structured, searchable, reviewable, and understandable.

The final goal is:

> To give every company, from a 10-person local business to a global enterprise, one intelligent operating layer where people, work, files, communication, AI review, and leadership clarity exist together.

---

## 37. Final Locked Philosophy

FebGrid must always follow this product philosophy:

```text
Everything is a Work Object.
Everything generates an Event.
Everything is searchable.
Everything is AI-readable.
Everything contributes to Company Memory.
Better System = Better Product.
```

This philosophy should guide every future product, design, database, backend, AI, and business decision.
