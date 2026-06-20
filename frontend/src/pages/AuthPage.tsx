import { ArrowRight, Building2, LogIn, UserPlus, Zap } from "lucide-react";
import { type FormEvent, useState } from "react";

import { Button } from "../components/ui/Button";
import { FieldShell, TextInput } from "../components/ui/FormControls";
import type { LoginPayload, RegisterPayload } from "../types/api";
import { makeSlug } from "../utils/format";

type AuthMode = "login" | "signup";

interface AuthPageProps {
  error: string | null;
  isSubmitting: boolean;
  onClearError: () => void;
  onLogin: (payload: LoginPayload) => Promise<void>;
  onRegister: (payload: RegisterPayload) => Promise<void>;
}

const loginInitial = {
  email: "",
  password: "",
};

const signupInitial = {
  full_name: "",
  email: "",
  password: "",
  company_name: "",
  company_slug: "",
  industry: "",
  size: "",
  timezone: "Asia/Calcutta",
};

export function AuthPage({ error, isSubmitting, onClearError, onLogin, onRegister }: AuthPageProps): JSX.Element {
  const [mode, setMode] = useState<AuthMode>("login");
  const [loginForm, setLoginForm] = useState(loginInitial);
  const [signupForm, setSignupForm] = useState(signupInitial);
  const [formError, setFormError] = useState<string | null>(null);

  function switchMode(nextMode: AuthMode): void {
    setMode(nextMode);
    setFormError(null);
    onClearError();
  }

  async function handleLogin(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    setFormError(null);
    try {
      await onLogin({
        email: loginForm.email.trim(),
        password: loginForm.password,
      });
    } catch {
      setFormError("Check your email and password, then try again.");
    }
  }

  async function handleSignup(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    setFormError(null);

    const companySlug = signupForm.company_slug.trim() || makeSlug(signupForm.company_name);
    if (companySlug.length < 2) {
      setFormError("Company slug must be at least 2 characters.");
      return;
    }

    try {
      await onRegister({
        full_name: signupForm.full_name.trim(),
        email: signupForm.email.trim(),
        password: signupForm.password,
        company_name: signupForm.company_name.trim(),
        company_slug: companySlug,
        industry: signupForm.industry.trim() || null,
        size: signupForm.size.trim() || null,
        timezone: signupForm.timezone.trim() || "UTC",
      });
    } catch {
      setFormError("Account could not be created. Check the details and try again.");
    }
  }

  return (
    <main className="min-h-screen bg-grid-50 text-ink-900">
      <div className="mx-auto grid min-h-screen w-full max-w-6xl items-center gap-8 px-4 py-8 lg:grid-cols-[0.9fr_1.1fr] lg:px-8">
        <section className="space-y-8">
          <div className="flex items-center gap-3">
            <span className="flex size-12 items-center justify-center rounded-lg bg-ink-950 text-white">
              <Zap className="size-6" aria-hidden="true" />
            </span>
            <div>
              <p className="text-xl font-black text-ink-950">FebGrid</p>
              <p className="text-sm font-semibold text-ink-500">Business Operating System</p>
            </div>
          </div>

          <div className="max-w-xl">
            <p className="text-sm font-bold uppercase tracking-normal text-blue-700">Company and user foundation</p>
            <h1 className="mt-4 text-4xl font-black tracking-normal text-ink-950 sm:text-5xl">Enter your operating layer.</h1>
            <p className="mt-4 text-base font-medium leading-7 text-ink-500">
              Create a company owner account, connect it to one tenant, and start running Phase 1 operations from a protected workspace.
            </p>
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            <div className="rounded-lg border border-grid-200 bg-white p-4 shadow-sm">
              <Building2 className="size-5 text-ink-700" aria-hidden="true" />
              <p className="mt-3 text-sm font-bold text-ink-950">Tenant boundary</p>
              <p className="mt-1 text-sm font-medium text-ink-500">Company data stays scoped to the authenticated account.</p>
            </div>
            <div className="rounded-lg border border-grid-200 bg-white p-4 shadow-sm">
              <UserPlus className="size-5 text-ink-700" aria-hidden="true" />
              <p className="mt-3 text-sm font-bold text-ink-950">Owner role</p>
              <p className="mt-1 text-sm font-medium text-ink-500">The first signup becomes company_owner for Sprint 2.</p>
            </div>
          </div>
        </section>

        <section className="rounded-lg border border-grid-200 bg-white shadow-soft">
          <div className="flex border-b border-grid-200 p-2">
            <button
              className={`flex h-11 flex-1 items-center justify-center gap-2 rounded-md text-sm font-bold transition ${
                mode === "login" ? "bg-ink-950 text-white" : "text-ink-600 hover:bg-grid-100"
              }`}
              type="button"
              onClick={() => switchMode("login")}
            >
              <LogIn className="size-4" aria-hidden="true" />
              Login
            </button>
            <button
              className={`flex h-11 flex-1 items-center justify-center gap-2 rounded-md text-sm font-bold transition ${
                mode === "signup" ? "bg-ink-950 text-white" : "text-ink-600 hover:bg-grid-100"
              }`}
              type="button"
              onClick={() => switchMode("signup")}
            >
              <UserPlus className="size-4" aria-hidden="true" />
              Signup
            </button>
          </div>

          {mode === "login" ? (
            <form className="space-y-4 p-5 sm:p-6" onSubmit={handleLogin}>
              <div>
                <h2 className="text-xl font-black text-ink-950">Welcome back</h2>
                <p className="mt-1 text-sm font-medium text-ink-500">Use your company account to open the dashboard.</p>
              </div>
              <FieldShell label="Email">
                <TextInput required type="email" value={loginForm.email} onChange={(event) => setLoginForm((current) => ({ ...current, email: event.target.value }))} />
              </FieldShell>
              <FieldShell label="Password">
                <TextInput required minLength={8} type="password" value={loginForm.password} onChange={(event) => setLoginForm((current) => ({ ...current, password: event.target.value }))} />
              </FieldShell>
              {formError || error ? <p className="text-sm font-semibold text-rose-700">{formError ?? error}</p> : null}
              <Button disabled={isSubmitting} type="submit" variant="primary" className="w-full" icon={<ArrowRight className="size-4" aria-hidden="true" />}>
                {isSubmitting ? "Signing in..." : "Enter dashboard"}
              </Button>
            </form>
          ) : (
            <form className="space-y-4 p-5 sm:p-6" onSubmit={handleSignup}>
              <div>
                <h2 className="text-xl font-black text-ink-950">Create company account</h2>
                <p className="mt-1 text-sm font-medium text-ink-500">Set up the first owner and company tenant.</p>
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                <FieldShell label="Full name">
                  <TextInput required value={signupForm.full_name} onChange={(event) => setSignupForm((current) => ({ ...current, full_name: event.target.value }))} />
                </FieldShell>
                <FieldShell label="Email">
                  <TextInput required type="email" value={signupForm.email} onChange={(event) => setSignupForm((current) => ({ ...current, email: event.target.value }))} />
                </FieldShell>
                <FieldShell label="Password">
                  <TextInput required minLength={8} type="password" value={signupForm.password} onChange={(event) => setSignupForm((current) => ({ ...current, password: event.target.value }))} />
                </FieldShell>
                <FieldShell label="Company name">
                  <TextInput
                    required
                    value={signupForm.company_name}
                    onChange={(event) => setSignupForm((current) => ({ ...current, company_name: event.target.value, company_slug: current.company_slug || makeSlug(event.target.value) }))}
                  />
                </FieldShell>
                <FieldShell label="Company slug">
                  <TextInput required value={signupForm.company_slug} onChange={(event) => setSignupForm((current) => ({ ...current, company_slug: makeSlug(event.target.value) }))} />
                </FieldShell>
                <FieldShell label="Industry">
                  <TextInput value={signupForm.industry} onChange={(event) => setSignupForm((current) => ({ ...current, industry: event.target.value }))} />
                </FieldShell>
                <FieldShell label="Company size">
                  <TextInput value={signupForm.size} onChange={(event) => setSignupForm((current) => ({ ...current, size: event.target.value }))} />
                </FieldShell>
                <FieldShell label="Timezone">
                  <TextInput value={signupForm.timezone} onChange={(event) => setSignupForm((current) => ({ ...current, timezone: event.target.value }))} />
                </FieldShell>
              </div>
              {formError || error ? <p className="text-sm font-semibold text-rose-700">{formError ?? error}</p> : null}
              <Button disabled={isSubmitting} type="submit" variant="primary" className="w-full" icon={<ArrowRight className="size-4" aria-hidden="true" />}>
                {isSubmitting ? "Creating account..." : "Create account"}
              </Button>
            </form>
          )}
        </section>
      </div>
    </main>
  );
}
