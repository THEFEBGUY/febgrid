import { useEffect, useMemo, useState } from "react";

import { AppLayout } from "./components/layout/AppLayout";
import { navigationItems } from "./data/navigation";
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

const pageComponents: Record<PageKey, JSX.Element> = {
  dashboard: <DashboardPage />,
  companies: <CompaniesPage />,
  employees: <EmployeesPage />,
  teams: <TeamsPage />,
  projects: <ProjectsPage />,
  "work-objects": <WorkObjectsPage />,
  leaves: <LeavesPage />,
  events: <EventsPage />,
  notifications: <NotificationsPage />,
};

function getPageFromHash(): PageKey {
  const hash = window.location.hash.replace("#/", "");
  const match = navigationItems.find((item) => item.key === hash);
  return match?.key ?? "dashboard";
}

export function App(): JSX.Element {
  const [activePage, setActivePage] = useState<PageKey>(() => getPageFromHash());
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  useEffect(() => {
    const handleHashChange = (): void => {
      setActivePage(getPageFromHash());
      setIsSidebarOpen(false);
    };

    window.addEventListener("hashchange", handleHashChange);
    return () => window.removeEventListener("hashchange", handleHashChange);
  }, []);

  const visiblePage = useMemo(() => pageComponents[activePage], [activePage]);

  function handleNavigate(page: PageKey): void {
    if (page === activePage) {
      setIsSidebarOpen(false);
      return;
    }
    window.location.hash = `/${page}`;
  }

  return (
    <AppLayout
      activePage={activePage}
      isSidebarOpen={isSidebarOpen}
      onCloseSidebar={() => setIsSidebarOpen(false)}
      onNavigate={handleNavigate}
      onOpenSidebar={() => setIsSidebarOpen(true)}
    >
      {visiblePage}
    </AppLayout>
  );
}
