import { useEffect, useMemo, useRef, useState } from "react";
import { Bell, Loader2, LogOut, Menu, Search, ShieldCheck } from "lucide-react";

import type { AuthUser, Company } from "../../types/api";
import type { ThemeMode } from "../../hooks/useTheme";
import { api } from "../../services/api";
import type { SearchResponse, SearchResultItem } from "../../types/api";
import { formatLabel, formatTime } from "../../utils/format";
import { Button } from "../ui/Button";
import { ThemeToggle } from "./ThemeToggle";

interface TopbarProps {
  title: string;
  description: string;
  onOpenSidebar: () => void;
  companies: Company[];
  selectedCompanyId: string | null;
  currentUser: AuthUser | null;
  theme: ThemeMode;
  unreadNotificationCount: number;
  onSelectCompany: (companyId: string) => void;
  onOpenNotifications: () => void;
  onToggleTheme: () => void;
  onLogout: () => void;
}

export function Topbar({
  title,
  description,
  onOpenSidebar,
  companies,
  selectedCompanyId,
  currentUser,
  theme,
  unreadNotificationCount,
  onSelectCompany,
  onOpenNotifications,
  onToggleTheme,
  onLogout,
}: TopbarProps): JSX.Element {
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResponse, setSearchResponse] = useState<SearchResponse | null>(null);
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const [isSearchLoading, setIsSearchLoading] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);
  const searchContainerRef = useRef<HTMLDivElement | null>(null);
  const searchRequestIdRef = useRef(0);
  const trimmedSearchQuery = searchQuery.trim();
  const canUseOperationalSearch = currentUser?.role !== "employee";

  const groupedSearchResults = useMemo(
    () => Object.entries(searchResponse?.groups ?? {}).filter(([, items]) => items.length > 0),
    [searchResponse],
  );

  useEffect(() => {
    if (!canUseOperationalSearch || !selectedCompanyId || trimmedSearchQuery.length < 2) {
      searchRequestIdRef.current += 1;
      setSearchResponse(null);
      setIsSearchLoading(false);
      setSearchError(null);
      return;
    }

    const requestId = searchRequestIdRef.current + 1;
    searchRequestIdRef.current = requestId;
    setIsSearchLoading(true);
    setSearchError(null);

    const timeoutId = window.setTimeout(() => {
      void api
        .search(selectedCompanyId, { q: trimmedSearchQuery, limit: 8 })
        .then((response) => {
          if (searchRequestIdRef.current !== requestId) return;
          setSearchResponse(response);
        })
        .catch(() => {
          if (searchRequestIdRef.current !== requestId) return;
          setSearchError("Search is unavailable right now.");
          setSearchResponse(null);
        })
        .finally(() => {
          if (searchRequestIdRef.current === requestId) setIsSearchLoading(false);
        });
    }, 250);

    return () => window.clearTimeout(timeoutId);
  }, [canUseOperationalSearch, selectedCompanyId, trimmedSearchQuery]);

  useEffect(() => {
    if (!isSearchOpen) return;

    function handlePointerDown(event: PointerEvent): void {
      if (!searchContainerRef.current?.contains(event.target as Node)) {
        setIsSearchOpen(false);
      }
    }

    document.addEventListener("pointerdown", handlePointerDown);
    return () => document.removeEventListener("pointerdown", handlePointerDown);
  }, [isSearchOpen]);

  function openSearchResult(item: SearchResultItem): void {
    if (item.href?.startsWith("#/")) {
      window.location.hash = item.href.slice(1);
    } else {
      const fallbackRoutes: Record<string, string> = {
        employee: "/employees",
        department: "/teams",
        team: "/teams",
        project: "/projects",
        work_object: "/work-objects",
        leave_request: "/leaves",
        file: "/work-objects",
        event: "/events",
        notification: "/notifications",
        announcement: "/announcements",
        comment: item.related_entity_type === "project" ? "/projects" : "/work-objects",
        work_object_type: "/settings",
        custom_field: "/settings",
      };
      window.location.hash = fallbackRoutes[item.type] ?? "/dashboard";
    }
    setIsSearchOpen(false);
  }

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
          {canUseOperationalSearch ? (
            <div ref={searchContainerRef} className="relative block min-w-0 sm:w-72">
              <span className="sr-only">Search operations</span>
              <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-ink-500" aria-hidden="true" />
              <input
                aria-label="Operational search"
                className="h-10 w-full rounded-md border border-grid-200 bg-white pl-9 pr-3 text-sm font-medium text-ink-900 shadow-sm placeholder:text-ink-500"
                placeholder="Operational search"
                type="search"
                value={searchQuery}
                onChange={(event) => {
                  setSearchQuery(event.target.value);
                  setIsSearchOpen(true);
                }}
                onFocus={() => setIsSearchOpen(true)}
                onKeyDown={(event) => {
                  if (event.key === "Escape") {
                    setIsSearchOpen(false);
                    event.currentTarget.blur();
                  }
                  if (event.key === "Enter" && searchResponse?.results[0]) {
                    event.preventDefault();
                    openSearchResult(searchResponse.results[0]);
                  }
                }}
              />
              {isSearchOpen ? (
                <div className="absolute right-0 top-12 z-30 w-[min(36rem,calc(100vw-2rem))] overflow-hidden rounded-lg border border-grid-200 bg-white shadow-soft">
                  <div className="border-b border-grid-100 px-4 py-3">
                    <p className="text-xs font-bold uppercase tracking-normal text-ink-500">Operational Search</p>
                    <p className="mt-1 text-sm font-semibold text-ink-700">Search employees, projects, work, files, events, and company activity.</p>
                  </div>
                  {trimmedSearchQuery.length < 2 ? (
                    <div className="px-4 py-5 text-sm font-medium text-ink-500">Type at least 2 characters to search company operations.</div>
                  ) : isSearchLoading ? (
                    <div className="flex items-center gap-2 px-4 py-5 text-sm font-semibold text-ink-600">
                      <Loader2 className="size-4 animate-spin" aria-hidden="true" />
                      Searching
                    </div>
                  ) : searchError ? (
                    <div className="px-4 py-5 text-sm font-semibold text-rose-700">{searchError}</div>
                  ) : groupedSearchResults.length === 0 ? (
                    <div className="px-4 py-5 text-sm font-medium text-ink-500">No operational results found.</div>
                  ) : (
                    <div className="max-h-[28rem] overflow-y-auto py-2">
                      {groupedSearchResults.map(([groupName, items]) => (
                        <div key={groupName} className="py-2">
                          <p className="px-4 pb-1 text-xs font-bold uppercase tracking-normal text-ink-500">{formatLabel(groupName)}</p>
                          <div className="space-y-1">
                            {items.map((item) => (
                              <button
                                key={`${item.type}-${item.id}`}
                                className="block w-full px-4 py-2 text-left hover:bg-grid-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-ink-950"
                                type="button"
                                onClick={() => openSearchResult(item)}
                              >
                                <span className="flex items-center justify-between gap-3">
                                  <span className="min-w-0">
                                    <span className="block truncate text-sm font-bold text-ink-950">{item.title}</span>
                                    <span className="mt-0.5 block truncate text-xs font-semibold text-ink-500">
                                      {[
                                        item.subtitle,
                                        item.status ? formatLabel(item.status) : null,
                                        item.updated_at || item.created_at ? formatTime(item.updated_at ?? item.created_at) : null,
                                      ]
                                        .filter(Boolean)
                                        .join(" / ")}
                                    </span>
                                  </span>
                                  {item.priority ? <span className="rounded-md border border-grid-200 px-2 py-1 text-xs font-bold text-ink-600">{formatLabel(item.priority)}</span> : null}
                                </span>
                                {item.description ? <span className="mt-1 line-clamp-1 text-xs text-ink-500">{item.description}</span> : null}
                              </button>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ) : null}
            </div>
          ) : null}
          <div className="flex gap-2">
            <Button icon={<ShieldCheck className="size-4" aria-hidden="true" />}>Tenant safe</Button>
            <ThemeToggle theme={theme} onToggle={onToggleTheme} />
            <Button
              aria-label="Notifications"
              className="relative size-10 px-0"
              icon={<Bell className="size-4" aria-hidden="true" />}
              onClick={onOpenNotifications}
            >
              <span className="sr-only">Notifications</span>
              {unreadNotificationCount > 0 ? (
                <span className="absolute -right-1 -top-1 flex h-5 min-w-5 items-center justify-center rounded-full bg-rose-600 px-1 text-[10px] font-black leading-none text-white">
                  {unreadNotificationCount > 99 ? "99+" : unreadNotificationCount}
                </span>
              ) : null}
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
