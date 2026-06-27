import { Zap } from "lucide-react";

import type { NavigationItem, PageKey } from "../../types/domain";

interface SidebarProps {
  activePage: PageKey;
  items: NavigationItem[];
  onNavigate: (page: PageKey) => void;
}

export function Sidebar({ activePage, items, onNavigate }: SidebarProps): JSX.Element {
  return (
    <aside className="flex h-full w-full flex-col border-r border-grid-200 bg-white/95">
      <div className="flex h-20 items-center gap-3 border-b border-grid-200 px-5">
        <div className="flex size-11 items-center justify-center rounded-lg bg-ink-950 text-white">
          <Zap className="size-5" aria-hidden="true" />
        </div>
        <div className="min-w-0">
          <p className="truncate text-lg font-black tracking-normal text-ink-950">FebGrid</p>
          <p className="truncate text-xs font-semibold text-ink-500">Business Operating System</p>
        </div>
      </div>

      <nav className="flex-1 space-y-1 overflow-y-auto px-3 py-4" aria-label="Primary navigation">
        {items.map((item) => {
          const Icon = item.icon;
          const isActive = activePage === item.key;

          return (
            <button
              key={item.key}
              type="button"
              onClick={() => onNavigate(item.key)}
              className={`flex min-h-14 w-full items-center gap-3 rounded-md px-3 text-left transition ${
                isActive ? "bg-ink-950 text-white shadow-soft" : "text-ink-700 hover:bg-grid-100"
              }`}
            >
              <Icon className="size-5 shrink-0" aria-hidden="true" />
              <span className="min-w-0">
                <span className="block truncate text-sm font-bold">{item.label}</span>
                <span className={`block truncate text-xs ${isActive ? "text-grid-200" : "text-ink-500"}`}>{item.description}</span>
              </span>
            </button>
          );
        })}
      </nav>
    </aside>
  );
}
