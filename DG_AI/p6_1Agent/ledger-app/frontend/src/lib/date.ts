/**
 * 날짜와 월 계산 순수 함수 (NFR-24, FR-14). 기준 시간대는 Asia/Seoul입니다.
 * 월 문자열은 YYYY-MM, 날짜 문자열은 YYYY-MM-DD 입니다.
 */

const SEOUL = 'Asia/Seoul';

const YEAR_MONTH_PATTERN = /^(\d{4})-(\d{2})$/;
const DATE_PATTERN = /^(\d{4})-(\d{2})-(\d{2})$/;

/** 지정한 시각의 서울 기준 날짜 (YYYY-MM-DD). */
export function toSeoulDate(now: Date = new Date()): string {
  return new Intl.DateTimeFormat('en-CA', {
    timeZone: SEOUL,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(now);
}

/** 오늘 날짜 (서울 기준, YYYY-MM-DD). 거래 입력 기본값과 미래 날짜 검사에 씁니다. */
export function todayKST(now: Date = new Date()): string {
  return toSeoulDate(now);
}

/** 이번 달 (서울 기준, YYYY-MM). */
export function currentYearMonth(now: Date = new Date()): string {
  return toSeoulDate(now).slice(0, 7);
}

export function isValidYearMonth(value: string): boolean {
  const match = YEAR_MONTH_PATTERN.exec(value);
  if (!match) return false;
  const month = Number(match[2]);
  return month >= 1 && month <= 12;
}

export function isValidDate(value: string): boolean {
  const match = DATE_PATTERN.exec(value);
  if (!match) return false;
  const [y, m, d] = [Number(match[1]), Number(match[2]), Number(match[3])];
  const check = new Date(Date.UTC(y, m - 1, d));
  return check.getUTCFullYear() === y && check.getUTCMonth() === m - 1 && check.getUTCDate() === d;
}

/** 월을 delta만큼 이동합니다. 예: shiftMonth("2026-01", -1) -> "2025-12" */
export function shiftMonth(yearMonth: string, delta: number): string {
  const match = YEAR_MONTH_PATTERN.exec(yearMonth);
  if (!match) throw new RangeError(`잘못된 월 형식: ${yearMonth}`);
  const index = Number(match[1]) * 12 + (Number(match[2]) - 1) + delta;
  const year = Math.floor(index / 12);
  const month = (index % 12) + 1;
  return `${year}-${String(month).padStart(2, '0')}`;
}

/** 두 월을 비교합니다. a가 이르면 음수, 같으면 0, 늦으면 양수. */
export function compareYearMonth(a: string, b: string): number {
  return a < b ? -1 : a > b ? 1 : 0;
}

/** 선택한 월이 이번 달보다 뒤인지 확인합니다 (FR-14, 미래 월 선택 불가). */
export function isFutureMonth(yearMonth: string, now: Date = new Date()): boolean {
  return compareYearMonth(yearMonth, currentYearMonth(now)) > 0;
}

/** 날짜가 오늘보다 뒤인지 확인합니다 (FR-10, 미래 날짜 입력 불가). */
export function isFutureDate(date: string, now: Date = new Date()): boolean {
  return date > todayKST(now);
}

/** 월의 첫날과 마지막 날 (YYYY-MM-DD). */
export function monthRange(yearMonth: string): { from: string; to: string } {
  const match = YEAR_MONTH_PATTERN.exec(yearMonth);
  if (!match) throw new RangeError(`잘못된 월 형식: ${yearMonth}`);
  const year = Number(match[1]);
  const month = Number(match[2]);
  const lastDay = new Date(Date.UTC(year, month, 0)).getUTCDate();
  return {
    from: `${yearMonth}-01`,
    to: `${yearMonth}-${String(lastDay).padStart(2, '0')}`,
  };
}

/** 화면 표시용 월 이름. 예: "2026-11" -> "2026년 11월" */
export function formatYearMonthLabel(yearMonth: string): string {
  const match = YEAR_MONTH_PATTERN.exec(yearMonth);
  if (!match) return yearMonth;
  return `${match[1]}년 ${Number(match[2])}월`;
}

/** 표시용 날짜. 예: "2026-11-06" -> "2026.11.06" */
export function formatDateLabel(date: string): string {
  return date.replace(/-/g, '.');
}

/** 시각 표시 (서울 기준). 예: "2026-11-06T10:30:00+09:00" -> "2026.11.06 10:30" */
export function formatDateTimeLabel(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  const parts = new Intl.DateTimeFormat('en-GB', {
    timeZone: SEOUL,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hourCycle: 'h23',
  }).formatToParts(date);
  const get = (type: string) => parts.find((p) => p.type === type)?.value ?? '';
  return `${get('year')}.${get('month')}.${get('day')} ${get('hour')}:${get('minute')}`;
}
