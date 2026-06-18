import type { ButtonHTMLAttributes, ReactNode } from "react";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  icon?: ReactNode;
  variant?: "primary" | "secondary" | "ghost";
}

const variantClasses = {
  primary: "bg-ink-950 text-white hover:bg-ink-900",
  secondary: "border border-grid-200 bg-white text-ink-900 hover:bg-grid-50",
  ghost: "text-ink-700 hover:bg-grid-100",
};

export function Button({ children, icon, variant = "secondary", className = "", type = "button", ...props }: ButtonProps): JSX.Element {
  return (
    <button
      type={type}
      className={`inline-flex h-10 items-center justify-center gap-2 rounded-md px-3 text-sm font-semibold transition ${variantClasses[variant]} ${className}`}
      {...props}
    >
      {icon}
      <span className="min-w-0 truncate">{children}</span>
    </button>
  );
}
