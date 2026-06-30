import { AlertTriangle, Inbox, Loader2 } from "lucide-react";

import { Button } from "./Button";

interface LoadingStateProps {
  label?: string;
}

interface EmptyStateProps {
  title: string;
  description: string;
  action?: JSX.Element;
}

interface ErrorStateProps {
  message: string;
  onRetry?: () => void;
}

export function LoadingState({ label = "Loading workspace data" }: LoadingStateProps): JSX.Element {
  return (
    <div className="flex min-h-56 flex-col items-center justify-center gap-4 px-5 py-10 text-center">
      <div className="flex size-14 items-center justify-center rounded-lg border border-grid-200 bg-white shadow-sm">
        <Loader2 className="size-6 animate-spin text-brand-600" aria-hidden="true" />
      </div>
      <div className="w-full max-w-xs space-y-2">
        <p className="text-sm font-bold text-ink-700">{label}</p>
        <div className="febgrid-skeleton mx-auto h-2 w-40 rounded-full" aria-hidden="true" />
      </div>
    </div>
  );
}

export function EmptyState({ title, description, action }: EmptyStateProps): JSX.Element {
  return (
    <div className="febgrid-empty-state flex min-h-56 flex-col items-center justify-center px-5 py-12 text-center">
      <span className="flex size-14 items-center justify-center rounded-lg border border-grid-200 bg-grid-50 text-ink-700 shadow-sm">
        <Inbox className="size-5" aria-hidden="true" />
      </span>
      <h3 className="mt-4 text-base font-bold text-ink-950">{title}</h3>
      <p className="mt-2 max-w-md text-sm font-medium text-ink-500">{description}</p>
      {action ? <div className="mt-5">{action}</div> : null}
    </div>
  );
}

export function ErrorState({ message, onRetry }: ErrorStateProps): JSX.Element {
  return (
    <div className="febgrid-empty-state flex min-h-56 flex-col items-center justify-center px-5 py-12 text-center">
      <span className="flex size-14 items-center justify-center rounded-lg border border-rose-200 bg-rose-50 text-rose-700 shadow-sm">
        <AlertTriangle className="size-5" aria-hidden="true" />
      </span>
      <h3 className="mt-4 text-base font-bold text-ink-950">Unable to load data</h3>
      <p className="mt-2 max-w-md text-sm font-medium text-ink-500">{message}</p>
      {onRetry ? (
        <Button className="mt-5" onClick={onRetry}>
          Retry
        </Button>
      ) : null}
    </div>
  );
}
