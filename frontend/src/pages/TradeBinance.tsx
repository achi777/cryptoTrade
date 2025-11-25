import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { useDispatch, useSelector } from 'react-redux';
import {
  Box,
  Grid,
  Typography,
  TextField,
  Button,
  ToggleButton,
  ToggleButtonGroup,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Tabs,
  Tab,
  List,
  ListItem,
  ListItemButton,
  ListItemText,
  Chip,
} from '@mui/material';
import { useForm } from 'react-hook-form';
import toast from 'react-hot-toast';

import { RootState, AppDispatch } from '../store';
import { fetchTradingPairs, fetchOrderBook, fetchRecentTrades, setCurrentPair } from '../store/slices/marketSlice';
import { createOrder, fetchOpenOrders, cancelOrder } from '../store/slices/tradingSlice';
import { fetchBalances } from '../store/slices/walletSlice';
import wsService from '../services/websocket';
import TradingChart from '../components/TradingChart';
import api from '../services/api';

interface OrderForm {
  amount: string;
  price: string;
}

const TradeBinance: React.FC = () => {
  const { pair } = useParams<{ pair?: string }>();
  const dispatch = useDispatch<AppDispatch>();

  const { tradingPairs, orderBook, recentTrades, tickers } = useSelector(
    (state: RootState) => state.market
  );
  const { openOrders } = useSelector((state: RootState) => state.trading);
  const { balances } = useSelector((state: RootState) => state.wallet);

  const [orderType, setOrderType] = useState<'limit' | 'market'>('limit');
  const [orderSide, setOrderSide] = useState<'buy' | 'sell'>('buy');
  const [selectedPair, setSelectedPair] = useState(pair || 'BTC_USDT');
  const [chartData, setChartData] = useState<any[]>([]);
  const [chartInterval, setChartInterval] = useState('1h');
  const [ordersTab, setOrdersTab] = useState(0);

  const buyForm = useForm<OrderForm>();
  const sellForm = useForm<OrderForm>();

  useEffect(() => {
    dispatch(fetchTradingPairs());
    dispatch(fetchBalances());
    dispatch(fetchOpenOrders());
  }, [dispatch]);

  // Load chart data
  const loadChartData = async () => {
    try {
      const response = await api.get(`/market/klines/${selectedPair}`, {
        params: { interval: chartInterval, limit: 100 }
      });
      setChartData(response.data.candles || []);
    } catch (error) {
      console.error('Failed to load chart data:', error);
    }
  };

  useEffect(() => {
    loadChartData();
    const interval = setInterval(loadChartData, 3000); // Refresh every 3 seconds
    return () => clearInterval(interval);
  }, [selectedPair, chartInterval]);

  useEffect(() => {
    if (selectedPair) {
      dispatch(setCurrentPair(selectedPair));
      dispatch(fetchOrderBook(selectedPair));
      dispatch(fetchRecentTrades(selectedPair));
      wsService.subscribeToMarket(selectedPair);
    }

    return () => {
      if (selectedPair) {
        wsService.unsubscribeFromMarket(selectedPair);
      }
    };
  }, [selectedPair, dispatch]);

  const ticker = tickers[selectedPair];
  const [baseCurrency, quoteCurrency] = selectedPair.split('_');
  const baseBalance = balances.find((b) => b.currency === baseCurrency);
  const quoteBalance = balances.find((b) => b.currency === quoteCurrency);

  const onBuySubmit = async (data: OrderForm) => {
    try {
      if (orderType === 'limit' && !data.price) {
        toast.error('Price is required for limit orders');
        return;
      }

      // Normalize decimal separator (replace comma with dot)
      const normalizedAmount = String(data.amount).replace(',', '.');
      const normalizedPrice = data.price ? String(data.price).replace(',', '.') : undefined;

      const orderData = {
        pair: selectedPair,
        type: orderType,
        side: 'buy',
        amount: normalizedAmount,
        ...(orderType === 'limit' && normalizedPrice && { price: normalizedPrice }),
      };

      await dispatch(createOrder(orderData)).unwrap();
      toast.success('Buy order placed successfully');
      dispatch(fetchBalances());
      dispatch(fetchOpenOrders());
      loadChartData(); // Reload chart immediately
      buyForm.reset();
    } catch (error: any) {
      toast.error(error || 'Failed to place buy order');
    }
  };

  const onSellSubmit = async (data: OrderForm) => {
    try {
      if (orderType === 'limit' && !data.price) {
        toast.error('Price is required for limit orders');
        return;
      }

      // Normalize decimal separator (replace comma with dot)
      const normalizedAmount = String(data.amount).replace(',', '.');
      const normalizedPrice = data.price ? String(data.price).replace(',', '.') : undefined;

      const orderData = {
        pair: selectedPair,
        type: orderType,
        side: 'sell',
        amount: normalizedAmount,
        ...(orderType === 'limit' && normalizedPrice && { price: normalizedPrice }),
      };

      await dispatch(createOrder(orderData)).unwrap();
      toast.success('Sell order placed successfully');
      dispatch(fetchBalances());
      dispatch(fetchOpenOrders());
      loadChartData(); // Reload chart immediately
      sellForm.reset();
    } catch (error: any) {
      toast.error(error || 'Failed to place sell order');
    }
  };

  const handleCancel = async (orderId: number) => {
    try {
      await dispatch(cancelOrder(orderId)).unwrap();
      toast.success('Order cancelled');
      dispatch(fetchBalances());
      dispatch(fetchOpenOrders());
    } catch (error: any) {
      toast.error(error || 'Failed to cancel order');
    }
  };

  return (
    <Box sx={{ height: 'calc(100vh - 64px)', display: 'flex', flexDirection: 'column', bgcolor: '#0e1117' }}>
      {/* Header */}
      <Box sx={{ bgcolor: '#161a1e', px: 2, py: 1, borderBottom: '1px solid #2b2f36' }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <Typography variant="h6" sx={{ color: '#fff', fontWeight: 'bold' }}>
            {selectedPair.replace('_', '/')}
          </Typography>
          {ticker && (
            <>
              <Typography variant="h6" sx={{ color: parseFloat(ticker.price_change_24h) >= 0 ? '#26a69a' : '#ef5350' }}>
                ${parseFloat(ticker.last_price).toFixed(2)}
              </Typography>
              <Chip
                label={`${parseFloat(ticker.price_change_24h).toFixed(2)}%`}
                size="small"
                sx={{
                  bgcolor: parseFloat(ticker.price_change_24h) >= 0 ? 'rgba(38, 166, 154, 0.1)' : 'rgba(239, 83, 80, 0.1)',
                  color: parseFloat(ticker.price_change_24h) >= 0 ? '#26a69a' : '#ef5350'
                }}
              />
              <Typography variant="caption" sx={{ color: '#b7bdc6' }}>
                24h High: {parseFloat(ticker.high_24h).toFixed(2)}
              </Typography>
              <Typography variant="caption" sx={{ color: '#b7bdc6' }}>
                24h Low: {parseFloat(ticker.low_24h).toFixed(2)}
              </Typography>
              <Typography variant="caption" sx={{ color: '#b7bdc6' }}>
                24h Volume: {parseFloat(ticker.volume_24h).toFixed(4)} {baseCurrency}
              </Typography>
            </>
          )}
        </Box>
      </Box>

      {/* Main Content */}
      <Box sx={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
        {/* Left - Order Book */}
        <Box sx={{ width: 280, borderRight: '1px solid #2b2f36', display: 'flex', flexDirection: 'column', bgcolor: '#161a1e' }}>
          <Box sx={{ p: 1.5, borderBottom: '1px solid #2b2f36' }}>
            <Typography variant="subtitle2" sx={{ color: '#d1d4dc' }}>Order Book</Typography>
          </Box>
          <Box sx={{ flex: 1, overflow: 'auto' }}>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell sx={{ color: '#b7bdc6', fontSize: 11, py: 0.5 }}>Price({quoteCurrency})</TableCell>
                  <TableCell align="right" sx={{ color: '#b7bdc6', fontSize: 11, py: 0.5 }}>Amount({baseCurrency})</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {orderBook.asks.slice(0, 12).reverse().map((ask, i) => (
                  <TableRow key={`ask-${i}`} sx={{ '&:hover': { bgcolor: '#1e2329' } }}>
                    <TableCell sx={{ color: '#ef5350', fontSize: 12, py: 0.3 }}>{parseFloat(ask.price).toFixed(2)}</TableCell>
                    <TableCell align="right" sx={{ color: '#d1d4dc', fontSize: 12, py: 0.3 }}>{parseFloat(ask.amount).toFixed(6)}</TableCell>
                  </TableRow>
                ))}
                <TableRow>
                  <TableCell colSpan={2} sx={{ py: 1, bgcolor: '#1e2329', textAlign: 'center' }}>
                    <Typography variant="h6" sx={{ color: ticker ? (parseFloat(ticker.price_change_24h) >= 0 ? '#26a69a' : '#ef5350') : '#d1d4dc' }}>
                      {ticker ? parseFloat(ticker.last_price).toFixed(2) : '-'}
                    </Typography>
                  </TableCell>
                </TableRow>
                {orderBook.bids.slice(0, 12).map((bid, i) => (
                  <TableRow key={`bid-${i}`} sx={{ '&:hover': { bgcolor: '#1e2329' } }}>
                    <TableCell sx={{ color: '#26a69a', fontSize: 12, py: 0.3 }}>{parseFloat(bid.price).toFixed(2)}</TableCell>
                    <TableCell align="right" sx={{ color: '#d1d4dc', fontSize: 12, py: 0.3 }}>{parseFloat(bid.amount).toFixed(6)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Box>
        </Box>

        {/* Center - Chart */}
        <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
          <Box sx={{ p: 1, bgcolor: '#161a1e', borderBottom: '1px solid #2b2f36', display: 'flex', gap: 1 }}>
            <ToggleButtonGroup value={chartInterval} exclusive onChange={(_, v) => v && setChartInterval(v)} size="small">
              <ToggleButton value="1m" sx={{ color: '#b7bdc6', fontSize: 11, '&.Mui-selected': { color: '#fff', bgcolor: '#1e2329' } }}>1m</ToggleButton>
              <ToggleButton value="5m" sx={{ color: '#b7bdc6', fontSize: 11, '&.Mui-selected': { color: '#fff', bgcolor: '#1e2329' } }}>5m</ToggleButton>
              <ToggleButton value="15m" sx={{ color: '#b7bdc6', fontSize: 11, '&.Mui-selected': { color: '#fff', bgcolor: '#1e2329' } }}>15m</ToggleButton>
              <ToggleButton value="1h" sx={{ color: '#b7bdc6', fontSize: 11, '&.Mui-selected': { color: '#fff', bgcolor: '#1e2329' } }}>1h</ToggleButton>
              <ToggleButton value="4h" sx={{ color: '#b7bdc6', fontSize: 11, '&.Mui-selected': { color: '#fff', bgcolor: '#1e2329' } }}>4h</ToggleButton>
              <ToggleButton value="1d" sx={{ color: '#b7bdc6', fontSize: 11, '&.Mui-selected': { color: '#fff', bgcolor: '#1e2329' } }}>1D</ToggleButton>
            </ToggleButtonGroup>
          </Box>
          <Box sx={{ flex: 1 }}>
            <TradingChart data={chartData} height={400} />
          </Box>
        </Box>

        {/* Right - Pairs List */}
        <Box sx={{ width: 300, borderLeft: '1px solid #2b2f36', bgcolor: '#161a1e', display: 'flex', flexDirection: 'column' }}>
          <Box sx={{ p: 1.5, borderBottom: '1px solid #2b2f36' }}>
            <Typography variant="subtitle2" sx={{ color: '#d1d4dc' }}>Markets</Typography>
          </Box>
          <List sx={{ flex: 1, overflow: 'auto', p: 0 }}>
            {tradingPairs.map((p) => {
              const pairTicker = tickers[p.symbol];
              return (
                <ListItem key={p.symbol} disablePadding>
                  <ListItemButton
                    selected={selectedPair === p.symbol}
                    onClick={() => setSelectedPair(p.symbol)}
                    sx={{
                      py: 1,
                      borderBottom: '1px solid #2b2f36',
                      '&.Mui-selected': { bgcolor: '#1e2329' },
                      '&:hover': { bgcolor: '#1e2329' }
                    }}
                  >
                    <ListItemText
                      primary={
                        <Typography sx={{ color: '#d1d4dc', fontSize: 13, fontWeight: 500 }}>
                          {p.symbol.replace('_', '/')}
                        </Typography>
                      }
                      secondary={
                        pairTicker && (
                          <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 0.5 }}>
                            <Typography sx={{ color: '#d1d4dc', fontSize: 12 }}>
                              ${parseFloat(pairTicker.last_price).toFixed(2)}
                            </Typography>
                            <Typography
                              sx={{
                                color: parseFloat(pairTicker.price_change_24h) >= 0 ? '#26a69a' : '#ef5350',
                                fontSize: 11,
                                fontWeight: 500
                              }}
                            >
                              {parseFloat(pairTicker.price_change_24h).toFixed(2)}%
                            </Typography>
                          </Box>
                        )
                      }
                    />
                  </ListItemButton>
                </ListItem>
              );
            })}
          </List>
        </Box>
      </Box>

      {/* Bottom - Order Forms & Open Orders */}
      <Box sx={{ height: 340, borderTop: '1px solid #2b2f36', bgcolor: '#161a1e', display: 'flex', flexDirection: 'column' }}>
        {/* Order Forms */}
        <Box sx={{ p: 2.5, borderBottom: '1px solid #2b2f36', background: 'linear-gradient(180deg, #161a1e 0%, #13171b 100%)' }}>
          <Grid container spacing={3}>
            {/* BUY SIDE */}
            <Grid item xs={6}>
              <Box
                sx={{
                  p: 2,
                  borderRadius: 1.5,
                  bgcolor: 'rgba(38, 166, 154, 0.03)',
                  border: '1px solid rgba(38, 166, 154, 0.15)',
                  transition: 'all 0.2s',
                  '&:hover': {
                    border: '1px solid rgba(38, 166, 154, 0.25)',
                    bgcolor: 'rgba(38, 166, 154, 0.05)',
                  }
                }}
              >
                <Box sx={{ display: 'flex', gap: 1, mb: 2, alignItems: 'center' }}>
                  <Typography variant="subtitle2" sx={{ color: '#26a69a', fontWeight: 700, flex: 1, fontSize: 14 }}>
                    Buy {baseCurrency}
                  </Typography>
                  <ToggleButtonGroup
                    value={orderType}
                    exclusive
                    onChange={(_, v) => v && setOrderType(v)}
                    size="small"
                    sx={{
                      '& .MuiToggleButton-root': {
                        border: '1px solid rgba(38, 166, 154, 0.2)',
                        '&.Mui-selected': {
                          bgcolor: 'rgba(38, 166, 154, 0.15)',
                          border: '1px solid rgba(38, 166, 154, 0.4)',
                        }
                      }
                    }}
                  >
                    <ToggleButton value="limit" sx={{ color: '#b7bdc6', fontSize: 10, px: 1.5, py: 0.3, '&.Mui-selected': { color: '#26a69a' } }}>
                      Limit
                    </ToggleButton>
                    <ToggleButton value="market" sx={{ color: '#b7bdc6', fontSize: 10, px: 1.5, py: 0.3, '&.Mui-selected': { color: '#26a69a' } }}>
                      Market
                    </ToggleButton>
                  </ToggleButtonGroup>
                </Box>
                <Box component="form" onSubmit={buyForm.handleSubmit(onBuySubmit)}>
                  <Grid container spacing={1.5}>
                    {orderType === 'limit' && (
                      <Grid item xs={6}>
                        <TextField
                          fullWidth
                          size="small"
                          label="Price"
                          type="text"
                          placeholder="0.00"
                          {...buyForm.register('price')}
                          inputProps={{ inputMode: 'decimal', pattern: '[0-9]*[.,]?[0-9]*' }}
                          sx={{
                            '& .MuiOutlinedInput-root': {
                              bgcolor: '#0e1117',
                              borderRadius: 1,
                              border: '1px solid rgba(38, 166, 154, 0.15)',
                              '&:hover': {
                                border: '1px solid rgba(38, 166, 154, 0.3)',
                              },
                              '&.Mui-focused': {
                                border: '1px solid rgba(38, 166, 154, 0.5)',
                              },
                              '& input': { color: '#d1d4dc', py: 1, fontSize: 13, fontWeight: 500 }
                            },
                            '& label': { color: '#b7bdc6', fontSize: 12 },
                            '& fieldset': { border: 'none' }
                          }}
                        />
                      </Grid>
                    )}
                    <Grid item xs={orderType === 'limit' ? 6 : 12}>
                      <TextField
                        fullWidth
                        size="small"
                        label="Amount"
                        type="text"
                        placeholder="0.00"
                        {...buyForm.register('amount', { required: true })}
                        inputProps={{ inputMode: 'decimal', pattern: '[0-9]*[.,]?[0-9]*' }}
                        sx={{
                          '& .MuiOutlinedInput-root': {
                            bgcolor: '#0e1117',
                            borderRadius: 1,
                            border: '1px solid rgba(38, 166, 154, 0.15)',
                            '&:hover': {
                              border: '1px solid rgba(38, 166, 154, 0.3)',
                            },
                            '&.Mui-focused': {
                              border: '1px solid rgba(38, 166, 154, 0.5)',
                            },
                            '& input': { color: '#d1d4dc', py: 1, fontSize: 13, fontWeight: 500 }
                          },
                          '& label': { color: '#b7bdc6', fontSize: 12 },
                          '& fieldset': { border: 'none' }
                        }}
                      />
                    </Grid>
                  </Grid>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mt: 1.5, mb: 1.5 }}>
                    <Typography variant="caption" sx={{ color: '#848e9c', fontSize: 11 }}>
                      Available
                    </Typography>
                    <Typography variant="caption" sx={{ color: '#d1d4dc', fontSize: 11, fontWeight: 600 }}>
                      {parseFloat(quoteBalance?.available || '0').toFixed(2)} {quoteCurrency}
                    </Typography>
                  </Box>
                  <Button
                    type="submit"
                    fullWidth
                    variant="contained"
                    sx={{
                      bgcolor: '#26a69a',
                      color: '#fff',
                      py: 1.2,
                      fontWeight: 700,
                      fontSize: 14,
                      borderRadius: 1.5,
                      textTransform: 'none',
                      boxShadow: '0 4px 12px rgba(38, 166, 154, 0.25)',
                      '&:hover': {
                        bgcolor: '#22948a',
                        boxShadow: '0 6px 16px rgba(38, 166, 154, 0.35)',
                        transform: 'translateY(-1px)'
                      },
                      transition: 'all 0.2s'
                    }}
                  >
                    Buy {baseCurrency}
                  </Button>
                </Box>
              </Box>
            </Grid>

            {/* SELL SIDE */}
            <Grid item xs={6}>
              <Box
                sx={{
                  p: 2,
                  borderRadius: 1.5,
                  bgcolor: 'rgba(239, 83, 80, 0.03)',
                  border: '1px solid rgba(239, 83, 80, 0.15)',
                  transition: 'all 0.2s',
                  '&:hover': {
                    border: '1px solid rgba(239, 83, 80, 0.25)',
                    bgcolor: 'rgba(239, 83, 80, 0.05)',
                  }
                }}
              >
                <Box sx={{ display: 'flex', gap: 1, mb: 2, alignItems: 'center' }}>
                  <Typography variant="subtitle2" sx={{ color: '#ef5350', fontWeight: 700, flex: 1, fontSize: 14 }}>
                    Sell {baseCurrency}
                  </Typography>
                  <ToggleButtonGroup
                    value={orderType}
                    exclusive
                    onChange={(_, v) => v && setOrderType(v)}
                    size="small"
                    sx={{
                      '& .MuiToggleButton-root': {
                        border: '1px solid rgba(239, 83, 80, 0.2)',
                        '&.Mui-selected': {
                          bgcolor: 'rgba(239, 83, 80, 0.15)',
                          border: '1px solid rgba(239, 83, 80, 0.4)',
                        }
                      }
                    }}
                  >
                    <ToggleButton value="limit" sx={{ color: '#b7bdc6', fontSize: 10, px: 1.5, py: 0.3, '&.Mui-selected': { color: '#ef5350' } }}>
                      Limit
                    </ToggleButton>
                    <ToggleButton value="market" sx={{ color: '#b7bdc6', fontSize: 10, px: 1.5, py: 0.3, '&.Mui-selected': { color: '#ef5350' } }}>
                      Market
                    </ToggleButton>
                  </ToggleButtonGroup>
                </Box>
                <Box component="form" onSubmit={sellForm.handleSubmit(onSellSubmit)}>
                  <Grid container spacing={1.5}>
                    {orderType === 'limit' && (
                      <Grid item xs={6}>
                        <TextField
                          fullWidth
                          size="small"
                          label="Price"
                          type="text"
                          placeholder="0.00"
                          {...sellForm.register('price')}
                          inputProps={{ inputMode: 'decimal', pattern: '[0-9]*[.,]?[0-9]*' }}
                          sx={{
                            '& .MuiOutlinedInput-root': {
                              bgcolor: '#0e1117',
                              borderRadius: 1,
                              border: '1px solid rgba(239, 83, 80, 0.15)',
                              '&:hover': {
                                border: '1px solid rgba(239, 83, 80, 0.3)',
                              },
                              '&.Mui-focused': {
                                border: '1px solid rgba(239, 83, 80, 0.5)',
                              },
                              '& input': { color: '#d1d4dc', py: 1, fontSize: 13, fontWeight: 500 }
                            },
                            '& label': { color: '#b7bdc6', fontSize: 12 },
                            '& fieldset': { border: 'none' }
                          }}
                        />
                      </Grid>
                    )}
                    <Grid item xs={orderType === 'limit' ? 6 : 12}>
                      <TextField
                        fullWidth
                        size="small"
                        label="Amount"
                        type="text"
                        placeholder="0.00"
                        {...sellForm.register('amount', { required: true })}
                        inputProps={{ inputMode: 'decimal', pattern: '[0-9]*[.,]?[0-9]*' }}
                        sx={{
                          '& .MuiOutlinedInput-root': {
                            bgcolor: '#0e1117',
                            borderRadius: 1,
                            border: '1px solid rgba(239, 83, 80, 0.15)',
                            '&:hover': {
                              border: '1px solid rgba(239, 83, 80, 0.3)',
                            },
                            '&.Mui-focused': {
                              border: '1px solid rgba(239, 83, 80, 0.5)',
                            },
                            '& input': { color: '#d1d4dc', py: 1, fontSize: 13, fontWeight: 500 }
                          },
                          '& label': { color: '#b7bdc6', fontSize: 12 },
                          '& fieldset': { border: 'none' }
                        }}
                      />
                    </Grid>
                  </Grid>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mt: 1.5, mb: 1.5 }}>
                    <Typography variant="caption" sx={{ color: '#848e9c', fontSize: 11 }}>
                      Available
                    </Typography>
                    <Typography variant="caption" sx={{ color: '#d1d4dc', fontSize: 11, fontWeight: 600 }}>
                      {parseFloat(baseBalance?.available || '0').toFixed(6)} {baseCurrency}
                    </Typography>
                  </Box>
                  <Button
                    type="submit"
                    fullWidth
                    variant="contained"
                    sx={{
                      bgcolor: '#ef5350',
                      color: '#fff',
                      py: 1.2,
                      fontWeight: 700,
                      fontSize: 14,
                      borderRadius: 1.5,
                      textTransform: 'none',
                      boxShadow: '0 4px 12px rgba(239, 83, 80, 0.25)',
                      '&:hover': {
                        bgcolor: '#e53935',
                        boxShadow: '0 6px 16px rgba(239, 83, 80, 0.35)',
                        transform: 'translateY(-1px)'
                      },
                      transition: 'all 0.2s'
                    }}
                  >
                    Sell {baseCurrency}
                  </Button>
                </Box>
              </Box>
            </Grid>
          </Grid>
        </Box>

        {/* Tabs */}
        <Tabs
          value={ordersTab}
          onChange={(_, v) => setOrdersTab(v)}
          sx={{
            borderBottom: '1px solid #2b2f36',
            minHeight: 36,
            '& .MuiTab-root': { color: '#b7bdc6', minHeight: 36, py: 1 },
            '& .Mui-selected': { color: '#fff' }
          }}
        >
          <Tab label={`Open Orders (${openOrders.length})`} />
          <Tab label="Recent Trades" />
        </Tabs>
        {ordersTab === 0 && (
          <Box sx={{ overflow: 'auto', flex: 1 }}>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell sx={{ color: '#b7bdc6', fontSize: 11, py: 1 }}>Date</TableCell>
                  <TableCell sx={{ color: '#b7bdc6', fontSize: 11, py: 1 }}>Pair</TableCell>
                  <TableCell sx={{ color: '#b7bdc6', fontSize: 11, py: 1 }}>Type</TableCell>
                  <TableCell sx={{ color: '#b7bdc6', fontSize: 11, py: 1 }}>Side</TableCell>
                  <TableCell sx={{ color: '#b7bdc6', fontSize: 11, py: 1 }}>Price</TableCell>
                  <TableCell sx={{ color: '#b7bdc6', fontSize: 11, py: 1 }}>Amount</TableCell>
                  <TableCell sx={{ color: '#b7bdc6', fontSize: 11, py: 1 }}>Filled</TableCell>
                  <TableCell sx={{ color: '#b7bdc6', fontSize: 11, py: 1 }}>Action</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {openOrders.map((order) => (
                  <TableRow key={order.id} sx={{ '&:hover': { bgcolor: '#1e2329' } }}>
                    <TableCell sx={{ color: '#d1d4dc', fontSize: 12, py: 0.8 }}>{new Date(order.created_at).toLocaleTimeString()}</TableCell>
                    <TableCell sx={{ color: '#d1d4dc', fontSize: 12, py: 0.8 }}>{order.trading_pair?.replace('_', '/')}</TableCell>
                    <TableCell sx={{ color: '#d1d4dc', fontSize: 12, py: 0.8 }}>{order.order_type}</TableCell>
                    <TableCell sx={{ color: order.side === 'buy' ? '#26a69a' : '#ef5350', fontSize: 12, py: 0.8 }}>{order.side.toUpperCase()}</TableCell>
                    <TableCell sx={{ color: '#d1d4dc', fontSize: 12, py: 0.8 }}>{order.price ? parseFloat(order.price).toFixed(2) : 'Market'}</TableCell>
                    <TableCell sx={{ color: '#d1d4dc', fontSize: 12, py: 0.8 }}>{parseFloat(order.amount).toFixed(6)}</TableCell>
                    <TableCell sx={{ color: '#d1d4dc', fontSize: 12, py: 0.8 }}>{parseFloat(order.filled_amount || '0').toFixed(6)}</TableCell>
                    <TableCell sx={{ py: 0.8 }}>
                      <Button size="small" onClick={() => handleCancel(order.id)} sx={{ color: '#ef5350', minWidth: 'auto', fontSize: 11 }}>
                        Cancel
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
                {openOrders.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={8} sx={{ textAlign: 'center', color: '#b7bdc6', py: 3 }}>You have no open orders.</TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </Box>
        )}
        {ordersTab === 1 && (
          <Box sx={{ overflow: 'auto', flex: 1 }}>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell sx={{ color: '#b7bdc6', fontSize: 11, py: 1 }}>Price</TableCell>
                  <TableCell sx={{ color: '#b7bdc6', fontSize: 11, py: 1 }}>Amount</TableCell>
                  <TableCell sx={{ color: '#b7bdc6', fontSize: 11, py: 1 }}>Time</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {recentTrades.slice(0, 15).map((trade, i) => (
                  <TableRow key={i} sx={{ '&:hover': { bgcolor: '#1e2329' } }}>
                    <TableCell sx={{ color: '#d1d4dc', fontSize: 12, py: 0.8 }}>{parseFloat(trade.price).toFixed(2)}</TableCell>
                    <TableCell sx={{ color: '#d1d4dc', fontSize: 12, py: 0.8 }}>{parseFloat(trade.amount).toFixed(6)}</TableCell>
                    <TableCell sx={{ color: '#b7bdc6', fontSize: 12, py: 0.8 }}>{new Date(trade.timestamp).toLocaleTimeString()}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Box>
        )}
      </Box>
    </Box>
  );
};

export default TradeBinance;
