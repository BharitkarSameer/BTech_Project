import { useEffect, useRef } from "react";

type Particle = {
  x: number;
  y: number;
  vx: number;
  vy: number;
  r: number;
};

/** Marco Guglielmelli CodePen ExGYae — connected-dot particle field. */
export default function ParticleBackground() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const mouse = { x: -9999, y: -9999 };
    let width = 0;
    let height = 0;
    let particles: Particle[] = [];
    let raf = 0;
    let running = true;

    function count() {
      return Math.max(55, Math.min(110, Math.floor((width * height) / 14000)));
    }

    function spawn(): Particle {
      return {
        x: Math.random() * width,
        y: Math.random() * height,
        vx: (Math.random() - 0.5) * 1.15,
        vy: (Math.random() - 0.5) * 1.15,
        r: Math.random() * 2.2 + 1.3,
      };
    }

    function size() {
      width = window.innerWidth;
      height = window.innerHeight;
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      canvas!.width = width * dpr;
      canvas!.height = height * dpr;
      canvas!.style.width = `${width}px`;
      canvas!.style.height = `${height}px`;
      ctx!.setTransform(dpr, 0, 0, dpr, 0, 0);
      particles = Array.from({ length: count() }, spawn);
    }

    function mouseMove(e: MouseEvent) {
      mouse.x = e.clientX;
      mouse.y = e.clientY;
    }

    function mouseLeave() {
      mouse.x = -9999;
      mouse.y = -9999;
    }

    function touchMove(e: TouchEvent) {
      const t = e.touches[0];
      if (!t) return;
      mouse.x = t.clientX;
      mouse.y = t.clientY;
    }

    function animate() {
      if (!running) return;
      ctx!.clearRect(0, 0, width, height);

      for (const p of particles) {
        p.x += p.vx;
        p.y += p.vy;
        if (p.x < 0 || p.x > width) p.vx *= -1;
        if (p.y < 0 || p.y > height) p.vy *= -1;

        const dx = p.x - mouse.x;
        const dy = p.y - mouse.y;
        const d2 = dx * dx + dy * dy;
        if (d2 < 16000) {
          p.x += dx * 0.012;
          p.y += dy * 0.012;
        }

        ctx!.beginPath();
        ctx!.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        ctx!.fillStyle = "rgba(255, 255, 255, 0.78)";
        ctx!.fill();
      }

      const link = 150;
      ctx!.lineWidth = 1;
      for (let i = 0; i < particles.length; i++) {
        const a = particles[i];
        for (let j = i + 1; j < particles.length; j++) {
          const b = particles[j];
          const dx = a.x - b.x;
          const dy = a.y - b.y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist > link) continue;
          const alpha = 0.42 * (1 - dist / link);
          ctx!.strokeStyle = `rgba(180, 220, 255, ${alpha})`;
          ctx!.beginPath();
          ctx!.moveTo(a.x, a.y);
          ctx!.lineTo(b.x, b.y);
          ctx!.stroke();
        }
      }

      raf = requestAnimationFrame(animate);
    }

    size();
    window.addEventListener("resize", size);
    window.addEventListener("mousemove", mouseMove);
    window.addEventListener("mouseleave", mouseLeave);
    window.addEventListener("touchmove", touchMove, { passive: true });
    animate();

    return () => {
      running = false;
      cancelAnimationFrame(raf);
      window.removeEventListener("resize", size);
      window.removeEventListener("mousemove", mouseMove);
      window.removeEventListener("mouseleave", mouseLeave);
      window.removeEventListener("touchmove", touchMove);
    };
  }, []);

  return (
    <div className="particle-bg" aria-hidden="true">
      <canvas ref={canvasRef} />
    </div>
  );
}
