# Crop Recommendation and Yield Intelligence Platform

College of Engineering Pune (COEP) · Crop yield prediction and advisory  
Coverage: Pune, Nashik, Ahmednagar, Satara, Solapur, Sangli, Kolhapur, Latur

---

## 1. Purpose

This project helps a farmer or field officer use **a farm’s location** to decide **what to grow**, **how much it might yield**, and **what to do on the plot this season**.

On a phone or laptop they should be able to:

1. Mark a farm with **latitude and longitude** (GPS or map).
2. See **which crops suit that soil and climate**.
3. Estimate **yield (kg/ha)** for those crops using **current satellite canopy** and **seasonal weather**.
4. Read a **plain-language roadmap**: fertiliser, water, pests, and what to watch this season.

The product is a **website that installs like an app** (Progressive Web App). The same URL works on a laptop and on a phone.

This is **decision support**. It does not replace a laboratory soil test or a plant-protection officer’s legal prescription.

---

## 2. What the platform does

| Goal | Meaning in this product |
|---|---|
| **Point-scale advice** | Decisions start from a GPS pin. |
| **Two-stage intelligence** | First *what to grow*, then *how much it might yield*, then *what to do about it*. |
| **Live earth observation** | Yield uses Sentinel-2 vegetation indices for the season window at that pin. |
| **Live climate** | Temperature, humidity, and rainfall come from meteorological APIs for that coordinate. |
| **Soil-aware recommendation** | Crop choice uses N, P, K, pH, and climate at the location. |
| **Comparable options** | A ranked list (typically five crops) with scores, then yield for each. |
| **Field language** | Gemini turns the numbers into fertiliser / IPM / climate notes. |
| **Mobile-first delivery** | Add to Home Screen; large controls; map plus GPS. |
| **Regional focus** | Eight Maharashtra districts so the crop list and agronomy stay relevant. |

**Who it is for:** farmers and farm managers in the eight districts; KVK and extension staff who want a location-specific demo.

---

## 3. Geographic and crop scope

**Districts:** Pune, Nashik, Ahmednagar, Satara, Solapur, Sangli, Kolhapur, Latur.

**Approximate service box:** latitude 16.25–20.65, longitude 73.15–77.05. Coordinates outside this region are rejected so advice is not applied to an agro-climate the models were not built for.

**Crops (v1):** sugarcane, grapes, onion, jowar, bajra, wheat, maize, soybean, chickpea, rice, tomato, groundnut, cotton.

**Seasons:** Kharif, Rabi, Zaid (satellite windows follow the selected season).

---

## 4. End-to-end user journey

```text
Home
  → Recommend a crop
       GPS / map pin → auto-fill climate & soil
       Optional manual N-P-K / climate edits
       Ranked crops (score + 3D chart)
       → Predict yield for all recommended crops
            One Sentinel pull for the pin
            Yield (kg/ha) per crop + comparison chart
            → AI analysis & roadmap (per crop)
  → Yield (standalone)
       Same pin + one crop chip → kg/ha + AI analysis
```

**Plan** in the bottom navigation reopens the last recommend → multi-yield session.

---

## 5. System architecture

```text
[ Phone / laptop PWA ]
        HTTPS or local URL
[ React frontend ]  ──JSON──►  [ FastAPI ]
                                  │
                    ┌─────────────┼─────────────┐
                    ▼             ▼             ▼
              Open-Meteo     SoilGrids    Planetary Computer
              (climate)      (soil maps)  (Sentinel-2 L2A)
                    │
                    ▼
         Crop model    Yield model    Gemini (analysis)
```

| Layer | Role |
|---|---|
| **Frontend** (`frontend/`) | Vite + React + TypeScript PWA, Leaflet map, 3D charts |
| **Backend** (`backend/`) | FastAPI: autofill, recommend, yield, batch yield, Gemini analysis |
| **Models** (`backend/models/`) | Crop classifier + yield regressor |
| **Training** (`ml/`) | Scripts to rebuild models when new labelled history is available |
| **Config** (`.env`) | Gemini API key only—no keys for weather, soil maps, or Sentinel |

The production-style local run serves the built frontend from FastAPI (`frontend/dist`), so phone and laptop hit **one origin** (API + UI).

---

## 6. Module 1 — Crop recommendation

### 6.1 Aim

Given a farm location (and optional season), return a **ranked list of suitable crops** with a confidence-style score, so the user can compare options instead of receiving a single opaque label.

### 6.2 Inputs the model uses

| Feature | Unit | Role |
|---|---|---|
| N | kg/ha | Available nitrogen status |
| P | kg/ha | Phosphorus |
| K | kg/ha | Potassium |
| Temperature | °C | Thermal regime |
| Humidity | % | Moisture in the air |
| pH | 0–14 | Soil reaction |
| Rainfall | mm (annual / 12-month window) | Water availability |

### 6.3 How values are obtained at a pin

| Feature | Intended live source |
|---|---|
| Temperature, humidity, rainfall | **Open-Meteo** archive + current conditions for that lat/lon |
| pH, texture, organic carbon, total nitrogen maps | **SoilGrids** (ISRIC) at the point |
| N, P, K (kg/ha) | Location-linked **soil nutrient table** for the nearest of the eight districts, overridable by the user if they have a soil-test report |

Users can always **edit** every field before predicting. The UI shows whether a value came from a live API, a district table, or a manual edit.

### 6.4 Model

- **Task:** multi-class classification (which crop).
- **Algorithm:** Random Forest, combined with **agronomic range scores** for western Maharashtra (pH, nutrients, temperature, humidity, rainfall envelopes per crop).
- **Blend:** majority weight on the learned model, remainder on the agronomic scorer, so recommendations stay agronomically plausible.
- **Output:** typically **top five** crops with score (%), season tag, and a short crop note.
- **Artefacts:** `backend/models/crop_recommender.joblib`, `crop_meta.json`.

Retrain with: `python -m ml.train_crop`.

### 6.5 Target of this module

A **crop ranking**, not a yield number. Yield is the next module.

---

## 7. Module 2 — Yield prediction

### 7.1 Aim

For a **chosen crop** (or **all recommended crops**) at the **same pin**, estimate **yield in kg/ha** using **current-season satellite vegetation** and **seasonal climate**, plus soil maps and the crop/season identity.

### 7.2 What the user types vs what the model sees

The user provides **lat, lon, crop(s), season**. The backend **builds** the feature vector.

**Target `y`:** `yield_kg_ha` (kilograms per hectare).

**Model inputs:**

| Group | Features |
|---|---|
| Identity | `crop_id`, `season_id`, `year` |
| Satellite (Sentinel-2) | `ndvi_mean`, `ndvi_max`, `ndvi_p90`, `evi_mean`, `ndwi_mean`, `scene_count` |
| Climate (season window) | `rainfall_mm`, `temperature_mean_c`, `avg_tmax_c`, `avg_tmin_c`, `humidity_mean_pct` |
| Soil maps | `ph`, `clay_pct`, `soc` |

N, P, K from the crop module are **not** yield-model features; they are passed later to **Gemini** so the roadmap can discuss fertiliser in context of both suitability and estimated yield.

### 7.3 Satellite pipeline

- Collection: **Sentinel-2 L2A** via **Microsoft Planetary Computer** (no user API key).
- Geometry: small box around the pin (~300 m).
- Cloud filter, then NDVI (NIR–Red), EVI, NDWI.
- Season windows: Kharif (Jun–Oct), Rabi (Nov–Mar), Zaid (Mar–Jun), clipped to available dates.
- Results are cached by rounded coordinate and date range so repeat clicks are faster.

**Batch yield** (`POST /yield/batch`) fetches Sentinel **once** for the pin, then scores every recommended crop. That is the “predict yield for all five crops” path.

### 7.4 Model

- **Task:** regression.
- **Algorithm:** LightGBM (gradient boosting).
- **Output:** point estimate kg/ha, 80% interval, NDVI interpretation text.
- **Artefacts:** `backend/models/yield_lgbm.joblib`, `yield_meta.json`.

Retrain with: `python -m ml.build_yield_dataset` then `python -m ml.train_yield` when an updated historical yield table is in `data/`.

### 7.5 How to read the number

The kg/ha figure is **indicative decision support**: trained on **historical district–season–crop yield behaviour** and applied with **this season’s canopy and weather at the pin**. It is not a weighbridge measurement of that farm.

---

## 8. Module 3 — AI analysis and field roadmap

### 8.1 Aim

Turn the **same numbers the models used** into **actionable language**: fertiliser thinking, water, pests/disease (IPM), and seasonal watch-outs—for **each crop** after its yield is shown.

### 8.2 What is sent to the language model

Latitude, longitude, district, crop, season, estimated yield and interval, crop-suitability score, N, P, K, pH, temperature, humidity, rainfall, NDVI and interpretation, plus seasonal climate and soil-map fields.

### 8.3 Expected structure of the answer

1. Situation  
2. Fertiliser plan (timing and common products such as urea / DAP / MOP where relevant)  
3. Water and climate  
4. Pests and disease (IPM; not a legal spray prescription)  
5. What to watch this season  

### 8.4 Provider

**Google Gemini** (AI Studio). Configure in project-root `.env`:

```
LLM_API_KEY=<Gemini AI Studio key>
LLM_MODEL=gemini-3.6-flash
```

Key: [Google AI Studio](https://aistudio.google.com/apikey). Restart the server after changing `.env`. Yield and crop recommend **do not** require this key; only **AI analysis** does.

The prompt instructs the model to treat NPK as location-based status (not necessarily a lab report) and yield as a model estimate.

---

## 9. External data sources (no paid keys except Gemini)

| Need | Service | Authentication |
|---|---|---|
| Climate now + history | [Open-Meteo](https://open-meteo.com/) | None |
| Soil maps (pH, SOC, clay, …) | [SoilGrids v2](https://rest.isric.org/soilgrids/v2.0/) | None |
| Sentinel-2 L2A | [Microsoft Planetary Computer](https://planetarycomputer.microsoft.com/) | Signed URLs in library; no project key |
| Map tiles | OpenStreetMap | None |
| Agronomy text | Gemini | `LLM_API_KEY` in `.env` |

**Intended future connections** (when accounts exist): official district APY series (e.g. data.gov.in) to refresh yield labels; Copernicus Data Space or Earth Engine as a second satellite path. The feature pipeline (indices + weather + soil + crop) stays the same.

---

## 10. HTTP API

Base URL locally: `http://127.0.0.1:8000` (also mounted under `/api/...`).

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Liveness; region; whether Gemini is configured |
| GET | `/crops` | Crop catalogue, bbox, district list |
| POST | `/autofill` | `{ lat, lon, season? }` → climate, soil maps, NPK, sources |
| POST | `/recommend` | Lat/lon and/or the seven agronomic fields → ranked crops |
| POST | `/yield` | `{ lat, lon, crop, season }` → kg/ha + satellite |
| POST | `/yield/batch` | `{ lat, lon, crops[], season }` → shared satellite, one yield per crop |
| POST | `/analyze` | Farm JSON → Gemini roadmap text |

Out-of-bbox coordinates: **HTTP 400** with the eight district names.

---

## 11. Repository map

```
backend/                 FastAPI app and services
  app.py                 Routes
  config.py              Districts, bbox, crop list, agronomic envelopes
  models/                Trained joblib + metadata JSON
  services/              soil, weather, sentinel, recommend, yield, llm, npk, bbox
frontend/                React PWA (src + dist)
ml/                      train_crop, build_yield_dataset, train_yield
data/                    Soil nutrient table and yield-training table
DOCUMENTATION.md         This file
.env.example             Gemini key template (copy to .env)
run_server.py            Bind 0.0.0.0:8000 and print LAN URL
```

Frontend routes: `/` home, `/recommend` crop, `/yield` single yield, `/yields` multi-crop plan.

---

## 12. How to run (local)

From the project root:

```bash
python -m pip install -r backend/requirements.txt
python -m ml.train_crop
python -m ml.build_yield_dataset
python -m ml.train_yield

cd frontend
npm install
npm run build
cd ..

python -m uvicorn backend.app:app --host 0.0.0.0 --port 8000
```

- Laptop: http://127.0.0.1:8000  
- Phone on the same network: `http://<laptop-LAN-IP>:8000`  
- Gemini: copy `.env.example` → `.env`, paste the AI Studio key, restart.

Optional live frontend: `cd frontend && npm run dev` (proxies `/api` to port 8000).

---

## 13. Training and model refresh

**Crop model**  
Historical examples of `(N, P, K, temperature, humidity, pH, rainfall) → crop`, plus agronomic envelopes in `backend/config.py` (`CROP_PROFILES`). Output: classifier used at `/recommend`.

**Yield model**  
Historical examples of district–season–crop yield together with vegetation and climate features for the same season. Output: regressor used at `/yield` and `/yield/batch`.

When better labelled harvests or soil tests become available, **replace the tables under `data/` and rerun the `ml/` scripts**. The live inference path (Open-Meteo, SoilGrids, Sentinel, Gemini) does not change.

---

## 14. Design notes

1. **Provenance on screen** — live API vs district table vs user edit.  
2. **One pin, many crops** — ranking then batch yield, not a single dead-end label.  
3. **Satellite for the current season, history for the model** — current NDVI/EVI/NDWI at inference; historical yields for learning.  
4. **Language model as explanation, not as the yield number** — kg/ha comes from the regressor; Gemini explains what to consider.  
5. **Regional gate** — eight districts so agronomy stays local.  
6. **Secrets only in `.env`** — never in git; Gemini is the only required key for advisory text.

---

## 15. Limitations

- Soil nutrient kg/ha from a district table is **not** a 0–15 cm laboratory test of that field unless the user types lab values.  
- Yield kg/ha is **indicative**.  
- Kharif cloud cover can reduce the number of Sentinel scenes.  
- Gemini text is **advisory**; pesticide use must follow labels and local regulation.  
- GPS in the browser on `http://<LAN-IP>` may be blocked; the map pin remains the fallback.

---

## 16. Suggested demo

1. Open the app, pin a farm inside one of the eight districts.  
2. Auto-fill, show source badges, recommend crops, discuss the 3D score chart.  
3. Predict yield for all recommended crops; compare kg/ha.  
4. Open AI analysis on the top crop; walk through fertiliser and IPM headings.  
5. Repeat on the standalone Yield page with another crop.

Flow in one line: **location → suitable crops → satellite yield → field notes.**
