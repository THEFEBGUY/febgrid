import { describe, expect, it } from "vitest";

import { getPageDataKeys } from "./pageDataPlan";

describe("page data plans", () => {
  it("loads only employee directory dependencies", () => {
    expect(getPageDataKeys("employees", "admin")).toEqual([
      "employees",
      "invitations",
      "departments",
      "teams",
      "notificationUnreadCount",
    ]);
  });

  it("keeps settings, billing, files, and AI off operational pages", () => {
    const ordinaryPages = ["dashboard", "employees", "teams", "projects", "work-objects", "leaves"] as const;
    const forbidden = ["companySettings", "billingSummary", "files", "aiJobs", "aiProviderStatus"];

    ordinaryPages.forEach((page) => {
      expect(getPageDataKeys(page, "company_owner")).not.toEqual(expect.arrayContaining(forbidden));
    });
  });

  it("uses the dashboard summary instead of loading the whole workspace", () => {
    expect(getPageDataKeys("dashboard", "company_owner")).toEqual([
      "dashboardSummary",
      "employees",
      "notificationUnreadCount",
    ]);
  });

  it("does not load admin AI or billing data for employee pages", () => {
    const keys = getPageDataKeys("my-dashboard", "employee");
    expect(keys).toEqual([
      "employees",
      "workObjects",
      "leaves",
      "notifications",
      "announcements",
      "notificationUnreadCount",
    ]);
    expect(keys).not.toContain("aiJobs");
    expect(keys).not.toContain("billingSummary");
  });
});
