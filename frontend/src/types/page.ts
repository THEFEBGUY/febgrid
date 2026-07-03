import type { Company, FebGridData, UserRole } from "./api";

export interface ModulePageProps {
  data: FebGridData;
  selectedCompany: Company | null;
  isLoadingCompanies: boolean;
  isLoadingModules: boolean;
  isMutating: boolean;
  moduleError: string | null;
  currentUserRole?: UserRole | null;
  onRetry: () => Promise<void>;
}
