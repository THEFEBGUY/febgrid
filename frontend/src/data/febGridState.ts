import type { FebGridData, Notification } from "../types/api";


type EntityWithId = { id: string };
export type EntityCollectionKey =
  | "departments"
  | "employees"
  | "invitations"
  | "teams"
  | "projects"
  | "workObjects"
  | "leaves"
  | "announcements"
  | "notifications";

export function prependEntity<T extends EntityWithId>(data: FebGridData, key: EntityCollectionKey, entity: T): FebGridData {
  const current = data[key] as EntityWithId[];
  return {
    ...data,
    [key]: [entity, ...current.filter((item) => item.id !== entity.id)],
  } as FebGridData;
}

export function replaceEntity<T extends EntityWithId>(data: FebGridData, key: EntityCollectionKey, entity: T): FebGridData {
  const current = data[key] as EntityWithId[];
  return {
    ...data,
    [key]: current.map((item) => (item.id === entity.id ? entity : item)),
  } as FebGridData;
}

export function markEntityInactive(data: FebGridData, key: "employees" | "projects" | "workObjects" | "leaves", entityId: string): FebGridData {
  const current = data[key] as Array<EntityWithId & { is_active: boolean }>;
  return {
    ...data,
    [key]: current.map((item) => (item.id === entityId ? { ...item, is_active: false } : item)),
  } as FebGridData;
}

export function setNotificationReadState(
  data: FebGridData,
  notificationId: string,
  isRead: boolean,
  changedAt: string | null,
): FebGridData {
  const existing = data.notifications.find((item) => item.id === notificationId);
  if (!existing || existing.is_read === isRead) return data;

  const notification: Notification = {
    ...existing,
    is_read: isRead,
    read_at: isRead ? changedAt : null,
  };
  return {
    ...replaceEntity(data, "notifications", notification),
    notificationUnreadCount: Math.max(0, data.notificationUnreadCount + (isRead ? -1 : 1)),
  };
}
