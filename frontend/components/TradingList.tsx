type Stock = {
  symbol: string;
  name: string;
  price: number;
  change: string;
  trigger: string;
};

interface TradingListProps {
  stocks: Stock[];
}

export default function TradingList({ stocks }: TradingListProps) {
  return (
    <table className="min-w-full bg-white dark:bg-gray-800 shadow rounded">
      <thead>
        <tr>
          <th className="px-4 py-2 text-gray-700 dark:text-gray-200">Symbol</th>
          <th className="px-4 py-2 text-gray-700 dark:text-gray-200">Name</th>
          <th className="px-4 py-2 text-gray-700 dark:text-gray-200">Price</th>
          <th className="px-4 py-2 text-gray-700 dark:text-gray-200">Change</th>
          <th className="px-4 py-2 text-gray-700 dark:text-gray-200">Trigger</th>
        </tr>
      </thead>
      <tbody>
        {stocks.map((stock, idx) => (
          <tr key={idx} className="border-t border-gray-200 dark:border-gray-700">
            <td className="px-4 py-2 font-mono text-gray-900 dark:text-gray-100">{stock.symbol}</td>
            <td className="px-4 py-2 text-gray-900 dark:text-gray-100">{stock.name}</td>
            <td className="px-4 py-2 text-gray-900 dark:text-gray-100">${stock.price.toFixed(2)}</td>
            <td className="px-4 py-2 text-gray-900 dark:text-gray-100">{stock.change}</td>
            <td className="px-4 py-2 font-semibold text-gray-900 dark:text-gray-100">{stock.trigger}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
