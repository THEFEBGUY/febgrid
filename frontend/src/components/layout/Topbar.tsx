import { useEffect, useMemo, useRef, useState } from "react";
import { Bell, Loader2, LogOut, Menu, Search, ShieldCheck } from "lucide-react";

import type { AuthUser, Company } from "../../types/api";
import type { ThemeMode } from "../../hooks/useTheme";
import { api } from "../../services/api";
import type { SearchResponse, SearchResultItem } from "../../types/api";
import { formatLabel, formatTime } from "../../utils/format";
import {
  operationalSearchResultClassName,
  operationalSearchSecondaryClassName,
  operationalSearchTitleClassName,
} from "../../utils/operationalSearch";
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
  const [activeSearchResultIndex, setActiveSearchResultIndex] = useState(-1);
  const searchContainerRef = useRef<HTMLDivElement | null>(null);
  const searchRequestIdRef = useRef(0);
  const trimmedSearchQuery = searchQuery.trim();
  const canUseOperationalSearch = currentUser?.role !== "employee";

  const groupedSearchResults = useMemo(
    () => Object.entries(searchResponse?.groups ?? {}).filter(([, items]) => items.length > 0),
    [searchResponse],
  );
  const flatSearchResults = useMemo(() => groupedSearchResults.flatMap(([, items]) => items), [groupedSearchResults]);

  useEffect(() => {
    if (!canUseOperationalSearch || !selectedCompanyId || trimmedSearchQuery.length < 2) {
      searchRequestIdRef.current += 1;
      setSearchResponse(null);
      setIsSearchLoading(false);
      setSearchError(null);
      setActiveSearchResultIndex(-1);
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
    setActiveSearchResultIndex(-1);
  }, [searchResponse]);

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
        company_memory: "/memory",
      };
      window.location.hash = fallbackRoutes[item.type] ?? "/dashboard";
    }
    setIsSearchOpen(false);
  }

  return (
    <header className="sticky top-0 z-20 border-b border-grid-200 bg-white/80 shadow-sm backdrop-blur-xl">
      <div className="flex min-h-20 flex-col gap-4 px-4 py-4 2xl:flex-row 2xl:items-center 2xl:justify-between lg:px-8">
        <div className="flex min-w-0 items-center gap-3 lg:w-52 lg:shrink-0 xl:w-64">
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
            <p className="truncate text-sm font-semibold text-ink-500">{description}</p>
          </div>
        </div>

        <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-center 2xl:justify-end">
          <label className="block min-w-0 sm:w-48 xl:w-52 2xl:w-56">
            <span className="sr-only">Active company</span>
            <select
              className="h-10 w-full rounded-md border border-grid-200 bg-white/90 px-3 text-sm font-bold text-ink-900 shadow-sm transition hover:border-brand-200 hover:shadow-button focus:border-brand-500 focus:outline-none focus:ring-4 focus:ring-brand-100 disabled:bg-grid-100 disabled:text-ink-500"
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
            <div ref={searchContainerRef} className="relative block min-w-0 sm:w-56 xl:w-64 2xl:w-72">
              <span className="sr-only">Search operations</span>
              <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-ink-500" aria-hidden="true" />
              <input
                aria-label="Operational search"
                aria-activedescendant={activeSearchResultIndex >= 0 ? `operational-search-result-${activeSearchResultIndex}` : undefined}
                aria-autocomplete="list"
                aria-controls="operational-search-results"
                aria-expanded={isSearchOpen}
                className="h-10 w-full rounded-md border border-grid-200 bg-white/90 pl-9 pr-3 text-sm font-semibold text-ink-900 shadow-sm transition placeholder:text-ink-500 hover:border-brand-200 hover:shadow-button focus:border-brand-500 focus:outline-none focus:ring-4 focus:ring-brand-100"
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
                  if (event.key === "ArrowDown" && flatSearchResults.length > 0) {
                    event.preventDefault();
                    setActiveSearchResultIndex((current) => (current + 1) % flatSearchResults.length);
                  }
                  if (event.key === "ArrowUp" && flatSearchResults.length > 0) {
                    event.preventDefault();
                    setActiveSearchResultIndex((current) => (current <= 0 ? flatSearchResults.length - 1 : current - 1));
                  }
                  const selectedResult = flatSearchResults[activeSearchResultIndex] ?? flatSearchResults[0];
                  if (event.key === "Enter" && selectedResult) {
                    event.preventDefault();
                    openSearchResult(selectedResult);
                  }
                }}
              />
              {isSearchOpen ? (
                <div className="febgrid-surface absolute right-0 top-12 z-30 w-[min(36rem,calc(100vw-2rem))] overflow-hidden rounded-lg">
                  <div className="febgrid-panel-header border-b border-grid-100 px-4 py-3">
                    <p className="text-xs font-black uppercase tracking-normal text-brand-600">Operational Search</p>
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
                    <div id="operational-search-results" className="max-h-[28rem] overflow-y-auto py-2" role="listbox">
                      {groupedSearchResults.map(([groupName, items]) => (
                        <div key={groupName} className="py-2">
                          <p className="px-4 pb-1 text-xs font-bold uppercase tracking-normal text-ink-500">{formatLabel(groupName)}</p>
                          <div className="space-y-1">
                            {items.map((item) => {
                              const resultIndex = flatSearchResults.indexOf(item);
                              const isSelected = resultIndex === activeSearchResultIndex;
                              return (
                                <button
                                  key={`${item.type}-${item.id}`}
                                  id={`operational-search-result-${resultIndex}`}
                                  aria-selected={isSelected}
                                  className={operationalSearchResultClassName(isSelected)}
                                  role="option"
                                  type="button"
                                  onFocus={() => setActiveSearchResultIndex(resultIndex)}
                                  onClick={() => openSearchResult(item)}
                                >
                                  <span className="flex items-center justify-between gap-3">
                                    <span className="min-w-0">
                                      <span className={operationalSearchTitleClassName(isSelected)}>{item.title}</span>
                                      <span className={`mt-0.5 block truncate text-xs font-semibold ${operationalSearchSecondaryClassName(isSelected)}`}>
                                        {[
                                          item.subtitle,
                                          item.status ? formatLabel(item.status) : null,
                                          item.updated_at || item.created_at ? formatTime(item.updated_at ?? item.created_at) : null,
                                        ]
                                          .filter(Boolean)
                                          .join(" / ")}
                                      </span>
                                    </span>
                                    {item.priority ? (
                                      <span
                                        className={`rounded-md border px-2 py-1 text-xs font-bold ${
                                          isSelected
                                            ? "border-white/30 text-white"
                                            : "border-grid-200 text-ink-600 group-hover:border-white/30 group-hover:text-white group-active:border-white/30 group-active:text-white"
                                        }`}
                                      >
                                        {formatLabel(item.priority)}
                                      </span>
                                    ) : null}
                                  </span>
                                  {item.description ? (
                                    <span className={`mt-1 line-clamp-1 text-xs ${operationalSearchSecondaryClassName(isSelected)}`}>{item.description}</span>
                                  ) : null}
                                </button>
                              );
                            })}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ) : null}
            </div>
          ) : null}
          <div className="flex shrink-0 gap-2">
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
            <div className="hidden min-w-0 rounded-md border border-grid-200 bg-white/90 px-3 py-1.5 shadow-sm 2xl:block">
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
