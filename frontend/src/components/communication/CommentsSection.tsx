import { MessageSquare, Pencil, Send, Trash2 } from "lucide-react";
import { type FormEvent, useCallback, useEffect, useState } from "react";

import { api } from "../../services/api";
import type { Comment, Employee } from "../../types/api";
import { formatTime } from "../../utils/format";
import { Button } from "../ui/Button";
import { FieldShell, TextArea } from "../ui/FormControls";
import { EmptyState, ErrorState, LoadingState } from "../ui/States";

interface CommentsSectionProps {
  companyId: string | null;
  targetEntityType: "work_object" | "project";
  targetEntityId: string | null;
  employees: Employee[];
  employeeNames: Record<string, string>;
  onChanged?: () => void;
}

export function CommentsSection({
  companyId,
  targetEntityType,
  targetEntityId,
  employees,
  employeeNames,
  onChanged,
}: CommentsSectionProps): JSX.Element {
  const [comments, setComments] = useState<Comment[]>([]);
  const [body, setBody] = useState("");
  const [mentionedEmployeeIds, setMentionedEmployeeIds] = useState<string[]>([]);
  const [editingCommentId, setEditingCommentId] = useState<string | null>(null);
  const [editingBody, setEditingBody] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadComments = useCallback(async (): Promise<void> => {
    if (!companyId || !targetEntityId) return;
    setIsLoading(true);
    setError(null);
    try {
      const nextComments = await api.comments(targetEntityType, targetEntityId, companyId);
      setComments(nextComments);
    } catch {
      setError("Unable to load comments.");
    } finally {
      setIsLoading(false);
    }
  }, [companyId, targetEntityId, targetEntityType]);

  useEffect(() => {
    setBody("");
    setMentionedEmployeeIds([]);
    setEditingCommentId(null);
    setEditingBody("");
    setComments([]);
    void loadComments();
  }, [loadComments]);

  function toggleMention(employeeId: string): void {
    setMentionedEmployeeIds((current) =>
      current.includes(employeeId) ? current.filter((id) => id !== employeeId) : [...current, employeeId],
    );
  }

  async function handleCreateComment(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (!companyId || !targetEntityId || !body.trim()) return;
    setIsSaving(true);
    setError(null);
    try {
      await api.createComment({
        company_id: companyId,
        target_entity_type: targetEntityType,
        target_entity_id: targetEntityId,
        body: body.trim(),
        metadata: {},
        mentioned_employee_ids: mentionedEmployeeIds,
      });
      setBody("");
      setMentionedEmployeeIds([]);
      await loadComments();
      onChanged?.();
    } catch {
      setError("Comment could not be saved.");
    } finally {
      setIsSaving(false);
    }
  }

  async function handleUpdateComment(comment: Comment): Promise<void> {
    if (!companyId || !editingBody.trim()) return;
    setIsSaving(true);
    setError(null);
    try {
      await api.updateComment(comment.id, companyId, { body: editingBody.trim() });
      setEditingCommentId(null);
      setEditingBody("");
      await loadComments();
      onChanged?.();
    } catch {
      setError("Comment could not be updated.");
    } finally {
      setIsSaving(false);
    }
  }

  async function handleArchiveComment(comment: Comment): Promise<void> {
    if (!companyId) return;
    setIsSaving(true);
    setError(null);
    try {
      await api.archiveComment(comment.id, companyId);
      await loadComments();
      onChanged?.();
    } catch {
      setError("Comment could not be archived.");
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <section className="rounded-lg border border-grid-200">
      <div className="flex flex-col gap-3 border-b border-grid-200 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex min-w-0 items-center gap-2">
          <MessageSquare className="size-4 shrink-0 text-ink-500" aria-hidden="true" />
          <h3 className="text-sm font-bold text-ink-950">Comments</h3>
        </div>
        <Button disabled={isLoading} onClick={() => void loadComments()}>
          Retry
        </Button>
      </div>

      <form className="space-y-3 border-b border-grid-100 p-4" onSubmit={handleCreateComment}>
        <FieldShell label="Add comment">
          <TextArea
            placeholder="Write an operational update or decision..."
            value={body}
            onChange={(event) => setBody(event.target.value)}
          />
        </FieldShell>

        {employees.length > 0 ? (
          <div className="rounded-md border border-grid-200 bg-grid-50 p-3">
            <p className="text-xs font-bold uppercase tracking-normal text-ink-500">Mention employees</p>
            <div className="mt-3 grid gap-2 sm:grid-cols-2">
              {employees.slice(0, 8).map((employee) => (
                <label key={employee.id} className="flex items-center gap-2 text-sm font-semibold text-ink-700">
                  <input
                    checked={mentionedEmployeeIds.includes(employee.id)}
                    className="size-4 rounded border-grid-300"
                    type="checkbox"
                    onChange={() => toggleMention(employee.id)}
                  />
                  <span className="min-w-0 truncate">{employee.full_name}</span>
                </label>
              ))}
            </div>
          </div>
        ) : null}

        <div className="flex justify-end">
          <Button disabled={isSaving || !body.trim()} type="submit" variant="primary" icon={<Send className="size-4" aria-hidden="true" />}>
            {isSaving ? "Posting..." : "Post comment"}
          </Button>
        </div>
      </form>

      {isLoading ? <LoadingState label="Loading comments" /> : null}
      {error ? <ErrorState message={error} onRetry={loadComments} /> : null}
      {!isLoading && !error ? (
        comments.length === 0 ? (
          <EmptyState description="Operational notes, decisions, and mentions will appear here." title="No comments yet" />
        ) : (
          <div className="divide-y divide-grid-100">
            {comments.map((comment) => {
              const author = comment.author_employee_id ? employeeNames[comment.author_employee_id] ?? "Employee" : "Team member";
              return (
                <article key={comment.id} className="px-4 py-3">
                  <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                    <div className="min-w-0">
                      <p className="text-sm font-bold text-ink-950">{author}</p>
                      <p className="mt-1 text-xs font-semibold text-ink-500">
                        {formatTime(comment.created_at)}
                        {comment.is_edited ? " / edited" : ""}
                      </p>
                    </div>
                    <div className="flex shrink-0 gap-2">
                      <Button
                        aria-label="Edit comment"
                        className="size-9 px-0"
                        disabled={isSaving}
                        icon={<Pencil className="size-4" aria-hidden="true" />}
                        onClick={() => {
                          setEditingCommentId(comment.id);
                          setEditingBody(comment.body);
                        }}
                      >
                        <span className="sr-only">Edit</span>
                      </Button>
                      <Button
                        aria-label="Archive comment"
                        className="size-9 px-0"
                        disabled={isSaving}
                        icon={<Trash2 className="size-4" aria-hidden="true" />}
                        onClick={() => void handleArchiveComment(comment)}
                      >
                        <span className="sr-only">Archive</span>
                      </Button>
                    </div>
                  </div>

                  {editingCommentId === comment.id ? (
                    <div className="mt-3 space-y-2">
                      <TextArea value={editingBody} onChange={(event) => setEditingBody(event.target.value)} />
                      <div className="flex justify-end gap-2">
                        <Button onClick={() => setEditingCommentId(null)}>Cancel</Button>
                        <Button disabled={isSaving || !editingBody.trim()} variant="primary" onClick={() => void handleUpdateComment(comment)}>
                          Save
                        </Button>
                      </div>
                    </div>
                  ) : (
                    <p className="mt-3 whitespace-pre-wrap text-sm font-medium leading-6 text-ink-700">{comment.body}</p>
                  )}

                  {comment.mentions.length > 0 ? (
                    <div className="mt-3 flex flex-wrap gap-2">
                      {comment.mentions.map((mention) => (
                        <span key={mention.id} className="rounded-md bg-blue-50 px-2 py-1 text-xs font-bold text-blue-700">
                          @{mention.mentioned_employee_id ? employeeNames[mention.mentioned_employee_id] ?? "employee" : "user"}
                        </span>
                      ))}
                    </div>
                  ) : null}
                </article>
              );
            })}
          </div>
        )
      ) : null}
    </section>
  );
}
