export function statusTone(status: string): "blue" | "green" | "amber" | "red" | "teal" | "slate" {
  const normalized = status.toLowerCase().replace(/[_-]+/g, " ");
  if (["active", "approved", "completed", "working", "online", "available"].includes(normalized)) return "green";
  if (["pending", "assigned", "in progress", "under review", "onboarding"].includes(normalized)) return "blue";
  if (["on hold", "busy", "on leave", "on break", "done for the day", "not started"].includes(normalized)) return "amber";
  if (["blocked", "rejected", "delayed", "paused", "offline", "inactive"].includes(normalized)) return "red";
  return "slate";
}

export function priorityTone(priority: string): "blue" | "green" | "amber" | "red" | "teal" | "slate" {
  const normalized = priority.toLowerCase();
  if (normalized === "critical") return "red";
  if (normalized === "high") return "amber";
  if (normalized === "medium") return "blue";
  if (normalized === "low") return "green";
  return "slate";
}
