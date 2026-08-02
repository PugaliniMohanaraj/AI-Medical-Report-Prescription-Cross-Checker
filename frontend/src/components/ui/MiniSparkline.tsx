import { cn } from "@/utils/cn";

interface MiniSparklineProps {
  values: number[];
  className?: string;
  stroke?: string;
}

export function MiniSparkline({
  values,
  className,
  stroke = "#2d6a4f",
}: MiniSparklineProps) {
  if (values.length < 2) return null;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const width = 72;
  const height = 28;
  const points = values
    .map((value, index) => {
      const x = (index / (values.length - 1)) * width;
      const y = height - ((value - min) / range) * (height - 4) - 2;
      return `${x},${y}`;
    })
    .join(" ");

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className={cn("h-7 w-[4.5rem]", className)} aria-hidden>
      <polyline
        fill="none"
        stroke={stroke}
        strokeWidth="2.2"
        strokeLinecap="round"
        strokeLinejoin="round"
        points={points}
      />
    </svg>
  );
}
