'use client';

import { useEffect, useState, useRef } from 'react';
import TradingMetrics from '../../components/TradingMetrics';
import TradingList from '../../components/TradingList';
import LoginModal from '../../components/LoginModal';
import { formatter } from '../../lib/utils';
import { 
  getHoldings, 
  getPositions, 
  getFunds, 
  getPNL, 
  getTradingMetrics,
  getWatchlist,
  addToWatchlist,
  deleteFromWatchlist,
  type Holding,
  type Position,
  type Fund,
  type PNL,
  type TradingMetric,
  type WatchlistStock,
} from '../../lib/trading';
import ChatWindow, { ChatWindowRef, ChatMessage } from '@/components/ChatWindow';

export default function TradingPage() {
  const [metrics, setMetrics] = useState<TradingMetric[]>([]);
  const [holdings, setHoldings] = useState<Holding[]>([]);
  const [positions, setPositions] = useState<Position[]>([]);
  const [funds, setFunds] = useState<Fund | null>(null);
  const [pnl, setPNL] = useState<PNL | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [stocks, setStocks] = useState<WatchlistStock[]>([]);
  const [isLoginOpen, setIsLoginOpen] = useState(false);
  const chatWindowRef = useRef<ChatWindowRef>(null);

  const handleChatMessage = async (history: ChatMessage[]) => {
    console.log(history);
    // Wait 2 seconds
    await new Promise((resolve) => setTimeout(resolve, 2000));

    // Update the loading message with the response
    const lastUserMessage = [...history].reverse().find(m => m.sender === 'user')?.text ?? '';
    chatWindowRef.current?.addMessage(`Echo: ${lastUserMessage}`);
  };

  // async function fetchWatchlist() {
  //   const stocksData = await getWatchlist();
  //   setStocks(stocksData);
  // }

  // async function handleAdd(symbol: string) {
  //   const symbols = symbol.split(',').map(s => s.trim()).filter(s => s.length > 0);
  //   if (symbols.length === 0) return;
  //   await addToWatchlist(symbols);
  //   await fetchWatchlist();
  // }

  // async function handleDelete(symbol: string) {
  //   await deleteFromWatchlist(symbol);
  //   await fetchWatchlist();
  // }

  useEffect(() => {
    async function fetchData() {
      try {
        setLoading(true);
        setError(null);

        // Fetch all data in parallel
        const [holdingsData, positionsData, fundsData, pnlData] = await Promise.all([
          getHoldings(),
          getPositions(),
          getFunds(),
          getPNL('week'),
        ]);

        setHoldings(holdingsData);
        setPositions(positionsData);
        setFunds(fundsData);
        setPNL(pnlData);

        // Generate metrics from fetched data
        const metricsData = await getTradingMetrics(fundsData, pnlData, holdingsData);
        setMetrics(metricsData);

        // await fetchWatchlist();
      } catch (err) {
        console.error('Error fetching trading data:', err);
        setError(err instanceof Error ? err.message : 'Failed to load trading data');
      } finally {
        setLoading(false);
      }
    }

    fetchData();
  }, []);


  return (
    <main>
      <div className="relative isolate bg-gray-900 min-h-screen px-6 lg:px-8">
        <div aria-hidden="true" className="absolute inset-x-0 -z-10 transform-gpu overflow-hidden blur-3xl">
          <div style={{clipPath: 'polygon(74.1% 44.1%, 100% 61.6%, 97.5% 26.9%, 85.5% 0.1%, 80.7% 2%, 72.5% 32.5%, 60.2% 62.4%, 52.4% 68.1%, 47.5% 58.3%, 45.2% 34.5%, 27.5% 76.7%, 0.1% 64.9%, 17.9% 100%, 27.6% 76.8%, 76.1% 97.7%, 74.1% 44.1%)'}} className="relative left-1/2 -z-10 aspect-[1155/678] w-[144.5rem] max-w-none -translate-x-1/2 rotate-[30deg] bg-gradient-to-tr from-[#ff80b5] to-[#9089fc] opacity-20 sm:left-[calc(50%-40rem)] sm:w-[288.75rem]" />
        </div>
        <div>
          <div className="flex items-center justify-between mb-6">
            <h1 className="text-3xl font-bold text-white">Trading Dashboard</h1>
            <button
              onClick={() => setIsLoginOpen(true)}
              className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-500"
            >
              Login
            </button>
          </div>
          
          {error && (
            <div className="mb-6 p-4 bg-red-500/10 border border-red-500 rounded text-red-400">
              {error}
            </div>
          )}

          {loading ? (
            <div className="text-center py-12">
              <p className="text-gray-300">Loading trading data...</p>
            </div>
          ) : (
            <>
              <div className="mb-8 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                <TradingMetrics metrics={metrics} />
              </div>

              {holdings.length > 0 && (
                <div className="mb-8">
                  <h2 className="text-2xl font-bold mb-4 text-white">Holdings</h2>
                  <div className="overflow-x-auto bg-white dark:bg-gray-800 shadow rounded">
                    <table className="min-w-full">
                      <thead>
                        <tr className="bg-gray-100 dark:bg-gray-700">
                          <th className="px-4 py-3 text-left text-gray-700 dark:text-gray-200 font-semibold">Symbol</th>
                          <th className="px-4 py-3 text-left text-gray-700 dark:text-gray-200 font-semibold">Quantity</th>
                          <th className="px-4 py-3 text-left text-gray-700 dark:text-gray-200 font-semibold">Avg Price</th>
                          <th className="px-4 py-3 text-left text-gray-700 dark:text-gray-200 font-semibold">Current Price</th>
                          <th className="px-4 py-3 text-left text-gray-700 dark:text-gray-200 font-semibold">Total Value</th>
                        </tr>
                      </thead>
                      <tbody>
                        {holdings.map((holding, idx) => (
                          <tr key={idx} className="border-t border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700">
                            <td className="px-4 py-3 font-mono font-semibold text-gray-900 dark:text-gray-100">{holding.symbol}</td>
                            <td className="px-4 py-3 text-gray-900 dark:text-gray-100">{holding.quantity}</td>
                            <td className="px-4 py-3 text-gray-900 dark:text-gray-100">{formatter.format(holding.avg_cost)}</td>
                            <td className="px-4 py-3 text-gray-900 dark:text-gray-100">{formatter.format(holding.current_price)}</td>
                            <td className="px-4 py-3 font-semibold text-gray-900 dark:text-gray-100">{formatter.format(holding.current_price * holding.quantity)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {positions.length > 0 && (
                <div className="mb-8">
                  <h2 className="text-2xl font-bold mb-4 text-white">Open Positions</h2>
                  <div className="overflow-x-auto bg-white dark:bg-gray-800 shadow rounded">
                    <table className="min-w-full">
                      <thead>
                        <tr className="bg-gray-100 dark:bg-gray-700">
                          <th className="px-4 py-3 text-left text-gray-700 dark:text-gray-200 font-semibold">Symbol</th>
                          <th className="px-4 py-3 text-left text-gray-700 dark:text-gray-200 font-semibold">Type</th>
                          <th className="px-4 py-3 text-left text-gray-700 dark:text-gray-200 font-semibold">Quantity</th>
                          <th className="px-4 py-3 text-left text-gray-700 dark:text-gray-200 font-semibold">Entry Price</th>
                          <th className="px-4 py-3 text-left text-gray-700 dark:text-gray-200 font-semibold">Current Price</th>
                          <th className="px-4 py-3 text-left text-gray-700 dark:text-gray-200 font-semibold">P&L</th>
                          <th className="px-4 py-3 text-left text-gray-700 dark:text-gray-200 font-semibold">Return %</th>
                        </tr>
                      </thead>
                      <tbody>
                        {positions.map((position, idx) => (
                          <tr key={idx} className="border-t border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700">
                            <td className="px-4 py-3 font-mono font-semibold text-gray-900 dark:text-gray-100">{position.symbol}</td>
                            <td className="px-4 py-3 text-gray-900 dark:text-gray-100">{position.type}</td>
                            <td className="px-4 py-3 text-gray-900 dark:text-gray-100">{position.quantity}</td>
                            <td className="px-4 py-3 text-gray-900 dark:text-gray-100">{formatter.format(position.entryPrice)}</td>
                            <td className="px-4 py-3 text-gray-900 dark:text-gray-100">{formatter.format(position.currentPrice)}</td>
                            <td className={`px-4 py-3 font-semibold ${position.pnl >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
                              {formatter.format(position.pnl)}
                            </td>
                            <td className={`px-4 py-3 font-semibold ${position.pnlPercent >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
                              {position.pnlPercent.toFixed(2)}%
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* <div className="mb-8">
                <h2 className="text-2xl font-bold mb-4 text-white">Watchlist</h2>
                <TradingList stocks={stocks} onRefresh={fetchWatchlist} onAdd={handleAdd} onDelete={handleDelete} />
              </div> */}
            </>
          )}
        </div>
      </div>

      <LoginModal
        isOpen={isLoginOpen}
        onClose={() => setIsLoginOpen(false)}
        onSuccess={() => { setIsLoginOpen(false); }}
      />

      <ChatWindow
        ref={chatWindowRef}
        title="Trading Support"
        onSendMessage={handleChatMessage}
      />
    </main>
  );
}
