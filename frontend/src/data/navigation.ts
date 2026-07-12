import {
  Bell,
  Brain,
  BriefcaseBusiness,
  Building2,
  CalendarDays,
  Fingerprint,
  FolderKanban,
  LayoutDashboard,
  Megaphone,
  Network,
  Settings,
  UserCircle,
  Users,
  Zap,
  Sparkles,
} from "lucide-react";

import type { AuthUser } from "../types/api";
import type { NavigationItem } from "../types/domain";

export const adminNavigationItems: NavigationItem[] = [
  { key: "dashboard", label: "Dashboard", description: "Mission control", icon: LayoutDashboard },
  { key: "companies", label: "Companies", description: "Tenant foundation", icon: Building2 },
  { key: "employees", label: "Employees", description: "People directory", icon: Users },
  { key: "teams", label: "Teams", description: "Operating groups", icon: Network },
  { key: "projects", label: "Projects", description: "Delivery tracking", icon: FolderKanban },
  { key: "work-objects", label: "Work Objects", description: "Core work engine", icon: BriefcaseBusiness },
  { key: "leaves", label: "Leaves", description: "Availability", icon: CalendarDays },
  { key: "events", label: "Events", description: "Universal timeline", icon: Zap },
  { key: "announcements", label: "Announcements", description: "Company broadcast", icon: Megaphone },
  { key: "notifications", label: "Notifications", description: "Action stream", icon: Bell },
  { key: "memory", label: "Memory", description: "Company knowledge", icon: Brain },
  { key: "work-dna", label: "Work DNA", description: "Work patterns", icon: Fingerprint },
  { key: "settings", label: "Settings", description: "Company config", icon: Settings },
];

export const managerNavigationItems: NavigationItem[] = [
  { key: "dashboard", label: "Dashboard", description: "Mission control", icon: LayoutDashboard },
  { key: "employees", label: "Employees", description: "People directory", icon: Users },
  { key: "teams", label: "Teams", description: "Operating groups", icon: Network },
  { key: "projects", label: "Projects", description: "Delivery tracking", icon: FolderKanban },
  { key: "work-objects", label: "Work Objects", description: "Core work engine", icon: BriefcaseBusiness },
  { key: "leaves", label: "Leaves", description: "Availability", icon: CalendarDays },
  { key: "announcements", label: "Announcements", description: "Company broadcast", icon: Megaphone },
  { key: "notifications", label: "Notifications", description: "Action stream", icon: Bell },
];

export const employeeNavigationItems: NavigationItem[] = [
  { key: "my-dashboard", label: "My Dashboard", description: "Personal overview", icon: LayoutDashboard },
  { key: "my-work", label: "My Work", description: "Assigned work", icon: BriefcaseBusiness },
  { key: "my-projects", label: "My Projects", description: "Assigned projects", icon: FolderKanban },
  { key: "my-digital-twin", label: "My Digital Twin", description: "Workload profile", icon: Sparkles },
  { key: "my-leave", label: "My Leave", description: "My availability", icon: CalendarDays },
  { key: "notifications", label: "Notifications", description: "My action stream", icon: Bell },
  { key: "announcements", label: "Announcements", description: "Company broadcast", icon: Megaphone },
  { key: "my-profile", label: "My Profile", description: "Personal details", icon: UserCircle },
];

export const navigationItems = adminNavigationItems;

export const allNavigationItems: NavigationItem[] = [
  ...adminNavigationItems,
  ...employeeNavigationItems.filter((employeeItem) => !adminNavigationItems.some((adminItem) => adminItem.key === employeeItem.key)),
];

export function getDefaultPageForRole(role: AuthUser["role"] | null | undefined): NavigationItem["key"] {
  return role === "employee" ? "my-dashboard" : "dashboard";
}

export function getNavigationItemsForRole(role: AuthUser["role"] | null | undefined): NavigationItem[] {
  if (role === "employee") return employeeNavigationItems;
  if (role === "manager") return managerNavigationItems;
  return adminNavigationItems;
}

export function isPageAllowedForRole(role: AuthUser["role"] | null | undefined, pageKey: NavigationItem["key"]): boolean {
  return getNavigationItemsForRole(role).some((item) => item.key === pageKey);
}

export function getAuthenticatedRouteTarget(
  role: AuthUser["role"],
  activePage: NavigationItem["key"],
  currentHash: string,
): NavigationItem["key"] | null {
  if (!currentHash.replace(/^#\/?/, "")) return getDefaultPageForRole(role);
  if (!isPageAllowedForRole(role, activePage)) return getDefaultPageForRole(role);
  return null;
}
