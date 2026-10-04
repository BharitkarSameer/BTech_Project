# Crop recommendation + yield (8 Maharashtra districts)

Website / PWA for:

**Pune, Nashik, Ahmednagar, Satara, Solapur, Sangli, Kolhapur, Latur.**

Two flows:

1. **Recommend a crop** — live Open-Meteo climate + SoilGrids maps at the pin; N-P-K kg/ha from the nearest district table (labelled as district average).
2. **Estimate yield** — live Sentinel-2 NDVI at the pin; kg/ha from a model trained on **synthetic regional harvest trends** until a data.gov.in APY key is available.

Install on a phone: Chrome/Safari → **Add to Home Screen**.

## Local run

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

- On the **laptop**: http://127.0.0.1:8000  
- On your **phone (same Wi-Fi)**: http://10.1.232.223:8000  
  (If your laptop IP changed, run `ipconfig` and use the Wi-Fi IPv4.)

`127.0.0.1` only works on the laptop. The phone needs `0.0.0.0` plus the laptop’s LAN IP.

If it still fails: Windows Firewall → allow Python on **Private** networks, or share a **hotspot** (many campus Wi-Fi networks block phone↔PC). GPS in the browser needs HTTPS except on localhost, so on `http://10.x...` use the map pin if Detect GPS is blocked.

Frontend hot reload: `cd frontend && npm run dev` (proxies `/api` to port 8000).

## AI fertiliser / IPM analysis (Gemini key)

1. Copy [`.env.example`](.env.example) to **`.env`** in the **project root** (same folder as `run_server.py`).
2. Get a key from [Google AI Studio](https://aistudio.google.com/apikey) and paste:

```
LLM_API_KEY=your-gemini-api-key-here
LLM_MODEL=gemini-3.6-flash
```

3. Restart uvicorn. Without this key, yield still works; **AI analysis & roadmap** fails until the key is set.

Do not commit `.env`. If that model name fails, check [AI Studio](https://aistudio.google.com/) for the current Flash model id.

## Live vs table data

| Input | Live at the coordinate? | Source |
|---|---|---|
| Temperature, humidity, rainfall | Yes | Open-Meteo (no key) |
| pH, clay, SOC, total N | Yes | SoilGrids (no key) |
| N, P, K kg/ha | No (no public GPS API) | Nearest of 8 districts in `india_soil_data.csv` |
| NDVI / EVI / NDWI | Yes | Sentinel-2, Planetary Computer (no key) |
| Yield kg/ha model labels | Training only | Synthetic trends by district/crop/year |

Coordinates outside the 8-district bbox return HTTP 400.
