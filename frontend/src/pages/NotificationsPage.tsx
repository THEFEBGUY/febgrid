import { Bell, Check, CheckCheck, ExternalLink, EyeOff, RotateCcw } from "lucide-react";
import { useMemo } from "react";

import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { ModuleBoundary } from "../components/ui/ModuleBoundary";
import { SectionPanel } from "../components/ui/SectionPanel";
import { priorityTone } from "../components/ui/tone";
import type { Notification } from "../types/api";
import type { ModulePageProps } from "../types/page";
import { formatLabel, formatTime } from "../utils/format";

interface NotificationsPageProps extends ModulePageProps {
  onMarkRead: (notificationId: string) => Promise<void>;
  onMarkUnread: (notificationId: string) => Promise<void>;
  onMarkAllRead: () => Promise<void>;
  onDismissNotification: (notificationId: string) => Promise<void>;
}

function notificationTarget(notification: Notification): string {
  if (!notification.target_entity_type) return "Company";
  return formatLabel(notification.target_entity_type);
}

function openActionUrl(actionUrl: string): void {
  if (actionUrl.startsWith("#/")) {
    window.location.hash = actionUrl.slice(1);
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
}: NotificationsPageProps): JSX.Element {
  const visibleNotifications = useMemo(
    () => data.notifications.filter((notification) => !notification.is_dismissed),
    [data.notifications],
  );
  const unreadCount = visibleNotifications.filter((notification) => !notification.is_read).length;

  return (
    <SectionPanel
      eyebrow={selectedCompany?.name ?? "Action stream"}
      title="Notifications"
      action={
        <Button
          disabled={isMutating || unreadCount === 0}
          icon={<CheckCheck className="size-4" aria-hidden="true" />}
          onClick={() => {
            void onMarkAllRead();
          }}
        >
          Mark all read
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
        <div className="divide-y divide-grid-100">
          {visibleNotifications.map((notification) => (
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
                      onClick={() => openActionUrl(notification.action_url ?? "")}
                    >
                      Open
                    </Button>
                  ) : null}
                  <Button
                    className="h-9"
                    disabled={isMutating}
                    icon={notification.is_read ? <RotateCcw className="size-4" aria-hidden="true" /> : <Check className="size-4" aria-hidden="true" />}
                    onClick={() => {
                      void (notification.is_read ? onMarkUnread(notification.id) : onMarkRead(notification.id));
                    }}
                  >
                    {notification.is_read ? "Unread" : "Read"}
                  </Button>
                  <Button
                    className="h-9"
                    disabled={isMutating}
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
      </ModuleBoundary>
    </SectionPanel>
  );
}
