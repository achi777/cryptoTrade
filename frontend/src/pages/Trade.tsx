import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { useDispatch, useSelector } from 'react-redux';
import {
  Box,
  Grid,
  Card,
  CardContent,
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
  Select,
  MenuItem,
  FormControl,
  InputLabel,
} from '@mui/material';
import { useForm } from 'react-hook-form';
import toast from 'react-hot-toast';

import { RootState, AppDispatch } from '../store';
import { fetchTradingPairs, fetchOrderBook, fetchRecentTrades, setCurrentPair } from '../store/slices/marketSlice';
import { createOrder, fetchOpenOrders, cancelOrder } from '../store/slices/tradingSlice';
import { fetchBalances } from '../store/slices/walletSlice';
import wsService from '../services/websocket';

interface OrderForm {
  amount: string;
  price: string;
}

const Trade: React.FC = () => {
  const { pair } = useParams<{ pair?: string }>();
  const dispatch = useDispatch<AppDispatch>();

  const { tradingPairs, currentPair, orderBook, recentTrades, tickers } = useSelector(
    (state: RootState) => state.market
  );
  const { openOrders } = useSelector((state: RootState) => state.trading);
  const { balances } = useSelector((state: RootState) => state.wallet);

  const [orderType, setOrderType] = useState<'limit' | 'market'>('limit');
  const [orderSide, setOrderSide] = useState<'buy' | 'sell'>('buy');
  const [selectedPair, setSelectedPair] = useState(pair || 'BTC_USDT');

  const { register, handleSubmit, setValue, watch } = useForm<OrderForm>();

  useEffect(() => {
    dispatch(fetchTradingPairs());
    dispatch(fetchBalances());
    dispatch(fetchOpenOrders());
  }, [dispatch]);

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

  const onSubmit = async (data: OrderForm) => {
    try {
      // Ensure we have a price for limit orders
      if (orderType === 'limit' && !data.price) {
        toast.error('Price is required for limit orders');
        return;
      }

      const orderData = {
        pair: selectedPair,
        type: orderType,
        side: orderSide,
        amount: data.amount,
        ...(orderType === 'limit' && { price: data.price }),
      };

      console.log('Creating order:', orderData); // Debug log
      await dispatch(createOrder(orderData)).unwrap();
      toast.success('Order placed successfully');
      dispatch(fetchBalances());
    } catch (error: any) {
      toast.error(error || 'Failed to place order');
    }
  };

  const handleCancel = async (orderId: number) => {
    try {
      await dispatch(cancelOrder(orderId)).unwrap();
      toast.success('Order cancelled');
      dispatch(fetchBalances());
    } catch (error: any) {
      toast.error(error || 'Failed to cancel order');
    }
  };

  return (
    <Box>
      <Grid container spacing={2}>
        {/* Pair Selector */}
        <Grid item xs={12}>
          <FormControl size="small" sx={{ minWidth: 200 }}>
            <InputLabel>Trading Pair</InputLabel>
            <Select
              value={selectedPair}
              label="Trading Pair"
              onChange={(e) => setSelectedPair(e.target.value)}
            >
              {tradingPairs.map((p) => (
                <MenuItem key={p.symbol} value={p.symbol}>
                  {p.symbol.replace('_', '/')}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          {ticker && (
            <Typography component="span" sx={{ ml: 2 }}>
              Price: {parseFloat(ticker.last_price).toFixed(2)} | 24h: {parseFloat(ticker.price_change_24h).toFixed(2)}%
            </Typography>
          )}
        </Grid>

        {/* Order Book */}
        <Grid item xs={12} md={3}>
          <Card sx={{ height: 400 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>Order Book</Typography>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Price</TableCell>
                    <TableCell align="right">Amount</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {orderBook.asks.slice(0, 8).reverse().map((ask, i) => (
                    <TableRow key={`ask-${i}`}>
                      <TableCell sx={{ color: 'error.main' }}>{parseFloat(ask.price).toFixed(2)}</TableCell>
                      <TableCell align="right">{parseFloat(ask.amount).toFixed(4)}</TableCell>
                    </TableRow>
                  ))}
                  <TableRow>
                    <TableCell colSpan={2} sx={{ textAlign: 'center', bgcolor: 'background.paper' }}>
                      <Typography variant="h6">{ticker ? parseFloat(ticker.last_price).toFixed(2) : '-'}</Typography>
                    </TableCell>
                  </TableRow>
                  {orderBook.bids.slice(0, 8).map((bid, i) => (
                    <TableRow key={`bid-${i}`}>
                      <TableCell sx={{ color: 'success.main' }}>{parseFloat(bid.price).toFixed(2)}</TableCell>
                      <TableCell align="right">{parseFloat(bid.amount).toFixed(4)}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </Grid>

        {/* Order Form */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <ToggleButtonGroup
                value={orderSide}
                exclusive
                onChange={(_, v) => v && setOrderSide(v)}
                fullWidth
                sx={{ mb: 2 }}
              >
                <ToggleButton value="buy" sx={{ color: 'success.main' }}>Buy</ToggleButton>
                <ToggleButton value="sell" sx={{ color: 'error.main' }}>Sell</ToggleButton>
              </ToggleButtonGroup>

              <ToggleButtonGroup
                value={orderType}
                exclusive
                onChange={(_, v) => v && setOrderType(v)}
                fullWidth
                size="small"
                sx={{ mb: 2 }}
              >
                <ToggleButton value="limit">Limit</ToggleButton>
                <ToggleButton value="market">Market</ToggleButton>
              </ToggleButtonGroup>

              <form onSubmit={handleSubmit(onSubmit)}>
                {orderType === 'limit' && (
                  <TextField
                    fullWidth
                    label={`Price (${quoteCurrency})`}
                    type="number"
                    margin="normal"
                    {...register('price', { required: orderType === 'limit' })}
                  />
                )}
                <TextField
                  fullWidth
                  label={`Amount (${baseCurrency})`}
                  type="number"
                  margin="normal"
                  {...register('amount', { required: true })}
                />
                <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                  Available: {orderSide === 'buy'
                    ? `${parseFloat(quoteBalance?.available || '0').toFixed(4)} ${quoteCurrency}`
                    : `${parseFloat(baseBalance?.available || '0').toFixed(8)} ${baseCurrency}`}
                </Typography>
                <Button
                  type="submit"
                  fullWidth
                  variant="contained"
                  sx={{ mt: 2, bgcolor: orderSide === 'buy' ? 'success.main' : 'error.main' }}
                >
                  {orderSide === 'buy' ? 'Buy' : 'Sell'} {baseCurrency}
                </Button>
              </form>
            </CardContent>
          </Card>
        </Grid>

        {/* Recent Trades */}
        <Grid item xs={12} md={3}>
          <Card sx={{ height: 400 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>Recent Trades</Typography>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Price</TableCell>
                    <TableCell align="right">Amount</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {recentTrades.slice(0, 15).map((trade) => (
                    <TableRow key={trade.id}>
                      <TableCell>{parseFloat(trade.price).toFixed(2)}</TableCell>
                      <TableCell align="right">{parseFloat(trade.amount).toFixed(4)}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </Grid>

        {/* Open Orders */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>Open Orders</Typography>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Pair</TableCell>
                    <TableCell>Type</TableCell>
                    <TableCell>Side</TableCell>
                    <TableCell align="right">Price</TableCell>
                    <TableCell align="right">Amount</TableCell>
                    <TableCell align="right">Filled</TableCell>
                    <TableCell>Action</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {openOrders.map((order) => (
                    <TableRow key={order.id}>
                      <TableCell>{order.trading_pair?.replace('_', '/')}</TableCell>
                      <TableCell>{order.order_type}</TableCell>
                      <TableCell sx={{ color: order.side === 'buy' ? 'success.main' : 'error.main' }}>
                        {order.side.toUpperCase()}
                      </TableCell>
                      <TableCell align="right">{order.price || 'Market'}</TableCell>
                      <TableCell align="right">{parseFloat(order.amount).toFixed(8)}</TableCell>
                      <TableCell align="right">{parseFloat(order.filled_amount).toFixed(8)}</TableCell>
                      <TableCell>
                        <Button size="small" color="error" onClick={() => handleCancel(order.id)}>
                          Cancel
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default Trade;
