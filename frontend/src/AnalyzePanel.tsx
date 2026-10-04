import { useState } from "react";
import { analyzeFarm } from "./api";

export default function AnalyzePanel({
  context,
}: {
  context: Record<string, unknown>;
}) {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [text, setText] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function run() {
    setOpen(true);
    setBusy(true);
    setError(null);
    try {
      const data = await analyzeFarm(context);
      setText(data.analysis);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="analyze-wrap">
      <button className="btn secondary fx-pulse" type="button" onClick={run} disabled={busy}>
        {busy ? "Asking agronomy AI…" : "AI analysis & roadmap"}
      </button>
      {open && (
        <div className="analyze-box">
          {busy && <p className="muted">Calling the LLM with this farm’s NPK, climate, NDVI and yield…</p>}
          {error && <p className="error">{error}</p>}
          {text && <pre className="analyze-text">{text}</pre>}
        </div>
      )}
    </div>
  );
}
