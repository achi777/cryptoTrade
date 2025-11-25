import React, { useEffect, useState } from 'react';
import { Box, Card, CardContent, Typography, Table, TableHead, TableRow, TableCell, TableBody, Button, Chip, Dialog, DialogTitle, DialogContent, DialogActions, TextField, Grid, IconButton, Tooltip } from '@mui/material';
import { Block, LockOpen, AccountBalance, Visibility } from '@mui/icons-material';
import { adminApi } from '../../services/api';
import toast from 'react-hot-toast';

const AdminUsers: React.FC = () => {
  const [users, setUsers] = useState<any[]>([]);
  const [selectedUser, setSelectedUser] = useState<any>(null);
  const [detailsDialog, setDetailsDialog] = useState(false);
  const [balanceDialog, setBalanceDialog] = useState(false);
  const [balanceForm, setBalanceForm] = useState({ currency: '', amount: '', type: 'credit', reason: '' });
  const [userBalances, setUserBalances] = useState<any[]>([]);
  const [userDetails, setUserDetails] = useState<any>(null);

  const loadUsers = () => {
    adminApi.get('/users').then((res) => setUsers(res.data.users || []));
  };

  useEffect(() => { loadUsers(); }, []);

  const handleBlockUser = async (userId: number, isBlocked: boolean) => {
    try {
      await adminApi.post(`/users/${userId}/${isBlocked ? 'unblock' : 'block'}`);
      toast.success(`User ${isBlocked ? 'unblocked' : 'blocked'} successfully`);
      loadUsers();
    } catch (error) {
      toast.error('Failed to update user status');
    }
  };

  const handleViewDetails = async (user: any) => {
    try {
      const [userRes, ordersRes, txRes] = await Promise.all([
        adminApi.get(`/users/${user.id}`),
        adminApi.get(`/users/${user.id}/orders`),
        adminApi.get(`/users/${user.id}/transactions`)
      ]);
      setUserDetails({
        ...userRes.data.user,
        orders: ordersRes.data.orders || [],
        transactions: txRes.data.transactions || []
      });
      setSelectedUser(user);
      setDetailsDialog(true);
    } catch (error) {
      toast.error('Failed to load user details');
    }
  };

  const handleOpenBalanceDialog = async (user: any) => {
    setSelectedUser(user);
    try {
      const res = await adminApi.get(`/users/${user.id}`);
      setUserBalances(res.data.balances || []);
    } catch (error) {
      console.error('Failed to load balances');
    }
    setBalanceDialog(true);
  };

  const handleAdjustBalance = async () => {
    if (!balanceForm.currency || !balanceForm.amount) {
      toast.error('Please fill currency and amount');
      return;
    }
    try {
      await adminApi.post(`/users/${selectedUser.id}/balance/adjust`, {
        currency: balanceForm.currency,
        amount: balanceForm.amount,
        type: balanceForm.type,
        reason: balanceForm.reason
      });
      toast.success('Balance adjusted successfully');
      setBalanceDialog(false);
      setBalanceForm({ currency: '', amount: '', type: 'credit', reason: '' });
    } catch (error: any) {
      toast.error(error.response?.data?.error || 'Failed to adjust balance');
    }
  };

  const handleVerifyEmail = async (userId: number) => {
    try {
      await adminApi.post(`/users/${userId}/verify-email`);
      toast.success('User email verified successfully');
      loadUsers();
    } catch (error) {
      toast.error('Failed to verify email');
    }
  };

  const handleToggleActive = async (userId: number, isActive: boolean) => {
    try {
      await adminApi.post(`/users/${userId}/toggle-active`);
      toast.success(`User ${isActive ? 'deactivated' : 'activated'} successfully`);
      loadUsers();
    } catch (error) {
      toast.error('Failed to toggle user status');
    }
  };

  return (
    <Box>
      <Typography variant="h4" gutterBottom>User Management</Typography>
      <Card>
        <CardContent>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>ID</TableCell>
                <TableCell>Email</TableCell>
                <TableCell>KYC Level</TableCell>
                <TableCell>2FA</TableCell>
                <TableCell>Verified</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Registered</TableCell>
                <TableCell>Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {users.map((u) => (
                <TableRow key={u.id}>
                  <TableCell>{u.id}</TableCell>
                  <TableCell>{u.email}</TableCell>
                  <TableCell>
                    <Chip label={`Level ${u.kyc_level}`} size="small" color={u.kyc_level >= 2 ? 'success' : 'default'} />
                  </TableCell>
                  <TableCell>
                    <Chip label={u.two_factor_enabled ? 'Yes' : 'No'} size="small" color={u.two_factor_enabled ? 'success' : 'default'} />
                  </TableCell>
                  <TableCell>
                    <Chip label={u.is_verified ? 'Yes' : 'No'} size="small" color={u.is_verified ? 'success' : 'warning'} />
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={u.is_blocked ? 'Blocked' : u.is_active ? 'Active' : 'Inactive'}
                      color={u.is_blocked ? 'error' : u.is_active ? 'success' : 'default'}
                      size="small"
                    />
                  </TableCell>
                  <TableCell>{new Date(u.created_at).toLocaleDateString()}</TableCell>
                  <TableCell>
                    <Tooltip title="View Details">
                      <IconButton size="small" onClick={() => handleViewDetails(u)}>
                        <Visibility fontSize="small" />
                      </IconButton>
                    </Tooltip>
                    <Tooltip title="Adjust Balance">
                      <IconButton size="small" onClick={() => handleOpenBalanceDialog(u)}>
                        <AccountBalance fontSize="small" />
                      </IconButton>
                    </Tooltip>
                    {!u.is_verified && (
                      <Tooltip title="Verify Email">
                        <Button size="small" variant="outlined" onClick={() => handleVerifyEmail(u.id)} sx={{ minWidth: 'auto', px: 1 }}>
                          Verify
                        </Button>
                      </Tooltip>
                    )}
                    <Tooltip title={u.is_active ? 'Deactivate' : 'Activate'}>
                      <Button
                        size="small"
                        variant="outlined"
                        color={u.is_active ? 'warning' : 'success'}
                        onClick={() => handleToggleActive(u.id, u.is_active)}
                        sx={{ minWidth: 'auto', px: 1, ml: 0.5 }}
                      >
                        {u.is_active ? 'Deactivate' : 'Activate'}
                      </Button>
                    </Tooltip>
                    <Tooltip title={u.is_blocked ? 'Unblock User' : 'Block User'}>
                      <IconButton size="small" color={u.is_blocked ? 'success' : 'error'} onClick={() => handleBlockUser(u.id, u.is_blocked)}>
                        {u.is_blocked ? <LockOpen fontSize="small" /> : <Block fontSize="small" />}
                      </IconButton>
                    </Tooltip>
                  </TableCell>
                </TableRow>
              ))}
              {users.length === 0 && (
                <TableRow>
                  <TableCell colSpan={8} align="center">No users found</TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* User Details Dialog */}
      <Dialog open={detailsDialog} onClose={() => setDetailsDialog(false)} maxWidth="md" fullWidth>
        <DialogTitle>User Details - {userDetails?.email}</DialogTitle>
        <DialogContent>
          {userDetails && (
            <Grid container spacing={2} sx={{ mt: 1 }}>
              <Grid item xs={6}>
                <Typography variant="subtitle2">User ID:</Typography>
                <Typography>{userDetails.id}</Typography>
              </Grid>
              <Grid item xs={6}>
                <Typography variant="subtitle2">Email:</Typography>
                <Typography>{userDetails.email}</Typography>
              </Grid>
              <Grid item xs={6}>
                <Typography variant="subtitle2">KYC Level:</Typography>
                <Typography>{userDetails.kyc_level}</Typography>
              </Grid>
              <Grid item xs={6}>
                <Typography variant="subtitle2">2FA Enabled:</Typography>
                <Typography>{userDetails.two_factor_enabled ? 'Yes' : 'No'}</Typography>
              </Grid>
              <Grid item xs={6}>
                <Typography variant="subtitle2">Verified:</Typography>
                <Typography>{userDetails.is_verified ? 'Yes' : 'No'}</Typography>
              </Grid>
              <Grid item xs={6}>
                <Typography variant="subtitle2">Status:</Typography>
                <Typography>{userDetails.is_blocked ? 'Blocked' : 'Active'}</Typography>
              </Grid>
              <Grid item xs={12}>
                <Typography variant="h6" sx={{ mt: 2 }}>Recent Orders ({userDetails.orders?.length || 0})</Typography>
              </Grid>
              <Grid item xs={12}>
                <Typography variant="h6" sx={{ mt: 2 }}>Recent Transactions ({userDetails.transactions?.length || 0})</Typography>
              </Grid>
            </Grid>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDetailsDialog(false)}>Close</Button>
        </DialogActions>
      </Dialog>

      {/* Balance Adjustment Dialog */}
      <Dialog open={balanceDialog} onClose={() => setBalanceDialog(false)} maxWidth="md" fullWidth>
        <DialogTitle>Adjust Balance - {selectedUser?.email}</DialogTitle>
        <DialogContent>
          {userBalances.length > 0 && (
            <Box sx={{ mb: 3, p: 2, bgcolor: 'background.default', borderRadius: 1 }}>
              <Typography variant="subtitle2" gutterBottom>Current Balances:</Typography>
              <Grid container spacing={1}>
                {userBalances.map((bal: any) => (
                  <Grid item xs={6} sm={4} key={bal.currency}>
                    <Chip
                      label={`${bal.currency}: ${parseFloat(bal.available).toFixed(8)}`}
                      size="small"
                      color="primary"
                      variant="outlined"
                    />
                  </Grid>
                ))}
              </Grid>
            </Box>
          )}

          <TextField
            fullWidth
            select
            label="Currency"
            value={balanceForm.currency}
            onChange={(e) => setBalanceForm({ ...balanceForm, currency: e.target.value })}
            margin="normal"
            SelectProps={{ native: true }}
          >
            <option value="">Select Currency</option>
            <option value="BTC">BTC - Bitcoin</option>
            <option value="ETH">ETH - Ethereum</option>
            <option value="USDT">USDT - Tether</option>
            <option value="USDC">USDC - USD Coin</option>
            <option value="BNB">BNB - Binance Coin</option>
            <option value="XRP">XRP - Ripple</option>
            <option value="ADA">ADA - Cardano</option>
            <option value="SOL">SOL - Solana</option>
          </TextField>

          <TextField
            fullWidth
            label="Amount"
            type="number"
            value={balanceForm.amount}
            onChange={(e) => setBalanceForm({ ...balanceForm, amount: e.target.value })}
            margin="normal"
            placeholder="0.00000000"
            inputProps={{ step: "0.00000001", min: "0" }}
          />

          <TextField
            fullWidth
            select
            label="Type"
            value={balanceForm.type}
            onChange={(e) => setBalanceForm({ ...balanceForm, type: e.target.value })}
            margin="normal"
            SelectProps={{ native: true }}
          >
            <option value="credit">Add / Credit</option>
            <option value="debit">Subtract / Debit</option>
          </TextField>

          <TextField
            fullWidth
            label="Reason (optional)"
            value={balanceForm.reason}
            onChange={(e) => setBalanceForm({ ...balanceForm, reason: e.target.value })}
            margin="normal"
            placeholder="e.g., Manual deposit, Compensation, Correction..."
            multiline
            rows={2}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setBalanceDialog(false)}>Cancel</Button>
          <Button onClick={handleAdjustBalance} variant="contained" color="primary">Adjust Balance</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};
export default AdminUsers;
