import { useEffect, useState } from "react";

import { api, ApiError, setApiAuthToken } from "../services/api";
import type { AuthUser, Company, LoginPayload, RegisterPayload } from "../types/api";

const TOKEN_STORAGE_KEY = "febgrid.authToken";

interface AuthState {
  user: AuthUser | null;
  company: Company | null;
  token: string | null;
  isLoading: boolean;
  isSubmitting: boolean;
  error: string | null;
  isAuthenticated: boolean;
  login: (payload: LoginPayload) => Promise<void>;
  register: (payload: RegisterPayload) => Promise<void>;
  logout: () => Promise<void>;
  clearError: () => void;
}

function getStoredToken(): string | null {
  try {
    return window.localStorage.getItem(TOKEN_STORAGE_KEY);
  } catch {
    return null;
  }
}

function storeToken(token: string): void {
  try {
    window.localStorage.setItem(TOKEN_STORAGE_KEY, token);
  } catch {
    // Local MVP fallback: the in-memory token still works for the current tab.
  }
}

function clearStoredToken(): void {
  try {
    window.localStorage.removeItem(TOKEN_STORAGE_KEY);
  } catch {
    // Non-critical during logout.
  }
}

function getErrorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  if (error instanceof Error) return error.message;
  return "Unable to complete authentication request.";
}

export function useAuth(): AuthState {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [company, setCompany] = useState<Company | null>(null);
  const [token, setToken] = useState<string | null>(() => getStoredToken());
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setApiAuthToken(token);
  }, [token]);

  useEffect(() => {
    let isActive = true;

    async function loadCurrentUser(): Promise<void> {
      if (!token) {
        setIsLoading(false);
        return;
      }

      setApiAuthToken(token);
      try {
        const session = await api.me();
        if (session.user.role === "employee") {
          try {
            await api.markPresenceOnline();
          } catch {
            // Presence is best-effort; an auth session should still load if it cannot update.
          }
        }
        if (!isActive) return;
        setUser(session.user);
        setCompany(session.company);
      } catch {
        if (!isActive) return;
        clearStoredToken();
        setToken(null);
        setUser(null);
        setCompany(null);
      } finally {
        if (isActive) setIsLoading(false);
      }
    }

    void loadCurrentUser();
    return () => {
      isActive = false;
    };
  }, [token]);

  useEffect(() => {
    if (!token || user?.role !== "employee") return;

    const markOffline = (): void => {
      void api.markPresenceOffline(true).catch(() => undefined);
    };

    window.addEventListener("pagehide", markOffline);
    window.addEventListener("beforeunload", markOffline);
    return () => {
      window.removeEventListener("pagehide", markOffline);
      window.removeEventListener("beforeunload", markOffline);
    };
  }, [token, user?.id, user?.role]);

  async function login(payload: LoginPayload): Promise<void> {
    setIsSubmitting(true);
    setError(null);
    try {
      const session = await api.login(payload);
      storeToken(session.access_token);
      setToken(session.access_token);
      setUser(session.user);
      setCompany(session.company);
    } catch (caughtError) {
      setError(getErrorMessage(caughtError));
      throw caughtError;
    } finally {
      setIsSubmitting(false);
    }
  }

  async function register(payload: RegisterPayload): Promise<void> {
    setIsSubmitting(true);
    setError(null);
    try {
      const session = await api.register(payload);
      storeToken(session.access_token);
      setToken(session.access_token);
      setUser(session.user);
      setCompany(session.company);
    } catch (caughtError) {
      setError(getErrorMessage(caughtError));
      throw caughtError;
    } finally {
      setIsSubmitting(false);
    }
  }

  async function logout(): Promise<void> {
    setIsSubmitting(true);
    setError(null);
    try {
      if (token) await api.logout();
    } catch {
      // Stateless local tokens are cleared client-side even if the server is unreachable.
    } finally {
      clearStoredToken();
      setApiAuthToken(null);
      setToken(null);
      setUser(null);
      setCompany(null);
      setIsSubmitting(false);
    }
  }

  return {
    user,
    company,
    token,
    isLoading,
    isSubmitting,
    error,
    isAuthenticated: Boolean(user && token),
    login,
    register,
    logout,
    clearError: () => setError(null),
  };
}
