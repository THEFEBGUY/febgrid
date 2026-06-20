import { Plus } from "lucide-react";
import { type FormEvent, useState } from "react";

import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { DataTable, type DataTableColumn } from "../components/ui/DataTable";
import { FieldShell, TextArea, TextInput } from "../components/ui/FormControls";
import { Modal } from "../components/ui/Modal";
import { ModuleBoundary } from "../components/ui/ModuleBoundary";
import { SectionPanel } from "../components/ui/SectionPanel";
import { statusTone } from "../components/ui/tone";
import type { Company, CompanyCreatePayload } from "../types/api";
import type { ModulePageProps } from "../types/page";
import { formatDate, makeSlug } from "../utils/format";

const columns: DataTableColumn<Company>[] = [
  { key: "name", label: "Company", render: (company) => <span className="font-bold text-ink-950">{company.name}</span> },
  { key: "industry", label: "Industry", render: (company) => company.industry ?? "Not set" },
  { key: "size", label: "Size", render: (company) => company.size ?? "Not set" },
  { key: "timezone", label: "Timezone", render: (company) => company.timezone },
  { key: "created", label: "Created", render: (company) => formatDate(company.created_at) },
  { key: "status", label: "Status", render: (company) => <Badge label={company.is_active ? "Active" : "Paused"} tone={statusTone(company.is_active ? "Active" : "Paused")} /> },
];

interface CompaniesPageProps extends ModulePageProps {
  onCreateCompany: (payload: CompanyCreatePayload) => Promise<void>;
}

const initialForm = {
  name: "",
  slug: "",
  industry: "",
  size: "",
  timezone: "Asia/Calcutta",
  description: "",
};

export function CompaniesPage({ data, isLoadingCompanies, onCreateCompany, isMutating }: CompaniesPageProps): JSX.Element {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [form, setForm] = useState(initialForm);
  const [formError, setFormError] = useState<string | null>(null);

  function openModal(): void {
    setForm(initialForm);
    setFormError(null);
    setIsModalOpen(true);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    setFormError(null);

    const slug = form.slug.trim() || makeSlug(form.name);
    if (!slug) {
      setFormError("Company slug is required.");
      return;
    }
    if (slug.length < 2) {
      setFormError("Company slug must be at least 2 characters.");
      return;
    }

    try {
      await onCreateCompany({
        name: form.name.trim(),
        slug,
        industry: form.industry.trim() || null,
        size: form.size.trim() || null,
        timezone: form.timezone.trim() || "UTC",
        description: form.description.trim() || null,
        settings: {},
      });
      setIsModalOpen(false);
    } catch {
      setFormError("Company could not be created. Check the details and try again.");
    }
  }

  return (
    <>
      <SectionPanel
        eyebrow="Tenant foundation"
        title="Companies"
        action={<Button variant="primary" icon={<Plus className="size-4" aria-hidden="true" />} onClick={openModal}>New company</Button>}
      >
        <ModuleBoundary
          emptyDescription="Create the first company tenant before adding people, projects, work objects, leaves, or notifications."
          emptyTitle="No companies yet"
          error={null}
          isEmpty={data.companies.length === 0}
          isLoading={isLoadingCompanies}
          onRetry={() => Promise.resolve()}
          emptyAction={<Button variant="primary" icon={<Plus className="size-4" aria-hidden="true" />} onClick={openModal}>New company</Button>}
        >
          <DataTable columns={columns} rows={data.companies} getRowKey={(company) => company.id} />
        </ModuleBoundary>
      </SectionPanel>

      <Modal description="Create a tenant record with UUID-backed data separation." isOpen={isModalOpen} title="New company" onClose={() => setIsModalOpen(false)}>
        <form className="space-y-4 p-5" onSubmit={handleSubmit}>
          <div className="grid gap-4 sm:grid-cols-2">
            <FieldShell label="Company name">
              <TextInput
                required
                value={form.name}
                onChange={(event) => setForm((current) => ({ ...current, name: event.target.value, slug: current.slug || makeSlug(event.target.value) }))}
              />
            </FieldShell>
            <FieldShell label="Slug">
              <TextInput required value={form.slug} onChange={(event) => setForm((current) => ({ ...current, slug: makeSlug(event.target.value) }))} />
            </FieldShell>
            <FieldShell label="Industry">
              <TextInput value={form.industry} onChange={(event) => setForm((current) => ({ ...current, industry: event.target.value }))} />
            </FieldShell>
            <FieldShell label="Company size">
              <TextInput value={form.size} onChange={(event) => setForm((current) => ({ ...current, size: event.target.value }))} />
            </FieldShell>
            <FieldShell label="Timezone">
              <TextInput value={form.timezone} onChange={(event) => setForm((current) => ({ ...current, timezone: event.target.value }))} />
            </FieldShell>
          </div>
          <FieldShell label="Description">
            <TextArea value={form.description} onChange={(event) => setForm((current) => ({ ...current, description: event.target.value }))} />
          </FieldShell>
          {formError ? <p className="text-sm font-semibold text-rose-700">{formError}</p> : null}
          <div className="flex justify-end gap-2 border-t border-grid-200 pt-4">
            <Button onClick={() => setIsModalOpen(false)}>Cancel</Button>
            <Button disabled={isMutating} type="submit" variant="primary">
              {isMutating ? "Creating..." : "Create company"}
            </Button>
          </div>
        </form>
      </Modal>
    </>
  );
}
