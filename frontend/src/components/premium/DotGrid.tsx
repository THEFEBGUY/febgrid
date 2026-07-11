import { useCallback, useEffect, useMemo, useRef } from "react";
import { gsap } from "gsap";
import { InertiaPlugin } from "gsap/InertiaPlugin";

import "./DotGrid.css";

gsap.registerPlugin(InertiaPlugin);

interface Dot {
  cx: number;
  cy: number;
  xOffset: number;
  yOffset: number;
  inertiaApplied: boolean;
}

interface PointerState {
  x: number;
  y: number;
  vx: number;
  vy: number;
  speed: number;
  lastTime: number;
  lastX: number;
  lastY: number;
}

interface DotGridProps {
  dotSize?: number;
  gap?: number;
  baseColor?: string;
  activeColor?: string;
  proximity?: number;
  speedTrigger?: number;
  shockRadius?: number;
  shockStrength?: number;
  maxSpeed?: number;
  resistance?: number;
  returnDuration?: number;
  className?: string;
}

function hexToRgb(hex: string): { r: number; g: number; b: number } {
  const match = hex.match(/^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i);
  if (!match) return { r: 0, g: 0, b: 0 };
  return { r: Number.parseInt(match[1], 16), g: Number.parseInt(match[2], 16), b: Number.parseInt(match[3], 16) };
}

function throttle<T extends (...args: never[]) => void>(callback: T, limit: number): T {
  let lastCall = 0;
  return ((...args: Parameters<T>) => {
    const now = performance.now();
    if (now - lastCall >= limit) {
      lastCall = now;
      callback(...args);
    }
  }) as T;
}

export function DotGrid({
  dotSize = 5,
  gap = 15,
  baseColor = "#2F293A",
  activeColor = "#5227FF",
  proximity = 120,
  speedTrigger = 100,
  shockRadius = 250,
  shockStrength = 5,
  maxSpeed = 5000,
  resistance = 750,
  returnDuration = 1.5,
  className = "",
}: DotGridProps): JSX.Element {
  const wrapperRef = useRef<HTMLDivElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const dotsRef = useRef<Dot[]>([]);
  const pointerRef = useRef<PointerState>({ x: -10_000, y: -10_000, vx: 0, vy: 0, speed: 0, lastTime: 0, lastX: 0, lastY: 0 });
  const reducedMotionRef = useRef(false);

  const baseRgb = useMemo(() => hexToRgb(baseColor), [baseColor]);
  const activeRgb = useMemo(() => hexToRgb(activeColor), [activeColor]);
  const circlePath = useMemo(() => {
    const path = new Path2D();
    path.arc(0, 0, dotSize / 2, 0, Math.PI * 2);
    return path;
  }, [dotSize]);

  const buildGrid = useCallback(() => {
    const wrapper = wrapperRef.current;
    const canvas = canvasRef.current;
    if (!wrapper || !canvas) return;

    const { width, height } = wrapper.getBoundingClientRect();
    if (!width || !height) return;
    const devicePixelRatio = Math.min(window.devicePixelRatio || 1, 1.5);
    canvas.width = Math.round(width * devicePixelRatio);
    canvas.height = Math.round(height * devicePixelRatio);
    const context = canvas.getContext("2d");
    if (!context) return;
    context.setTransform(devicePixelRatio, 0, 0, devicePixelRatio, 0, 0);

    const cell = dotSize + gap;
    const columns = Math.floor((width + gap) / cell);
    const rows = Math.floor((height + gap) / cell);
    const gridWidth = cell * columns - gap;
    const gridHeight = cell * rows - gap;
    const startX = (width - gridWidth) / 2 + dotSize / 2;
    const startY = (height - gridHeight) / 2 + dotSize / 2;
    const dots: Dot[] = [];

    for (let row = 0; row < rows; row += 1) {
      for (let column = 0; column < columns; column += 1) {
        dots.push({ cx: startX + column * cell, cy: startY + row * cell, xOffset: 0, yOffset: 0, inertiaApplied: false });
      }
    }
    dotsRef.current = dots;
  }, [dotSize, gap]);

  useEffect(() => {
    const mediaQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
    const updatePreference = (): void => {
      reducedMotionRef.current = mediaQuery.matches;
    };
    updatePreference();
    mediaQuery.addEventListener("change", updatePreference);
    return () => mediaQuery.removeEventListener("change", updatePreference);
  }, []);

  useEffect(() => {
    buildGrid();
    const observer = new ResizeObserver(buildGrid);
    if (wrapperRef.current) observer.observe(wrapperRef.current);
    return () => observer.disconnect();
  }, [buildGrid]);

  useEffect(() => {
    const proximitySquared = proximity * proximity;
    let animationFrame = 0;

    const draw = (): void => {
      const canvas = canvasRef.current;
      const context = canvas?.getContext("2d");
      if (!canvas || !context) return;
      const ratio = Math.min(window.devicePixelRatio || 1, 1.5);
      context.clearRect(0, 0, canvas.width / ratio, canvas.height / ratio);
      const pointer = pointerRef.current;

      for (const dot of dotsRef.current) {
        const x = dot.cx + dot.xOffset;
        const y = dot.cy + dot.yOffset;
        const dx = dot.cx - pointer.x;
        const dy = dot.cy - pointer.y;
        const distanceSquared = dx * dx + dy * dy;
        let color = baseColor;
        if (!reducedMotionRef.current && distanceSquared <= proximitySquared) {
          const proximityFactor = 1 - Math.sqrt(distanceSquared) / proximity;
          color = `rgb(${Math.round(baseRgb.r + (activeRgb.r - baseRgb.r) * proximityFactor)}, ${Math.round(baseRgb.g + (activeRgb.g - baseRgb.g) * proximityFactor)}, ${Math.round(baseRgb.b + (activeRgb.b - baseRgb.b) * proximityFactor)})`;
        }
        context.save();
        context.translate(x, y);
        context.fillStyle = color;
        context.fill(circlePath);
        context.restore();
      }
      animationFrame = window.requestAnimationFrame(draw);
    };

    draw();
    return () => window.cancelAnimationFrame(animationFrame);
  }, [activeRgb, baseColor, baseRgb, circlePath, proximity]);

  useEffect(() => {
    const onMove = (event: MouseEvent): void => {
      if (reducedMotionRef.current || !canvasRef.current) return;
      const now = performance.now();
      const pointer = pointerRef.current;
      const deltaTime = pointer.lastTime ? now - pointer.lastTime : 16;
      let velocityX = ((event.clientX - pointer.lastX) / deltaTime) * 1000;
      let velocityY = ((event.clientY - pointer.lastY) / deltaTime) * 1000;
      let speed = Math.hypot(velocityX, velocityY);
      if (speed > maxSpeed) {
        const scale = maxSpeed / speed;
        velocityX *= scale;
        velocityY *= scale;
        speed = maxSpeed;
      }
      const rect = canvasRef.current.getBoundingClientRect();
      pointer.lastTime = now;
      pointer.lastX = event.clientX;
      pointer.lastY = event.clientY;
      pointer.x = event.clientX - rect.left;
      pointer.y = event.clientY - rect.top;
      pointer.vx = velocityX;
      pointer.vy = velocityY;
      pointer.speed = speed;

      for (const dot of dotsRef.current) {
        const distance = Math.hypot(dot.cx - pointer.x, dot.cy - pointer.y);
        if (speed <= speedTrigger || distance >= proximity || dot.inertiaApplied) continue;
        dot.inertiaApplied = true;
        gsap.killTweensOf(dot);
        gsap.to(dot, {
          inertia: { xOffset: dot.cx - pointer.x + velocityX * 0.005, yOffset: dot.cy - pointer.y + velocityY * 0.005, resistance },
          onComplete: () => {
            gsap.to(dot, { xOffset: 0, yOffset: 0, duration: returnDuration, ease: "elastic.out(1,0.75)" });
            dot.inertiaApplied = false;
          },
        });
      }
    };

    const onClick = (event: MouseEvent): void => {
      if (reducedMotionRef.current || !canvasRef.current) return;
      const rect = canvasRef.current.getBoundingClientRect();
      const clickX = event.clientX - rect.left;
      const clickY = event.clientY - rect.top;
      for (const dot of dotsRef.current) {
        const distance = Math.hypot(dot.cx - clickX, dot.cy - clickY);
        if (distance >= shockRadius || dot.inertiaApplied) continue;
        dot.inertiaApplied = true;
        gsap.killTweensOf(dot);
        const falloff = 1 - distance / shockRadius;
        gsap.to(dot, {
          inertia: { xOffset: (dot.cx - clickX) * shockStrength * falloff, yOffset: (dot.cy - clickY) * shockStrength * falloff, resistance },
          onComplete: () => {
            gsap.to(dot, { xOffset: 0, yOffset: 0, duration: returnDuration, ease: "elastic.out(1,0.75)" });
            dot.inertiaApplied = false;
          },
        });
      }
    };

    const throttledMove = throttle(onMove, 50);
    window.addEventListener("mousemove", throttledMove, { passive: true });
    window.addEventListener("click", onClick, { passive: true });
    return () => {
      window.removeEventListener("mousemove", throttledMove);
      window.removeEventListener("click", onClick);
      gsap.killTweensOf(dotsRef.current);
    };
  }, [maxSpeed, proximity, resistance, returnDuration, shockRadius, shockStrength, speedTrigger]);

  return (
    <section aria-hidden="true" className={`dot-grid ${className}`}>
      <div ref={wrapperRef} className="dot-grid__wrap">
        <canvas ref={canvasRef} className="dot-grid__canvas" />
      </div>
    </section>
  );
}
