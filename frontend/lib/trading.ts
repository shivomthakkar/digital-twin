import { formatter } from './utils';
import { authFetch } from './api';

const API_BASE_URL = process.env.NEXT_PUBLIC_TRADING_API_URL || 'http://localhost:8000';
const REAL_TIME_API_BASE_URL = process.env.NEXT_PUBLIC_REAL_TIME_API_URL || 'http://localhost:8001';

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

export type WatchlistStock = {
  symbol: string;
  company_name: string;
  current_price: string;
  market_cap: string;
  stock_pe: string;
  sector: string;
  roe: string;
  roce: string;
  dividend_yield: string;
  book_value: string;
  revenue: string;
  operating_profit: string;
  net_profit: string;
  scraped_at: string;
  company_url: string;
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

export async function generateToken(clientId: string, pin: string, totp: string): Promise<{ dhan_client_id: string; expiry_time: string }> {
  const response = await authFetch(`${API_BASE_URL}/auth/generate-token`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ dhan_client_id: clientId, pin, totp }),
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error((err as { detail?: string }).detail || `Login failed: ${response.statusText}`);
  }
  return response.json();
}

export async function getWatchlist(): Promise<WatchlistStock[]> {
  try {
    const response = await authFetch(`${REAL_TIME_API_BASE_URL}/watchlist`);
    if (!response.ok) {
      throw new Error(`Failed to fetch watchlist: ${response.statusText}`);
    }
    const data = await response.json();
    return (Array.isArray(data) ? data : data.results) || [];
  } catch (error) {
    console.error('Error fetching watchlist:', error);
    return [];
  }
}

export async function addToWatchlist(symbols: string[]): Promise<void> {
  const response = await authFetch(`${REAL_TIME_API_BASE_URL}/watchlist`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ symbols: symbols.map(s => s.trim().toUpperCase()) }),
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error((err as { detail?: string }).detail || `Failed to add to watchlist: ${response.statusText}`);
  }
}

export async function deleteFromWatchlist(symbol: string): Promise<void> {
  const response = await authFetch(`${REAL_TIME_API_BASE_URL}/watchlist`, {
    method: 'DELETE',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ symbols: [symbol.trim().toUpperCase()] }),
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error((err as { detail?: string }).detail || `Failed to delete from watchlist: ${response.statusText}`);
  }
}
