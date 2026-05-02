"use client";

import { useEffect } from "react";
import Lenis from "lenis";

/**
 * Wraps the page in Lenis smooth-scroll. Drop into the root layout (or
 * just the marketing site) to get that "buttery" parallax scroll feel.
 *
 * Lenis intercepts wheel/touch input and animates window.scrollY itself,
 * which is what framer-motion's useScroll already listens to — no other
 * wiring required.
 */
export function SmoothScroll() {
  useEffect(() => {
    const lenis = new Lenis({
      duration: 1.15,
      // Custom ease-out: snappy at the start, glides at the end.
      easing: (t: number) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
      wheelMultiplier: 1,
      touchMultiplier: 1.5,
      lerp: 0.1,
    });

    let raf = 0;
    const tick = (time: number) => {
      lenis.raf(time);
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);

    return () => {
      cancelAnimationFrame(raf);
      lenis.destroy();
    };
  }, []);

  return null;
}
