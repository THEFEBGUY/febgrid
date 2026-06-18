import { Bell, CheckCheck } from "lucide-react";

import { notifications } from "../data/sampleData";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { SectionPanel } from "../components/ui/SectionPanel";

export function NotificationsPage(): JSX.Element {
  return (
    <SectionPanel
      eyebrow="Action stream"
      title="Notifications"
      action={<Button icon={<CheckCheck className="size-4" aria-hidden="true" />}>Mark all read</Button>}
    >
      <div className="divide-y divide-grid-100">
        {notifications.map((notification) => (
          <article key={notification.id} className="flex flex-col gap-3 px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex min-w-0 items-start gap-3">
              <span className="flex size-10 shrink-0 items-center justify-center rounded-md bg-grid-100 text-ink-700">
                <Bell className="size-4" aria-hidden="true" />
              </span>
              <div className="min-w-0">
                <p className="truncate text-sm font-bold text-ink-950">{notification.title}</p>
                <p className="mt-1 line-clamp-2 text-sm text-ink-500">{notification.message}</p>
              </div>
            </div>
            <div className="flex shrink-0 items-center gap-2">
              <Badge label={notification.type} tone="blue" />
              <Badge label={notification.read ? "Read" : "Open"} tone={notification.read ? "slate" : "amber"} />
            </div>
          </article>
        ))}
      </div>
    </SectionPanel>
  );
}
