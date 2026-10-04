import { useEffect, useState } from "react";
import { fetchCrops, predictYield, type CropInfo } from "./api";
import AnalyzePanel from "./AnalyzePanel";
import Chart3D from "./Chart3D";
import FarmMap from "./FarmMap";
import TextMorph from "./TextMorph";
import TiltedCarousel from "./TiltedCarousel";

const YIELD_MORPH = ["AI Yield", "Predict yield", "Sentinel"];

const PUNE = { lat: 18.5204, lon: 73.8567 };

export default function YieldPage() {
  const [lat, setLat] = useState(PUNE.lat);
  const [lon, setLon] = useState(PUNE.lon);
  const [crops, setCrops] = useState<CropInfo[]>([]);
  const [crop, setCrop] = useState("sugarcane");
  const [season, setSeason] = useState("Kharif");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<any>(null);

  useEffect(() => {
    fetchCrops()
      .then((d) => {
        setCrops(d.crops);
        if (d.crops[0]) setCrop(d.crops[0].id);
      })
      .catch((e) => setError(e.message));
  }, []);

  function gps() {
    if (!navigator.geolocation) {
      setError("Geolocation is not supported.");
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setLat(pos.coords.latitude);
        setLon(pos.coords.longitude);
        setError(null);
      },
      (err) => setError(err.message),
      { enableHighAccuracy: true, timeout: 12000 }
    );
  }

  async function run() {
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      setResult(await predictYield(lat, lon, crop, season));
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  const sat = result?.satellite;

  return (
    <>
      <TextMorph texts={YIELD_MORPH} className="hero-morph" />
      <p className="hero-sub">Sentinel-2 + climate at this pin</p>

      <div className="card">
        <h2>Location</h2>
        <FarmMap lat={lat} lon={lon} onPick={(a, b) => { setLat(a); setLon(b); }} />
        <div className="grid2">
          <div>
            <label>Latitude</label>
            <input type="number" step="0.0001" value={lat} onChange={(e) => setLat(+e.target.value)} />
          </div>
          <div>
            <label>Longitude</label>
            <input type="number" step="0.0001" value={lon} onChange={(e) => setLon(+e.target.value)} />
          </div>
        </div>
        <button className="btn secondary fx-slide" type="button" onClick={gps} style={{ marginTop: 10 }}>
          Detect GPS
        </button>
      </div>

      <TiltedCarousel height={320}>
        <div className="card">
          <h2>Crop & season</h2>
          <div className="chips">
            {crops.map((c) => (
              <button
                type="button"
                key={c.id}
                className={crop === c.id ? "chip on fx-fill" : "chip fx-fill"}
                onClick={() => {
                  setCrop(c.id);
                  if (c.season === "Rabi" || c.season === "Kharif") setSeason(c.season);
                }}
              >
                {c.emoji} {c.id}
              </button>
            ))}
          </div>
          <div style={{ marginTop: 10 }}>
            <label>Season window for satellite</label>
            <select value={season} onChange={(e) => setSeason(e.target.value)}>
              <option>Kharif</option>
              <option>Rabi</option>
              <option>Zaid</option>
            </select>
          </div>
        </div>
        <div className="card">
          <h2>How yield is scored</h2>
          <p className="muted">
            Sentinel-2 NDVI / EVI at this pin, plus climate. First lookup can take 30–60 seconds.
            The number is a model estimate, not a weighed harvest.
          </p>
        </div>
      </TiltedCarousel>

      <p className="muted">First Sentinel lookup can take 30–60 seconds.</p>
      {error && <p className="error">{error}</p>}
      <button className="btn fx-raise" type="button" onClick={run} disabled={busy}>
        {busy ? "Fetching satellite…" : "Predict yield"}
      </button>

      {result && (
        <div className="result-box">
          <div className="muted">Estimated yield</div>
          <div className="result-crop">
            {Math.round(result.yield_kg_ha).toLocaleString()} {result.unit}
          </div>
          <div className="result-conf">
            80% interval {result.interval_80pct?.[0]} – {result.interval_80pct?.[1]}
          </div>
          <p className="muted">{result.disclaimer}</p>
          {sat && (
            <>
              <p className="muted">
                NDVI {sat.latest_ndvi ?? sat.ndvi_mean} ({sat.source}
                {sat.latest_date ? ` · ${sat.latest_date}` : ""})
                <br />
                {result.ndvi_interpretation}
                {sat.note ? ` ${sat.note}` : ""}
              </p>
              {Array.isArray(sat.series) && sat.series.length > 0 && (
                <Chart3D
                  bars={sat.series.slice(-7).map((s: any) => ({
                    label: (s.date || "").slice(5),
                    value: Math.max(0, Number(s.ndvi) || 0),
                  }))}
                  max={1}
                />
              )}
              {(!sat.series || sat.series.length === 0) && (
                <Chart3D
                  bars={[
                    { label: "NDVI", value: sat.ndvi_mean || 0 },
                    { label: "NDVI max", value: sat.ndvi_max || 0 },
                    { label: "EVI", value: sat.evi_mean || 0 },
                  ]}
                  max={1}
                />
              )}
              <AnalyzePanel
                context={{
                  lat,
                  lon,
                  crop,
                  season: result.season,
                  yield_kg_ha: result.yield_kg_ha,
                  interval_80pct: result.interval_80pct,
                  ndvi: sat.latest_ndvi ?? sat.ndvi_mean,
                  ndvi_interpretation: result.ndvi_interpretation,
                  climate: result.climate,
                  soil: result.soil,
                }}
              />
            </>
          )}
        </div>
      )}
    </>
  );
}
