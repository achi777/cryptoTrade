import React, { useEffect, useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { Box, Card, CardContent, Typography, Table, TableBody, TableCell, TableHead, TableRow, Button, Dialog, DialogTitle, DialogContent, DialogActions, TextField } from '@mui/material';
import { QRCodeSVG } from 'qrcode.react';
import { RootState, AppDispatch } from '../store';
import { fetchBalances } from '../store/slices/walletSlice';
import api from '../services/api';
import toast from 'react-hot-toast';

const Wallets: React.FC = () => {
  const dispatch = useDispatch<AppDispatch>();
  const { balances } = useSelector((state: RootState) => state.wallet);
  const [depositDialog, setDepositDialog] = useState<{ open: boolean; currency: string; address: string }>({ open: false, currency: '', address: '' });
  const [withdrawDialog, setWithdrawDialog] = useState<{ open: boolean; currency: string }>({ open: false, currency: '' });
  const [withdrawForm, setWithdrawForm] = useState({ address: '', amount: '' });
  const [withdrawLoading, setWithdrawLoading] = useState(false);

  useEffect(() => { dispatch(fetchBalances()); }, [dispatch]);

  const handleDeposit = async (currency: string) => {
    try {
      const response = await api.get(`/wallets/${currency}/address`);
      setDepositDialog({ open: true, currency, address: response.data.address });
    } catch (error) { toast.error('Failed to get deposit address'); }
  };

  const handleWithdraw = async () => {
    if (!withdrawForm.address || !withdrawForm.amount) {
      toast.error('Please fill all fields');
      return;
    }
    setWithdrawLoading(true);
    try {
      await api.post('/wallets/withdraw', {
        currency: withdrawDialog.currency,
        address: withdrawForm.address,
        amount: withdrawForm.amount
      });
      toast.success('Withdrawal request submitted!');
      setWithdrawDialog({ open: false, currency: '' });
      setWithdrawForm({ address: '', amount: '' });
      dispatch(fetchBalances());
    } catch (error: any) {
      toast.error(error.response?.data?.error || 'Withdrawal failed');
    } finally {
      setWithdrawLoading(false);
    }
  };

  const getAvailableBalance = (currency: string) => {
    const balance = balances.find(b => b.currency === currency);
    return balance ? parseFloat(balance.available) : 0;
  };

  return (
    <Box>
      <Typography variant="h4" gutterBottom>Wallets</Typography>
      <Card>
        <CardContent>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Currency</TableCell>
                <TableCell align="right">Available</TableCell>
                <TableCell align="right">Locked</TableCell>
                <TableCell align="right">Total</TableCell>
                <TableCell>Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {balances.map((b) => (
                <TableRow key={b.currency}>
                  <TableCell>{b.currency}</TableCell>
                  <TableCell align="right">{parseFloat(b.available).toFixed(8)}</TableCell>
                  <TableCell align="right">{parseFloat(b.locked).toFixed(8)}</TableCell>
                  <TableCell align="right">{parseFloat(b.total).toFixed(8)}</TableCell>
                  <TableCell>
                    <Button size="small" onClick={() => handleDeposit(b.currency)}>Deposit</Button>
                    <Button size="small" onClick={() => setWithdrawDialog({ open: true, currency: b.currency })}>Withdraw</Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Deposit Dialog */}
      <Dialog open={depositDialog.open} onClose={() => setDepositDialog({ ...depositDialog, open: false })}>
        <DialogTitle>Deposit {depositDialog.currency}</DialogTitle>
        <DialogContent sx={{ textAlign: 'center', p: 3 }}>
          {depositDialog.address && <QRCodeSVG value={depositDialog.address} size={200} />}
          <Typography variant="body2" sx={{ mt: 2, wordBreak: 'break-all' }}>{depositDialog.address}</Typography>
        </DialogContent>
      </Dialog>

      {/* Withdraw Dialog */}
      <Dialog open={withdrawDialog.open} onClose={() => { setWithdrawDialog({ open: false, currency: '' }); setWithdrawForm({ address: '', amount: '' }); }} maxWidth="sm" fullWidth>
        <DialogTitle>Withdraw {withdrawDialog.currency}</DialogTitle>
        <DialogContent>
          <Typography variant="body2" sx={{ mb: 2 }}>
            Available: {getAvailableBalance(withdrawDialog.currency).toFixed(8)} {withdrawDialog.currency}
          </Typography>
          <TextField
            fullWidth
            label="Recipient Address"
            value={withdrawForm.address}
            onChange={(e) => setWithdrawForm({ ...withdrawForm, address: e.target.value })}
            margin="normal"
            placeholder="Enter wallet address"
          />
          <TextField
            fullWidth
            label="Amount"
            type="number"
            value={withdrawForm.amount}
            onChange={(e) => setWithdrawForm({ ...withdrawForm, amount: e.target.value })}
            margin="normal"
            placeholder="0.00"
            inputProps={{ step: '0.00000001', min: '0' }}
          />
          <Button
            size="small"
            onClick={() => setWithdrawForm({ ...withdrawForm, amount: getAvailableBalance(withdrawDialog.currency).toString() })}
            sx={{ mt: 1 }}
          >
            Max
          </Button>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => { setWithdrawDialog({ open: false, currency: '' }); setWithdrawForm({ address: '', amount: '' }); }}>Cancel</Button>
          <Button onClick={handleWithdraw} variant="contained" disabled={withdrawLoading}>
            {withdrawLoading ? 'Processing...' : 'Withdraw'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};
export default Wallets;
