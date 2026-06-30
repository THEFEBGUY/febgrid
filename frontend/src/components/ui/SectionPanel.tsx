import type { ReactNode } from "react";

interface SectionPanelProps {
  title: string;
  eyebrow?: string;
  description?: string;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
}

export function SectionPanel({ title, eyebrow, description, action, children, className = "" }: SectionPanelProps): JSX.Element {
  return (
    <section className={`febgrid-surface animate-fade-up overflow-hidden rounded-lg ${className}`}>
      <div className="febgrid-panel-header flex flex-col gap-3 border-b border-grid-200 px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="min-w-0">
          {eyebrow ? <p className="text-xs font-black uppercase tracking-normal text-brand-600">{eyebrow}</p> : null}
          <h2 className="mt-1 truncate text-lg font-bold text-ink-950">{title}</h2>
          {description ? <p className="mt-1 max-w-2xl text-sm font-semibold text-ink-500">{description}</p> : null}
        </div>
        {action ? <div className="shrink-0">{action}</div> : null}
      </div>
      <div>{children}</div>
    </section>
  );
}
