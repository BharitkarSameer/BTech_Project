from __future__ import annotations

import json
import os
import time

import requests

SYSTEM = (
    "You are an agronomy advisor for farmers in Maharashtra, India "
    "(Pune, Nashik, Ahmednagar, Satara, Solapur, Sangli, Kolhapur, Latur). "
    "Give a practical field roadmap. Be specific but cautious: NPK values may be "
    "district averages, yield is model-estimated, not a measured harvest. "
    "Do not invent illegal pesticide advice; prefer IPM and label-legal products "
    "commonly used in India. Structure the answer with short headings:\n"
    "1. Situation\n2. Fertiliser plan (N-P-K timing, products like urea/DAP/MOP if relevant)\n"
    "3. Water and climate\n4. Pests and disease (IPM, not a spray schedule as prescription)\n"
    "5. What to watch this season\n"
    "Use plain language. 400-700 words max."
)

DEFAULT_MODELS = [
    "gemini-3.6-flash",
    "gemini-2.5-flash",
    "gemini-flash-latest",
]


def llm_configured() -> bool:
    return bool(os.environ.get("LLM_API_KEY", "").strip())


def _model_list() -> list[str]:
    primary = os.environ.get("LLM_MODEL", "gemini-3.6-flash").strip()
    extra = os.environ.get("LLM_FALLBACK_MODELS", "")
    names = [primary]
    if extra:
        names.extend(n.strip() for n in extra.split(",") if n.strip())
    else:
        names.extend(DEFAULT_MODELS)
    seen: list[str] = []
    for n in names:
        if n and n not in seen:
            seen.append(n)
    return seen


def _gemini_once(key: str, model: str, user: str) -> tuple[int, str]:
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent"
    )
    r = requests.post(
        url,
        params={"key": key},
        json={
            "systemInstruction": {"parts": [{"text": SYSTEM}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": {"temperature": 0.4, "maxOutputTokens": 2048},
        },
        timeout=90,
    )
    return r.status_code, r.text


def _parse_ok(text: str) -> str:
    data = json.loads(text)
    parts = data["candidates"][0]["content"]["parts"]
    return "".join(p.get("text", "") for p in parts).strip()


def analyze_farm(payload: dict) -> str:
    key = os.environ.get("LLM_API_KEY", "").strip()
    if not key:
        raise RuntimeError(
            "LLM_API_KEY is not set. Put your Gemini AI Studio key in .env "
            "(see .env.example) and restart the server."
        )
    user = "Farm context for analysis:\n" f"{payload}\n\nWrite the roadmap now."
    last_err = "Gemini request failed."
    for model in _model_list():
        for attempt in range(4):
            try:
                status, body = _gemini_once(key, model, user)
            except requests.RequestException as e:
                last_err = f"Gemini network error ({model}): {e}"
                time.sleep(2 ** attempt)
                continue
            if status == 200:
                try:
                    text = _parse_ok(body)
                except Exception as e:
                    raise RuntimeError(f"Unexpected Gemini response: {body[:400]}") from e
                if not text:
                    last_err = f"Gemini returned empty text ({model})."
                    break
                return text
            if status in (429, 503):
                last_err = (
                    f"Gemini is busy ({status} on {model}). "
                    "Wait a few seconds and tap AI analysis again."
                )
                time.sleep(2 ** attempt)
                continue
            last_err = f"Gemini HTTP {status}: {body[:400]}"
            break
    raise RuntimeError(last_err)
