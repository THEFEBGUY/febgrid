import type { ReactNode } from "react";
import { RotateCcw } from "lucide-react";

import { Button } from "./Button";

interface FilterBarProps {
  children: ReactNode;
  isResetDisabled?: boolean;
  onReset: () => void;
}

interface FilterFieldProps {
  label: string;
  children: ReactNode;
}

export function FilterBar({ children, isResetDisabled = false, onReset }: FilterBarProps): JSX.Element {
  return (
    <div className="border-b border-grid-100 bg-grid-50/60 px-5 py-4">
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
        {children}
        <div className="flex items-end">
          <Button
            className="w-full"
            disabled={isResetDisabled}
            icon={<RotateCcw className="size-4" aria-hidden="true" />}
            onClick={onReset}
          >
            Reset filters
          </Button>
        </div>
      </div>
    </div>
  );
}

export function FilterField({ label, children }: FilterFieldProps): JSX.Element {
  return (
    <label className="block min-w-0">
      <span className="mb-2 block text-xs font-bold uppercase tracking-normal text-ink-500">{label}</span>
      {children}
    </label>
  );
}
