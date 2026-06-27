import { type FormEvent, useEffect, useState } from "react";
import { Save, UserCircle } from "lucide-react";

import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { FieldShell, TextInput } from "../components/ui/FormControls";
import { SectionPanel } from "../components/ui/SectionPanel";
import { ErrorState, LoadingState } from "../components/ui/States";
import { api } from "../services/api";
import type { Company, Employee, EmployeeSelfUpdatePayload } from "../types/api";
import { compactList, formatDate, formatLabel } from "../utils/format";

interface MyProfilePageProps {
  selectedCompany: Company | null;
  onProfileSaved: () => Promise<void>;
}

interface ProfileForm {
  full_name: string;
  phone: string;
  location: string;
  profile_image_url: string;
  skills: string;
}

function formFromEmployee(employee: Employee): ProfileForm {
  return {
    full_name: employee.full_name,
    phone: employee.phone ?? "",
    location: employee.location ?? "",
    profile_image_url: employee.profile_image_url ?? "",
    skills: employee.skills.join(", "),
  };
}

export function MyProfilePage({ selectedCompany, onProfileSaved }: MyProfilePageProps): JSX.Element {
  const [profile, setProfile] = useState<Employee | null>(null);
  const [form, setForm] = useState<ProfileForm | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  async function loadProfile(): Promise<void> {
    setIsLoading(true);
    setError(null);
    try {
      const nextProfile = await api.employeeMe();
      setProfile(nextProfile);
      setForm(formFromEmployee(nextProfile));
    } catch {
      setError("Unable to load your employee profile.");
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    void loadProfile();
  }, []);

  async function handleSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (!form) return;
    if (!form.full_name.trim()) {
      setError("Full name is required.");
      return;
    }

    const payload: EmployeeSelfUpdatePayload = {
      full_name: form.full_name.trim(),
      phone: form.phone.trim() || null,
      location: form.location.trim() || null,
      profile_image_url: form.profile_image_url.trim() || null,
      skills: form.skills
        .split(",")
        .map((skill) => skill.trim())
        .filter(Boolean),
    };

    setIsSaving(true);
    setError(null);
    setSuccessMessage(null);
    try {
      const nextProfile = await api.updateEmployeeMe(payload);
      setProfile(nextProfile);
      setForm(formFromEmployee(nextProfile));
      setSuccessMessage("Profile updated.");
      await onProfileSaved();
    } catch {
      setError("Unable to update your profile. Check the details and try again.");
    } finally {
      setIsSaving(false);
    }
  }

  if (isLoading) {
    return <LoadingState label="Loading my profile" />;
  }

  if (error && !profile) {
    return <ErrorState message={error} onRetry={loadProfile} />;
  }

  return (
    <SectionPanel eyebrow={selectedCompany?.name ?? "My company"} title="My Profile">
      {profile && form ? (
        <div className="grid gap-6 p-5 xl:grid-cols-[0.85fr_1.15fr]">
          <aside className="space-y-4">
            <div className="rounded-lg border border-grid-200 bg-grid-50 p-5">
              <div className="flex items-start gap-3">
                <span className="flex size-12 shrink-0 items-center justify-center rounded-lg bg-white text-ink-700 ring-1 ring-grid-200">
                  <UserCircle className="size-6" aria-hidden="true" />
                </span>
                <div className="min-w-0">
                  <p className="truncate text-lg font-black text-ink-950">{profile.full_name}</p>
                  <p className="mt-1 truncate text-sm font-semibold text-ink-500">{profile.email ?? "No email recorded"}</p>
                  <div className="mt-3 flex flex-wrap gap-2">
                    <Badge label={formatLabel(profile.account_status)} tone={profile.account_status === "active" ? "green" : "amber"} />
                    <Badge label={formatLabel(profile.profile_completion_status)} tone="blue" />
                  </div>
                </div>
              </div>
            </div>

            <ReadOnlyItem label="Company" value={selectedCompany?.name ?? "Assigned company"} />
            <ReadOnlyItem label="Job title" value={profile.role_title} />
            <ReadOnlyItem label="Department" value={profile.department ?? "Not assigned"} />
            <ReadOnlyItem label="Team" value={profile.team_id ? "Assigned team" : "Not assigned"} />
            <ReadOnlyItem label="Manager" value={profile.manager_id ? "Assigned manager" : "Not assigned"} />
            <ReadOnlyItem label="Employment" value={compactList([formatLabel(profile.employment_type), profile.joined_at ? `Joined ${formatDate(profile.joined_at)}` : null])} />
            <ReadOnlyItem label="Current status" value={formatLabel(profile.current_status)} />
          </aside>

          <form className="space-y-4 rounded-lg border border-grid-200 bg-white p-5" onSubmit={handleSubmit}>
            <div>
              <p className="text-sm font-black text-ink-950">Personal details</p>
              <p className="mt-1 text-sm font-medium text-ink-500">You can update safe personal fields. Company, role, department, team, and manager stay controlled by admins.</p>
            </div>
            <FieldShell label="Full name">
              <TextInput required value={form.full_name} onChange={(event) => setForm((current) => current ? { ...current, full_name: event.target.value } : current)} />
            </FieldShell>
            <div className="grid gap-4 sm:grid-cols-2">
              <FieldShell label="Phone">
                <TextInput value={form.phone} onChange={(event) => setForm((current) => current ? { ...current, phone: event.target.value } : current)} />
              </FieldShell>
              <FieldShell label="Location">
                <TextInput value={form.location} onChange={(event) => setForm((current) => current ? { ...current, location: event.target.value } : current)} />
              </FieldShell>
            </div>
            <FieldShell label="Profile image URL">
              <TextInput value={form.profile_image_url} onChange={(event) => setForm((current) => current ? { ...current, profile_image_url: event.target.value } : current)} />
            </FieldShell>
            <FieldShell label="Skills">
              <TextInput placeholder="React, customer support, site operations" value={form.skills} onChange={(event) => setForm((current) => current ? { ...current, skills: event.target.value } : current)} />
            </FieldShell>
            {error ? <p className="text-sm font-semibold text-rose-700">{error}</p> : null}
            {successMessage ? <p className="text-sm font-semibold text-emerald-700">{successMessage}</p> : null}
            <div className="flex justify-end border-t border-grid-200 pt-4">
              <Button disabled={isSaving} type="submit" variant="primary" icon={<Save className="size-4" aria-hidden="true" />}>
                {isSaving ? "Saving..." : "Save profile"}
              </Button>
            </div>
          </form>
        </div>
      ) : null}
    </SectionPanel>
  );
}

function ReadOnlyItem({ label, value }: { label: string; value: string }): JSX.Element {
  return (
    <div className="rounded-lg border border-grid-200 bg-white p-4">
      <p className="text-xs font-bold uppercase tracking-normal text-ink-500">{label}</p>
      <p className="mt-2 text-sm font-bold text-ink-950">{value}</p>
    </div>
  );
}
