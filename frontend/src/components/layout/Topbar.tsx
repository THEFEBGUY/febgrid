import { Bell, LogOut, Menu, Search, ShieldCheck } from "lucide-react";

import type { AuthUser, Company } from "../../types/api";
import { formatLabel } from "../../utils/format";
import { Button } from "../ui/Button";

interface TopbarProps {
  title: string;
  description: string;
  onOpenSidebar: () => void;
  companies: Company[];
  selectedCompanyId: string | null;
  currentUser: AuthUser | null;
  onSelectCompany: (companyId: string) => void;
  onLogout: () => void;
}

export function Topbar({
  title,
  description,
  onOpenSidebar,
  companies,
  selectedCompanyId,
  currentUser,
  onSelectCompany,
  onLogout,
}: TopbarProps): JSX.Element {
  return (
    <header className="sticky top-0 z-20 border-b border-grid-200 bg-grid-50/90 backdrop-blur">
      <div className="flex min-h-20 flex-col gap-4 px-4 py-4 lg:flex-row lg:items-center lg:justify-between lg:px-8">
        <div className="flex min-w-0 items-center gap-3">
          <Button
            aria-label="Open navigation"
            className="size-10 px-0 lg:hidden"
            icon={<Menu className="size-5" aria-hidden="true" />}
            onClick={onOpenSidebar}
          >
            <span className="sr-only">Open navigation</span>
          </Button>
          <div className="min-w-0">
            <h1 className="truncate text-2xl font-black tracking-normal text-ink-950">{title}</h1>
            <p className="truncate text-sm font-medium text-ink-500">{description}</p>
          </div>
        </div>

        <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
          <label className="block min-w-0 sm:w-56">
            <span className="sr-only">Active company</span>
            <select
              className="h-10 w-full rounded-md border border-grid-200 bg-white px-3 text-sm font-bold text-ink-900 shadow-sm disabled:bg-grid-100 disabled:text-ink-500"
              disabled={companies.length === 0}
              value={selectedCompanyId ?? ""}
              onChange={(event) => onSelectCompany(event.target.value)}
            >
              {companies.length === 0 ? <option value="">No companies</option> : null}
              {companies.map((company) => (
                <option key={company.id} value={company.id}>
                  {company.name}
                </option>
              ))}
            </select>
          </label>
          <label className="relative block min-w-0 sm:w-72">
            <span className="sr-only">Search operations</span>
            <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-ink-500" aria-hidden="true" />
            <input
              className="h-10 w-full rounded-md border border-grid-200 bg-white pl-9 pr-3 text-sm font-medium text-ink-900 shadow-sm placeholder:text-ink-500"
              placeholder="Search company memory"
              type="search"
            />
          </label>
          <div className="flex gap-2">
            <Button icon={<ShieldCheck className="size-4" aria-hidden="true" />}>Tenant safe</Button>
            <Button aria-label="Notifications" className="size-10 px-0" icon={<Bell className="size-4" aria-hidden="true" />}>
              <span className="sr-only">Notifications</span>
            </Button>
            <div className="hidden min-w-0 rounded-md border border-grid-200 bg-white px-3 py-1.5 shadow-sm xl:block">
              <p className="max-w-40 truncate text-sm font-bold text-ink-950">{currentUser?.full_name ?? "User"}</p>
              <p className="text-xs font-semibold text-ink-500">{formatLabel(currentUser?.role)}</p>
            </div>
            <Button aria-label="Logout" className="size-10 px-0" icon={<LogOut className="size-4" aria-hidden="true" />} onClick={onLogout}>
              <span className="sr-only">Logout</span>
            </Button>
          </div>
        </div>
      </div>
    </header>
  );
}
