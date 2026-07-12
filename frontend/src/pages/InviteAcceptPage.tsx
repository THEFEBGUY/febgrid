import { AlertTriangle, ArrowRight, CheckCircle2, Lock, MailCheck, ShieldCheck, UserRoundCheck } from "lucide-react";
import { type FormEvent, type ReactNode, useEffect, useRef, useState } from "react";

import { DotGrid } from "../components/premium/DotGrid";
import { Button } from "../components/ui/Button";
import { FieldShell, TextArea, TextInput } from "../components/ui/FormControls";
import { ErrorState, LoadingState } from "../components/ui/States";
import { api, ApiError, setApiAuthToken } from "../services/api";
import { getSupabaseClient, isSupabaseMagicLinkAvailable } from "../services/supabase";
import type { InvitationAcceptResult, InvitationPreview } from "../types/api";
import { compactList, formatDate, formatLabel } from "../utils/format";

const TOKEN_STORAGE_KEY = "febgrid.authToken";

interface InviteAcceptPageProps {
  token: string;
}

const initialAccountForm = {
  full_name: "",
  password: "",
  confirm_password: "",
};

const initialProfileForm = {
  full_name: "",
  phone: "",
  location: "",
  skills: "",
  bio: "",
  emergency_contact_name: "",
  emergency_contact_phone: "",
};

type AccountForm = typeof initialAccountForm;
type ProfileForm = typeof initialProfileForm;

function OnboardingShell({ children }: { children: ReactNode }): JSX.Element {
  return (
    <div className="febgrid-auth-bg relative min-h-screen overflow-x-clip text-ink-900">
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
      <div className="relative z-10 min-h-screen">{children}</div>
    </div>
  );
}

function storeSessionToken(token: string): void {
  try {
    window.localStorage.setItem(TOKEN_STORAGE_KEY, token);
  } catch {
    // In-memory API token still works until redirect reloads the app.
  }
  setApiAuthToken(token);
}

function needsProfileCompletion(preview: InvitationPreview): boolean {
  return preview.status === "accepted" && (
    preview.profile_completion_status === "needs_completion" ||
    preview.account_status === "profile_pending"
  );
}

function statusMessage(preview: InvitationPreview): string | null {
  if (preview.status === "accepted" && !needsProfileCompletion(preview)) {
    return "This invitation has already been accepted and completed. Ask your company admin to resend if you need a new onboarding link.";
  }
  if (preview.status === "approved") return "This employee profile has already been approved.";
  if (preview.status === "rejected") return "This employee profile was rejected. Ask your company admin for the next step.";
  if (preview.status === "revoked") return "This invitation has been revoked by the company.";
  if (preview.status === "expired") return "This invitation has expired. Ask your company admin to resend it.";
  if (preview.status === "submitted_for_approval") return "Your profile has already been submitted and is waiting for company approval.";
  return null;
}

export function InviteAcceptPage({ token }: InviteAcceptPageProps): JSX.Element {
  const [preview, setPreview] = useState<InvitationPreview | null>(null);
  const [accepted, setAccepted] = useState<InvitationAcceptResult | null>(null);
  const [accountForm, setAccountForm] = useState<AccountForm>(initialAccountForm);
  const [profileForm, setProfileForm] = useState<ProfileForm>(initialProfileForm);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [completionMessage, setCompletionMessage] = useState<string | null>(null);
  const [magicLinkMessage, setMagicLinkMessage] = useState<string | null>(null);
  const [isMagicLinkSubmitting, setIsMagicLinkSubmitting] = useState(false);
  const [previewRetry, setPreviewRetry] = useState(0);
  const magicSessionHandled = useRef(false);

  useEffect(() => {
    let isActive = true;
    const controller = new AbortController();

    async function loadPreview(): Promise<void> {
      setIsLoading(true);
      setError(null);
      try {
        const result = await api.previewInvitation(token, controller.signal);
        if (!isActive) return;
        setPreview(result);
        const displayName = result.employee_name ?? "";
        setAccountForm((current) => ({ ...current, full_name: displayName }));
        setProfileForm((current) => ({ ...current, full_name: displayName }));
      } catch (caughtError) {
        if (!isActive) return;
        if (caughtError instanceof ApiError) {
          if (caughtError.status === 499) return;
          setError(caughtError.status === 410 ? "This invite link is expired, revoked, or no longer available." : caughtError.message);
        } else {
          setError("Unable to load this invite.");
        }
      } finally {
        if (isActive) setIsLoading(false);
      }
    }

    void loadPreview();
    return () => {
      isActive = false;
      controller.abort();
    };
  }, [previewRetry, token]);

  useEffect(() => {
    if (!preview || accepted || magicSessionHandled.current || !isSupabaseMagicLinkAvailable) return;
    if (preview.status !== "pending" && preview.status !== "activation_sent") return;
    const client = getSupabaseClient();
    if (!client) return;
    const supabaseClient = client;
    const expectedEmail = preview.invited_email.trim().toLowerCase();
    let isActive = true;

    async function acceptVerifiedSession(): Promise<void> {
      const { data, error: sessionError } = await supabaseClient.auth.getSession();
      const accessToken = data.session?.access_token;
      const sessionEmail = data.session?.user.email?.trim().toLowerCase();
      if (!accessToken || sessionError || sessionEmail !== expectedEmail) return;
      magicSessionHandled.current = true;
      setIsMagicLinkSubmitting(true);
      setError(null);
      try {
        const result = await api.acceptInvitationWithMagicLink({ token, access_token: accessToken });
        if (!isActive) return;
        setAccepted(result);
        setProfileForm((current) => ({ ...current, full_name: result.employee.full_name }));
        setMagicLinkMessage("Email verified. Complete your profile to finish onboarding.");
      } catch (caughtError) {
        if (!isActive) return;
        setError(caughtError instanceof ApiError ? caughtError.message : "Unable to verify this magic-link session.");
      } finally {
        if (isActive) setIsMagicLinkSubmitting(false);
      }
    }

    void acceptVerifiedSession();
    return () => {
      isActive = false;
    };
  }, [accepted, preview, token]);

  async function sendMagicLink(): Promise<void> {
    if (!preview) return;
    const client = getSupabaseClient();
    if (!client) return;
    setError(null);
    setMagicLinkMessage(null);
    setIsMagicLinkSubmitting(true);
    try {
      const redirectTo = `${window.location.origin}/accept-invite/${encodeURIComponent(token)}`;
      const { error: magicError } = await client.auth.signInWithOtp({
        email: preview.invited_email,
        options: { emailRedirectTo: redirectTo },
      });
      if (magicError) throw magicError;
      setMagicLinkMessage(`A sign-in link was sent to ${preview.invited_email}. Open it in this browser to verify the invite.`);
    } catch {
      setError("Unable to send a magic link. Check the deployment's Supabase redirect configuration or use password onboarding.");
    } finally {
      setIsMagicLinkSubmitting(false);
    }
  }

  async function acceptInvite(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (!preview) return;
    setError(null);
    if (accountForm.password !== accountForm.confirm_password) {
      setError("Passwords do not match.");
      return;
    }
    setIsSubmitting(true);
    try {
      const result = await api.acceptInvitation({
        token,
        email: preview.invited_email,
        password: accountForm.password,
        full_name: accountForm.full_name.trim() || preview.employee_name,
      });
      setAccepted(result);
      setProfileForm((current) => ({
        ...current,
        full_name: result.employee.full_name,
      }));
    } catch (caughtError) {
      setError(caughtError instanceof ApiError ? caughtError.message : "Unable to accept this invite.");
    } finally {
      setIsSubmitting(false);
    }
  }

  async function completeProfile(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (!preview) return;
    setError(null);
    setIsSubmitting(true);
    try {
      const result = await api.completeInvitationProfile({
        token,
        email: preview.invited_email,
        full_name: profileForm.full_name.trim() || null,
        phone: profileForm.phone.trim() || null,
        location: profileForm.location.trim() || null,
        skills: profileForm.skills
          .split(",")
          .map((skill) => skill.trim())
          .filter(Boolean),
        bio: profileForm.bio.trim() || null,
        emergency_contact_name: profileForm.emergency_contact_name.trim() || null,
        emergency_contact_phone: profileForm.emergency_contact_phone.trim() || null,
        metadata: {},
      });
      if (result.session) {
        storeSessionToken(result.session.access_token);
        window.location.assign(`${window.location.origin}/#/dashboard`);
        return;
      }
      setCompletionMessage(result.message || "Your profile was submitted for approval.");
    } catch (caughtError) {
      setError(caughtError instanceof ApiError ? caughtError.message : "Unable to complete this profile.");
    } finally {
      setIsSubmitting(false);
    }
  }

  if (isLoading) {
    return (
      <OnboardingShell>
        <div className="min-h-screen px-4 py-10">
          <LoadingState label="Loading invitation" />
        </div>
      </OnboardingShell>
    );
  }

  if (error && !preview) {
    return (
      <OnboardingShell>
        <div className="min-h-screen px-4 py-10">
          <div className="febgrid-surface mx-auto max-w-2xl rounded-lg">
            <ErrorState message={error} onRetry={async () => { setPreviewRetry((value) => value + 1); }} />
          </div>
        </div>
      </OnboardingShell>
    );
  }

  if (!preview) {
    return (
      <OnboardingShell>
        <div className="min-h-screen px-4 py-10">
          <div className="febgrid-surface mx-auto max-w-2xl rounded-lg p-6">
            <p className="text-sm font-bold text-ink-950">Invite not found.</p>
          </div>
        </div>
      </OnboardingShell>
    );
  }

  const canCompletePendingProfile = needsProfileCompletion(preview);
  const terminalStatusMessage = statusMessage(preview);
  const assignment = compactList([preview.department_name, preview.team_name, preview.manager_name ? `Manager: ${preview.manager_name}` : null]) || "No org assignment";

  return (
    <OnboardingShell>
      <main className="mx-auto max-w-3xl space-y-4 px-4 py-10">
        <section className="febgrid-surface animate-fade-up overflow-hidden rounded-lg">
          <div className="border-b border-grid-200 bg-white/60 px-5 py-4">
            <div className="flex items-start gap-3">
              <span className="flex size-11 shrink-0 items-center justify-center rounded-lg bg-brand-600 text-white shadow-button">
                <UserRoundCheck className="size-5" aria-hidden="true" />
              </span>
              <div className="min-w-0">
                <p className="text-xs font-bold uppercase tracking-normal text-ink-500">FebGrid onboarding</p>
                <h1 className="mt-1 text-2xl font-black text-ink-950">{preview.company_name}</h1>
                <p className="mt-1 text-sm font-semibold text-ink-500">Review and accept your company invitation.</p>
              </div>
            </div>
          </div>

          <div className="grid gap-3 p-5 sm:grid-cols-2">
            <LockedFact label="Invited email" value={preview.invited_email} />
            <LockedFact label="Company role" value={formatLabel(preview.invited_role)} />
            <LockedFact label="Job title" value={preview.job_title ?? "Not assigned"} />
            <LockedFact label="Department / team" value={assignment} />
            <LockedFact label="Employment type" value={formatLabel(preview.employment_type)} />
            <LockedFact label="Joining date" value={formatDate(preview.joining_date)} />
            <LockedFact label="Pre-verification" value={preview.approval_required ? "Required before access" : "Direct after profile completion"} />
            <LockedFact label="Expires" value={formatDate(preview.expires_at)} />
          </div>
        </section>

        {terminalStatusMessage && !accepted ? (
          <section className="animate-fade-up rounded-lg border border-amber-200 bg-amber-50 p-5 text-amber-700 shadow-sm">
            <div className="flex gap-3">
              <AlertTriangle className="mt-0.5 size-5 shrink-0" aria-hidden="true" />
              <div>
                <h2 className="text-base font-black">Invite status: {formatLabel(preview.status)}</h2>
                <p className="mt-1 text-sm font-semibold">{terminalStatusMessage}</p>
              </div>
            </div>
          </section>
        ) : null}

        {!terminalStatusMessage && !accepted && !canCompletePendingProfile && !completionMessage ? (
          <section className="febgrid-surface animate-fade-up overflow-hidden rounded-lg">
            <div className="border-b border-grid-200 bg-white/60 px-5 py-4">
              <h2 className="text-lg font-black text-ink-950">Create a password and accept invitation</h2>
              <p className="mt-1 text-sm font-medium text-ink-500">The email, company, and role are locked by the invite. This option creates a FebGrid password.</p>
            </div>
            <form className="space-y-4 p-5" onSubmit={acceptInvite}>
              <FieldShell label="Email">
                <TextInput readOnly autoComplete="email" value={preview.invited_email} />
              </FieldShell>
              <FieldShell label="Full name">
                <TextInput value={accountForm.full_name} onChange={(event) => setAccountForm((current) => ({ ...current, full_name: event.target.value }))} />
              </FieldShell>
              <div className="grid gap-4 sm:grid-cols-2">
                <FieldShell label="Password">
                  <TextInput required autoComplete="new-password" minLength={8} type="password" value={accountForm.password} onChange={(event) => setAccountForm((current) => ({ ...current, password: event.target.value }))} />
                </FieldShell>
                <FieldShell label="Confirm password">
                  <TextInput
                    required
                    autoComplete="new-password"
                    minLength={8}
                    type="password"
                    value={accountForm.confirm_password}
                    onChange={(event) => setAccountForm((current) => ({ ...current, confirm_password: event.target.value }))}
                  />
                </FieldShell>
              </div>
              {error ? <p className="text-sm font-semibold text-rose-700">{error}</p> : null}
              <div className="flex justify-end border-t border-grid-200 pt-4">
                <Button disabled={isSubmitting} type="submit" variant="primary" icon={<ArrowRight className="size-4" aria-hidden="true" />}>
                  {isSubmitting ? "Accepting..." : "Create password and accept"}
                </Button>
              </div>
            </form>
            {isSupabaseMagicLinkAvailable ? (
              <div className="febgrid-auth-alternative border-t border-grid-200 px-5 py-4">
                <p className="text-sm font-bold text-ink-900">Prefer passwordless sign-in?</p>
                <p className="mt-1 text-sm text-ink-500">A secure email link signs in the locked invited email without creating a password. FebGrid still verifies the invite, company, status, and expiry.</p>
                {magicLinkMessage ? <p className="mt-3 text-sm font-semibold text-green-700">{magicLinkMessage}</p> : null}
                <Button
                  className="mt-3"
                  disabled={isMagicLinkSubmitting || isSubmitting}
                  onClick={() => void sendMagicLink()}
                  type="button"
                  variant="secondary"
                  icon={<MailCheck className="size-4" aria-hidden="true" />}
                >
                  {isMagicLinkSubmitting ? "Verifying..." : "Send magic link"}
                </Button>
              </div>
            ) : null}
          </section>
        ) : null}

        {(accepted || canCompletePendingProfile) && !completionMessage ? (
          <section className="febgrid-surface animate-fade-up overflow-hidden rounded-lg">
            <div className="border-b border-grid-200 bg-white/60 px-5 py-4">
              <h2 className="text-lg font-black text-ink-950">Complete profile</h2>
              <p className="mt-1 text-sm font-medium text-ink-500">Personal details only. Company-controlled fields stay locked.</p>
            </div>
            <form className="space-y-4 p-5" onSubmit={completeProfile}>
              <div className="grid gap-4 sm:grid-cols-2">
                <FieldShell label="Full name">
                  <TextInput value={profileForm.full_name} onChange={(event) => setProfileForm((current) => ({ ...current, full_name: event.target.value }))} />
                </FieldShell>
                <FieldShell label="Phone">
                  <TextInput value={profileForm.phone} onChange={(event) => setProfileForm((current) => ({ ...current, phone: event.target.value }))} />
                </FieldShell>
                <FieldShell label="Location">
                  <TextInput value={profileForm.location} onChange={(event) => setProfileForm((current) => ({ ...current, location: event.target.value }))} />
                </FieldShell>
                <FieldShell label="Skills">
                  <TextInput placeholder="Operations, Field work" value={profileForm.skills} onChange={(event) => setProfileForm((current) => ({ ...current, skills: event.target.value }))} />
                </FieldShell>
                <FieldShell label="Emergency contact name">
                  <TextInput value={profileForm.emergency_contact_name} onChange={(event) => setProfileForm((current) => ({ ...current, emergency_contact_name: event.target.value }))} />
                </FieldShell>
                <FieldShell label="Emergency contact phone">
                  <TextInput value={profileForm.emergency_contact_phone} onChange={(event) => setProfileForm((current) => ({ ...current, emergency_contact_phone: event.target.value }))} />
                </FieldShell>
              </div>
              <FieldShell label="Bio">
                <TextArea value={profileForm.bio} onChange={(event) => setProfileForm((current) => ({ ...current, bio: event.target.value }))} />
              </FieldShell>
              {error ? <p className="text-sm font-semibold text-rose-700">{error}</p> : null}
              <div className="flex justify-end border-t border-grid-200 pt-4">
                <Button disabled={isSubmitting} type="submit" variant="primary" icon={<ShieldCheck className="size-4" aria-hidden="true" />}>
                  {isSubmitting ? "Submitting..." : preview.approval_required ? "Submit for approval" : "Complete and enter FebGrid"}
                </Button>
              </div>
            </form>
          </section>
        ) : null}

        {completionMessage ? (
          <section className="animate-fade-up rounded-lg border border-green-200 bg-green-50 p-5 text-green-700 shadow-sm">
            <div className="flex gap-3">
              <CheckCircle2 className="mt-0.5 size-5 shrink-0" aria-hidden="true" />
              <div>
                <h2 className="text-base font-black">Onboarding submitted</h2>
                <p className="mt-1 text-sm font-semibold">{completionMessage}</p>
              </div>
            </div>
          </section>
        ) : null}
      </main>
    </OnboardingShell>
  );
}

function LockedFact({ label, value }: { label: string; value: string }): JSX.Element {
  return (
    <div className="febgrid-muted-surface rounded-lg p-4">
      <div className="flex items-center gap-2">
        <Lock className="size-3.5 text-ink-500" aria-hidden="true" />
        <p className="text-xs font-bold uppercase tracking-normal text-ink-500">{label}</p>
      </div>
      <p className="mt-2 text-sm font-bold text-ink-950">{value}</p>
    </div>
  );
}
