import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import type { TrendItem } from '../../api/types';
import { formatKRW, groupThousands } from '../../lib/money';

/** 막대 색. 사용자 토큰 --color-primary 와 같은 값입니다 (SVG는 CSS 변수를 직접 받지 않습니다). */
const BAR_COLOR = '#1d4ed8';

/** "2026-11" -> "11" (축 공간이 좁으므로 숫자만 표시. 자세한 월은 툴팁과 표가 보여 줍니다) */
function shortMonthLabel(yearMonth: string): string {
  const month = yearMonth.split('-')[1] ?? '';
  return String(Number(month));
}

/** 월별 지출 막대 그래프 (FR-17). 거래가 없는 월은 0원으로 그립니다. */
export function MonthlyTrendChart({ items }: { items: TrendItem[] }) {
  const data = items.map((item) => ({ ...item, label: shortMonthLabel(item.year_month) }));

  return (
    <div className="trend-chart" aria-hidden="true">
      <ResponsiveContainer width="100%" height={260}>
        <BarChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" vertical={false} />
          <XAxis dataKey="label" tick={{ fill: '#4b5563', fontSize: 12 }} interval={0} tickLine={false} />
          <YAxis
            tick={{ fill: '#4b5563', fontSize: 12 }}
            tickFormatter={(value: number) => groupThousands(value)}
            width={84}
            tickLine={false}
          />
          <Tooltip formatter={(value) => formatKRW(Number(value))} labelFormatter={(label) => String(label)} />
          <Bar dataKey="expense" name="지출" fill={BAR_COLOR} radius={[4, 4, 0, 0]} isAnimationActive={false} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function TrendTable({ items }: { items: TrendItem[] }) {
  return (
    <table className="data-table data-table--compact">
      <caption className="sr-only">월별 지출 표 (최근 12개월)</caption>
      <thead>
        <tr>
          <th scope="col">월</th>
          <th scope="col" className="num">
            지출
          </th>
        </tr>
      </thead>
      <tbody>
        {items.map((item) => (
          <tr key={item.year_month}>
            <th scope="row" data-label="월">
              {item.year_month}
            </th>
            <td className="num" data-label="지출">
              {formatKRW(item.expense)}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
