export interface User {
  id: number;
  email: string;
  is_verified: boolean;
  is_admin: boolean;
  kyc_level: number;
  two_factor_enabled: boolean;
  profile?: UserProfile;
}

export interface UserProfile {
  first_name?: string;
  last_name?: string;
  phone?: string;
  country?: string;
  city?: string;
  address?: string;
  date_of_birth?: string;
}

export interface Balance {
  currency: string;
  available: string;
  locked: string;
  total: string;
}

export interface Order {
  id: number;
  trading_pair: string;
  order_type: string;
  side: 'buy' | 'sell';
  status: string;
  price: string | null;
  amount: string;
  filled_amount: string;
  remaining_amount: string;
  created_at: string;
}

export interface Trade {
  id: number;
  trading_pair: string;
  price: string;
  amount: string;
  total: string;
  timestamp: string;
}

export interface Ticker {
  symbol: string;
  last_price: string;
  price_change_24h: string;
  high_24h: string;
  low_24h: string;
  volume_24h: string;
}

export interface TradingPair {
  id: number;
  symbol: string;
  base_currency: string;
  quote_currency: string;
  is_active: boolean;
  min_order_size: string;
  max_order_size: string;
}
