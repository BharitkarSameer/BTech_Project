import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { autofill, PLAN_KEY, recommend, type Autofill } from "./api";
import Chart3D from "./Chart3D";
import FarmMap from "./FarmMap";
import TextMorph from "./TextMorph";
import TiltedCarousel from "./TiltedCarousel";

const REC_MORPH = ["Recommend crop", "Crop AI", "Best crop"];

const PUNE = { lat: 18.5204, lon: 73.8567 };

function badge(src?: string) {
  if (!src) return null;
  const label = src === "api" ? "Live API" : src === "district" ? "District avg" : "Fallback";
  return <span className={`src ${src}`}>{label}</span>;
}

export default function Recommend() {
  const navigate = useNavigate();
  const [lat, setLat] = useState(PUNE.lat);
  const [lon, setLon] = useState(PUNE.lon);
  const [season, setSeason] = useState("Kharif");
  const [fields, setFields] = useState({
    N: 55,
    P: 27,
    K: 185,
    temperature: 25,
    humidity: 60,
    ph: 6.8,
    rainfall: 750,
  });
  const [sources, setSources] = useState<Record<string, string>>({});
  const [note, setNote] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<any>(null);

  function applyFill(data: Autofill) {
    setFields({
      N: data.N,
      P: data.P,
      K: data.K,
      temperature: data.temperature,
      humidity: data.humidity,
      ph: data.ph,
      rainfall: data.rainfall,
    });
    setSources(data.sources || {});
    setNote(
      data.district
        ? `Nearest district: ${data.district} (~${data.district_distance_km ?? "?"} km). ${data.npk_meta?.note ?? ""}`
        : data.npk_meta?.note ?? null
    );
  }

  async function fill() {
    setBusy(true);
    setError(null);
    try {
      applyFill(await autofill(lat, lon, season));
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  function gps() {
    if (!navigator.geolocation) {
      setError("Geolocation is not supported. Drop a pin on the map.");
      return;
    }
    setBusy(true);
    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        const la = pos.coords.latitude;
        const lo = pos.coords.longitude;
        setLat(la);
        setLon(lo);
        try {
          applyFill(await autofill(la, lo, season));
          setError(null);
        } catch (e: any) {
          setError(e.message);
        } finally {
          setBusy(false);
        }
      },
      (err) => {
        setBusy(false);
        setError(err.message || "Location permission denied.");
      },
      { enableHighAccuracy: true, timeout: 12000 }
    );
  }

  async function run() {
    setBusy(true);
    setError(null);
    try {
      const data = await recommend({ lat, lon, season, ...fields });
      setResult(data);
      const plan = {
        lat,
        lon,
        season,
        fields,
        district: data.autofill?.district,
        recommendations: data.recommendations,
      };
      sessionStorage.setItem(PLAN_KEY, JSON.stringify(plan));
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    fill();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const top = result?.recommendations?.[0];

  return (
    <>
      <TextMorph texts={REC_MORPH} className="hero-morph" />
      <p className="hero-sub">Live climate & soil maps</p>

      <div className="card">
        <h2>Farm location</h2>
        <p className="muted">
          Tap the map or use GPS. Coverage: Pune, Nashik, Ahmednagar, Satara, Solapur, Sangli,
          Kolhapur, Latur.
        </p>
        <FarmMap
          lat={lat}
          lon={lon}
          onPick={(a, b) => {
            setLat(a);
            setLon(b);
          }}
        />
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
        <div style={{ marginTop: 10 }}>
          <label>Season (for NPK table)</label>
          <select value={season} onChange={(e) => setSeason(e.target.value)}>
            <option>Kharif</option>
            <option>Rabi</option>
            <option>Zaid</option>
          </select>
        </div>
        <div className="grid2" style={{ marginTop: 10 }}>
          <button className="btn secondary fx-slide" type="button" onClick={gps} disabled={busy}>
            Detect GPS
          </button>
          <button className="btn fx-raise" type="button" onClick={fill} disabled={busy}>
            {busy ? "Loading…" : "Auto-fill"}
          </button>
        </div>
        {note && <p className="muted" style={{ marginTop: 8 }}>{note}</p>}
      </div>

      <TiltedCarousel height={280}>
        <div className="card">
          <h2>Soil nutrients {badge(sources.N)}</h2>
          <div className="grid3">
            {(["N", "P", "K"] as const).map((k) => (
              <div key={k}>
                <label>{k} kg/ha</label>
                <input
                  type="number"
                  value={fields[k]}
                  onChange={(e) => setFields({ ...fields, [k]: +e.target.value })}
                />
              </div>
            ))}
          </div>
        </div>
        <div className="card">
          <h2>Climate {badge(sources.temperature)}</h2>
          <div className="grid2">
            <div>
              <label>Temperature °C</label>
              <input
                type="number"
                value={fields.temperature}
                onChange={(e) => setFields({ ...fields, temperature: +e.target.value })}
              />
            </div>
            <div>
              <label>Humidity %</label>
              <input
                type="number"
                value={fields.humidity}
                onChange={(e) => setFields({ ...fields, humidity: +e.target.value })}
              />
            </div>
            <div>
              <label>pH {badge(sources.ph)}</label>
              <input
                type="number"
                step="0.1"
                value={fields.ph}
                onChange={(e) => setFields({ ...fields, ph: +e.target.value })}
              />
            </div>
            <div>
              <label>Rainfall 12 months mm</label>
              <input
                type="number"
                value={fields.rainfall}
                onChange={(e) => setFields({ ...fields, rainfall: +e.target.value })}
              />
            </div>
          </div>
        </div>
      </TiltedCarousel>

      {error && <p className="error">{error}</p>}
      <button className="btn fx-raise" type="button" onClick={run} disabled={busy}>
        Recommend best crop
      </button>

      {top && (
        <div className="result-box">
          <div style={{ fontSize: 42 }}>{top.emoji}</div>
          <div className="muted">Recommended crop</div>
          <div className="result-crop">{top.crop}</div>
          <div className="result-conf">
            {top.confidence_pct}% blend score · {top.season}
          </div>
          <p className="muted">{top.info}</p>
          <Chart3D
            bars={result.recommendations.map((c: any) => ({
              label: c.crop,
              value: c.confidence_pct,
            }))}
            unit="%"
          />
          <button
            className="btn result-cta fx-raise"
            type="button"
            onClick={() =>
              navigate("/yields", {
                state: {
                  lat,
                  lon,
                  season,
                  fields,
                  district: result.autofill?.district,
                  recommendations: result.recommendations,
                },
              })
            }
          >
            Predict yield for all {result.recommendations.length} crops
          </button>
        </div>
      )}
    </>
  );
}
