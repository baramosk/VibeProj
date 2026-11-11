import { notificationApi } from '../api/endpoints';
import { ApiError } from '../api/client';
import type { NotificationListResponse } from '../api/types';
import { useAsync } from './useAsync';

/** 알림 목록과 읽음 처리 (FR-22). */
export function useNotificationManager() {
  const list = useAsync<NotificationListResponse>((signal) => notificationApi.list(undefined, signal), []);

  const markRead = async (id: number) => {
    await notificationApi.markRead(id);
    list.reload();
  };

  /** "모두 읽음": 계약에 일괄 API가 없어 읽지 않은 항목을 하나씩 처리합니다. */
  const markAllRead = async () => {
    const unread = (list.data?.items ?? []).filter((n) => !n.is_read);
    const results = await Promise.allSettled(unread.map((n) => notificationApi.markRead(n.id)));
    list.reload();
    if (results.some((r) => r.status === 'rejected')) {
      throw new ApiError(0, 'PARTIAL_FAILURE', '일부 알림을 읽음으로 바꾸지 못했습니다. 다시 시도해 주세요.');
    }
  };

  return {
    items: list.data?.items ?? [],
    unreadCount: list.data?.unread_count ?? 0,
    loading: list.loading,
    error: list.error,
    reload: list.reload,
    markRead,
    markAllRead,
  };
}

/** 헤더의 읽지 않은 알림 개수. 화면이 바뀔 때마다 refreshKey를 넘겨 갱신합니다. */
export function useUnreadNotificationCount(refreshKey: string) {
  const state = useAsync<NotificationListResponse>(
    (signal) => notificationApi.list(undefined, signal),
    [refreshKey],
  );
  return { unreadCount: state.data?.unread_count ?? 0 };
}
