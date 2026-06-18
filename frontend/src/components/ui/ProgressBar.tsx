interface ProgressBarProps {
  value: number;
}

export function ProgressBar({ value }: ProgressBarProps): JSX.Element {
  const normalizedValue = Math.max(0, Math.min(100, value));

  return (
    <div className="flex min-w-40 items-center gap-3">
      <div className="h-2 w-full overflow-hidden rounded-full bg-grid-100">
        <div className="h-full rounded-full bg-ink-950" style={{ width: `${normalizedValue}%` }} />
      </div>
      <span className="w-10 text-right text-xs font-bold text-ink-500">{normalizedValue}%</span>
    </div>
  );
}
