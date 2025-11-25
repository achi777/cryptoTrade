import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import api from '../../services/api';

interface Balance {
  currency: string;
  available: string;
  locked: string;
  total: string;
}

interface WalletState {
  balances: Balance[];
  loading: boolean;
  error: string | null;
}

const initialState: WalletState = {
  balances: [],
  loading: false,
  error: null,
};

export const fetchBalances = createAsyncThunk('wallet/fetchBalances', async (_, { rejectWithValue }) => {
  try {
    const response = await api.get('/user/balances');
    return response.data.balances;
  } catch (error: any) {
    return rejectWithValue(error.response?.data?.error || 'Failed to fetch balances');
  }
});

export const getDepositAddress = createAsyncThunk(
  'wallet/getDepositAddress',
  async (currency: string, { rejectWithValue }) => {
    try {
      const response = await api.get(`/wallets/${currency}/address`);
      return response.data;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.error || 'Failed to get deposit address');
    }
  }
);

export const createWithdrawal = createAsyncThunk(
  'wallet/createWithdrawal',
  async (
    data: { currency: string; address: string; amount: string; totp_code?: string },
    { rejectWithValue }
  ) => {
    try {
      const response = await api.post('/wallets/withdraw', data);
      return response.data;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.error || 'Withdrawal failed');
    }
  }
);

const walletSlice = createSlice({
  name: 'wallet',
  initialState,
  reducers: {
    clearError: (state) => {
      state.error = null;
    },
    updateBalance: (state, action) => {
      const index = state.balances.findIndex((b) => b.currency === action.payload.currency);
      if (index >= 0) {
        state.balances[index] = action.payload;
      } else {
        state.balances.push(action.payload);
      }
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchBalances.pending, (state) => {
        state.loading = true;
      })
      .addCase(fetchBalances.fulfilled, (state, action) => {
        state.loading = false;
        state.balances = action.payload;
      })
      .addCase(fetchBalances.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload as string;
      });
  },
});

export const { clearError, updateBalance } = walletSlice.actions;
export default walletSlice.reducer;
