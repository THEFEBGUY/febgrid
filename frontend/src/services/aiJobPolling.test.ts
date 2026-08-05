import { describe, expect, it, vi } from "vitest";

import { aiJobTerminalError, pollAIJob } from "./aiJobPolling";
import type { AIJob } from "../types/api";

function job(status: string): AIJob {
  return {
    id: "job-1",
    company_id: "company-1",
    requested_by_user_id: "user-1",
    requested_by_employee_id: null,
    job_type: "work_object_summary_safe",
    status,
    priority: "normal",
    input_entity_type: "work_object",
    input_entity_id: "work-1",
    input_payload: {},
    output_payload: status === "succeeded" ? { summary: "Completed" } : {},
    error_message: status === "failed" ? "Provider failed safely." : null,
    provider_key: "groq",
    provider_mode: "groq",
    attempts: 1,
    max_attempts: 3,
    queued_at: null,
    locked_at: null,
    locked_by: null,
    next_attempt_at: null,
    last_attempt_at: null,
    timeout_seconds: 30,
    error_code: null,
    retryable: false,
    cancelled_by_user_id: null,
    cancellation_reason: null,
    run_mode: "manual",
    scheduled_at: null,
    started_at: null,
    completed_at: null,
    failed_at: null,
    cancelled_at: null,
    metadata: {},
    created_at: "2026-07-13T00:00:00Z",
    updated_at: "2026-07-13T00:00:00Z",
  };
}

describe("AI job polling", () => {
  it("polls only the created job until it succeeds", async () => {
    const fetchJob = vi.fn().mockResolvedValueOnce(job("running")).mockResolvedValueOnce(job("succeeded"));
    const updates: string[] = [];

    const result = await pollAIJob(job("queued"), "company-1", {
      fetchJob,
      intervalMs: 0,
      timeoutMs: 1_000,
      onUpdate: (current) => updates.push(current.status),
    });

    expect(result.status).toBe("succeeded");
    expect(fetchJob).toHaveBeenCalledTimes(2);
    expect(fetchJob).toHaveBeenCalledWith("job-1", "company-1");
    expect(updates).toEqual(["queued", "running", "succeeded"]);
  });

  it("returns a safe terminal error for failed jobs", () => {
    expect(aiJobTerminalError(job("failed"))).toBe("Provider failed safely.");
    expect(aiJobTerminalError(job("succeeded"))).toBeNull();
  });
});
