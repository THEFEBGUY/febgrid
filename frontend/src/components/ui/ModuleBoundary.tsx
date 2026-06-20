import type { ReactNode } from "react";

import { EmptyState, ErrorState, LoadingState } from "./States";

interface ModuleBoundaryProps {
  isLoading: boolean;
  error: string | null;
  isEmpty: boolean;
  emptyTitle: string;
  emptyDescription: string;
  emptyAction?: JSX.Element;
  onRetry: () => Promise<void>;
  children: ReactNode;
}

export function ModuleBoundary({
  isLoading,
  error,
  isEmpty,
  emptyTitle,
  emptyDescription,
  emptyAction,
  onRetry,
  children,
}: ModuleBoundaryProps): JSX.Element {
  if (isLoading) {
    return <LoadingState />;
  }

  if (error) {
    return <ErrorState message={error} onRetry={onRetry} />;
  }

  if (isEmpty) {
    return <EmptyState title={emptyTitle} description={emptyDescription} action={emptyAction} />;
  }

  return <>{children}</>;
}
