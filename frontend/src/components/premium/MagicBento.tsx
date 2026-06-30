import { useCallback, useEffect, useRef, useState, type CSSProperties, type ReactNode } from "react";

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
  enableStars?: boolean;
  enableSpotlight?: boolean;
  enableBorderGlow?: boolean;
  enableTilt?: boolean;
  enableMagnetism?: boolean;
  clickEffect?: boolean;
  spotlightRadius?: number;
  glowColor?: string;
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
  enableStars = true,
  enableSpotlight = true,
  enableBorderGlow = true,
  enableTilt = true,
  enableMagnetism = true,
  clickEffect = true,
  spotlightRadius = 300,
  glowColor = "132 0 255",
}: MagicBentoCardProps): JSX.Element {
  const rippleTimeoutRef = useRef<number | null>(null);
  const [isRippling, setIsRippling] = useState(false);

  useEffect(() => {
    return () => {
      if (rippleTimeoutRef.current !== null) {
        window.clearTimeout(rippleTimeoutRef.current);
      }
    };
  }, []);

  const handlePointerMove = useCallback((event: React.PointerEvent<HTMLDivElement>) => {
    const bounds = event.currentTarget.getBoundingClientRect();
    const localX = event.clientX - bounds.left;
    const localY = event.clientY - bounds.top;
    const relativeX = bounds.width > 0 ? localX / bounds.width : 0.5;
    const relativeY = bounds.height > 0 ? localY / bounds.height : 0.5;

    event.currentTarget.style.setProperty("--magic-x", `${localX}px`);
    event.currentTarget.style.setProperty("--magic-y", `${localY}px`);
    event.currentTarget.style.setProperty("--glow-x", `${relativeX * 100}%`);
    event.currentTarget.style.setProperty("--glow-y", `${relativeY * 100}%`);
    event.currentTarget.style.setProperty("--glow-intensity", "1");

    if (enableTilt) {
      event.currentTarget.style.setProperty("--magic-rotate-x", `${(0.5 - relativeY) * 5}deg`);
      event.currentTarget.style.setProperty("--magic-rotate-y", `${(relativeX - 0.5) * 6}deg`);
    }

    if (enableMagnetism) {
      event.currentTarget.style.setProperty("--magic-shift-x", `${(relativeX - 0.5) * 5}px`);
      event.currentTarget.style.setProperty("--magic-shift-y", `${(relativeY - 0.5) * 5}px`);
    }
  }, [enableMagnetism, enableTilt]);

  const handlePointerLeave = useCallback((event: React.PointerEvent<HTMLDivElement>) => {
    event.currentTarget.style.setProperty("--glow-intensity", "0");
    event.currentTarget.style.setProperty("--magic-rotate-x", "0deg");
    event.currentTarget.style.setProperty("--magic-rotate-y", "0deg");
    event.currentTarget.style.setProperty("--magic-shift-x", "0px");
    event.currentTarget.style.setProperty("--magic-shift-y", "0px");
  }, []);

  const handlePointerDown = useCallback((event: React.PointerEvent<HTMLDivElement>) => {
    if (!clickEffect) return;
    const bounds = event.currentTarget.getBoundingClientRect();
    event.currentTarget.style.setProperty("--ripple-x", `${event.clientX - bounds.left}px`);
    event.currentTarget.style.setProperty("--ripple-y", `${event.clientY - bounds.top}px`);

    if (rippleTimeoutRef.current !== null) {
      window.clearTimeout(rippleTimeoutRef.current);
    }
    setIsRippling(false);
    window.requestAnimationFrame(() => setIsRippling(true));
    rippleTimeoutRef.current = window.setTimeout(() => setIsRippling(false), 700);
  }, [clickEffect]);

  const normalizedGlowColor = glowColor.replace(/,/g, " ");

  const style = {
    "--magic-x": "50%",
    "--magic-y": "50%",
    "--magic-glow": normalizedGlowColor,
    "--glow-x": "50%",
    "--glow-y": "50%",
    "--glow-intensity": "0",
    "--glow-radius": `${spotlightRadius}px`,
    "--magic-rotate-x": "0deg",
    "--magic-rotate-y": "0deg",
    "--magic-shift-x": "0px",
    "--magic-shift-y": "0px",
    "--magic-lift": "0px",
    "--ripple-x": "50%",
    "--ripple-y": "50%",
  } as CSSProperties;

  const cardClasses = [
    "magic-bento-card",
    `magic-bento-card--${tone}`,
    enableStars ? "magic-bento-card--stars" : "",
    enableSpotlight ? "magic-bento-card--spotlight" : "",
    enableBorderGlow ? "magic-bento-card--border-glow" : "",
    enableTilt ? "magic-bento-card--tilt" : "",
    enableMagnetism ? "magic-bento-card--magnetic" : "",
    clickEffect ? "magic-bento-card--clickable" : "",
    isRippling ? "magic-bento-card--rippling" : "",
    className,
  ].filter(Boolean).join(" ");

  return (
    <div className={cardClasses} onPointerDown={handlePointerDown} onPointerLeave={handlePointerLeave} onPointerMove={handlePointerMove} style={style}>
      <div className="magic-bento-card__shine" aria-hidden="true" />
      <div className="magic-bento-card__ripple" aria-hidden="true" />
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
