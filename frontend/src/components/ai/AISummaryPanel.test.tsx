// @vitest-environment jsdom

import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { AIJob } from "../../types/api";
import { AISummaryPanel } from "./AISummaryPanel";

function job(status: string, output_payload: Record<string, unknown> = {}): AIJob {
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
    output_payload,
    error_message: null,
    provider_key: "groq",
    provider_mode: "groq",
    attempts: status === "queued" ? 0 : 1,
    max_attempts: 3,
    queued_at: "2026-07-13T00:00:00Z",
    locked_at: null,
    locked_by: null,
    next_attempt_at: null,
    last_attempt_at: null,
    timeout_seconds: 30,
    error_code: null,
    retryable: false,
    cancelled_by_user_id: null,
    cancellation_reason: null,
    run_mode: "queued",
    scheduled_at: null,
    started_at: null,
    completed_at: status === "succeeded" ? "2026-07-13T00:00:02Z" : null,
    failed_at: null,
    cancelled_at: null,
    metadata: {},
    created_at: "2026-07-13T00:00:00Z",
    updated_at: "2026-07-13T00:00:00Z",
  };
}

afterEach(cleanup);

describe("AISummaryPanel queue lifecycle", () => {
  it("shows a clear queued state while waiting for the worker", () => {
    render(
      <AISummaryPanel
        error={null}
        generateLabel="Generate AI Summary"
        isGenerating
        isLoading={false}
        job={job("queued")}
        kind="work_object"
        onGenerate={vi.fn()}
      />,
    );

    expect(screen.getByText("Queued for secure processing")).toBeTruthy();
    expect(screen.getByText("FebGuyAI")).toBeTruthy();
  });

  it("renders the completed result in the same panel", () => {
    render(
      <AISummaryPanel
        error={null}
        generateLabel="Generate AI Summary"
        isGenerating={false}
        isLoading={false}
        job={job("succeeded", { summary: "The work object is ready for review." })}
        kind="work_object"
        onGenerate={vi.fn()}
      />,
    );

    expect(screen.getByText("The work object is ready for review.")).toBeTruthy();
    expect(screen.getByText("Succeeded")).toBeTruthy();
  });
});
