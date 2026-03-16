import { useState } from 'react';
import { formatter } from '../lib/utils';
import type { WatchlistStock } from '../lib/trading';

interface TradingListProps {
  stocks: WatchlistStock[];
  onRefresh: () => Promise<void>;
  onAdd: (symbol: string) => Promise<void>;
  onDelete: (symbol: string) => Promise<void>;
}

export default function TradingList({ stocks, onRefresh, onAdd, onDelete }: TradingListProps) {
  const [refreshing, setRefreshing] = useState(false);
  const [addSymbol, setAddSymbol] = useState('');
  const [adding, setAdding] = useState(false);
  const [addError, setAddError] = useState<string | null>(null);
  const [deletingSymbol, setDeletingSymbol] = useState<string | null>(null);

  async function handleRefresh() {
    setRefreshing(true);
    await onRefresh();
    setRefreshing(false);
  }

  async function handleAdd() {
    if (!addSymbol.trim()) return;
    setAdding(true);
    setAddError(null);
    try {
      await onAdd(addSymbol.trim());
      setAddSymbol('');
    } catch (err) {
      setAddError(err instanceof Error ? err.message : 'Failed to add stock');
    } finally {
      setAdding(false);
    }
  }

  async function handleDelete(symbol: string) {
    setDeletingSymbol(symbol);
    try {
      await onDelete(symbol);
    } finally {
      setDeletingSymbol(null);
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-2 gap-2">
        <div className="flex items-center gap-2">
          <input
            type="text"
            value={addSymbol}
            onChange={e => setAddSymbol(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleAdd()}
            placeholder="Symbol(s) (e.g. TCS or TCS,INFY)"
            className="rounded-lg border border-gray-600 bg-gray-800 px-3 py-1.5 text-sm text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
          <button
            onClick={handleAdd}
            disabled={adding || !addSymbol.trim()}
            className="rounded-lg bg-green-600 px-3 py-1.5 text-sm font-semibold text-white hover:bg-green-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {adding ? 'Adding...' : '+ Add to Watchlist'}
          </button>
          {addError && <span className="text-sm text-red-400">{addError}</span>}
        </div>
        <button
          onClick={handleRefresh}
          disabled={refreshing}
          className="rounded-lg bg-indigo-600 px-3 py-1.5 text-sm font-semibold text-white hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {refreshing ? 'Refreshing...' : 'Refresh'}
        </button>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full bg-white dark:bg-gray-800 shadow rounded">
          <thead>
            <tr className="bg-gray-100 dark:bg-gray-700">
              <th className="px-4 py-2 text-left text-gray-700 dark:text-gray-200">Symbol</th>
              <th className="px-4 py-2 text-left text-gray-700 dark:text-gray-200">Company Name</th>
              <th className="px-4 py-2 text-left text-gray-700 dark:text-gray-200">Current Price</th>
              <th className="px-4 py-2 text-left text-gray-700 dark:text-gray-200">P/E Ratio</th>
              <th className="px-4 py-2 text-left text-gray-700 dark:text-gray-200">Market Cap</th>
              <th className="px-4 py-2 text-left text-gray-700 dark:text-gray-200">ROE</th>
              <th className="px-4 py-2 text-left text-gray-700 dark:text-gray-200">ROCE</th>
              <th className="px-4 py-2 text-left text-gray-700 dark:text-gray-200">Div Yield</th>
              <th className="px-4 py-2 text-center text-gray-700 dark:text-gray-200">Action</th>
            </tr>
          </thead>
          <tbody>
            {stocks.map((stock, idx) => (
              <tr key={idx} className="border-t border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700">
                <td className="px-4 py-2 font-mono text-gray-900 dark:text-gray-100">{stock.symbol}</td>
                <td className="px-4 py-2 text-gray-900 dark:text-gray-100">{stock.company_name}</td>
                <td className="px-4 py-2 text-gray-900 dark:text-gray-100">₹{stock.current_price}</td>
                <td className="px-4 py-2 text-gray-900 dark:text-gray-100">{stock.stock_pe}</td>
                <td className="px-4 py-2 text-gray-900 dark:text-gray-100">₹{stock.market_cap}Cr</td>
                <td className="px-4 py-2 text-gray-900 dark:text-gray-100">{stock.roe}%</td>
                <td className="px-4 py-2 text-gray-900 dark:text-gray-100">{stock.roce}%</td>
                <td className="px-4 py-2 text-gray-900 dark:text-gray-100">{stock.dividend_yield}%</td>
                <td className="px-4 py-2 text-center">
                  <button
                    onClick={() => handleDelete(stock.symbol)}
                    disabled={deletingSymbol === stock.symbol}
                    className="rounded px-2 py-1 text-xs font-semibold text-red-400 hover:bg-red-500/10 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {deletingSymbol === stock.symbol ? '...' : 'Delete'}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
