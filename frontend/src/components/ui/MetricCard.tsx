import type { LucideIcon } from "lucide-react";

import { MagicBentoCard } from "../premium/MagicBento";
import type { Metric } from "../../types/domain";

interface MetricCardProps {
  metric: Metric;
  icon: LucideIcon;
}

const toneClasses = {
  blue: "bg-blue-50 text-blue-700 ring-blue-100",
  green: "bg-green-50 text-green-700 ring-green-100",
  amber: "bg-amber-50 text-amber-700 ring-amber-100",
  red: "bg-rose-50 text-rose-700 ring-rose-100",
  teal: "bg-teal-50 text-teal-700 ring-teal-100",
  slate: "bg-slate-50 text-slate-700 ring-slate-100",
};

export function MetricCard({ metric, icon: Icon }: MetricCardProps): JSX.Element {
  return (
    <MagicBentoCard tone={metric.tone} className="group p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="truncate text-sm font-bold text-ink-500">{metric.label}</p>
          <p className="mt-2 text-3xl font-bold tracking-normal text-ink-950">{metric.value}</p>
        </div>
        <span className={`hidden size-10 shrink-0 items-center justify-center rounded-md ring-1 transition group-hover:scale-105 sm:inline-flex ${toneClasses[metric.tone]}`}>
          <Icon className="size-5" aria-hidden="true" />
        </span>
      </div>
      <p className="mt-4 truncate text-sm font-semibold text-ink-500">{metric.delta}</p>
    </MagicBentoCard>
  );
}
