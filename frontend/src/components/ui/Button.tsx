import { Children, isValidElement, type ButtonHTMLAttributes, type ReactElement, type ReactNode } from "react";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  icon?: ReactNode;
  variant?: "primary" | "secondary" | "ghost" | "danger";
}

const variantClasses = {
  primary: "border border-brand-600 bg-brand-600 text-white shadow-button hover:bg-brand-700",
  secondary: "border border-grid-200 bg-white text-ink-900 shadow-sm hover:border-grid-300 hover:bg-grid-50 hover:shadow-button",
  ghost: "border border-transparent text-ink-700 hover:bg-grid-100 hover:text-ink-950",
  danger: "border border-rose-200 bg-rose-50 text-rose-700 hover:bg-rose-100",
};

function isSrOnlyElement(child: ReactNode): child is ReactElement<{ className?: string }> {
  if (!isValidElement<{ className?: string }>(child)) return false;
  return typeof child.props.className === "string" && child.props.className.split(/\s+/).includes("sr-only");
}

function hasVisibleContent(children: ReactNode): boolean {
  return Children.toArray(children).some((child) => {
    if (typeof child === "string") return child.trim().length > 0;
    if (typeof child === "number") return true;
    if (isSrOnlyElement(child)) return false;
    return child !== null && child !== undefined;
  });
}

export function Button({ children, icon, variant = "secondary", className = "", title, type = "button", ...props }: ButtonProps): JSX.Element {
  const ariaLabel = typeof props["aria-label"] === "string" ? props["aria-label"] : undefined;
  const resolvedTitle = title ?? ariaLabel;
  const hasVisibleLabel = hasVisibleContent(children);
  const layoutClasses = icon && !hasVisibleLabel ? "size-10 gap-0 p-0" : "h-10 gap-2.5 px-3.5";

  return (
    <button
      type={type}
      title={resolvedTitle}
      className={`inline-flex items-center justify-center rounded-md text-sm font-bold transition duration-150 ease-out active:translate-y-px focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-600 disabled:cursor-not-allowed disabled:translate-y-0 disabled:opacity-55 disabled:shadow-none ${layoutClasses} ${variantClasses[variant]} ${className}`}
      {...props}
    >
      {icon ? (
        <span className="febgrid-button-icon flex shrink-0 items-center justify-center text-current" aria-hidden="true">
          {icon}
        </span>
      ) : null}
      {hasVisibleLabel ? <span className="min-w-0 truncate">{children}</span> : children}
    </button>
  );
}
