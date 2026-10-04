import { useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { PLAN_KEY, predictYieldsBatch } from "./api";
import AnalyzePanel from "./AnalyzePanel";
import Chart3D from "./Chart3D";
import TextMorph from "./TextMorph";
import TiltedCarousel from "./TiltedCarousel";

const PLAN_MORPH = ["Yield plan", "AI analysis", "All crops"];

type Rec = { crop: string; confidence_pct: number; emoji?: string; season?: string; info?: string };

export default function YieldsCompare() {
  const loc = useLocation();
  const [plan, setPlan] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [batch, setBatch] = useState<any>(null);

  useEffect(() => {
    const fromNav = (loc.state as any) || null;
    if (fromNav?.recommendations) {
      setPlan(fromNav);
      sessionStorage.setItem(PLAN_KEY, JSON.stringify(fromNav));
      return;
    }
    const raw = sessionStorage.getItem(PLAN_KEY);
    if (raw) setPlan(JSON.parse(raw));
  }, [loc.state]);

  useEffect(() => {
    if (!plan?.recommendations?.length) return;
    let cancelled = false;
    (async () => {
      setBusy(true);
      setError(null);
      try {
        const crops = plan.recommendations.map((r: Rec) => r.crop);
        const data = await predictYieldsBatch(plan.lat, plan.lon, crops, plan.season || "Kharif");
        if (!cancelled) setBatch(data);
      } catch (e: any) {
        if (!cancelled) setError(e.message);
      } finally {
        if (!cancelled) setBusy(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [plan]);

  if (!plan) {
    return (
      <>
        <TextMorph texts={PLAN_MORPH} className="hero-morph" />
        <p className="muted">Run crop recommend first, then open yields for those crops.</p>
        <Link className="btn fx-raise" to="/recommend">
          Go to recommend
        </Link>
      </>
    );
  }

  const recs: Rec[] = plan.recommendations || [];
  const fields = plan.fields || {};
  const yields = batch?.yields || [];

  return (
    <>
      <TextMorph texts={PLAN_MORPH} className="hero-morph" />
      <p className="hero-sub">
        {plan.district ? `${plan.district} · ` : ""}
        {plan.lat?.toFixed(4)}, {plan.lon?.toFixed(4)} · {plan.season}
      </p>
      <p className="muted">
        One Sentinel scene set is reused for every recommended crop. Then open AI analysis on each
        card for fertiliser / IPM notes (needs LLM_API_KEY in `.env`).
      </p>

      {busy && <p className="muted">Fetching satellite + scoring {recs.length} crops… this can take a minute.</p>}
      {error && <p className="error">{error}</p>}

      {yields.length > 0 && (
        <TiltedCarousel height={520}>
          <div className="card">
            <h2>Yield comparison</h2>
            <Chart3D
              bars={yields.map((y: any) => ({
                label: y.crop,
                value: y.yield_kg_ha,
              }))}
            />
          </div>
          {yields.map((y: any) => {
            const rec = recs.find((r) => r.crop === y.crop);
            return (
              <div className="card yield-card" key={y.crop}>
                <h2>
                  {rec?.emoji || "🌱"} {y.crop}{" "}
                  {rec ? <span className="src api">{rec.confidence_pct}% suit</span> : null}
                </h2>
                <p className="result-crop" style={{ fontSize: "1.6rem", margin: "0.2rem 0" }}>
                  {Math.round(y.yield_kg_ha).toLocaleString()} {y.unit}
                </p>
                <p className="muted">
                  80% interval {y.interval_80pct?.[0]} – {y.interval_80pct?.[1]} · {y.season}
                </p>
                <AnalyzePanel
                  context={{
                    lat: plan.lat,
                    lon: plan.lon,
                    district: plan.district,
                    crop: y.crop,
                    season: y.season,
                    yield_kg_ha: y.yield_kg_ha,
                    interval_80pct: y.interval_80pct,
                    confidence_pct: rec?.confidence_pct,
                    N: fields.N,
                    P: fields.P,
                    K: fields.K,
                    ph: fields.ph,
                    temperature: fields.temperature,
                    humidity: fields.humidity,
                    rainfall: fields.rainfall,
                    ndvi: y.satellite?.latest_ndvi ?? y.satellite?.ndvi_mean,
                    ndvi_interpretation: y.ndvi_interpretation,
                    climate: y.climate,
                    soil: y.soil,
                  }}
                />
              </div>
            );
          })}
        </TiltedCarousel>
      )}
    </>
  );
}
