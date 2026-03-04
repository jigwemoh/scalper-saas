"use client";

import { useEffect, useRef } from "react";
import { createChart, ColorType, LineStyle } from "lightweight-charts";

type DataPoint = { date: string; daily_return_percent: number };

export default function EquityCurve({ data }: { data: DataPoint[] }) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!ref.current || data.length === 0) return;

    const chart = createChart(ref.current, {
      layout: { background: { type: ColorType.Solid, color: "transparent" }, textColor: "#8892a4" },
      grid: { vertLines: { color: "#2d3148" }, horzLines: { color: "#2d3148" } },
      height: 200,
      rightPriceScale: { borderColor: "#2d3148" },
      timeScale: { borderColor: "#2d3148", timeVisible: true },
    });

    const lineSeries = chart.addLineSeries({
      color: "#6c63ff",
      lineWidth: 2,
      lineStyle: LineStyle.Solid,
      priceLineVisible: false,
    });

    // Build cumulative return
    let cumulative = 100;
    const chartData = data.map(({ date, daily_return_percent }) => {
      cumulative *= 1 + daily_return_percent / 100;
      return {
        time: date,
        value: parseFloat(cumulative.toFixed(2)),
      };
    });

    lineSeries.setData(chartData as unknown[]);
    chart.timeScale().fitContent();

    const observer = new ResizeObserver(() => {
      chart.applyOptions({ width: ref.current?.clientWidth || 600 });
    });
    observer.observe(ref.current);

    return () => {
      observer.disconnect();
      chart.remove();
    };
  }, [data]);

  return <div ref={ref} className="w-full" />;
}
