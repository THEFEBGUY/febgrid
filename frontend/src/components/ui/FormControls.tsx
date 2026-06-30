import type { InputHTMLAttributes, ReactNode, SelectHTMLAttributes, TextareaHTMLAttributes } from "react";

interface FieldShellProps {
  label: string;
  children: ReactNode;
  helperText?: string;
}

const controlClasses =
  "w-full rounded-md border border-grid-200 bg-white text-sm font-semibold text-ink-900 shadow-sm transition placeholder:text-ink-400 hover:border-grid-300 focus:border-brand-500 focus:outline-none focus:ring-4 focus:ring-brand-100 disabled:cursor-not-allowed disabled:bg-grid-100 disabled:text-ink-500 read-only:bg-grid-50";

export function FieldShell({ label, children, helperText }: FieldShellProps): JSX.Element {
  return (
    <label className="block min-w-0">
      <span className="mb-2 block text-sm font-bold text-ink-700">{label}</span>
      {children}
      {helperText ? <span className="mt-1.5 block text-xs font-semibold text-ink-500">{helperText}</span> : null}
    </label>
  );
}

export function TextInput({ className = "", ...props }: InputHTMLAttributes<HTMLInputElement>): JSX.Element {
  return <input className={`h-10 px-3 ${controlClasses} ${className}`} {...props} />;
}

export function TextArea({ className = "", ...props }: TextareaHTMLAttributes<HTMLTextAreaElement>): JSX.Element {
  return <textarea className={`min-h-24 resize-y px-3 py-2 ${controlClasses} ${className}`} {...props} />;
}

export function SelectInput({ className = "", ...props }: SelectHTMLAttributes<HTMLSelectElement>): JSX.Element {
  return <select className={`h-10 px-3 ${controlClasses} ${className}`} {...props} />;
}
