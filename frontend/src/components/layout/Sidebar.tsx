import { Zap } from "lucide-react";

import type { NavigationItem, PageKey } from "../../types/domain";

interface SidebarProps {
  activePage: PageKey;
  items: NavigationItem[];
  onNavigate: (page: PageKey) => void;
}

export function Sidebar({ activePage, items, onNavigate }: SidebarProps): JSX.Element {
  return (
    <aside className="relative flex h-full w-full flex-col overflow-hidden border-r border-grid-200 bg-white/95 backdrop-blur">
      <div className="febgrid-sidebar-glow pointer-events-none absolute inset-x-0 top-0 h-52" aria-hidden="true" />
      <div className="relative flex h-20 items-center gap-3 border-b border-grid-200 px-5">
        <div className="flex size-11 items-center justify-center rounded-lg bg-gradient-to-br from-brand-500 to-brand-700 text-white shadow-button">
          <Zap className="size-5" aria-hidden="true" />
        </div>
        <div className="min-w-0">
          <p className="truncate text-lg font-black tracking-normal text-ink-950">FebGrid</p>
          <p className="truncate text-xs font-semibold text-ink-500">Business Operating System</p>
        </div>
      </div>

      <nav className="relative flex-1 space-y-1.5 overflow-y-auto px-3 py-4" aria-label="Primary navigation">
        {items.map((item) => {
          const Icon = item.icon;
          const isActive = activePage === item.key;

          return (
            <button
              key={item.key}
              type="button"
              onClick={() => onNavigate(item.key)}
              className={`flex min-h-14 w-full items-center gap-3 rounded-md px-3 text-left transition ${
                isActive
                  ? "bg-gradient-to-r from-brand-600 to-brand-500 text-white shadow-button"
                  : "text-ink-700 hover:bg-white/80 hover:text-ink-950 hover:shadow-sm"
              }`}
            >
              <span className={`flex size-8 shrink-0 items-center justify-center rounded-md ${isActive ? "bg-white/15" : "bg-white/70 text-ink-600 ring-1 ring-grid-200"}`}>
                <Icon className="size-4 shrink-0" aria-hidden="true" />
              </span>
              <span className="min-w-0">
                <span className="block truncate text-sm font-bold">{item.label}</span>
                <span className={`block truncate text-xs font-semibold ${isActive ? "text-blue-100" : "text-ink-500"}`}>{item.description}</span>
              </span>
            </button>
          );
        })}
      </nav>
      <div className="relative border-t border-grid-200 px-5 py-4">
        <p className="text-xs font-black uppercase tracking-normal text-ink-500">Operating layer</p>
        <p className="mt-1 text-xs font-semibold leading-5 text-ink-500">People, work, files, events, and company memory in one tenant-safe system.</p>
      </div>
    </aside>
  );
}
