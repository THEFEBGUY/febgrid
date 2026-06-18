import type { ReactNode } from "react";

interface SectionPanelProps {
  title: string;
  eyebrow?: string;
  action?: ReactNode;
  children: ReactNode;
}

export function SectionPanel({ title, eyebrow, action, children }: SectionPanelProps): JSX.Element {
  return (
    <section className="rounded-lg border border-grid-200 bg-white shadow-sm">
      <div className="flex flex-col gap-3 border-b border-grid-200 px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="min-w-0">
          {eyebrow ? <p className="text-xs font-bold uppercase tracking-normal text-ink-500">{eyebrow}</p> : null}
          <h2 className="mt-1 truncate text-lg font-bold text-ink-950">{title}</h2>
        </div>
        {action ? <div className="shrink-0">{action}</div> : null}
      </div>
      <div>{children}</div>
    </section>
  );
}
