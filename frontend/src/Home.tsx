import { Link } from "react-router-dom";
import Chart3D from "./Chart3D";
import InstallHint from "./InstallHint";
import TextMorph from "./TextMorph";
import TiltedCarousel from "./TiltedCarousel";

const DISTRICTS = "Pune · Nashik · Ahmednagar · Satara · Solapur · Sangli · Kolhapur · Latur";

const HOME_MORPH = ["Crop AI", "Recommend crop", "AI Yield"];

const PREVIEW = [
  { label: "Sugarcane", value: 92 },
  { label: "Grapes", value: 78 },
  { label: "Onion", value: 71 },
  { label: "Wheat", value: 64 },
  { label: "Jowar", value: 58 },
  { label: "Soybean", value: 49 },
  { label: "Cotton", value: 41 },
];

export default function Home() {
  return (
    <>
      <TextMorph texts={HOME_MORPH} className="hero-morph" />
      <p className="hero-sub">3D harvest intelligence · Maharashtra 8</p>
      <InstallHint />
      <TiltedCarousel height={400}>
        <div className="card">
          <h2>Regional crop signal</h2>
          <Chart3D bars={PREVIEW} unit="" />
        </div>
        <Link className="cta card-like fx-raise" to="/recommend">
          <strong>Recommend a crop</strong>
          <span>Orbit the scores in 3D after auto-fill</span>
        </Link>
        <Link className="cta card-like fx-raise" to="/yield">
          <strong>Predict yield</strong>
          <span>Sentinel canopy as a live 3D chart</span>
        </Link>
      </TiltedCarousel>
      <p className="muted" style={{ textAlign: "center", marginBottom: "1.1rem" }}>
        Drop a pin in {DISTRICTS}. Live Open-Meteo + SoilGrids at the coordinate.
        Yield bars come from Sentinel-2 NDVI at this farm.
      </p>
    </>
  );
}
