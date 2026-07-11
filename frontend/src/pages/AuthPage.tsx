import { ArrowRight, Building2, Layers3, LogIn, ShieldCheck, Sparkles, UserPlus, Zap } from "lucide-react";
import { type FormEvent, useState } from "react";

import { DotGrid } from "../components/premium/DotGrid";
import { MagicBentoCard, MagicBentoGrid } from "../components/premium/MagicBento";
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
    <main className="febgrid-auth-bg relative min-h-screen overflow-x-clip text-ink-900">
      <DotGrid
        className="febgrid-dot-grid"
        baseColor="#2F293A"
        activeColor="#5227FF"
        dotSize={5}
        gap={15}
        proximity={120}
        shockRadius={250}
        shockStrength={5}
        resistance={750}
        returnDuration={1.5}
      />
      <div className="relative z-10 mx-auto grid min-h-screen w-full max-w-7xl items-center gap-8 px-4 py-8 lg:grid-cols-[1.02fr_0.98fr] lg:px-8">
        <section className="animate-fade-up space-y-7">
          <div className="flex items-center gap-3">
            <span className="flex size-12 items-center justify-center rounded-lg bg-brand-600 text-white shadow-button">
              <Zap className="size-6" aria-hidden="true" />
            </span>
            <div>
              <p className="text-xl font-black text-ink-950">FebGrid</p>
              <p className="text-sm font-semibold text-ink-500">Business Operating System</p>
            </div>
          </div>

          <div className="max-w-xl">
            <p className="text-sm font-black uppercase tracking-normal text-brand-600">Company operating layer</p>
            <h1 className="mt-4 text-4xl font-black tracking-normal text-ink-950 sm:text-6xl">Enter your operating layer.</h1>
            <p className="mt-4 text-base font-semibold leading-7 text-ink-600 sm:text-lg">
              One protected workspace for people, work, files, events, notifications, and company memory.
            </p>
          </div>

          <MagicBentoGrid className="grid-cols-1 sm:grid-cols-2">
            <MagicBentoCard className="p-4" tone="blue" eyebrow="Tenant safe" title="Every company stays isolated" description="Company data, roles, files, and events stay scoped to one operating tenant.">
              <Building2 className="mt-4 size-5 text-brand-600" aria-hidden="true" />
            </MagicBentoCard>
            <MagicBentoCard className="p-4" tone="teal" eyebrow="Company memory" title="Events become history" description="Work, approvals, comments, uploads, and notifications all contribute to the timeline.">
              <Layers3 className="mt-4 size-5 text-teal-700" aria-hidden="true" />
            </MagicBentoCard>
            <MagicBentoCard className="p-4 sm:col-span-2" tone="amber" eyebrow="Operational command" title="Built for owners, managers, and employees" description="Admin and employee views stay role-aware while preserving the same business operating system underneath.">
              <div className="mt-5 grid gap-2 sm:grid-cols-3">
                {["People", "Work Objects", "Timeline"].map((label) => (
                  <span key={label} className="rounded-md border border-grid-200 bg-white/60 px-3 py-2 text-xs font-black uppercase text-ink-700">
                    {label}
                  </span>
                ))}
              </div>
            </MagicBentoCard>
          </MagicBentoGrid>
        </section>

        <MagicBentoCard className="animate-fade-up overflow-hidden p-0" tone="blue">
          <div className="flex border-b border-grid-200 bg-white/60 p-2">
            <button
              className={`flex h-11 flex-1 items-center justify-center gap-2 rounded-md text-sm font-bold transition ${
                mode === "login" ? "bg-brand-600 text-white shadow-button" : "text-ink-600 hover:bg-grid-100"
              }`}
              type="button"
              onClick={() => switchMode("login")}
            >
              <LogIn className="size-4" aria-hidden="true" />
              Login
            </button>
            <button
              className={`flex h-11 flex-1 items-center justify-center gap-2 rounded-md text-sm font-bold transition ${
                mode === "signup" ? "bg-brand-600 text-white shadow-button" : "text-ink-600 hover:bg-grid-100"
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
                <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-brand-200 bg-brand-50 px-3 py-1 text-xs font-black uppercase text-brand-700">
                  <ShieldCheck className="size-3.5" aria-hidden="true" />
                  Secure tenant session
                </div>
                <h2 className="text-xl font-black text-ink-950">Welcome back</h2>
                <p className="mt-1 text-sm font-medium text-ink-500">Use your company account to open the dashboard.</p>
              </div>
              <FieldShell label="Email">
                <TextInput required autoComplete="email" type="email" value={loginForm.email} onChange={(event) => setLoginForm((current) => ({ ...current, email: event.target.value }))} />
              </FieldShell>
              <FieldShell label="Password">
                <TextInput required autoComplete="current-password" minLength={8} type="password" value={loginForm.password} onChange={(event) => setLoginForm((current) => ({ ...current, password: event.target.value }))} />
              </FieldShell>
              {formError || error ? <p className="text-sm font-semibold text-rose-700">{formError ?? error}</p> : null}
              <Button disabled={isSubmitting} type="submit" variant="primary" className="w-full" icon={<ArrowRight className="size-4" aria-hidden="true" />}>
                {isSubmitting ? "Signing in..." : "Enter dashboard"}
              </Button>
            </form>
          ) : (
            <form className="space-y-4 p-5 sm:p-6" onSubmit={handleSignup}>
              <div>
                <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-brand-200 bg-brand-50 px-3 py-1 text-xs font-black uppercase text-brand-700">
                  <Sparkles className="size-3.5" aria-hidden="true" />
                  Create operating tenant
                </div>
                <h2 className="text-xl font-black text-ink-950">Create company account</h2>
                <p className="mt-1 text-sm font-medium text-ink-500">Set up the first owner and company tenant.</p>
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                <FieldShell label="Full name">
                  <TextInput required value={signupForm.full_name} onChange={(event) => setSignupForm((current) => ({ ...current, full_name: event.target.value }))} />
                </FieldShell>
                <FieldShell label="Email">
                  <TextInput required autoComplete="email" type="email" value={signupForm.email} onChange={(event) => setSignupForm((current) => ({ ...current, email: event.target.value }))} />
                </FieldShell>
                <FieldShell label="Password">
                  <TextInput required autoComplete="new-password" minLength={8} type="password" value={signupForm.password} onChange={(event) => setSignupForm((current) => ({ ...current, password: event.target.value }))} />
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
        </MagicBentoCard>
      </div>
    </main>
  );
}
