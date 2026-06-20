import type { InputHTMLAttributes, ReactNode, SelectHTMLAttributes, TextareaHTMLAttributes } from "react";

interface FieldShellProps {
  label: string;
  children: ReactNode;
}

export function FieldShell({ label, children }: FieldShellProps): JSX.Element {
  return (
    <label className="block min-w-0">
      <span className="mb-2 block text-sm font-bold text-ink-700">{label}</span>
      {children}
    </label>
  );
}

export function TextInput(props: InputHTMLAttributes<HTMLInputElement>): JSX.Element {
  return (
    <input
      className="h-10 w-full rounded-md border border-grid-200 bg-white px-3 text-sm font-medium text-ink-900 shadow-sm placeholder:text-ink-500"
      {...props}
    />
  );
}

export function TextArea(props: TextareaHTMLAttributes<HTMLTextAreaElement>): JSX.Element {
  return (
    <textarea
      className="min-h-24 w-full resize-y rounded-md border border-grid-200 bg-white px-3 py-2 text-sm font-medium text-ink-900 shadow-sm placeholder:text-ink-500"
      {...props}
    />
  );
}

export function SelectInput(props: SelectHTMLAttributes<HTMLSelectElement>): JSX.Element {
  return (
    <select className="h-10 w-full rounded-md border border-grid-200 bg-white px-3 text-sm font-medium text-ink-900 shadow-sm" {...props} />
  );
}
