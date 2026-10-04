const API = import.meta.env.VITE_API_URL ?? "/api";

async function parse(res: Response) {
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = (data as { detail?: string }).detail || res.statusText;
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return data;
}

export type CropInfo = {
  id: string;
  emoji: string;
  info: string;
  season: string;
};

export type Autofill = {
  lat: number;
  lon: number;
  N: number;
  P: number;
  K: number;
  ph: number;
  temperature: number;
  humidity: number;
  rainfall: number;
  district?: string;
  district_distance_km?: number;
  sources: Record<string, string>;
  npk_meta: {
    note: string;
    source: string;
    year: number | null;
    season: string;
    district?: string;
  };
  soil: Record<string, number | null> | null;
};

export async function fetchCrops() {
  return parse(await fetch(`${API}/crops`)) as Promise<{
    crops: CropInfo[];
    bbox: { lat_min: number; lat_max: number; lon_min: number; lon_max: number };
    center: { lat: number; lon: number };
  }>;
}

export async function autofill(lat: number, lon: number, season?: string) {
  return parse(
    await fetch(`${API}/autofill`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ lat, lon, season }),
    })
  ) as Promise<Autofill>;
}

export async function recommend(body: Record<string, number | string | null>) {
  return parse(
    await fetch(`${API}/recommend`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    })
  );
}

export async function predictYield(lat: number, lon: number, crop: string, season: string) {
  return parse(
    await fetch(`${API}/yield`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ lat, lon, crop, season }),
    })
  );
}

export async function predictYieldsBatch(
  lat: number,
  lon: number,
  crops: string[],
  season: string
) {
  return parse(
    await fetch(`${API}/yield/batch`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ lat, lon, crops, season }),
    })
  );
}

export async function analyzeFarm(body: Record<string, unknown>) {
  return parse(
    await fetch(`${API}/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    })
  ) as Promise<{ analysis: string; model?: string }>;
}

export const PLAN_KEY = "cropai_plan";
