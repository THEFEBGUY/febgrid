import type { ReactNode } from "react";
import { X } from "lucide-react";

import type { PageKey } from "../../types/domain";
import { navigationItems } from "../../data/navigation";
import { Button } from "../ui/Button";
import { Sidebar } from "./Sidebar";
import { Topbar } from "./Topbar";

interface AppLayoutProps {
  activePage: PageKey;
  isSidebarOpen: boolean;
  onNavigate: (page: PageKey) => void;
  onCloseSidebar: () => void;
  onOpenSidebar: () => void;
  children: ReactNode;
}

export function AppLayout({
  activePage,
  isSidebarOpen,
  onNavigate,
  onCloseSidebar,
  onOpenSidebar,
  children,
}: AppLayoutProps): JSX.Element {
  const activeNavigation = navigationItems.find((item) => item.key === activePage) ?? navigationItems[0];

  return (
    <div className="min-h-screen bg-grid-50 text-ink-900">
      <div className="hidden lg:fixed lg:inset-y-0 lg:left-0 lg:block lg:w-72">
        <Sidebar activePage={activePage} onNavigate={onNavigate} />
      </div>

      {isSidebarOpen ? (
        <div className="fixed inset-0 z-40 lg:hidden" role="dialog" aria-modal="true">
          <button className="absolute inset-0 bg-ink-950/40" type="button" aria-label="Close navigation" onClick={onCloseSidebar} />
          <div className="relative h-full w-80 max-w-[86vw] bg-white shadow-soft">
            <div className="absolute right-3 top-3 z-10">
              <Button
                aria-label="Close navigation"
                className="size-10 px-0"
                icon={<X className="size-4" aria-hidden="true" />}
                onClick={onCloseSidebar}
              >
                <span className="sr-only">Close navigation</span>
              </Button>
            </div>
            <Sidebar activePage={activePage} onNavigate={onNavigate} />
          </div>
        </div>
      ) : null}

      <div className="lg:pl-72">
        <Topbar title={activeNavigation.label} description={activeNavigation.description} onOpenSidebar={onOpenSidebar} />
        <main className="mx-auto w-full max-w-7xl px-4 py-6 lg:px-8">{children}</main>
      </div>
    </div>
  );
}
