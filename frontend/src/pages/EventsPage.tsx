import { Clock3 } from "lucide-react";

import { Badge } from "../components/ui/Badge";
import { ModuleBoundary } from "../components/ui/ModuleBoundary";
import { SectionPanel } from "../components/ui/SectionPanel";
import type { ModulePageProps } from "../types/page";
import { formatTime } from "../utils/format";

export function EventsPage({ data, selectedCompany, isLoadingModules, moduleError, onRetry }: ModulePageProps): JSX.Element {
  return (
    <SectionPanel eyebrow={selectedCompany?.name ?? "Universal timeline"} title="Events">
      <ModuleBoundary
        emptyDescription="Important backend actions will appear here as company memory events."
        emptyTitle="No events yet"
        error={moduleError}
        isEmpty={data.events.length === 0}
        isLoading={isLoadingModules}
        onRetry={onRetry}
      >
        <div className="divide-y divide-grid-100">
          {data.events.map((event) => (
            <article key={event.id} className="flex flex-col gap-3 px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
              <div className="flex min-w-0 items-start gap-3">
                <span className="flex size-10 shrink-0 items-center justify-center rounded-md bg-grid-100 text-ink-700">
                  <Clock3 className="size-4" aria-hidden="true" />
                </span>
                <div className="min-w-0">
                  <p className="truncate text-sm font-bold text-ink-950">{event.title}</p>
                  <p className="mt-1 truncate text-sm text-ink-500">
                    {formatTime(event.created_at)} / {event.target_entity_type ?? "company"}
                  </p>
                </div>
              </div>
              <Badge label={event.event_type} tone="teal" />
            </article>
          ))}
        </div>
      </ModuleBoundary>
    </SectionPanel>
  );
}
