import { useEffect, useState } from "react";

import { AppLayout } from "./components/layout/AppLayout";
import { ErrorState, LoadingState } from "./components/ui/States";
import { navigationItems } from "./data/navigation";
import { useAuth } from "./hooks/useAuth";
import { useFebGridData } from "./hooks/useFebGridData";
import { AuthPage } from "./pages/AuthPage";
import { CompaniesPage } from "./pages/CompaniesPage";
import { DashboardPage } from "./pages/DashboardPage";
import { EmployeesPage } from "./pages/EmployeesPage";
import { EventsPage } from "./pages/EventsPage";
import { LeavesPage } from "./pages/LeavesPage";
import { NotificationsPage } from "./pages/NotificationsPage";
import { ProjectsPage } from "./pages/ProjectsPage";
import { TeamsPage } from "./pages/TeamsPage";
import { WorkObjectsPage } from "./pages/WorkObjectsPage";
import type { PageKey } from "./types/domain";

function getPageFromHash(): PageKey {
  const hash = window.location.hash.replace("#/", "");
  const match = navigationItems.find((item) => item.key === hash);
  return match?.key ?? "dashboard";
}

export function App(): JSX.Element {
  const [activePage, setActivePage] = useState<PageKey>(() => getPageFromHash());
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const auth = useAuth();
  const febGrid = useFebGridData({ enabled: auth.isAuthenticated });

  useEffect(() => {
    const handleHashChange = (): void => {
      setActivePage(getPageFromHash());
      setIsSidebarOpen(false);
    };

    window.addEventListener("hashchange", handleHashChange);
    return () => window.removeEventListener("hashchange", handleHashChange);
  }, []);

  function handleNavigate(page: PageKey): void {
    if (page === activePage) {
      setIsSidebarOpen(false);
      return;
    }
    window.location.hash = `/${page}`;
  }

  function renderPage(): JSX.Element {
    if (febGrid.error) {
      return <ErrorState message={febGrid.error} onRetry={febGrid.refreshCompanies} />;
    }

    const sharedProps = {
      data: febGrid.data,
      selectedCompany: febGrid.selectedCompany,
      isLoadingCompanies: febGrid.isLoadingCompanies,
      isLoadingModules: febGrid.isLoadingModules,
      isMutating: febGrid.isMutating,
      onRetry: febGrid.refreshModules,
    };

    const withModuleError = (moduleError: string | null) => ({
      ...sharedProps,
      moduleError,
    });

    switch (activePage) {
      case "companies":
        return <CompaniesPage {...withModuleError(null)} onCreateCompany={febGrid.createCompany} />;
      case "employees":
        return (
          <EmployeesPage
            {...withModuleError(febGrid.moduleErrors.employees ?? febGrid.moduleErrors.departments ?? null)}
            onCreateEmployee={febGrid.createEmployee}
            onDeactivateEmployee={febGrid.deactivateEmployee}
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
        return <LeavesPage {...withModuleError(febGrid.moduleErrors.leaves ?? null)} onCreateLeave={febGrid.createLeave} />;
      case "events":
        return <EventsPage {...withModuleError(febGrid.moduleErrors.events ?? null)} />;
      case "notifications":
        return <NotificationsPage {...withModuleError(febGrid.moduleErrors.notifications ?? null)} />;
      case "dashboard":
      default:
        return <DashboardPage {...withModuleError(null)} />;
    }
  }

  if (auth.isLoading) {
    return <LoadingState label="Loading FebGrid session" />;
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
      isSidebarOpen={isSidebarOpen}
      companies={febGrid.data.companies}
      currentUser={auth.user}
      onCloseSidebar={() => setIsSidebarOpen(false)}
      onLogout={auth.logout}
      onNavigate={handleNavigate}
      onOpenSidebar={() => setIsSidebarOpen(true)}
      onSelectCompany={febGrid.selectCompany}
      selectedCompanyId={febGrid.selectedCompanyId}
    >
      {renderPage()}
    </AppLayout>
  );
}
