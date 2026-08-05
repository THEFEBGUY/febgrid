import { api } from "./api";
import type { AIJob } from "../types/api";

const TERMINAL_AI_JOB_STATUSES = new Set(["succeeded", "failed", "cancelled", "skipped"]);

interface PollAIJobOptions {
  fetchJob?: (jobId: string, companyId: string) => Promise<AIJob>;
  intervalMs?: number;
  timeoutMs?: number;
  onUpdate?: (job: AIJob) => void;
}

export async function pollAIJob(
  initialJob: AIJob,
  companyId: string,
  options: PollAIJobOptions = {},
): Promise<AIJob> {
  const fetchJob = options.fetchJob ?? api.aiJob;
  const intervalMs = options.intervalMs ?? 800;
  const timeoutMs = options.timeoutMs ?? 90_000;
  const startedAt = Date.now();
  let job = initialJob;
  options.onUpdate?.(job);

  while (!TERMINAL_AI_JOB_STATUSES.has(job.status)) {
    if (Date.now() - startedAt >= timeoutMs) {
      throw new Error("AI processing is taking longer than expected. The queued job is still available in AI Foundation.");
    }
    await new Promise((resolve) => globalThis.setTimeout(resolve, intervalMs));
    job = await fetchJob(job.id, companyId);
    options.onUpdate?.(job);
  }
  return job;
}

export function aiJobTerminalError(job: AIJob): string | null {
  if (job.status === "succeeded") return null;
  if (job.status === "cancelled") return "AI processing was cancelled.";
  return job.error_message || "AI processing failed safely. Review the job in AI Foundation.";
}
