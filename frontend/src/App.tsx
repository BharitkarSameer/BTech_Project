import { NavLink, Route, Routes } from "react-router-dom";
import Home from "./Home";
import ParticleBackground from "./ParticleBackground";
import Recommend from "./Recommend";
import YieldPage from "./YieldPage";
import YieldsCompare from "./YieldsCompare";

export default function App() {
  return (
    <>
      <ParticleBackground />
      <div className="app-shell">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/recommend" element={<Recommend />} />
          <Route path="/yield" element={<YieldPage />} />
          <Route path="/yields" element={<YieldsCompare />} />
        </Routes>
        <nav className="nav">
          <NavLink to="/" end className={({ isActive }) => (isActive ? "active" : "fx-up")}>
            Home
          </NavLink>
          <NavLink to="/recommend" className={({ isActive }) => (isActive ? "active" : "fx-up")}>
            Crop
          </NavLink>
          <NavLink to="/yield" className={({ isActive }) => (isActive ? "active" : "fx-up")}>
            Yield
          </NavLink>
          <NavLink to="/yields" className={({ isActive }) => (isActive ? "active" : "fx-up")}>
            Plan
          </NavLink>
        </nav>
      </div>
    </>
  );
}
