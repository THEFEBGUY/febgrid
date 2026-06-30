import { useCallback, type CSSProperties, type ReactNode } from "react";

import "./MagicBento.css";

type MagicTone = "blue" | "teal" | "amber" | "green" | "red" | "slate";

interface MagicBentoGridProps {
  children: ReactNode;
  className?: string;
}

interface MagicBentoCardProps {
  children?: ReactNode;
  className?: string;
  tone?: MagicTone;
  eyebrow?: string;
  title?: string;
  description?: string;
  metric?: string;
}

export function MagicBentoGrid({ children, className = "" }: MagicBentoGridProps): JSX.Element {
  return <div className={`magic-bento-grid ${className}`}>{children}</div>;
}

export function MagicBentoCard({
  children,
  className = "",
  tone = "blue",
  eyebrow,
  title,
  description,
  metric,
}: MagicBentoCardProps): JSX.Element {
  const handlePointerMove = useCallback((event: React.PointerEvent<HTMLDivElement>) => {
    const bounds = event.currentTarget.getBoundingClientRect();
    event.currentTarget.style.setProperty("--magic-x", `${event.clientX - bounds.left}px`);
    event.currentTarget.style.setProperty("--magic-y", `${event.clientY - bounds.top}px`);
  }, []);

  const style = { "--magic-x": "50%", "--magic-y": "50%" } as CSSProperties;

  return (
    <div className={`magic-bento-card magic-bento-card--${tone} ${className}`} onPointerMove={handlePointerMove} style={style}>
      <div className="magic-bento-card__shine" aria-hidden="true" />
      <div className="magic-bento-card__content">
        {eyebrow ? <p className="magic-bento-card__eyebrow">{eyebrow}</p> : null}
        {metric ? <p className="magic-bento-card__metric">{metric}</p> : null}
        {title ? <h3 className="magic-bento-card__title">{title}</h3> : null}
        {description ? <p className="magic-bento-card__description">{description}</p> : null}
        {children}
      </div>
    </div>
  );
}
