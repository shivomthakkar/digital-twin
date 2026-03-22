'use client';

interface HealthStatusProps {
  mode: string;
  baseUrl: string;
}

export default function HealthStatus({ mode, baseUrl }: HealthStatusProps) {
  const isSandbox = mode.toLowerCase() === 'sandbox';
  const borderColor = isSandbox ? 'border-yellow-500/50' : 'border-red-500/50';
  const textColor = isSandbox ? 'text-yellow-500' : 'text-red-500';
  const bgColor = isSandbox ? 'bg-yellow-500/5' : 'bg-red-500/5';
  const dotColor = isSandbox ? 'bg-yellow-500' : 'bg-red-500';

  return (
    <div className={`rounded-lg border ${borderColor} ${bgColor} px-4 py-2 flex items-center gap-3`}>
      <span className={`inline-flex items-center gap-2`}>
        <span className={`h-2 w-2 rounded-full ${dotColor}`}></span>
        <span className={`text-sm font-semibold ${textColor}`}>
          {mode.toUpperCase()}
        </span>
      </span>
      <span className={`${textColor} opacity-30`}>•</span>
      <span className="truncate">
        <span className={`text-xs ${textColor} opacity-60`}>{baseUrl}</span>
      </span>
    </div>
  );
}
