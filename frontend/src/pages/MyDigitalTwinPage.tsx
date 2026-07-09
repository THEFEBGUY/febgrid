import { useEffect, useState } from "react";

import { DigitalTwinPanel } from "../components/employee/DigitalTwinPanel";
import { SectionPanel } from "../components/ui/SectionPanel";
import { ErrorState, LoadingState } from "../components/ui/States";
import { api } from "../services/api";
import type { EmployeeDigitalTwinSnapshot } from "../types/api";
import type { ModulePageProps } from "../types/page";

export function MyDigitalTwinPage({ data, selectedCompany, isLoadingModules, moduleError, onRetry }: ModulePageProps): JSX.Element {
  const profile = data.employees[0] ?? null;
  const [periodDays, setPeriodDays] = useState(30);
  const [twin, setTwin] = useState<EmployeeDigitalTwinSnapshot | null>(null);
  const [history, setHistory] = useState<EmployeeDigitalTwinSnapshot[]>([]);
  const [isLoadingTwin, setIsLoadingTwin] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [twinError, setTwinError] = useState<string | null>(null);
  const profileId = profile?.id ?? null;
  const selectedCompanyId = selectedCompany?.id ?? null;

  async function loadTwin(employeeId: string, companyId: string): Promise<void> {
    setIsLoadingTwin(true);
    setTwinError(null);
    try {
      const [latest, nextHistory] = await Promise.all([
        api.latestEmployeeDigitalTwin(employeeId, companyId),
        api.employeeDigitalTwinHistory(employeeId, companyId, 8),
      ]);
      setTwin(latest);
      setHistory(nextHistory);
    } catch {
      setTwinError("Unable to load your Digital Twin snapshot.");
    } finally {
      setIsLoadingTwin(false);
    }
  }

  useEffect(() => {
    if (!profileId || !selectedCompanyId) return;
    void loadTwin(profileId, selectedCompanyId);
  }, [profileId, selectedCompanyId]);

  async function handleGenerate(): Promise<void> {
    if (!profile || !selectedCompany) return;
    setIsGenerating(true);
    setTwinError(null);
    try {
      const nextTwin = await api.generateEmployeeDigitalTwin(profile.id, selectedCompany.id, periodDays);
      setTwin(nextTwin);
      const nextHistory = await api.employeeDigitalTwinHistory(profile.id, selectedCompany.id, 8);
      setHistory(nextHistory);
    } catch {
      setTwinError("Unable to generate your Digital Twin snapshot.");
    } finally {
      setIsGenerating(false);
    }
  }

  if (isLoadingModules) {
    return <LoadingState label="Loading your Digital Twin" />;
  }

  if (moduleError) {
    return <ErrorState message={moduleError} onRetry={onRetry} />;
  }

  return (
    <SectionPanel eyebrow={selectedCompany?.name ?? "My company"} title="My Digital Twin">
      <div className="p-5">
        <DigitalTwinPanel
          title={profile ? `${profile.full_name}'s Digital Twin` : "My Digital Twin"}
          twin={twin}
          history={history}
          isLoading={isLoadingTwin}
          isGenerating={isGenerating}
          error={twinError}
          onGenerate={handleGenerate}
          periodDays={periodDays}
          onPeriodChange={setPeriodDays}
        />
      </div>
    </SectionPanel>
  );
}
