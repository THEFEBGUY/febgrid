// @vitest-environment jsdom

import { act, fireEvent, render, renderHook, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { getAuthenticatedRouteTarget } from "../data/navigation";
import { api, ApiError, resetApiRequestDiagnostics, setApiAuthToken } from "../services/api";
import type { AuthSession } from "../types/api";
import { useAuth } from "./useAuth";

const session: AuthSession = {
  access_token: "persisted-test-token",
  token_type: "bearer",
  user: {
    id: "user-1",
    company_id: "company-1",
    full_name: "Test Owner",
    email: "owner@example.com",
    role: "company_owner",
    auth_provider: "local",
    is_active: true,
    last_login_at: null,
    created_at: "2026-07-12T00:00:00Z",
    updated_at: "2026-07-12T00:00:00Z",
  },
  company: {
    id: "company-1",
    name: "Test Company",
    slug: "test-company",
    industry: null,
    size: null,
    timezone: "UTC",
    description: null,
    settings: {},
    is_active: true,
    created_at: "2026-07-12T00:00:00Z",
    updated_at: "2026-07-12T00:00:00Z",
  },
};

function AuthGateHarness(): JSX.Element {
  const auth = useAuth();
  if (auth.isLoading) return <p>Restoring session</p>;
  if (auth.isAuthenticated) return <main>Authenticated dashboard</main>;
  return <button onClick={() => void auth.login({ email: "owner@example.com", password: "password" })}>Login form</button>;
}

describe("authentication persistence", () => {
  beforeEach(() => {
    window.localStorage.clear();
    resetApiRequestDiagnostics();
    setApiAuthToken(null);
    vi.restoreAllMocks();
  });

  it("saves a successful login and immediately exposes authenticated state", async () => {
    const login = vi.spyOn(api, "login").mockResolvedValue(session);
    const me = vi.spyOn(api, "me").mockResolvedValue({ user: session.user, company: session.company });
    const { result } = renderHook(() => useAuth());
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    await act(async () => {
      await result.current.login({ email: "owner@example.com", password: "password" });
    });

    expect(login).toHaveBeenCalledOnce();
    expect(window.localStorage.getItem("febgrid.authToken")).toBe(session.access_token);
    expect(result.current.isAuthenticated).toBe(true);
    expect(result.current.user?.id).toBe(session.user.id);
    expect(me).not.toHaveBeenCalled();
  });

  it("transitions away from the login gate to the authenticated dashboard", async () => {
    vi.spyOn(api, "login").mockResolvedValue(session);
    render(<AuthGateHarness />);
    const loginButton = await screen.findByRole("button", { name: "Login form" });

    fireEvent.click(loginButton);
    await screen.findByText("Authenticated dashboard");
    expect(screen.queryByRole("button", { name: "Login form" })).toBeNull();
  });

  it("restores a persisted session after a browser refresh", async () => {
    window.localStorage.setItem("febgrid.authToken", session.access_token);
    const me = vi.spyOn(api, "me").mockResolvedValue({ user: session.user, company: session.company });
    const { result } = renderHook(() => useAuth());

    await waitFor(() => expect(result.current.isAuthenticated).toBe(true));
    expect(me).toHaveBeenCalledOnce();
    expect(window.localStorage.getItem("febgrid.authToken")).toBe(session.access_token);
  });

  it("does not delete a persisted session after an intentional request cancellation", async () => {
    window.localStorage.setItem("febgrid.authToken", session.access_token);
    vi.spyOn(api, "me").mockRejectedValue(new ApiError("Workspace request cancelled", 499));
    const { result } = renderHook(() => useAuth());

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(window.localStorage.getItem("febgrid.authToken")).toBe(session.access_token);
    expect(result.current.token).toBe(session.access_token);
  });

  it("does not create a session after failed login", async () => {
    vi.spyOn(api, "login").mockRejectedValue(new ApiError("Invalid email or password", 401));
    const { result } = renderHook(() => useAuth());
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    await expect(act(async () => result.current.login({ email: "owner@example.com", password: "wrong" }))).rejects.toThrow();
    expect(window.localStorage.getItem("febgrid.authToken")).toBeNull();
    expect(result.current.isAuthenticated).toBe(false);
  });

  it("clears the persisted session on logout", async () => {
    window.localStorage.setItem("febgrid.authToken", session.access_token);
    vi.spyOn(api, "me").mockResolvedValue({ user: session.user, company: session.company });
    vi.spyOn(api, "logout").mockResolvedValue({ status: "ok" });
    const { result } = renderHook(() => useAuth());
    await waitFor(() => expect(result.current.isAuthenticated).toBe(true));

    await act(async () => result.current.logout());
    expect(window.localStorage.getItem("febgrid.authToken")).toBeNull();
    expect(result.current.isAuthenticated).toBe(false);
  });

  it("routes authenticated users to the correct dashboard without overriding valid deep links", () => {
    expect(getAuthenticatedRouteTarget("company_owner", "dashboard", "")).toBe("dashboard");
    expect(getAuthenticatedRouteTarget("employee", "dashboard", "#/dashboard")).toBe("my-dashboard");
    expect(getAuthenticatedRouteTarget("company_owner", "projects", "#/projects")).toBeNull();
  });
});
