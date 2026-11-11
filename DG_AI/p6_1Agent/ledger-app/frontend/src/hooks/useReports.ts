import { reportApi } from '../api/endpoints';
import { useAsync } from './useAsync';

/** 월 요약과 카테고리별 지출 (FR-15, FR-16). */
export function useMonthlyReport(yearMonth: string) {
  return useAsync((signal) => reportApi.monthly(yearMonth, signal), [yearMonth]);
}

/** 최근 12개월 월별 지출 (FR-17). */
export function useExpenseTrend(end: string) {
  return useAsync((signal) => reportApi.trend(end, signal), [end]);
}
