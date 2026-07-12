// @vitest-environment jsdom

import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { api, ApiError } from "../services/api";
import type { InvitationPreview } from "../types/api";
import { InviteAcceptPage } from "./InviteAcceptPage";

vi.mock("../components/premium/DotGrid", () => ({ DotGrid: () => <div data-testid="dot-grid" /> }));

const preview: InvitationPreview = {
  company_id: "company-1",
  company_name: "FebGrid Test Company",
  employee_id: null,
  employee_name: "Invitee",
  invited_email: "invitee@example.com",
  invited_role: "employee",
  invite_source: "invitation",
  approval_required: false,
  status: "pending",
  expires_at: "2026-08-01T00:00:00Z",
  inviter_name: "Owner",
  job_title: null,
  employment_type: null,
  joining_date: null,
  department_name: null,
  team_name: null,
  manager_name: null,
  account_status: null,
  activation_status: null,
  profile_completion_status: null,
  metadata: {},
};

describe("public invitation preview lifecycle", () => {
  beforeEach(() => vi.restoreAllMocks());

  it("renders a public preview without requiring an authenticated workspace", async () => {
    vi.spyOn(api, "previewInvitation").mockResolvedValue(preview);
    render(<InviteAcceptPage token="public-token" />);
    expect(await screen.findByText("FebGrid Test Company")).toBeTruthy();
    expect(screen.getAllByDisplayValue("invitee@example.com").length).toBeGreaterThan(0);
  });

  it("does not display an intentional cancellation as a fatal error", async () => {
    vi.spyOn(api, "previewInvitation").mockRejectedValue(new ApiError("Request cancelled", 499));
    render(<InviteAcceptPage token="cancelled-token" />);
    await waitFor(() => expect(api.previewInvitation).toHaveBeenCalledOnce());
    expect(screen.queryByText("Unable to load data")).toBeNull();
    expect(screen.queryByText("Request cancelled")).toBeNull();
  });

  it("cancels only the old preview when the invitation token changes", async () => {
    const signals: AbortSignal[] = [];
    vi.spyOn(api, "previewInvitation").mockImplementation((token, signal) => {
      if (signal) signals.push(signal);
      if (token === "new-token") return Promise.resolve(preview);
      return new Promise((_resolve, reject) => {
        signal?.addEventListener("abort", () => reject(new ApiError("Request cancelled", 499)), { once: true });
      });
    });
    const view = render(<InviteAcceptPage token="old-token" />);
    await waitFor(() => expect(api.previewInvitation).toHaveBeenCalledTimes(1));
    view.rerender(<InviteAcceptPage token="new-token" />);
    expect(signals[0]?.aborted).toBe(true);
    expect(await screen.findByText("FebGrid Test Company")).toBeTruthy();
  });
});
