/**
 * 엔드포인트별 호출 함수 모음 (API 계약 1~6절).
 * 화면 컴포넌트는 이 함수를 직접 부르지 않고 src/hooks/ 의 훅을 통해 씁니다.
 */

import { api } from './client';
import type {
  AppNotification,
  AuthResponse,
  Budget,
  Category,
  CategoryType,
  DeleteTransactionResponse,
  MonthlyReport,
  NotificationListResponse,
  TransactionFilters,
  TransactionInput,
  TransactionListResponse,
  TransactionMutationResponse,
  TrendResponse,
} from './types';

// 1. 인증 (FR-01~04)
export const authApi = {
  signup: (input: { email: string; password: string; nickname: string }) =>
    api.post<AuthResponse>('/auth/signup', { body: input }),
  login: (input: { email: string; password: string }) => api.post<AuthResponse>('/auth/login', { body: input }),
  logout: () => api.post<void>('/auth/logout'),
  me: (signal?: AbortSignal) => api.get<AuthResponse>('/auth/me', { signal }),
  deleteAccount: (password: string) => api.delete<void>('/auth/account', { body: { password } }),
};

// 2. 카테고리 (FR-06~09)
export const categoryApi = {
  list: (type?: CategoryType, signal?: AbortSignal) =>
    api.get<Category[]>('/categories', { query: { type }, signal }),
  create: (input: { name: string; type: CategoryType; color: string }) =>
    api.post<Category>('/categories', { body: input }),
  update: (id: number, input: { name?: string; color?: string }) =>
    api.patch<Category>(`/categories/${id}`, { body: input }),
  remove: (id: number, replacementId: number) =>
    api.delete<void>(`/categories/${id}`, { query: { replacement_id: replacementId } }),
};

// 3. 거래 (FR-10~13)
export const transactionApi = {
  list: (filters: TransactionFilters, signal?: AbortSignal) =>
    api.get<TransactionListResponse>('/transactions', {
      query: {
        from: filters.from,
        to: filters.to,
        category_id: filters.category_id,
        type: filters.type,
        page: filters.page,
        size: filters.size,
      },
      signal,
    }),
  create: (input: TransactionInput) => api.post<TransactionMutationResponse>('/transactions', { body: input }),
  update: (id: number, input: Partial<TransactionInput>) =>
    api.patch<TransactionMutationResponse>(`/transactions/${id}`, { body: input }),
  remove: (id: number) => api.delete<DeleteTransactionResponse>(`/transactions/${id}`),
};

// 4. 리포트 (FR-14~17)
export const reportApi = {
  monthly: (yearMonth: string, signal?: AbortSignal) =>
    api.get<MonthlyReport>('/reports/monthly', { query: { year_month: yearMonth }, signal }),
  trend: (end?: string, signal?: AbortSignal) => api.get<TrendResponse>('/reports/trend', { query: { end }, signal }),
};

// 5. 예산 (FR-18~20)
export const budgetApi = {
  list: (yearMonth: string, signal?: AbortSignal) =>
    api.get<Budget[]>('/budgets', { query: { year_month: yearMonth }, signal }),
  create: (input: { year_month: string; amount: number; category_id?: number }) =>
    api.post<Budget>('/budgets', { body: input }),
  updateAmount: (id: number, amount: number) => api.put<Budget>(`/budgets/${id}`, { body: { amount } }),
  remove: (id: number) => api.delete<void>(`/budgets/${id}`),
};

// 6. 알림 (FR-21~22)
export const notificationApi = {
  list: (unreadOnly?: boolean, signal?: AbortSignal) =>
    api.get<NotificationListResponse>('/notifications', { query: { unread_only: unreadOnly }, signal }),
  markRead: (id: number) => api.post<AppNotification>(`/notifications/${id}/read`),
};

