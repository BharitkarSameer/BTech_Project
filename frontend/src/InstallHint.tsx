import { useState } from "react";

export default function InstallHint() {
  const [hidden, setHidden] = useState(() => localStorage.getItem("hideInstall") === "1");
  if (hidden) return null;
  const ios = /iphone|ipad|ipod/i.test(navigator.userAgent);
  return (
    <div className="install-banner">
      <strong>Use it like an app.</strong>{" "}
      {ios
        ? "In Safari, tap Share → Add to Home Screen."
        : "In Chrome, open the menu → Install app / Add to Home Screen."}
      <button
        className="btn secondary fx-offset"
        style={{ marginTop: 8 }}
        onClick={() => {
          localStorage.setItem("hideInstall", "1");
          setHidden(true);
        }}
      >
        Got it
      </button>
    </div>
  );
}
