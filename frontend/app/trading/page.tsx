import TradingMetrics from '../../components/TradingMetrics';
import TradingList from '../../components/TradingList';
import { getTradingMetrics, getStockList } from '../../lib/trading';

export default function TradingPage() {
  const metrics = getTradingMetrics();
  const stocks = getStockList();

  return (
    <main>
      <div className="relative isolate bg-gray-900 min-h-screen px-6 lg:px-8">
        <div aria-hidden="true" className="absolute inset-x-0 -z-10 transform-gpu overflow-hidden blur-3xl">
          <div style={{clipPath: 'polygon(74.1% 44.1%, 100% 61.6%, 97.5% 26.9%, 85.5% 0.1%, 80.7% 2%, 72.5% 32.5%, 60.2% 62.4%, 52.4% 68.1%, 47.5% 58.3%, 45.2% 34.5%, 27.5% 76.7%, 0.1% 64.9%, 17.9% 100%, 27.6% 76.8%, 76.1% 97.7%, 74.1% 44.1%)'}} className="relative left-1/2 -z-10 aspect-[1155/678] w-[144.5rem] max-w-none -translate-x-1/2 rotate-[30deg] bg-gradient-to-tr from-[#ff80b5] to-[#9089fc] opacity-20 sm:left-[calc(50%-40rem)] sm:w-[288.75rem]" />
        </div>
        <div>
          <h1 className="text-3xl font-bold mb-6 text-white">Trading Dashboard</h1>
          <div className="mb-8 grid grid-cols-1 md:grid-cols-3 gap-4">
            <TradingMetrics metrics={metrics} />
          </div>
          <div>
            <TradingList stocks={stocks} />
          </div>
        </div>
      </div>
    </main>
  );
}
