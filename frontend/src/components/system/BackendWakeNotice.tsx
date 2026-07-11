import { useEffect, useState } from "react";

import { API_WAKE_EVENT } from "../../services/api";


export function BackendWakeNotice(): JSX.Element | null {
  const [isWaking, setIsWaking] = useState(false);

  useEffect(() => {
    const handleWakeState = (event: Event): void => {
      const detail = (event as CustomEvent<{ state?: string }>).detail;
      setIsWaking(detail?.state === "waking");
    };
    window.addEventListener(API_WAKE_EVENT, handleWakeState);
    return () => window.removeEventListener(API_WAKE_EVENT, handleWakeState);
  }, []);

  if (!isWaking) return null;

  return (
    <div className="pointer-events-none fixed inset-x-0 top-3 z-[100] flex justify-center px-4" role="status" aria-live="polite">
      <div className="rounded-md border border-amber-300 bg-amber-50/95 px-4 py-2 text-sm font-bold text-amber-800 shadow-premium backdrop-blur dark:border-amber-700 dark:bg-amber-950/90 dark:text-amber-100">
        FebGrid's service is waking up. This first request can take about a minute on the free demo tier.
      </div>
    </div>
  );
}
