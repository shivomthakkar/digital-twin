import TradingMetrics from '../../components/TradingMetrics';
import TradingList from '../../components/TradingList';
import { getTradingMetrics, getStockList } from '../../lib/trading';

export default function TradingPage() {
  const metrics = getTradingMetrics();
  const stocks = getStockList();

  return (
    <main className="p-6">
      <h1 className="text-3xl font-bold mb-6">Trading Dashboard</h1>
      <div className="mb-8 grid grid-cols-1 md:grid-cols-3 gap-4">
        <TradingMetrics metrics={metrics} />
      </div>
      <div>
        <TradingList stocks={stocks} />
      </div>
    </main>
  );
}
