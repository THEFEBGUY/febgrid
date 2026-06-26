import { AlertTriangle, ArrowRight, CheckCircle2, Lock, ShieldCheck, UserRoundCheck } from "lucide-react";
import { type FormEvent, useEffect, useState } from "react";

import { Button } from "../components/ui/Button";
import { FieldShell, TextArea, TextInput } from "../components/ui/FormControls";
import { ErrorState, LoadingState } from "../components/ui/States";
import { api, ApiError, setApiAuthToken } from "../services/api";
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

function storeSessionToken(token: string): void {
  try {
    window.localStorage.setItem(TOKEN_STORAGE_KEY, token);
  } catch {
    // In-memory API token still works until redirect reloads the app.
  }
  setApiAuthToken(token);
}

function statusMessage(status: string): string | null {
  if (status === "accepted") return "This invitation has already been accepted. Continue from the original onboarding session or ask your company admin to resend if needed.";
  if (status === "approved") return "This employee profile has already been approved.";
  if (status === "rejected") return "This employee profile was rejected. Ask your company admin for the next step.";
  if (status === "revoked") return "This invitation has been revoked by the company.";
  if (status === "expired") return "This invitation has expired. Ask your company admin to resend it.";
  if (status === "submitted_for_approval") return "Your profile has already been submitted and is waiting for company approval.";
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

  useEffect(() => {
    let isActive = true;

    async function loadPreview(): Promise<void> {
      setIsLoading(true);
      setError(null);
      try {
        const result = await api.previewInvitation(token);
        if (!isActive) return;
        setPreview(result);
        const displayName = result.employee_name ?? "";
        setAccountForm((current) => ({ ...current, full_name: displayName }));
        setProfileForm((current) => ({ ...current, full_name: displayName }));
      } catch (caughtError) {
        if (!isActive) return;
        if (caughtError instanceof ApiError) {
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
    };
  }, [token]);

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
      <div className="min-h-screen bg-grid-50 px-4 py-10">
        <LoadingState label="Loading invitation" />
      </div>
    );
  }

  if (error && !preview) {
    return (
      <div className="min-h-screen bg-grid-50 px-4 py-10">
        <div className="mx-auto max-w-2xl rounded-lg border border-grid-200 bg-white shadow-sm">
          <ErrorState message={error} onRetry={() => window.location.reload()} />
        </div>
      </div>
    );
  }

  if (!preview) {
    return (
      <div className="min-h-screen bg-grid-50 px-4 py-10">
        <div className="mx-auto max-w-2xl rounded-lg border border-grid-200 bg-white p-6 shadow-sm">
          <p className="text-sm font-bold text-ink-950">Invite not found.</p>
        </div>
      </div>
    );
  }

  const terminalStatusMessage = statusMessage(preview.status);
  const assignment = compactList([preview.department_name, preview.team_name, preview.manager_name ? `Manager: ${preview.manager_name}` : null]) || "No org assignment";

  return (
    <div className="min-h-screen bg-grid-50 px-4 py-10">
      <main className="mx-auto max-w-3xl space-y-4">
        <section className="rounded-lg border border-grid-200 bg-white shadow-sm">
          <div className="border-b border-grid-200 px-5 py-4">
            <div className="flex items-start gap-3">
              <span className="flex size-11 shrink-0 items-center justify-center rounded-lg bg-ink-950 text-white">
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
          <section className="rounded-lg border border-amber-200 bg-amber-50 p-5 text-amber-700">
            <div className="flex gap-3">
              <AlertTriangle className="mt-0.5 size-5 shrink-0" aria-hidden="true" />
              <div>
                <h2 className="text-base font-black">Invite status: {formatLabel(preview.status)}</h2>
                <p className="mt-1 text-sm font-semibold">{terminalStatusMessage}</p>
              </div>
            </div>
          </section>
        ) : null}

        {!terminalStatusMessage && !accepted && !completionMessage ? (
          <section className="rounded-lg border border-grid-200 bg-white shadow-sm">
            <div className="border-b border-grid-200 px-5 py-4">
              <h2 className="text-lg font-black text-ink-950">Accept invitation</h2>
              <p className="mt-1 text-sm font-medium text-ink-500">The email, company, and role are locked by the invite.</p>
            </div>
            <form className="space-y-4 p-5" onSubmit={acceptInvite}>
              <FieldShell label="Email">
                <TextInput readOnly value={preview.invited_email} />
              </FieldShell>
              <FieldShell label="Full name">
                <TextInput value={accountForm.full_name} onChange={(event) => setAccountForm((current) => ({ ...current, full_name: event.target.value }))} />
              </FieldShell>
              <div className="grid gap-4 sm:grid-cols-2">
                <FieldShell label="Password">
                  <TextInput required minLength={8} type="password" value={accountForm.password} onChange={(event) => setAccountForm((current) => ({ ...current, password: event.target.value }))} />
                </FieldShell>
                <FieldShell label="Confirm password">
                  <TextInput
                    required
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
                  {isSubmitting ? "Accepting..." : "Accept with this email"}
                </Button>
              </div>
            </form>
          </section>
        ) : null}

        {accepted && !completionMessage ? (
          <section className="rounded-lg border border-grid-200 bg-white shadow-sm">
            <div className="border-b border-grid-200 px-5 py-4">
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
          <section className="rounded-lg border border-green-200 bg-green-50 p-5 text-green-700">
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
    </div>
  );
}

function LockedFact({ label, value }: { label: string; value: string }): JSX.Element {
  return (
    <div className="rounded-lg border border-grid-200 bg-grid-50 p-4">
      <div className="flex items-center gap-2">
        <Lock className="size-3.5 text-ink-500" aria-hidden="true" />
        <p className="text-xs font-bold uppercase tracking-normal text-ink-500">{label}</p>
      </div>
      <p className="mt-2 text-sm font-bold text-ink-950">{value}</p>
    </div>
  );
}
