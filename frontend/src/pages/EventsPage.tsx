import { Clock3 } from "lucide-react";

import { events } from "../data/sampleData";
import { Badge } from "../components/ui/Badge";
import { SectionPanel } from "../components/ui/SectionPanel";

export function EventsPage(): JSX.Element {
  return (
    <SectionPanel eyebrow="Universal timeline" title="Events">
      <div className="divide-y divide-grid-100">
        {events.map((event) => (
          <article key={event.id} className="flex flex-col gap-3 px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex min-w-0 items-start gap-3">
              <span className="flex size-10 shrink-0 items-center justify-center rounded-md bg-grid-100 text-ink-700">
                <Clock3 className="size-4" aria-hidden="true" />
              </span>
              <div className="min-w-0">
                <p className="truncate text-sm font-bold text-ink-950">{event.title}</p>
                <p className="mt-1 truncate text-sm text-ink-500">{event.time} / {event.entity}</p>
              </div>
            </div>
            <Badge label={event.type} tone="teal" />
          </article>
        ))}
      </div>
    </SectionPanel>
  );
}
