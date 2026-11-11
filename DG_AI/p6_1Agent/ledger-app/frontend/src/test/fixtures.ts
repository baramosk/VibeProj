import type {
  Budget,
  Category,
  MonthlyReport,
  NotificationListResponse,
  Transaction,
  TrendItem,
  User,
} from '../api/types';

export const USER: User = {
  id: 1,
  email: 'user@example.com',
  nickname: '가계',
  created_at: '2026-11-01T09:00:00+09:00',
};

export const CATEGORIES: Category[] = [
  { id: 1, name: '식비', type: 'EXPENSE', color: '#f59e0b', is_default: true, created_at: '2026-11-01T09:00:00+09:00' },
  { id: 2, name: '교통', type: 'EXPENSE', color: '#3b82f6', is_default: true, created_at: '2026-11-01T09:00:00+09:00' },
  { id: 3, name: '급여', type: 'INCOME', color: '#22c55e', is_default: true, created_at: '2026-11-01T09:00:00+09:00' },
];

export const MONTHLY_REPORT: MonthlyReport = {
  year_month: '2026-11',
  income_total: 3000000,
  expense_total: 1200000,
  balance: 1800000,
  by_category: [
    { category_id: 1, name: '식비', color: '#f59e0b', amount: 400000, ratio: 33.3 },
    { category_id: 2, name: '교통', color: '#3b82f6', amount: 800000, ratio: 66.7 },
  ],
};

/** 2026-11을 끝으로 하는 최근 12개월 추이 (거래 없는 달은 0원) */
export function makeTrend(end = '2026-11'): TrendItem[] {
  const [y, m] = end.split('-').map(Number) as [number, number];
  const items: TrendItem[] = [];
  for (let i = 11; i >= 0; i -= 1) {
    const index = y * 12 + (m - 1) - i;
    const year = Math.floor(index / 12);
    const month = (index % 12) + 1;
    items.push({ year_month: `${year}-${String(month).padStart(2, '0')}`, expense: i === 0 ? 1200000 : 0 });
  }
  return items;
}

export const TRANSACTIONS: Transaction[] = [
  {
    id: 10,
    type: 'EXPENSE',
    amount: 12000,
    category_id: 1,
    category_name: '식비',
    occurred_on: '2026-11-05',
    memo: '점심',
    created_at: '2026-11-05T12:00:00+09:00',
    updated_at: '2026-11-05T12:00:00+09:00',
  },
  {
    id: 11,
    type: 'INCOME',
    amount: 3000000,
    category_id: 3,
    category_name: '급여',
    occurred_on: '2026-11-01',
    memo: null,
    created_at: '2026-11-01T09:00:00+09:00',
    updated_at: '2026-11-01T09:00:00+09:00',
  },
];

export const BUDGETS: Budget[] = [
  {
    id: 1,
    year_month: '2026-11',
    category_id: 1,
    category_name: '식비',
    amount: 500000,
    spent: 400000,
    usage_percent: 80,
    status: 'WARNING',
  },
  {
    id: 2,
    year_month: '2026-11',
    category_id: null,
    category_name: null,
    amount: 1000000,
    spent: 1100000,
    usage_percent: 110,
    status: 'EXCEEDED',
  },
];

export const NOTIFICATIONS: NotificationListResponse = {
  unread_count: 1,
  items: [
    {
      id: 5,
      budget_id: 1,
      year_month: '2026-11',
      threshold_percent: 80,
      message: '11월 식비 예산의 80%를 사용했습니다 (400,000원 / 500,000원).',
      is_read: false,
      created_at: '2026-11-05T18:00:00+09:00',
    },
  ],
};
