import { Bell, BriefcaseBusiness, Building2, CalendarDays, FolderKanban, LayoutDashboard, Megaphone, Network, Settings, Users, Zap } from "lucide-react";

import type { NavigationItem } from "../types/domain";

export const navigationItems: NavigationItem[] = [
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
  { key: "settings", label: "Settings", description: "Company config", icon: Settings },
];
