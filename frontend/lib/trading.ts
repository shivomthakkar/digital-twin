export function getTradingMetrics() {
  return [
    { title: 'Total Stocks', value: 5 },
    { title: 'Market Value', value: '$120,000' },
    { title: 'Active Triggers', value: 2 },
  ];
}

export function getStockList() {
  return [
    { symbol: 'AAPL', name: 'Apple Inc.', price: 175.12, change: '+1.2%', trigger: 'Buy' },
    { symbol: 'GOOGL', name: 'Alphabet Inc.', price: 2825.50, change: '-0.5%', trigger: 'Sell' },
    { symbol: 'AMZN', name: 'Amazon.com Inc.', price: 3400.00, change: '+0.8%', trigger: 'Hold' },
    { symbol: 'TSLA', name: 'Tesla Inc.', price: 900.10, change: '+2.1%', trigger: 'Buy' },
    { symbol: 'MSFT', name: 'Microsoft Corp.', price: 299.35, change: '-1.0%', trigger: 'Sell' },
  ];
}
