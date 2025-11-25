import React, { useEffect, useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { Box, Card, CardContent, Typography, Table, TableBody, TableCell, TableHead, TableRow, Chip, Tabs, Tab, Button } from '@mui/material';
import { RootState, AppDispatch } from '../store';
import { fetchOrderHistory, fetchOpenOrders, cancelOrder } from '../store/slices/tradingSlice';
import toast from 'react-hot-toast';

const Orders: React.FC = () => {
  const dispatch = useDispatch<AppDispatch>();
  const { orderHistory, openOrders } = useSelector((state: RootState) => state.trading);
  const [tab, setTab] = useState(0);

  useEffect(() => {
    dispatch(fetchOrderHistory({}));
    dispatch(fetchOpenOrders());
  }, [dispatch]);

  const handleCancel = async (orderId: number) => {
    try {
      await dispatch(cancelOrder(orderId)).unwrap();
      toast.success('Order cancelled');
      dispatch(fetchOpenOrders());
    } catch (error) {
      toast.error('Failed to cancel order');
    }
  };

  const allOrders = [...openOrders, ...orderHistory];

  return (
    <Box>
      <Typography variant="h4" gutterBottom>Orders</Typography>
      <Card>
        <Tabs value={tab} onChange={(e, v) => setTab(v)} sx={{ borderBottom: 1, borderColor: 'divider' }}>
          <Tab label="All Orders" />
          <Tab label="Open Orders" />
          <Tab label="Order History" />
        </Tabs>
        <CardContent>
          <Table>
            <TableHead><TableRow>
              <TableCell>Pair</TableCell><TableCell>Type</TableCell><TableCell>Side</TableCell>
              <TableCell align="right">Price</TableCell><TableCell align="right">Amount</TableCell>
              <TableCell align="right">Filled</TableCell><TableCell>Status</TableCell>
              <TableCell>Date</TableCell><TableCell>Actions</TableCell>
            </TableRow></TableHead>
            <TableBody>
              {(tab === 0 ? allOrders : tab === 1 ? openOrders : orderHistory).map((o) => (
                <TableRow key={o.id}>
                  <TableCell>{o.trading_pair}</TableCell><TableCell>{o.order_type}</TableCell>
                  <TableCell sx={{ color: o.side === 'buy' ? 'success.main' : 'error.main' }}>{o.side}</TableCell>
                  <TableCell align="right">{o.price || 'Market'}</TableCell>
                  <TableCell align="right">{parseFloat(o.amount).toFixed(8)}</TableCell>
                  <TableCell align="right">{parseFloat(o.filled_amount || '0').toFixed(8)}</TableCell>
                  <TableCell><Chip label={o.status} size="small" color={o.status === 'open' ? 'primary' : o.status === 'filled' ? 'success' : 'default'} /></TableCell>
                  <TableCell>{new Date(o.created_at).toLocaleString()}</TableCell>
                  <TableCell>
                    {o.status === 'open' && (
                      <Button size="small" color="error" onClick={() => handleCancel(o.id)}>Cancel</Button>
                    )}
                  </TableCell>
                </TableRow>
              ))}
              {(tab === 0 ? allOrders : tab === 1 ? openOrders : orderHistory).length === 0 && (
                <TableRow>
                  <TableCell colSpan={9} align="center">No orders found</TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </Box>
  );
};
export default Orders;
