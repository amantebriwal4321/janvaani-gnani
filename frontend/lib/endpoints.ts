/** Where the desk sends HTTP and the call socket. Same-origin when nothing is configured. */

function trimBase(value: string | undefined): string {
  return (value || "").trim().replace(/\/$/, "");
}

function localHost(host: string): boolean {
  return (
    host === "localhost" ||
    host === "127.0.0.1" ||
    host.endsWith(".local") ||
    /^(10\.|192\.168\.|172\.(1[6-9]|2\d|3[0-1])\.)/.test(host)
  );
}

export function apiBase(): string {
  const configured = trimBase(process.env.NEXT_PUBLIC_API_BASE);
  if (configured) return configured;
  if (typeof window === "undefined") return "http://127.0.0.1:8766";
  const host = window.location.hostname;
  if (localHost(host)) return `${window.location.protocol}//${host}:8766`;
  return window.location.origin;
}

export function wsBase(): string {
  const configured = trimBase(process.env.NEXT_PUBLIC_WS_BASE);
  if (configured) return configured;
  const http = apiBase();
  if (http.startsWith("https://")) return `wss://${http.slice("https://".length)}`;
  if (http.startsWith("http://")) return `ws://${http.slice("http://".length)}`;
  return http;
}
