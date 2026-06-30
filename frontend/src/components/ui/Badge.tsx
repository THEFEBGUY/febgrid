interface BadgeProps {
  label: string;
  tone?: "blue" | "green" | "amber" | "red" | "teal" | "slate";
}

const toneClasses = {
  blue: "border-blue-200 bg-blue-50 text-blue-700",
  green: "border-green-200 bg-green-50 text-green-700",
  amber: "border-amber-200 bg-amber-50 text-amber-700",
  red: "border-rose-200 bg-rose-50 text-rose-700",
  teal: "border-teal-200 bg-teal-50 text-teal-700",
  slate: "border-slate-200 bg-slate-50 text-slate-700",
};

export function Badge({ label, tone = "slate" }: BadgeProps): JSX.Element {
  return (
    <span
      className={`inline-flex h-7 max-w-full items-center rounded-md border px-2.5 text-xs font-bold leading-none shadow-sm ${toneClasses[tone]}`}
    >
      <span className="truncate">{label}</span>
    </span>
  );
}
