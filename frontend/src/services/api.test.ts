import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  api,
  cancelInFlightGetRequests,
  getApiRequestDiagnostics,
  resetApiRequestDiagnostics,
  setApiAuthToken,
} from "./api";

function jsonResponse(body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

describe("API request coordination", () => {
  beforeEach(() => {
    resetApiRequestDiagnostics();
    setApiAuthToken("test-token");
  });

  afterEach(() => {
    vi.restoreAllMocks();
    resetApiRequestDiagnostics();
    setApiAuthToken(null);
  });

  it("deduplicates identical in-flight GET requests", async () => {
    let resolveFetch: ((response: Response) => void) | undefined;
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockImplementation(
      () => new Promise<Response>((resolve) => { resolveFetch = resolve; }),
    );

    const first = api.departments("company-1");
    const second = api.departments("company-1");
    expect(fetchSpy).toHaveBeenCalledTimes(1);
    expect(getApiRequestDiagnostics().deduplicatedGetCount).toBe(1);

    resolveFetch?.(jsonResponse([]));
    await expect(Promise.all([first, second])).resolves.toEqual([[], []]);
    expect(getApiRequestDiagnostics().inFlightGetCount).toBe(0);
  });

  it("cancels stale GET requests when the company or session changes", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation((_input, init) => new Promise<Response>((_resolve, reject) => {
      init?.signal?.addEventListener("abort", () => reject(new DOMException("Aborted", "AbortError")), { once: true });
    }));

    const pending = api.projects("company-a");
    cancelInFlightGetRequests();
    await expect(pending).rejects.toMatchObject({ status: 499 });
    expect(getApiRequestDiagnostics().inFlightGetCount).toBe(0);
  });

  it("does not start permanent health polling after a successful request", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(jsonResponse({ status: "ok" }));

    await api.health();
    await new Promise((resolve) => globalThis.setTimeout(resolve, 20));
    expect(fetchSpy).toHaveBeenCalledTimes(1);
  });
});
