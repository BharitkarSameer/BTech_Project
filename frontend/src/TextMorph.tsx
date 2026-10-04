import { useEffect, useId, useRef } from "react";

type Props = {
  texts: string[];
  className?: string;
};

/** Valgo Text Morph (CodePen PowZaNY): dual-layer blur + SVG threshold. */
export default function TextMorph({ texts, className = "" }: Props) {
  const rawId = useId().replace(/:/g, "");
  const filterId = `threshold-${rawId}`;
  const t1 = useRef<HTMLSpanElement>(null);
  const t2 = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    const elts = { text1: t1.current, text2: t2.current };
    if (!elts.text1 || !elts.text2 || texts.length === 0) return;

    const morphTime = 1;
    const cooldownTime = 0.35;
    let textIndex = texts.length - 1;
    let time = new Date();
    let morph = 0;
    let cooldown = cooldownTime;
    let raf = 0;
    let live = true;

    elts.text1.textContent = texts[textIndex % texts.length];
    elts.text2.textContent = texts[(textIndex + 1) % texts.length];

    function setMorph(fraction: number) {
      if (!elts.text1 || !elts.text2) return;
      elts.text2.style.filter = `blur(${Math.min(8 / fraction - 8, 100)}px)`;
      elts.text2.style.opacity = `${Math.pow(fraction, 0.4) * 100}%`;
      fraction = 1 - fraction;
      elts.text1.style.filter = `blur(${Math.min(8 / fraction - 8, 100)}px)`;
      elts.text1.style.opacity = `${Math.pow(fraction, 0.4) * 100}%`;
      elts.text1.textContent = texts[textIndex % texts.length];
      elts.text2.textContent = texts[(textIndex + 1) % texts.length];
    }

    function doMorph() {
      morph -= cooldown;
      cooldown = 0;
      let fraction = morph / morphTime;
      if (fraction > 1) {
        cooldown = cooldownTime;
        fraction = 1;
      }
      setMorph(fraction);
    }

    function doCooldown() {
      morph = 0;
      if (!elts.text2 || !elts.text1) return;
      elts.text2.style.filter = "";
      elts.text2.style.opacity = "100%";
      elts.text1.style.filter = "";
      elts.text1.style.opacity = "0%";
    }

    function animate() {
      if (!live) return;
      raf = requestAnimationFrame(animate);
      const newTime = new Date();
      const shouldIncrementIndex = cooldown > 0;
      const dt = (newTime.getTime() - time.getTime()) / 1000;
      time = newTime;
      cooldown -= dt;
      if (cooldown <= 0) {
        if (shouldIncrementIndex) textIndex += 1;
        doMorph();
      } else {
        doCooldown();
      }
    }

    animate();
    return () => {
      live = false;
      cancelAnimationFrame(raf);
    };
  }, [texts]);

  return (
    <div
      className={`text-morph ${className}`}
      style={{ filter: `url(#${filterId}) blur(0.6px)` }}
    >
      <span ref={t1} className="text-morph-layer" />
      <span ref={t2} className="text-morph-layer" />
      <svg className="text-morph-svg" aria-hidden="true">
        <defs>
          <filter id={filterId}>
            <feColorMatrix
              in="SourceGraphic"
              type="matrix"
              values="1 0 0 0 0  0 1 0 0 0  0 0 1 0 0  0 0 0 255 -140"
            />
          </filter>
        </defs>
      </svg>
    </div>
  );
}
