'use client';

import type { Holding } from '../lib/trading';
import { formatter } from '../lib/utils';

interface StockLevels {
  trigger: number;
  limit: number;
}

interface StockLevelConfig {
  sl: StockLevels | null;
  gtt: StockLevels | null;
}

const SL_GTT_MAP: Record<string, StockLevelConfig> = {
  TCS:         { sl: { trigger: 3800, limit: 3750 }, gtt: { trigger: 4200, limit: 4250 } },
  RELIANCE:    { sl: { trigger: 2800, limit: 2750 }, gtt: { trigger: 3200, limit: 3250 } },
  INFY:        { sl: { trigger: 1700, limit: 1680 }, gtt: { trigger: 2000, limit: 2020 } },
  HDFCBANK:    { sl: { trigger: 1600, limit: 1575 }, gtt: { trigger: 1900, limit: 1920 } },
  ICICIBANK:   { sl: { trigger: 1150, limit: 1130 }, gtt: { trigger: 1400, limit: 1420 } },
  WIPRO:       { sl: { trigger: 550,  limit: 540  }, gtt: { trigger: 680,  limit: 690  } },
  SBIN:        { sl: { trigger: 700,  limit: 690  }, gtt: { trigger: 850,  limit: 860  } },
  AXISBANK:    { sl: { trigger: 1050, limit: 1030 }, gtt: { trigger: 1250, limit: 1270 } },
  BAJFINANCE:  { sl: { trigger: 7000, limit: 6900 }, gtt: { trigger: 8500, limit: 8600 } },
  TATAMOTORS:  { sl: { trigger: 920,  limit: 905  }, gtt: { trigger: 1100, limit: 1120 } },
  HINDUNILVR:  { sl: { trigger: 2300, limit: 2280 }, gtt: { trigger: 2700, limit: 2720 } },
  MARUTI:      { sl: { trigger: 11000, limit: 10800 }, gtt: { trigger: 13500, limit: 13700 } },
  LTIM:        { sl: { trigger: 5200, limit: 5150 }, gtt: { trigger: 6200, limit: 6250 } },
  ADANIPORTS:  { sl: { trigger: 1100, limit: 1080 }, gtt: { trigger: 1400, limit: 1420 } },
  ONGC:        { sl: { trigger: 280,  limit: 275  }, gtt: { trigger: 350,  limit: 358  } },
};

const MAX_TILES = 12;

interface StockGridProps {
  holdings: Holding[];
}

function formatPrice(price: number): string {
  if (price >= 1000) return formatter.format(price);
  return `₹${price.toFixed(2)}`;
}

export default function StockGrid({ holdings }: StockGridProps) {
  if (holdings.length === 0) return null;

  // Sort by total value descending
  const sorted = [...holdings].sort(
    (a, b) => b.current_price * b.quantity - a.current_price * a.quantity,
  );

  const overflow = sorted.length > MAX_TILES ? sorted.length - (MAX_TILES - 1) : 0;
  const displayed = overflow > 0 ? sorted.slice(0, MAX_TILES - 1) : sorted.slice(0, MAX_TILES);

  return (
    <div className="mb-6">
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3">
        {displayed.map((holding) => {
          const levels = SL_GTT_MAP[holding.symbol] ?? { sl: null, gtt: null };
          const isPositive = holding.day_change_percent >= 0;
          const totalValue = holding.current_price * holding.quantity;

          return (
            <div
              key={holding.symbol}
              className="bg-gray-800 border border-gray-700 rounded-xl p-3 flex flex-col gap-1.5 hover:border-indigo-500/50 transition-colors"
            >
              {/* Header */}
              <div className="flex items-start justify-between gap-1">
                <span className="font-mono font-bold text-white text-sm leading-tight">
                  {holding.symbol}
                </span>
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-gray-700 text-gray-400 font-medium flex-shrink-0">
                  {holding.exchange}
                </span>
              </div>

              {/* Current price */}
              <div className="text-2xl font-bold text-white leading-none">
                ₹{holding.current_price.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </div>

              {/* Day change */}
              <div className={`text-xs font-semibold ${isPositive ? 'text-green-400' : 'text-red-400'}`}>
                {isPositive ? '+' : ''}{holding.day_change.toFixed(2)}&nbsp;
                ({isPositive ? '+' : ''}{holding.day_change_percent.toFixed(2)}%)
              </div>

              {/* Total value */}
              <div className="text-[11px] text-gray-400">
                Val: {formatter.format(totalValue)}
              </div>

              <div className="border-t border-gray-700 my-0.5" />

              {/* SL Level */}
              {levels.sl ? (
                <div className="flex flex-col gap-0.5">
                  <span className="text-[10px] font-semibold text-red-400 uppercase tracking-wide">SL</span>
                  <div className="flex items-center gap-1 text-[11px] text-gray-300">
                    <span className="bg-red-900/40 text-red-300 rounded px-1 font-mono">
                      {formatPrice(levels.sl.trigger)}
                    </span>
                    <span className="text-gray-500">→</span>
                    <span className="bg-red-900/20 text-red-400 rounded px-1 font-mono">
                      {formatPrice(levels.sl.limit)}
                    </span>
                  </div>
                </div>
              ) : (
                <div className="text-[11px] text-gray-600 italic">— No SL set</div>
              )}

              {/* GTT Level */}
              {levels.gtt ? (
                <div className="flex flex-col gap-0.5">
                  <span className="text-[10px] font-semibold text-indigo-400 uppercase tracking-wide">GTT</span>
                  <div className="flex items-center gap-1 text-[11px] text-gray-300">
                    <span className="bg-indigo-900/40 text-indigo-300 rounded px-1 font-mono">
                      {formatPrice(levels.gtt.trigger)}
                    </span>
                    <span className="text-gray-500">→</span>
                    <span className="bg-indigo-900/20 text-indigo-400 rounded px-1 font-mono">
                      {formatPrice(levels.gtt.limit)}
                    </span>
                  </div>
                </div>
              ) : (
                <div className="text-[11px] text-gray-600 italic">— No GTT set</div>
              )}
            </div>
          );
        })}

        {/* Overflow tile */}
        {overflow > 0 && (
          <div className="bg-gray-800/60 border border-dashed border-gray-600 rounded-xl p-3 flex items-center justify-center">
            <div className="text-center">
              <div className="text-2xl font-bold text-gray-400">+{overflow}</div>
              <div className="text-xs text-gray-500 mt-1">more stocks</div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
