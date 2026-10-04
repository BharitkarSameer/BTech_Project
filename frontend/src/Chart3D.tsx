import { useRef, useState } from "react";

export type ChartBar = {
  label: string;
  value: number;
  color?: string;
};

const PALETTE = ["#3dff9a", "#5ce1ff", "#c084fc", "#ffb020", "#ff5c8a", "#7cff6b", "#4d8bff"];

export default function Chart3D({
  bars,
  max,
  unit = "",
}: {
  bars: ChartBar[];
  max?: number;
  unit?: string;
}) {
  const wrap = useRef<HTMLDivElement>(null);
  const [rot, setRot] = useState({ x: 62, z: -32 });
  const peak = max || Math.max(...bars.map((b) => b.value), 1);

  function tilt(clientX: number, clientY: number) {
    const el = wrap.current;
    if (!el) return;
    const r = el.getBoundingClientRect();
    const nx = (clientX - r.left) / r.width - 0.5;
    const ny = (clientY - r.top) / r.height - 0.5;
    setRot({ x: 58 + ny * 16, z: -32 + nx * 28 });
  }

  return (
    <div
      className="chart3d-wrap"
      ref={wrap}
      onMouseMove={(e) => tilt(e.clientX, e.clientY)}
      onMouseLeave={() => setRot({ x: 62, z: -32 })}
      onTouchMove={(e) => {
        const t = e.touches[0];
        if (t) tilt(t.clientX, t.clientY);
      }}
    >
      <div className="chart3d-stage">
        <div
          className="chart3d"
          style={{
            transform: `rotateX(${rot.x}deg) rotateZ(${rot.z}deg)`,
          }}
        >
          <div className="chart3d-floor" />
          <div className="chart3d-bars">
            {bars.map((b, i) => {
              const h = Math.max(8, (b.value / peak) * 160);
              const color = b.color || PALETTE[i % PALETTE.length];
              return (
                <div className="bar3d" key={b.label} style={{ ["--h" as string]: `${h}px`, ["--c" as string]: color }}>
                  <div className="bar3d-face bar3d-front" />
                  <div className="bar3d-face bar3d-back" />
                  <div className="bar3d-face bar3d-left" />
                  <div className="bar3d-face bar3d-right" />
                  <div className="bar3d-face bar3d-top" />
                  <span className="bar3d-val">
                    {Number.isInteger(b.value) ? b.value : b.value.toFixed(1)}
                    {unit}
                  </span>
                  <span className="bar3d-lab">{b.label}</span>
                </div>
              );
            })}
          </div>
        </div>
      </div>
      <p className="chart3d-hint">Drag / move to orbit the chart</p>
    </div>
  );
}
