import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import api from '../../services/api';

interface Ticker {
  symbol: string;
  last_price: string;
  price_change_24h: string;
  high_24h: string;
  low_24h: string;
  volume_24h: string;
}

interface TradingPair {
  id: number;
  symbol: string;
  base_currency: string;
  quote_currency: string;
  is_active: boolean;
  min_order_size: string;
  max_order_size: string;
  last_price: string;
}

interface OrderBook {
  bids: { price: string; amount: string }[];
  asks: { price: string; amount: string }[];
}

interface RecentTrade {
  id: number;
  price: string;
  amount: string;
  timestamp: string;
}

interface MarketState {
  tickers: Record<string, Ticker>;
  tradingPairs: TradingPair[];
  currentPair: TradingPair | null;
  orderBook: OrderBook;
  recentTrades: RecentTrade[];
  loading: boolean;
  error: string | null;
}

const initialState: MarketState = {
  tickers: {},
  tradingPairs: [],
  currentPair: null,
  orderBook: { bids: [], asks: [] },
  recentTrades: [],
  loading: false,
  error: null,
};

export const fetchTickers = createAsyncThunk('market/fetchTickers', async (_, { rejectWithValue }) => {
  try {
    const response = await api.get('/market/tickers');
    return response.data.tickers;
  } catch (error: any) {
    return rejectWithValue(error.response?.data?.error || 'Failed to fetch tickers');
  }
});

export const fetchTradingPairs = createAsyncThunk(
  'market/fetchTradingPairs',
  async (_, { rejectWithValue }) => {
    try {
      const response = await api.get('/trading/pairs');
      return response.data.pairs;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.error || 'Failed to fetch trading pairs');
    }
  }
);

export const fetchOrderBook = createAsyncThunk(
  'market/fetchOrderBook',
  async (symbol: string, { rejectWithValue }) => {
    try {
      const response = await api.get(`/market/orderbook/${symbol}`);
      return response.data;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.error || 'Failed to fetch order book');
    }
  }
);

export const fetchRecentTrades = createAsyncThunk(
  'market/fetchRecentTrades',
  async (symbol: string, { rejectWithValue }) => {
    try {
      const response = await api.get(`/market/trades/${symbol}`);
      return response.data.trades;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.error || 'Failed to fetch trades');
    }
  }
);

const marketSlice = createSlice({
  name: 'market',
  initialState,
  reducers: {
    setCurrentPair: (state, action: PayloadAction<string>) => {
      state.currentPair = state.tradingPairs.find((p) => p.symbol === action.payload) || null;
    },
    updateTicker: (state, action: PayloadAction<Ticker>) => {
      state.tickers[action.payload.symbol] = action.payload;
    },
    updateOrderBook: (state, action: PayloadAction<OrderBook>) => {
      state.orderBook = action.payload;
    },
    addRecentTrade: (state, action: PayloadAction<RecentTrade>) => {
      state.recentTrades.unshift(action.payload);
      if (state.recentTrades.length > 100) {
        state.recentTrades.pop();
      }
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchTickers.fulfilled, (state, action) => {
        action.payload.forEach((ticker: Ticker) => {
          state.tickers[ticker.symbol] = ticker;
        });
      })
      .addCase(fetchTradingPairs.fulfilled, (state, action) => {
        state.tradingPairs = action.payload;
      })
      .addCase(fetchOrderBook.fulfilled, (state, action) => {
        state.orderBook = {
          bids: action.payload.bids || [],
          asks: action.payload.asks || [],
        };
      })
      .addCase(fetchRecentTrades.fulfilled, (state, action) => {
        state.recentTrades = action.payload;
      });
  },
});

export const { setCurrentPair, updateTicker, updateOrderBook, addRecentTrade } = marketSlice.actions;
export default marketSlice.reducer;
