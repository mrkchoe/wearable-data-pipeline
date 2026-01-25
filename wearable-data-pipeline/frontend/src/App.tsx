import { useEffect } from "react";
import Dashboard from "./pages/Dashboard";
import { initAnalytics, track } from "./lib/analytics/track";
import { EventName } from "./types/events";

const ANALYTICS_ENDPOINT =
  import.meta.env.VITE_ANALYTICS_ENDPOINT ?? "http://localhost:5173/analytics";
const APP_VERSION = import.meta.env.VITE_APP_VERSION ?? "0.1.0";
const ENVIRONMENT =
  (import.meta.env.VITE_ENVIRONMENT as
    | "local"
    | "dev"
    | "staging"
    | "prod") ?? "local";

export default function App() {
  useEffect(() => {
    initAnalytics({
      endpoint: ANALYTICS_ENDPOINT,
      appVersion: APP_VERSION,
      env: ENVIRONMENT,
    });

    track(EventName.PageView, {
      page_title: "Dashboard",
      entry_point: "direct",
    });
  }, []);

  return (
    <div style={{ fontFamily: "Inter, system-ui, sans-serif", padding: 24 }}>
      <h1>Wearable Analytics MVP</h1>
      <p style={{ maxWidth: 720 }}>
        Minimal frontend to validate the analytics event contract and SDK.
      </p>
      <Dashboard />
    </div>
  );
}
