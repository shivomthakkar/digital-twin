type Metric = {
  title: string;
  value: string | number;
};

interface TradingMetricsProps {
  metrics: Metric[];
}

export default function TradingMetrics({ metrics }: TradingMetricsProps) {
  return (
    <>
      {metrics.map((metric, idx) => (
        <div key={idx} className="bg-white dark:bg-gray-800 shadow rounded p-4 flex flex-col items-center">
          <span className="text-lg font-semibold">{metric.title}</span>
          <span className="text-2xl font-bold mt-2">{metric.value}</span>
        </div>
      ))}
    </>
  );
}
