const DEFAULT_API_URL = "http://127.0.0.1:8000";

export const API_URL = (
  import.meta.env.VITE_API_URL || DEFAULT_API_URL
).replace(/\/$/, "");

export function apiUrl(path) {
  return `${API_URL}${path}`;
}
