/**
 * API 계약(docs/api-contract.md)의 응답과 요청 형태입니다.
 * 계약이 바뀌면 이 파일과 docs/api-contract.md를 함께 고칩니다.
 */

export type CategoryType = 'INCOME' | 'EXPENSE';
export type BudgetStatus = 'NORMAL' | 'WARNING' | 'EXCEEDED';
export type ErrorCode =
  | 'VALIDATION_ERROR'
  | 'UNAUTHORIZED'
  | 'FORBIDDEN'
  | 'NOT_FOUND'
  | 'CONFLICT'
  | 'ACCOUNT_LOCKED'
  | 'INTERNAL_ERROR';

export interface User {
  id: number;
  email: string;
  nickname: string;
  created_at: string;
}

export interface AuthResponse {
  user: User;
  csrf_token: string;
}

export interface Category {
  id: number;
  name: string;
  type: CategoryType;
  color: string;
  is_default: boolean;
  created_at: string;
}

export interface Transaction {
  id: number;
  type: CategoryType;
  amount: number;
  category_id: number;
  category_name: string;
  occurred_on: string;
  memo: string | null;
  created_at: string;
  updated_at: string;
}

export interface TransactionListResponse {
  items: Transaction[];
  total: number;
  page: number;
  size: number;
}

export interface BudgetStatusItem {
  budget_id: number;
  category_id: number | null;
  year_month: string;
  spent: number;
  amount: number;
  usage_percent: number;
  new_thresholds: Array<80 | 100>;
}

export interface TransactionMutationResponse {
  transaction: Transaction;
  budget_status: BudgetStatusItem[];
}

export interface DeleteTransactionResponse {
  budget_status: BudgetStatusItem[];
}

export interface CategoryBreakdown {
  category_id: number;
  name: string;
  color: string;
  amount: number;
  ratio: number;
}

export interface MonthlyReport {
  year_month: string;
  income_total: number;
  expense_total: number;
  balance: number;
  by_category: CategoryBreakdown[];
}

export interface TrendItem {
  year_month: string;
  expense: number;
}

export interface TrendResponse {
  items: TrendItem[];
}

export interface Budget {
  id: number;
  year_month: string;
  /** null이면 전체 지출 예산 */
  category_id: number | null;
  category_name: string | null;
  amount: number;
  spent: number;
  usage_percent: number;
  status: BudgetStatus;
}

export interface AppNotification {
  id: number;
  budget_id: number;
  year_month: string;
  threshold_percent: 80 | 100;
  message: string;
  is_read: boolean;
  created_at: string;
}

export interface NotificationListResponse {
  items: AppNotification[];
  unread_count: number;
}

export interface ApiErrorBody {
  error: {
    code?: string;
    message?: string;
    details?: Record<string, unknown>;
  };
}

export interface TransactionInput {
  type: CategoryType;
  amount: number;
  category_id: number;
  occurred_on: string;
  memo?: string | null;
}

export interface TransactionFilters {
  from?: string;
  to?: string;
  category_id?: number;
  type?: CategoryType;
  page: number;
  size: number;
}
