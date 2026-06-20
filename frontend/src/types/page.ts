import type { Company, FebGridData } from "./api";

export interface ModulePageProps {
  data: FebGridData;
  selectedCompany: Company | null;
  isLoadingCompanies: boolean;
  isLoadingModules: boolean;
  isMutating: boolean;
  moduleError: string | null;
  onRetry: () => Promise<void>;
}
