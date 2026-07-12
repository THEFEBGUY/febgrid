import { describe, expect, it } from "vitest";

import type { FebGridData } from "../types/api";
import { markEntityInactive, prependEntity, replaceEntity, setNotificationReadState } from "./febGridState";

function dataFixture(): FebGridData {
  return {
    companies: [],
    aiCapabilities: null,
    aiProviderStatus: null,
    aiSafetySettings: null,
    aiJobQueueSummary: null,
    aiJobs: [],
    auditLogs: [],
    billingPlans: [],
    billingSummary: null,
    companySettings: null,
    industryTemplates: [],
    workObjectTypes: [],
    customFields: [],
    dashboardSummary: null,
    departments: [],
    employees: [],
    leaveApprovers: [],
    invitations: [],
    teams: [],
    projects: [],
    workObjects: [],
    leaves: [],
    events: [],
    notifications: [],
    notificationUnreadCount: 0,
    announcements: [],
    files: [],
  };
}

describe("targeted mutation state", () => {
  const appendCases = [
    ["create department", "departments"],
    ["create team", "teams"],
    ["create project", "projects"],
    ["create work object", "workObjects"],
    ["create leave", "leaves"],
    ["create announcement", "announcements"],
    ["create invitation and expose its returned link immediately", "invitations"],
  ] as const;

  it.each(appendCases)("%s changes only %s", (_name, key) => {
    const before = dataFixture();
    const entity = { id: `${key}-1`, is_active: true };
    const after = prependEntity(before, key, entity);

    expect(after[key]).toEqual([entity]);
    Object.keys(before).forEach((field) => {
      if (field !== key) expect(after[field as keyof FebGridData]).toBe(before[field as keyof FebGridData]);
    });
  });

  it("employee deactivation updates one row and preserves other collections", () => {
    const before = dataFixture();
    before.employees = [
      { id: "employee-1", is_active: true },
      { id: "employee-2", is_active: true },
    ] as FebGridData["employees"];
    const after = markEntityInactive(before, "employees", "employee-1");

    expect(after.employees.map(({ id, is_active }) => ({ id, is_active }))).toEqual([
      { id: "employee-1", is_active: false },
      { id: "employee-2", is_active: true },
    ]);
    expect(after.projects).toBe(before.projects);
  });

  it("replaces only the affected entity returned by an API", () => {
    const before = dataFixture();
    before.teams = [{ id: "team-1", name: "Before" }, { id: "team-2", name: "Other" }] as FebGridData["teams"];
    const updated = { ...before.teams[0], name: "After" };
    const after = replaceEntity(before, "teams", updated);

    expect(after.teams[0].name).toBe("After");
    expect(after.teams[1]).toBe(before.teams[1]);
  });

  it("optimistically reads a notification and supports exact rollback", () => {
    const before = dataFixture();
    before.notificationUnreadCount = 1;
    before.notifications = [{ id: "notification-1", is_read: false, read_at: null }] as FebGridData["notifications"];

    const optimistic = setNotificationReadState(before, "notification-1", true, "2026-07-12T10:00:00Z");
    expect(optimistic.notifications[0].is_read).toBe(true);
    expect(optimistic.notificationUnreadCount).toBe(0);

    const rolledBack = setNotificationReadState(optimistic, "notification-1", false, null);
    expect(rolledBack.notifications[0].is_read).toBe(false);
    expect(rolledBack.notifications[0].read_at).toBeNull();
    expect(rolledBack.notificationUnreadCount).toBe(1);
  });
});
