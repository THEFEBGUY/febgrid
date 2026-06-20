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
    <div className="flex min-h-56 flex-col items-center justify-center gap-3 px-5 py-10 text-center">
      <Loader2 className="size-6 animate-spin text-ink-500" aria-hidden="true" />
      <p className="text-sm font-semibold text-ink-500">{label}</p>
    </div>
  );
}

export function EmptyState({ title, description, action }: EmptyStateProps): JSX.Element {
  return (
    <div className="flex min-h-56 flex-col items-center justify-center px-5 py-10 text-center">
      <span className="flex size-12 items-center justify-center rounded-lg bg-grid-100 text-ink-700">
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
    <div className="flex min-h-56 flex-col items-center justify-center px-5 py-10 text-center">
      <span className="flex size-12 items-center justify-center rounded-lg bg-rose-50 text-rose-700">
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
