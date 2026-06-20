import type { ReactNode } from "react";
import { X } from "lucide-react";

import { Button } from "./Button";

interface ModalProps {
  title: string;
  description: string;
  isOpen: boolean;
  onClose: () => void;
  children: ReactNode;
}

export function Modal({ title, description, isOpen, onClose, children }: ModalProps): JSX.Element | null {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-ink-950/45 px-3 py-4 sm:items-center" role="dialog" aria-modal="true">
      <div className="max-h-[92vh] w-full max-w-2xl overflow-y-auto rounded-lg bg-white shadow-soft">
        <div className="flex items-start justify-between gap-4 border-b border-grid-200 px-5 py-4">
          <div className="min-w-0">
            <h2 className="truncate text-lg font-black text-ink-950">{title}</h2>
            <p className="mt-1 text-sm font-medium text-ink-500">{description}</p>
          </div>
          <Button aria-label="Close modal" className="size-10 shrink-0 px-0" icon={<X className="size-4" aria-hidden="true" />} onClick={onClose}>
            <span className="sr-only">Close modal</span>
          </Button>
        </div>
        {children}
      </div>
    </div>
  );
}
