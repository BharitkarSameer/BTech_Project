import { Children, type ReactNode, useMemo, useState } from "react";

type Props = {
  children: ReactNode;
  height?: number;
};

/** Yudiz “Expandable Animated Card Slider” (CodePen wvzrPoj). */
export default function TiltedCarousel({ children, height = 420 }: Props) {
  const items = useMemo(() => Children.toArray(children).filter(Boolean), [children]);
  const [active, setActive] = useState(0);
  if (items.length === 0) return null;

  return (
    <div className="expand-wrap">
      <div className="expand-track" style={{ height }}>
        {items.map((child, i) => {
          const open = i === active;
          return (
            <article
              key={i}
              className={`expand-card${open ? " is-open" : ""}`}
              style={{ flexGrow: open ? 12 : 1 }}
              onClick={() => {
                if (!open) setActive(i);
              }}
            >
              <span className="expand-icon">{i + 1}</span>
              <div className="expand-body">{child}</div>
            </article>
          );
        })}
      </div>
    </div>
  );
}
