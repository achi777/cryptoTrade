import React, { useEffect } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
} from '@mui/material';
import { TrendingUp, TrendingDown } from '@mui/icons-material';

import { RootState, AppDispatch } from '../store';
import { fetchBalances } from '../store/slices/walletSlice';
import { fetchTickers } from '../store/slices/marketSlice';

const Dashboard: React.FC = () => {
  const dispatch = useDispatch<AppDispatch>();
  const { user } = useSelector((state: RootState) => state.auth);
  const { balances } = useSelector((state: RootState) => state.wallet);
  const { tickers } = useSelector((state: RootState) => state.market);

  useEffect(() => {
    dispatch(fetchBalances());
    dispatch(fetchTickers());
  }, [dispatch]);

  const totalBalance = balances.reduce((sum, b) => {
    const ticker = Object.values(tickers).find((t) => t.symbol.startsWith(b.currency));
    const price = ticker ? parseFloat(ticker.last_price) : b.currency === 'USDT' ? 1 : 0;
    return sum + parseFloat(b.total) * price;
  }, 0);

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Welcome back, {user?.profile?.first_name || user?.email?.split('@')[0]}
      </Typography>

      <Grid container spacing={3}>
        {/* Total Balance Card */}
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom>
                Total Balance (USDT)
              </Typography>
              <Typography variant="h4">${totalBalance.toFixed(2)}</Typography>
            </CardContent>
          </Card>
        </Grid>

        {/* KYC Level Card */}
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom>
                KYC Level
              </Typography>
              <Typography variant="h4">Level {user?.kyc_level || 0}</Typography>
            </CardContent>
          </Card>
        </Grid>

        {/* 2FA Status Card */}
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom>
                2FA Status
              </Typography>
              <Typography variant="h4" color={user?.two_factor_enabled ? 'success.main' : 'warning.main'}>
                {user?.two_factor_enabled ? 'Enabled' : 'Disabled'}
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        {/* Balances Table */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Your Balances
              </Typography>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Currency</TableCell>
                    <TableCell align="right">Available</TableCell>
                    <TableCell align="right">Locked</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {balances.filter((b) => parseFloat(b.total) > 0).map((balance) => (
                    <TableRow key={balance.currency}>
                      <TableCell>{balance.currency}</TableCell>
                      <TableCell align="right">{parseFloat(balance.available).toFixed(8)}</TableCell>
                      <TableCell align="right">{parseFloat(balance.locked).toFixed(8)}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </Grid>

        {/* Market Overview */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Market Overview
              </Typography>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Pair</TableCell>
                    <TableCell align="right">Price</TableCell>
                    <TableCell align="right">24h Change</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {Object.values(tickers).slice(0, 5).map((ticker) => (
                    <TableRow key={ticker.symbol}>
                      <TableCell>{ticker.symbol.replace('_', '/')}</TableCell>
                      <TableCell align="right">{parseFloat(ticker.last_price).toFixed(2)}</TableCell>
                      <TableCell
                        align="right"
                        sx={{
                          color: parseFloat(ticker.price_change_24h) >= 0 ? 'success.main' : 'error.main',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'flex-end',
                        }}
                      >
                        {parseFloat(ticker.price_change_24h) >= 0 ? (
                          <TrendingUp fontSize="small" />
                        ) : (
                          <TrendingDown fontSize="small" />
                        )}
                        {parseFloat(ticker.price_change_24h).toFixed(2)}%
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

export default Dashboard;
