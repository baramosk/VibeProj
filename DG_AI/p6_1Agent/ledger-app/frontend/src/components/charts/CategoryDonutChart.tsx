import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts';
import type { CategoryBreakdown } from '../../api/types';
import { formatKRW, formatPercent } from '../../lib/money';

interface Props {
  items: CategoryBreakdown[];
  total: number;
}

/**
 * 카테고리별 지출 도넛 차트 (FR-16). 금액 내림차순, 0원 카테고리는 제외합니다.
 * 차트 자체는 보조 표현이며, 같은 내용을 CategoryBreakdownTable이 텍스트로 제공합니다 (NFR-17).
 */
export function CategoryDonutChart({ items, total }: Props) {
  const data = items.filter((item) => item.amount > 0);

  if (data.length === 0) return null;

  return (
    <div className="donut">
      <div className="donut__chart" aria-hidden="true">
        <ResponsiveContainer width="100%" height={240}>
          <PieChart>
            <Pie
              data={data}
              dataKey="amount"
              nameKey="name"
              innerRadius={64}
              outerRadius={104}
              paddingAngle={1}
              isAnimationActive={false}
            >
              {data.map((item) => (
                <Cell key={item.category_id} fill={item.color} />
              ))}
            </Pie>
            <Tooltip formatter={(value) => formatKRW(Number(value))} />
          </PieChart>
        </ResponsiveContainer>
        <div className="donut__center">
          <span className="donut__center-label">총 지출</span>
          <span className="donut__center-value">{formatKRW(total)}</span>
        </div>
      </div>
    </div>
  );
}

export function CategoryBreakdownTable({ items }: { items: CategoryBreakdown[] }) {
  const rows = items.filter((item) => item.amount > 0).sort((a, b) => b.amount - a.amount);

  if (rows.length === 0) return null;

  return (
    <table className="data-table data-table--compact">
      <caption className="sr-only">카테고리별 지출 표 (금액 내림차순)</caption>
      <thead>
        <tr>
          <th scope="col">카테고리</th>
          <th scope="col" className="num">
            금액
          </th>
          <th scope="col" className="num">
            비율
          </th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <tr key={row.category_id}>
            <th scope="row" data-label="카테고리">
              <span className="swatch" style={{ backgroundColor: row.color }} aria-hidden="true" />
              {row.name}
            </th>
            <td className="num" data-label="금액">
              {formatKRW(row.amount)}
            </td>
            <td className="num" data-label="비율">
              {formatPercent(row.ratio)}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
