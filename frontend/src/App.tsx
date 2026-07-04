import { useEffect, useState } from "react";

import { AppLayout } from "./components/layout/AppLayout";
import { ErrorState, LoadingState } from "./components/ui/States";
import { allNavigationItems, getDefaultPageForRole, getNavigationItemsForRole, isPageAllowedForRole } from "./data/navigation";
import { useAuth } from "./hooks/useAuth";
import { useFebGridData } from "./hooks/useFebGridData";
import { useTheme } from "./hooks/useTheme";
import { AnnouncementsPage } from "./pages/AnnouncementsPage";
import { AuthPage } from "./pages/AuthPage";
import { CompaniesPage } from "./pages/CompaniesPage";
import { CompanyMemoryPage } from "./pages/CompanyMemoryPage";
import { DashboardPage } from "./pages/DashboardPage";
import { EmployeesPage } from "./pages/EmployeesPage";
import { EmployeeDashboardPage } from "./pages/EmployeeDashboardPage";
import { EventsPage } from "./pages/EventsPage";
import { InviteAcceptPage } from "./pages/InviteAcceptPage";
import { LeavesPage } from "./pages/LeavesPage";
import { MyLeavePage } from "./pages/MyLeavePage";
import { MyProfilePage } from "./pages/MyProfilePage";
import { MyProjectsPage } from "./pages/MyProjectsPage";
import { MyWorkPage } from "./pages/MyWorkPage";
import { NotificationsPage } from "./pages/NotificationsPage";
import { ProjectsPage } from "./pages/ProjectsPage";
import { SettingsPage } from "./pages/SettingsPage";
import { TeamsPage } from "./pages/TeamsPage";
import { WorkObjectsPage } from "./pages/WorkObjectsPage";
import type { PageKey } from "./types/domain";

function getPageFromHash(): PageKey {
  const hash = window.location.hash.replace("#/", "");
  const match = allNavigationItems.find((item) => item.key === hash);
  return match?.key ?? "dashboard";
}

function getInviteTokenFromLocation(): string | null {
  const pathMatch = window.location.pathname.match(/^\/(?:accept-invite|join)\/([^/?#]+)/);
  if (pathMatch?.[1]) return decodeURIComponent(pathMatch[1]);

  const hash = window.location.hash.replace(/^#\/?/, "");
  const hashMatch = hash.match(/^(?:accept-invite|join)\/([^/?#]+)/);
  if (hashMatch?.[1]) return decodeURIComponent(hashMatch[1]);

  return null;
}

export function App(): JSX.Element {
  const [activePage, setActivePage] = useState<PageKey>(() => getPageFromHash());
  const [inviteToken, setInviteToken] = useState<string | null>(() => getInviteTokenFromLocation());
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const auth = useAuth();
  const { theme, toggleTheme } = useTheme();
  const currentUserRole = auth.user?.role ?? null;
  const navigationItems = getNavigationItemsForRole(currentUserRole);
  const febGrid = useFebGridData({ enabled: auth.isAuthenticated && !inviteToken, role: currentUserRole });
  const unreadNotificationCount = febGrid.data.notifications.filter((notification) => !notification.is_read && !notification.is_dismissed).length;

  useEffect(() => {
    const handleHashChange = (): void => {
      setActivePage(getPageFromHash());
      setInviteToken(getInviteTokenFromLocation());
      setIsSidebarOpen(false);
    };

    window.addEventListener("hashchange", handleHashChange);
    window.addEventListener("popstate", handleHashChange);
    return () => {
      window.removeEventListener("hashchange", handleHashChange);
      window.removeEventListener("popstate", handleHashChange);
    };
  }, []);

  useEffect(() => {
    if (!auth.isAuthenticated || !auth.user || inviteToken) return;
    if (isPageAllowedForRole(auth.user.role, activePage)) return;
    const nextPage = getDefaultPageForRole(auth.user.role);
    if (activePage === nextPage) return;
    window.location.hash = `/${nextPage}`;
  }, [activePage, auth.isAuthenticated, auth.user, inviteToken]);

  function handleNavigate(page: PageKey): void {
    const nextPage = isPageAllowedForRole(currentUserRole, page) ? page : getDefaultPageForRole(currentUserRole);
    if (page === activePage) {
      setIsSidebarOpen(false);
      return;
    }
    window.location.hash = `/${nextPage}`;
  }

  function renderPage(): JSX.Element {
    if (auth.user && !isPageAllowedForRole(auth.user.role, activePage)) {
      return <LoadingState label="Opening your workspace" />;
    }

    if (febGrid.error) {
      return <ErrorState message={febGrid.error} onRetry={febGrid.refreshCompanies} />;
    }

    const sharedProps = {
      data: febGrid.data,
      selectedCompany: febGrid.selectedCompany,
      isLoadingCompanies: febGrid.isLoadingCompanies,
      isLoadingModules: febGrid.isLoadingModules,
      isMutating: febGrid.isMutating,
      currentUserRole,
      onRetry: febGrid.refreshModules,
    };

    const withModuleError = (moduleError: string | null) => ({
      ...sharedProps,
      moduleError,
    });

    switch (activePage) {
      case "my-dashboard":
        return (
          <EmployeeDashboardPage
            {...withModuleError(
              febGrid.moduleErrors.employees ??
                febGrid.moduleErrors.workObjects ??
                febGrid.moduleErrors.leaves ??
                febGrid.moduleErrors.notifications ??
                febGrid.moduleErrors.announcements ??
                null,
            )}
            onNavigate={handleNavigate}
          />
        );
      case "my-work":
        return (
          <MyWorkPage
            {...withModuleError(febGrid.moduleErrors.workObjects ?? null)}
            onCompleteWorkObject={febGrid.completeWorkObject}
            onUpdateWorkObjectStatus={febGrid.updateWorkObjectStatus}
          />
        );
      case "my-projects":
        return <MyProjectsPage {...withModuleError(febGrid.moduleErrors.projects ?? null)} />;
      case "my-leave":
        return (
          <MyLeavePage
            {...withModuleError(febGrid.moduleErrors.leaves ?? febGrid.moduleErrors.employees ?? febGrid.moduleErrors.leaveApprovers ?? null)}
            onCancelLeave={febGrid.cancelLeave}
            onCreateLeave={febGrid.createLeave}
            onUpdateLeave={febGrid.updateLeave}
          />
        );
      case "my-profile":
        return <MyProfilePage selectedCompany={febGrid.selectedCompany} onProfileSaved={febGrid.refreshModules} />;
      case "companies":
        return <CompaniesPage {...withModuleError(null)} onCreateCompany={febGrid.createCompany} />;
      case "employees":
        return (
          <EmployeesPage
            {...withModuleError(febGrid.moduleErrors.employees ?? febGrid.moduleErrors.departments ?? febGrid.moduleErrors.invitations ?? null)}
            onApproveInvitation={febGrid.approveInvitation}
            onCreateEmployee={febGrid.createEmployee}
            onCreateInvitation={febGrid.createInvitation}
            onDeactivateEmployee={febGrid.deactivateEmployee}
            onRejectInvitation={febGrid.rejectInvitation}
            onResendInvitation={febGrid.resendInvitation}
            onRevokeInvitation={febGrid.revokeInvitation}
            onUpdateEmployee={febGrid.updateEmployee}
            onUpdateEmployeeStatus={febGrid.updateEmployeeStatus}
          />
        );
      case "teams":
        return (
          <TeamsPage
            {...withModuleError(febGrid.moduleErrors.teams ?? febGrid.moduleErrors.departments ?? null)}
            onCreateDepartment={febGrid.createDepartment}
            onCreateTeam={febGrid.createTeam}
          />
        );
      case "projects":
        return (
          <ProjectsPage
            {...withModuleError(febGrid.moduleErrors.projects ?? null)}
            onAddProjectMember={febGrid.addProjectMember}
            onCreateProject={febGrid.createProject}
            onDeactivateProject={febGrid.deactivateProject}
            onRemoveProjectMember={febGrid.removeProjectMember}
            onUpdateProject={febGrid.updateProject}
            onUpdateProjectPriority={febGrid.updateProjectPriority}
            onUpdateProjectStatus={febGrid.updateProjectStatus}
          />
        );
      case "work-objects":
        return (
          <WorkObjectsPage
            {...withModuleError(febGrid.moduleErrors.workObjects ?? null)}
            onAssignWorkObject={febGrid.assignWorkObject}
            onCompleteWorkObject={febGrid.completeWorkObject}
            onCreateWorkObject={febGrid.createWorkObject}
            onDeactivateWorkObject={febGrid.deactivateWorkObject}
            onUpdateWorkObject={febGrid.updateWorkObject}
            onUpdateWorkObjectPriority={febGrid.updateWorkObjectPriority}
            onUpdateWorkObjectStatus={febGrid.updateWorkObjectStatus}
          />
        );
      case "leaves":
        return (
          <LeavesPage
            {...withModuleError(febGrid.moduleErrors.leaves ?? null)}
            onApproveLeave={febGrid.approveLeave}
            onCancelLeave={febGrid.cancelLeave}
            onCreateLeave={febGrid.createLeave}
            onDeactivateLeave={febGrid.deactivateLeave}
            onRejectLeave={febGrid.rejectLeave}
            onUpdateLeave={febGrid.updateLeave}
          />
        );
      case "events":
        return <EventsPage {...withModuleError(febGrid.moduleErrors.events ?? febGrid.moduleErrors.auditLogs ?? null)} />;
      case "announcements":
        return (
          <AnnouncementsPage
            {...withModuleError(febGrid.moduleErrors.announcements ?? null)}
            currentUserRole={currentUserRole}
            onArchiveAnnouncement={febGrid.archiveAnnouncement}
            onCreateAnnouncement={febGrid.createAnnouncement}
            onUpdateAnnouncement={febGrid.updateAnnouncement}
          />
        );
      case "notifications":
        return (
          <NotificationsPage
            {...withModuleError(febGrid.moduleErrors.notifications ?? null)}
            currentUserRole={currentUserRole}
            onDismissNotification={febGrid.dismissNotification}
            onMarkAllRead={febGrid.markAllNotificationsRead}
            onMarkRead={febGrid.markNotificationRead}
            onMarkUnread={febGrid.markNotificationUnread}
          />
        );
      case "memory":
        return <CompanyMemoryPage selectedCompany={febGrid.selectedCompany} currentUserRole={auth.user?.role ?? null} />;
      case "settings":
        return (
          <SettingsPage
            {...withModuleError(
              febGrid.moduleErrors.companySettings ??
                febGrid.moduleErrors.billingPlans ??
                febGrid.moduleErrors.billingSummary ??
                febGrid.moduleErrors.files ??
                febGrid.moduleErrors.aiCapabilities ??
                febGrid.moduleErrors.aiProviderStatus ??
                febGrid.moduleErrors.aiSafetySettings ??
                febGrid.moduleErrors.aiJobs ??
                febGrid.moduleErrors.industryTemplates ??
                febGrid.moduleErrors.workObjectTypes ??
                febGrid.moduleErrors.customFields ??
                null,
            )}
            currentUserRole={auth.user?.role ?? null}
            onApplyIndustryTemplate={febGrid.applyIndustryTemplate}
            onArchiveFile={febGrid.archiveFile}
            onArchiveCustomField={febGrid.archiveCustomField}
            onArchiveWorkObjectType={febGrid.archiveWorkObjectType}
            onCancelAIJob={febGrid.cancelAIJob}
            onCreateAIJob={febGrid.createAIJob}
            onCreateCustomField={febGrid.createCustomField}
            onCreateWorkObjectType={febGrid.createWorkObjectType}
            onRunAIJob={febGrid.runAIJob}
            onUpdateAISafetySettings={febGrid.updateAISafetySettings}
            onUpdateCompanySettings={febGrid.updateCompanySettings}
            onUpdateCompanyPlan={febGrid.updateCompanyPlan}
            onUpdateCustomField={febGrid.updateCustomField}
            onUpdateFile={febGrid.updateFile}
            onUpdateWorkObjectType={febGrid.updateWorkObjectType}
            onRestoreFile={febGrid.restoreFile}
          />
        );
      case "dashboard":
      default:
        return <DashboardPage {...withModuleError(febGrid.moduleErrors.dashboardSummary ?? null)} />;
    }
  }

  if (auth.isLoading) {
    return <LoadingState label="Loading FebGrid session" />;
  }

  if (inviteToken) {
    return <InviteAcceptPage token={inviteToken} />;
  }

  if (!auth.isAuthenticated) {
    return (
      <AuthPage
        error={auth.error}
        isSubmitting={auth.isSubmitting}
        onClearError={auth.clearError}
        onLogin={auth.login}
        onRegister={auth.register}
      />
    );
  }

  return (
    <AppLayout
      activePage={activePage}
      navigationItems={navigationItems}
      isSidebarOpen={isSidebarOpen}
      companies={febGrid.data.companies}
      currentUser={auth.user}
      theme={theme}
      unreadNotificationCount={unreadNotificationCount}
      onCloseSidebar={() => setIsSidebarOpen(false)}
      onLogout={auth.logout}
      onNavigate={handleNavigate}
      onOpenSidebar={() => setIsSidebarOpen(true)}
      onSelectCompany={febGrid.selectCompany}
      onToggleTheme={toggleTheme}
      selectedCompanyId={febGrid.selectedCompanyId}
    >
      {renderPage()}
    </AppLayout>
  );
}
