import { Bell, Check, CheckCheck, ExternalLink, EyeOff, RotateCcw } from "lucide-react";
import { useMemo, useState } from "react";

import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { FilterBar, FilterField } from "../components/ui/FilterBar";
import { SelectInput, TextInput } from "../components/ui/FormControls";
import { ModuleBoundary } from "../components/ui/ModuleBoundary";
import { SectionPanel } from "../components/ui/SectionPanel";
import { priorityTone } from "../components/ui/tone";
import type { Notification, UserRole } from "../types/api";
import type { ModulePageProps } from "../types/page";
import { formatLabel, formatTime } from "../utils/format";

interface NotificationsPageProps extends ModulePageProps {
  currentUserRole?: UserRole | null;
  onMarkRead: (notificationId: string) => Promise<void>;
  onMarkUnread: (notificationId: string) => Promise<void>;
  onMarkAllRead: () => Promise<void>;
  onDismissNotification: (notificationId: string) => Promise<void>;
}

function notificationTarget(notification: Notification): string {
  if (!notification.target_entity_type) return "Company";
  return formatLabel(notification.target_entity_type);
}

function openActionUrl(actionUrl: string, currentUserRole?: UserRole | null): void {
  if (actionUrl.startsWith("#/")) {
    const route = actionUrl.slice(1);
    if (currentUserRole === "employee") {
      const employeeRouteMap: Record<string, string> = {
        "/dashboard": "/my-dashboard",
        "/work-objects": "/my-work",
        "/leaves": "/my-leave",
        "/employees": "/my-profile",
        "/companies": "/my-dashboard",
        "/projects": "/my-projects",
        "/events": "/my-dashboard",
        "/settings": "/my-dashboard",
      };
      window.location.hash = employeeRouteMap[route] ?? route;
      return;
    }
    window.location.hash = route;
  }
}

export function NotificationsPage({
  data,
  selectedCompany,
  isLoadingModules,
  isMutating,
  moduleError,
  onRetry,
  onMarkRead,
  onMarkUnread,
  onMarkAllRead,
  onDismissNotification,
  currentUserRole,
}: NotificationsPageProps): JSX.Element {
  const [pendingNotificationIds, setPendingNotificationIds] = useState<Set<string>>(new Set());
  const [actionError, setActionError] = useState<string | null>(null);
  const [searchFilter, setSearchFilter] = useState("");
  const [readFilter, setReadFilter] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const [priorityFilter, setPriorityFilter] = useState("");
  const visibleNotifications = useMemo(
    () => data.notifications.filter((notification) => !notification.is_dismissed),
    [data.notifications],
  );
  const notificationTypes = useMemo(
    () => Array.from(new Set(visibleNotifications.map((notification) => notification.notification_type))).sort(),
    [visibleNotifications],
  );
  const filteredNotifications = useMemo(() => {
    const query = searchFilter.trim().toLowerCase();
    return visibleNotifications.filter((notification) => {
      const searchable = [notification.title, notification.message, notification.notification_type, notification.priority, notificationTarget(notification)]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();
      if (query && !searchable.includes(query)) return false;
      if (readFilter === "read" && !notification.is_read) return false;
      if (readFilter === "unread" && notification.is_read) return false;
      if (readFilter === "action" && !notification.action_url) return false;
      if (typeFilter && notification.notification_type !== typeFilter) return false;
      if (priorityFilter && notification.priority !== priorityFilter) return false;
      return true;
    });
  }, [priorityFilter, readFilter, searchFilter, typeFilter, visibleNotifications]);
  const unreadCount = visibleNotifications.filter((notification) => !notification.is_read).length;
  const hasActiveFilters = Boolean(searchFilter || readFilter || typeFilter || priorityFilter);

  async function runNotificationAction(notificationId: string, action: () => Promise<void>): Promise<void> {
    setActionError(null);
    setPendingNotificationIds((current) => new Set(current).add(notificationId));
    try {
      await action();
    } catch {
      setActionError("The notification update could not be saved. Its previous state was restored.");
    } finally {
      setPendingNotificationIds((current) => {
        const next = new Set(current);
        next.delete(notificationId);
        return next;
      });
    }
  }

  return (
    <SectionPanel
      eyebrow={selectedCompany?.name ?? "Action stream"}
      title="Notifications"
      action={
        <Button
          disabled={isMutating || unreadCount === 0}
          icon={<CheckCheck className="size-4" aria-hidden="true" />}
          onClick={() => {
            void runNotificationAction("all", onMarkAllRead);
          }}
        >
          {pendingNotificationIds.has("all") ? "Saving..." : "Mark all read"}
        </Button>
      }
    >
      <ModuleBoundary
        emptyDescription="Work assignments, leave decisions, project changes, and file uploads that need attention will appear here."
        emptyTitle="No notifications yet"
        error={moduleError}
        isEmpty={visibleNotifications.length === 0}
        isLoading={isLoadingModules}
        onRetry={onRetry}
      >
        {actionError ? <p className="border-b border-rose-200 bg-rose-50 px-5 py-3 text-sm font-semibold text-rose-700">{actionError}</p> : null}
        <FilterBar
          isResetDisabled={!hasActiveFilters}
          onReset={() => {
            setSearchFilter("");
            setReadFilter("");
            setTypeFilter("");
            setPriorityFilter("");
          }}
        >
          <FilterField label="Search">
            <TextInput placeholder="Title, message, type" value={searchFilter} onChange={(event) => setSearchFilter(event.target.value)} />
          </FilterField>
          <FilterField label="State">
            <SelectInput value={readFilter} onChange={(event) => setReadFilter(event.target.value)}>
              <option value="">All states</option>
              <option value="unread">Unread</option>
              <option value="read">Read</option>
              <option value="action">Action needed</option>
            </SelectInput>
          </FilterField>
          <FilterField label="Type">
            <SelectInput value={typeFilter} onChange={(event) => setTypeFilter(event.target.value)}>
              <option value="">All types</option>
              {notificationTypes.map((notificationType) => (
                <option key={notificationType} value={notificationType}>
                  {formatLabel(notificationType)}
                </option>
              ))}
            </SelectInput>
          </FilterField>
          <FilterField label="Priority">
            <SelectInput value={priorityFilter} onChange={(event) => setPriorityFilter(event.target.value)}>
              <option value="">All priorities</option>
              {["low", "normal", "high", "urgent"].map((priority) => (
                <option key={priority} value={priority}>
                  {formatLabel(priority)}
                </option>
              ))}
            </SelectInput>
          </FilterField>
        </FilterBar>
        {filteredNotifications.length === 0 ? (
          <div className="px-5 py-10 text-center">
            <p className="text-sm font-bold text-ink-950">No notifications match these filters</p>
            <p className="mt-1 text-sm font-medium text-ink-500">Reset filters to return to the action stream.</p>
          </div>
        ) : (
        <div className="divide-y divide-grid-100">
          {filteredNotifications.map((notification) => (
            <article
              key={notification.id}
              className={`flex flex-col gap-4 px-5 py-4 lg:flex-row lg:items-center lg:justify-between ${
                notification.is_read ? "bg-white" : "bg-blue-50/50"
              }`}
            >
              <div className="flex min-w-0 items-start gap-3">
                <span className="flex size-10 shrink-0 items-center justify-center rounded-md bg-grid-100 text-ink-700">
                  <Bell className="size-4" aria-hidden="true" />
                </span>
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="text-sm font-bold text-ink-950">{notification.title}</p>
                    {!notification.is_read ? <span className="size-2 rounded-full bg-blue-600" aria-label="Unread" /> : null}
                  </div>
                  <p className="mt-1 line-clamp-2 text-sm text-ink-500">{notification.message}</p>
                  <p className="mt-2 text-xs font-semibold text-ink-500">
                    {formatTime(notification.created_at)} / {notificationTarget(notification)}
                  </p>
                </div>
              </div>

              <div className="flex flex-col gap-3 lg:items-end">
                <div className="flex flex-wrap gap-2">
                  <Badge label={formatLabel(notification.notification_type)} tone="teal" />
                  <Badge label={formatLabel(notification.priority)} tone={priorityTone(notification.priority)} />
                  <Badge label={notification.is_read ? "Read" : "Unread"} tone={notification.is_read ? "slate" : "blue"} />
                </div>
                <div className="flex flex-wrap gap-2">
                  {notification.action_url ? (
                    <Button
                      className="h-9"
                      icon={<ExternalLink className="size-4" aria-hidden="true" />}
                      onClick={() => openActionUrl(notification.action_url ?? "", currentUserRole)}
                    >
                      Open
                    </Button>
                  ) : null}
                  <Button
                    className="h-9"
                    disabled={isMutating || pendingNotificationIds.has(notification.id)}
                    icon={notification.is_read ? <RotateCcw className="size-4" aria-hidden="true" /> : <Check className="size-4" aria-hidden="true" />}
                    onClick={() => {
                      void runNotificationAction(notification.id, () => (notification.is_read ? onMarkUnread(notification.id) : onMarkRead(notification.id)));
                    }}
                  >
                    {notification.is_read ? "Unread" : "Read"}
                  </Button>
                  <Button
                    className="h-9"
                    disabled={isMutating || pendingNotificationIds.has(notification.id)}
                    icon={<EyeOff className="size-4" aria-hidden="true" />}
                    onClick={() => {
                      void onDismissNotification(notification.id);
                    }}
                  >
                    Dismiss
                  </Button>
                </div>
              </div>
            </article>
          ))}
        </div>
        )}
      </ModuleBoundary>
    </SectionPanel>
  );
}
