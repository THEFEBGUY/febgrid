import { Archive, Megaphone, Pencil, Plus } from "lucide-react";
import { type FormEvent, useMemo, useState } from "react";

import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { FilterBar, FilterField } from "../components/ui/FilterBar";
import { FieldShell, SelectInput, TextArea, TextInput } from "../components/ui/FormControls";
import { Modal } from "../components/ui/Modal";
import { ModuleBoundary } from "../components/ui/ModuleBoundary";
import { SectionPanel } from "../components/ui/SectionPanel";
import { priorityTone } from "../components/ui/tone";
import type { Announcement, AnnouncementCreatePayload, AnnouncementUpdatePayload } from "../types/api";
import type { ModulePageProps } from "../types/page";
import { formatTime } from "../utils/format";

interface AnnouncementsPageProps extends ModulePageProps {
  onCreateAnnouncement: (payload: Omit<AnnouncementCreatePayload, "company_id">) => Promise<void>;
  onUpdateAnnouncement: (announcementId: string, payload: AnnouncementUpdatePayload) => Promise<void>;
  onArchiveAnnouncement: (announcementId: string) => Promise<void>;
}

const priorities = ["low", "normal", "high", "urgent"] as const;

const initialForm = {
  title: "",
  body: "",
  priority: "normal" as AnnouncementCreatePayload["priority"],
  is_published: true,
};

export function AnnouncementsPage({
  data,
  selectedCompany,
  isLoadingModules,
  isMutating,
  moduleError,
  onRetry,
  onCreateAnnouncement,
  onUpdateAnnouncement,
  onArchiveAnnouncement,
}: AnnouncementsPageProps): JSX.Element {
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [editingAnnouncement, setEditingAnnouncement] = useState<Announcement | null>(null);
  const [form, setForm] = useState(initialForm);
  const [formError, setFormError] = useState<string | null>(null);
  const [searchFilter, setSearchFilter] = useState("");
  const [priorityFilter, setPriorityFilter] = useState("");
  const [publishedFilter, setPublishedFilter] = useState("");

  const filteredAnnouncements = useMemo(() => {
    const query = searchFilter.trim().toLowerCase();
    return data.announcements.filter((announcement) => {
      const searchable = [announcement.title, announcement.body, announcement.priority, announcement.is_published ? "published" : "draft"]
        .join(" ")
        .toLowerCase();
      if (query && !searchable.includes(query)) return false;
      if (priorityFilter && announcement.priority !== priorityFilter) return false;
      if (publishedFilter === "published" && !announcement.is_published) return false;
      if (publishedFilter === "draft" && announcement.is_published) return false;
      return true;
    });
  }, [data.announcements, priorityFilter, publishedFilter, searchFilter]);
  const hasActiveFilters = Boolean(searchFilter || priorityFilter || publishedFilter);

  function openCreate(): void {
    setEditingAnnouncement(null);
    setForm(initialForm);
    setFormError(null);
    setIsFormOpen(true);
  }

  function openEdit(announcement: Announcement): void {
    setEditingAnnouncement(announcement);
    setForm({
      title: announcement.title,
      body: announcement.body,
      priority: announcement.priority,
      is_published: announcement.is_published,
    });
    setFormError(null);
    setIsFormOpen(true);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (!form.title.trim() || !form.body.trim()) {
      setFormError("Title and body are required.");
      return;
    }

    try {
      if (editingAnnouncement) {
        await onUpdateAnnouncement(editingAnnouncement.id, {
          title: form.title.trim(),
          body: form.body.trim(),
          priority: form.priority,
          is_published: form.is_published,
          metadata: {},
        });
      } else {
        await onCreateAnnouncement({
          title: form.title.trim(),
          body: form.body.trim(),
          priority: form.priority,
          is_published: form.is_published,
          metadata: {},
        });
      }
      setIsFormOpen(false);
    } catch {
      setFormError("Announcement could not be saved.");
    }
  }

  return (
    <>
      <SectionPanel
        eyebrow={selectedCompany?.name ?? "Company broadcast"}
        title="Announcements"
        action={<Button variant="primary" icon={<Plus className="size-4" aria-hidden="true" />} onClick={openCreate}>Create announcement</Button>}
      >
        <ModuleBoundary
          emptyDescription="Internal company announcements will appear here after they are published."
          emptyTitle="No announcements yet"
          error={moduleError}
          isEmpty={data.announcements.length === 0}
          isLoading={isLoadingModules}
          onRetry={onRetry}
        >
          <FilterBar
            isResetDisabled={!hasActiveFilters}
            onReset={() => {
              setSearchFilter("");
              setPriorityFilter("");
              setPublishedFilter("");
            }}
          >
            <FilterField label="Search">
              <TextInput placeholder="Title or body" value={searchFilter} onChange={(event) => setSearchFilter(event.target.value)} />
            </FilterField>
            <FilterField label="Priority">
              <SelectInput value={priorityFilter} onChange={(event) => setPriorityFilter(event.target.value)}>
                <option value="">All priorities</option>
                {priorities.map((priority) => (
                  <option key={priority} value={priority}>
                    {priority}
                  </option>
                ))}
              </SelectInput>
            </FilterField>
            <FilterField label="State">
              <SelectInput value={publishedFilter} onChange={(event) => setPublishedFilter(event.target.value)}>
                <option value="">All states</option>
                <option value="published">Published</option>
                <option value="draft">Draft</option>
              </SelectInput>
            </FilterField>
          </FilterBar>
          {filteredAnnouncements.length === 0 ? (
            <div className="px-5 py-10 text-center">
              <p className="text-sm font-bold text-ink-950">No announcements match these filters</p>
              <p className="mt-1 text-sm font-medium text-ink-500">Reset filters to return to company broadcasts.</p>
            </div>
          ) : (
          <div className="divide-y divide-grid-100">
            {filteredAnnouncements.map((announcement) => (
              <article key={announcement.id} className="flex flex-col gap-4 px-5 py-4 lg:flex-row lg:items-start lg:justify-between">
                <div className="flex min-w-0 gap-3">
                  <span className="flex size-10 shrink-0 items-center justify-center rounded-md bg-grid-100 text-ink-700">
                    <Megaphone className="size-4" aria-hidden="true" />
                  </span>
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="text-sm font-bold text-ink-950">{announcement.title}</p>
                      <Badge label={announcement.is_published ? "Published" : "Draft"} tone={announcement.is_published ? "green" : "slate"} />
                    </div>
                    <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-ink-600">{announcement.body}</p>
                    <p className="mt-2 text-xs font-semibold text-ink-500">
                      {announcement.published_at ? `Published ${formatTime(announcement.published_at)}` : `Created ${formatTime(announcement.created_at)}`}
                    </p>
                  </div>
                </div>

                <div className="flex shrink-0 flex-wrap gap-2 lg:justify-end">
                  <Badge label={announcement.priority} tone={priorityTone(announcement.priority)} />
                  <Button className="h-9" disabled={isMutating} icon={<Pencil className="size-4" aria-hidden="true" />} onClick={() => openEdit(announcement)}>
                    Edit
                  </Button>
                  <Button className="h-9" disabled={isMutating} icon={<Archive className="size-4" aria-hidden="true" />} onClick={() => void onArchiveAnnouncement(announcement.id)}>
                    Archive
                  </Button>
                </div>
              </article>
            ))}
          </div>
          )}
        </ModuleBoundary>
      </SectionPanel>

      <Modal
        description="Create a company-wide internal announcement."
        isOpen={isFormOpen}
        title={editingAnnouncement ? "Edit announcement" : "Create announcement"}
        onClose={() => setIsFormOpen(false)}
      >
        <form className="space-y-4 p-5" onSubmit={handleSubmit}>
          <FieldShell label="Title">
            <TextInput value={form.title} onChange={(event) => setForm((current) => ({ ...current, title: event.target.value }))} />
          </FieldShell>
          <FieldShell label="Body">
            <TextArea value={form.body} onChange={(event) => setForm((current) => ({ ...current, body: event.target.value }))} />
          </FieldShell>
          <div className="grid gap-4 sm:grid-cols-2">
            <FieldShell label="Priority">
              <SelectInput value={form.priority} onChange={(event) => setForm((current) => ({ ...current, priority: event.target.value as AnnouncementCreatePayload["priority"] }))}>
                {priorities.map((priority) => (
                  <option key={priority} value={priority}>
                    {priority}
                  </option>
                ))}
              </SelectInput>
            </FieldShell>
            <label className="self-end inline-flex h-10 items-center gap-2 rounded-md px-1 text-sm font-bold text-ink-700">
              <input
                checked={form.is_published}
                className="size-4 rounded border-grid-300 accent-blue-600"
                type="checkbox"
                onChange={(event) => setForm((current) => ({ ...current, is_published: event.target.checked }))}
              />
              Publish now
            </label>
          </div>
          {formError ? <p className="text-sm font-semibold text-rose-700">{formError}</p> : null}
          <div className="flex justify-end gap-2 border-t border-grid-200 pt-4">
            <Button onClick={() => setIsFormOpen(false)}>Cancel</Button>
            <Button disabled={isMutating} type="submit" variant="primary">
              {isMutating ? "Saving..." : editingAnnouncement ? "Save changes" : "Publish"}
            </Button>
          </div>
        </form>
      </Modal>
    </>
  );
}
