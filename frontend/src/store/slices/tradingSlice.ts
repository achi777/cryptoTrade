import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import api from '../../services/api';

interface Order {
  id: number;
  trading_pair: string;
  order_type: string;
  side: string;
  status: string;
  price: string | null;
  amount: string;
  filled_amount: string;
  remaining_amount: string;
  created_at: string;
}

interface TradingState {
  openOrders: Order[];
  orderHistory: Order[];
  loading: boolean;
  error: string | null;
}

const initialState: TradingState = {
  openOrders: [],
  orderHistory: [],
  loading: false,
  error: null,
};

export const fetchOpenOrders = createAsyncThunk(
  'trading/fetchOpenOrders',
  async (pair: string | undefined = undefined, { rejectWithValue }) => {
    try {
      const response = await api.get('/trading/orders/open', { params: { pair } });
      return response.data.orders;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.error || 'Failed to fetch orders');
    }
  }
);

export const fetchOrderHistory = createAsyncThunk(
  'trading/fetchOrderHistory',
  async (params: { pair?: string; page?: number }, { rejectWithValue }) => {
    try {
      const response = await api.get('/trading/orders', { params });
      return response.data;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.error || 'Failed to fetch order history');
    }
  }
);

export const createOrder = createAsyncThunk(
  'trading/createOrder',
  async (
    data: { pair: string; type: string; side: string; amount: string; price?: string },
    { rejectWithValue }
  ) => {
    try {
      const response = await api.post('/trading/orders', data);
      return response.data.order;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.error || 'Order creation failed');
    }
  }
);

export const cancelOrder = createAsyncThunk(
  'trading/cancelOrder',
  async (orderId: number, { rejectWithValue }) => {
    try {
      const response = await api.post(`/trading/orders/${orderId}/cancel`);
      return response.data.order;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.error || 'Cancel failed');
    }
  }
);

const tradingSlice = createSlice({
  name: 'trading',
  initialState,
  reducers: {
    clearError: (state) => {
      state.error = null;
    },
    updateOrder: (state, action: PayloadAction<Order>) => {
      const index = state.openOrders.findIndex((o) => o.id === action.payload.id);
      if (action.payload.status === 'cancelled' || action.payload.status === 'filled') {
        if (index >= 0) {
          state.openOrders.splice(index, 1);
        }
        state.orderHistory.unshift(action.payload);
      } else if (index >= 0) {
        state.openOrders[index] = action.payload;
      }
    },
    addOrder: (state, action: PayloadAction<Order>) => {
      if (['open', 'partially_filled'].includes(action.payload.status)) {
        state.openOrders.unshift(action.payload);
      }
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchOpenOrders.pending, (state) => {
        state.loading = true;
      })
      .addCase(fetchOpenOrders.fulfilled, (state, action) => {
        state.loading = false;
        state.openOrders = action.payload;
      })
      .addCase(fetchOpenOrders.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload as string;
      })
      .addCase(createOrder.fulfilled, (state, action) => {
        if (['open', 'partially_filled'].includes(action.payload.status)) {
          state.openOrders.unshift(action.payload);
        }
      })
      .addCase(cancelOrder.fulfilled, (state, action) => {
        state.openOrders = state.openOrders.filter((o) => o.id !== action.payload.id);
      });
  },
});

export const { clearError, updateOrder, addOrder } = tradingSlice.actions;
export default tradingSlice.reducer;
