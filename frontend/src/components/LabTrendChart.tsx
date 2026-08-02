import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ReferenceArea,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { LabChartSeries } from "@/types/api";
import { cn } from "@/utils/cn";

interface LabTrendChartProps {
  chart: LabChartSeries;
}

export function LabTrendChart({ chart }: LabTrendChartProps) {
  const stroke = chart.is_abnormal_trend ? "#ef4444" : "#2d6a4f";
  const data = chart.data.map((point) => ({
    ...point,
    label: point.date,
  }));

  return (
    <div
      className={cn(
        "rounded-2xl border bg-white/80 p-4 dark:bg-surface-900/70",
        chart.is_abnormal_trend
          ? "border-red-200 dark:border-red-900"
          : "border-brand-100 dark:border-surface-700",
      )}
    >
      <div className="mb-3 flex flex-wrap items-start justify-between gap-2">
        <div>
          <h3 className="font-display text-lg font-semibold text-surface-900 dark:text-surface-50">
            {chart.test_name}
            {chart.unit ? ` (${chart.unit})` : ""}
          </h3>
          <p className="text-xs text-surface-500">
            {chart.is_abnormal_trend ? `Abnormal trend · ${chart.severity}` : "Within expected pattern"}
          </p>
        </div>
      </div>

      <div className="h-56 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#7a9488" strokeOpacity={0.25} />
            <XAxis dataKey="date" tick={{ fontSize: 11, fill: "#879e92" }} stroke="#879e92" />
            <YAxis tick={{ fontSize: 11, fill: "#879e92" }} stroke="#879e92" domain={["auto", "auto"]} />
            <Tooltip
              contentStyle={{
                borderRadius: 12,
                borderColor: "#d9e5de",
                background: "var(--tooltip-bg, #fff)",
                fontSize: 12,
              }}
            />
            <Legend />
            {chart.reference_low != null && chart.reference_high != null && (
              <ReferenceArea
                y1={chart.reference_low}
                y2={chart.reference_high}
                fill="#2d6a4f"
                fillOpacity={0.08}
                ifOverflow="extendDomain"
              />
            )}
            {chart.reference_high != null && (
              <ReferenceLine
                y={chart.reference_high}
                stroke="#d97706"
                strokeDasharray="4 4"
                label={{ value: "High", position: "insideTopRight", fontSize: 10, fill: "#d97706" }}
              />
            )}
            {chart.reference_low != null && (
              <ReferenceLine
                y={chart.reference_low}
                stroke="#d97706"
                strokeDasharray="4 4"
                label={{ value: "Low", position: "insideBottomRight", fontSize: 10, fill: "#d97706" }}
              />
            )}
            <Line
              type="monotone"
              dataKey="value"
              name={chart.test_name}
              stroke={stroke}
              strokeWidth={2.5}
              dot={(props: {
                cx?: number;
                cy?: number;
                payload?: { abnormal?: boolean };
              }) => {
                const { cx = 0, cy = 0, payload } = props;
                const abnormal = Boolean(payload?.abnormal);
                return (
                  <circle
                    key={`${cx}-${cy}-${abnormal}`}
                    cx={cx}
                    cy={cy}
                    r={abnormal ? 5 : 3.5}
                    fill={abnormal ? "#dc2626" : stroke}
                    stroke="#fff"
                    strokeWidth={1.5}
                  />
                );
              }}
              activeDot={{ r: 6 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
