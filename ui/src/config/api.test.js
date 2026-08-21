import { afterEach, describe, expect, it, vi } from "vitest";


afterEach(() => {
  vi.unstubAllEnvs();
  vi.resetModules();
});


describe("API URL configuration", () => {
  it("uses the local backend by default", async () => {
    const { apiUrl } = await import("./api");

    expect(apiUrl("/api/health")).toBe(
      "http://127.0.0.1:8000/api/health"
    );
  });

  it("uses VITE_API_URL without duplicating a trailing slash", async () => {
    vi.stubEnv("VITE_API_URL", "https://api.example.test/");

    const { apiUrl } = await import("./api");

    expect(apiUrl("/api/decisions")).toBe(
      "https://api.example.test/api/decisions"
    );
  });
});
