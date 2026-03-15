import { formatter } from './utils';
import { authFetch } from './api';

const API_BASE_URL = 'http://localhost:8000';

export type Holding = {
  symbol: string;
  exchange: string;
  quantity: number;
  avg_cost: number;
  current_price: number;
  pnl: number;
  day_change: number;
  day_change_percent: number;
};

export type Position = {
  symbol: string;
  type: string;
  quantity: number;
  entryPrice: number;
  currentPrice: number;
  pnl: number;
  pnlPercent: number;
};

export type Fund = {
  totalBalance: number;
  availableFunds: number;
  marginUsed: number;
  marginAvailable: number;
};

export type PNL = {
  period: string;
  profitLoss: number;
  percentageReturn: number;
};

export type TradingMetric = {
  title: string;
  value: string | number | null;
};

export async function getHoldings(): Promise<Holding[]> {
  try {
    const response = await authFetch(`${API_BASE_URL}/holdings`);
    if (!response.ok) {
      throw new Error(`Failed to fetch holdings: ${response.statusText}`);
    }
    const data = await response.json();
    return Array.isArray(data) ? data : data.holdings || [];
  } catch (error) {
    console.error('Error fetching holdings:', error);
    return [];
  }
}

export async function getPositions(): Promise<Position[]> {
  try {
    const response = await authFetch(`${API_BASE_URL}/positions`);
    if (!response.ok) {
      throw new Error(`Failed to fetch positions: ${response.statusText}`);
    }
    const data = await response.json();
    return Array.isArray(data) ? data : data.positions || [];
  } catch (error) {
    console.error('Error fetching positions:', error);
    return [];
  }
}

export async function getFunds(): Promise<Fund> {
  try {
    const response = await authFetch(`${API_BASE_URL}/funds`);
    if (!response.ok) {
      throw new Error(`Failed to fetch funds: ${response.statusText}`);
    }
    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Error fetching funds:', error);
    return {
      totalBalance: 0,
      availableFunds: 0,
      marginUsed: 0,
      marginAvailable: 0,
    };
  }
}

export async function getPNL(period: string = 'week'): Promise<PNL> {
  try {
    const response = await authFetch(`${API_BASE_URL}/pnl?period=${period}`);
    if (!response.ok) {
      throw new Error(`Failed to fetch PNL: ${response.statusText}`);
    }
    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Error fetching PNL:', error);
    return {
      period: period,
      profitLoss: 0,
      percentageReturn: 0,
    };
  }
}

export async function getTradingMetrics(funds: Fund, pnl: PNL, holdings: Holding[]): Promise<TradingMetric[]> {
  return [
    { title: 'Total Holdings', value: holdings?.length ?? 0 },
    { title: 'Account Balance', value: `${(formatter.format(funds?.totalBalance ?? 0))}` },
    { title: 'Available Funds', value: `${(formatter.format(funds?.availableFunds ?? 0))}` },
    { title: 'P&L (Week)', value: `${(formatter.format(pnl?.profitLoss ?? 0))}` },
    { title: 'Return % (Week)', value: `${(formatter.format(pnl?.percentageReturn ?? 0))}%` },
    { title: 'Margin Used', value: `${(formatter.format(funds?.marginUsed ?? 0))}` },
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
