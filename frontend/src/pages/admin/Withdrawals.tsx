import React, { useEffect, useState } from 'react';
import { Box, Card, CardContent, Typography, Table, TableHead, TableRow, TableCell, TableBody, Button, Tabs, Tab, Chip, Dialog, DialogTitle, DialogContent, DialogActions, TextField, Grid, IconButton, Tooltip } from '@mui/material';
import { CheckCircle, Cancel, Visibility, Warning } from '@mui/icons-material';
import { adminApi } from '../../services/api';
import toast from 'react-hot-toast';

const AdminWithdrawals: React.FC = () => {
  const [tab, setTab] = useState(0);
  const [withdrawals, setWithdrawals] = useState<any[]>([]);
  const [allWithdrawals, setAllWithdrawals] = useState<any[]>([]);
  const [selectedWithdrawal, setSelectedWithdrawal] = useState<any>(null);
  const [detailsDialog, setDetailsDialog] = useState(false);
  const [rejectDialog, setRejectDialog] = useState(false);
  const [rejectReason, setRejectReason] = useState('');

  const loadData = async () => {
    try {
      const pendingRes = await adminApi.get('/wallets/withdrawals/pending');
      setWithdrawals(pendingRes.data.withdrawals || []);

      // Get all withdrawals for history tab
      const usersRes = await adminApi.get('/users');
      const users = usersRes.data.users || [];
      const allWithdrawalsPromises = users.map((u: any) =>
        adminApi.get(`/users/${u.id}/transactions`).catch(() => ({ data: { transactions: [] } }))
      );
      const results = await Promise.all(allWithdrawalsPromises);
      const allTxs = results.flatMap(r => r.data.transactions || []).filter((t: any) => t.type === 'withdrawal');
      setAllWithdrawals(allTxs);
    } catch (error) {
      console.error('Failed to load withdrawals', error);
    }
  };

  useEffect(() => { loadData(); }, []);

  const handleApprove = async (withdrawal: any) => {
    try {
      await adminApi.post(`/wallets/withdrawals/${withdrawal.id}/approve`);
      toast.success('Withdrawal approved successfully');
      loadData();
      setDetailsDialog(false);
    } catch (error) {
      toast.error('Failed to approve withdrawal');
    }
  };

  const handleReject = async () => {
    if (!rejectReason.trim()) {
      toast.error('Please provide a reason');
      return;
    }
    try {
      await adminApi.post(`/wallets/withdrawals/${selectedWithdrawal.id}/reject`, { reason: rejectReason });
      toast.success('Withdrawal rejected');
      setRejectDialog(false);
      setDetailsDialog(false);
      setRejectReason('');
      loadData();
    } catch (error) {
      toast.error('Failed to reject withdrawal');
    }
  };

  const openRejectDialog = (withdrawal: any) => {
    setSelectedWithdrawal(withdrawal);
    setRejectDialog(true);
  };

  const displayWithdrawals = tab === 0 ? withdrawals : allWithdrawals;

  return (
    <Box>
      <Typography variant="h4" gutterBottom>Withdrawal Management</Typography>

      <Card>
        <Tabs value={tab} onChange={(e, v) => setTab(v)} sx={{ borderBottom: 1, borderColor: 'divider' }}>
          <Tab label={`Pending (${withdrawals.length})`} />
          <Tab label="All Withdrawals" />
        </Tabs>
        <CardContent>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>ID</TableCell>
                <TableCell>User</TableCell>
                <TableCell>Currency</TableCell>
                <TableCell align="right">Amount</TableCell>
                <TableCell align="right">Fee</TableCell>
                <TableCell align="right">Net</TableCell>
                <TableCell>Address</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Date</TableCell>
                <TableCell>Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {displayWithdrawals.map((w) => (
                <TableRow key={w.id}>
                  <TableCell>{w.id}</TableCell>
                  <TableCell>{w.user_id}</TableCell>
                  <TableCell>
                    <Chip label={w.currency} size="small" />
                  </TableCell>
                  <TableCell align="right">{parseFloat(w.amount).toFixed(8)}</TableCell>
                  <TableCell align="right">{parseFloat(w.fee || 0).toFixed(8)}</TableCell>
                  <TableCell align="right">{parseFloat(w.net_amount || w.amount).toFixed(8)}</TableCell>
                  <TableCell>
                    <Tooltip title={w.to_address}>
                      <span>{w.to_address?.slice(0, 10)}...{w.to_address?.slice(-8)}</span>
                    </Tooltip>
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={w.status || 'pending'}
                      size="small"
                      color={w.status === 'approved' ? 'success' : w.status === 'rejected' ? 'error' : 'warning'}
                    />
                  </TableCell>
                  <TableCell>{new Date(w.created_at).toLocaleDateString()}</TableCell>
                  <TableCell>
                    <Tooltip title="View Details">
                      <IconButton size="small" onClick={() => { setSelectedWithdrawal(w); setDetailsDialog(true); }}>
                        <Visibility fontSize="small" />
                      </IconButton>
                    </Tooltip>
                    {w.status === 'pending' && (
                      <>
                        <Tooltip title="Approve">
                          <IconButton size="small" color="success" onClick={() => handleApprove(w)}>
                            <CheckCircle fontSize="small" />
                          </IconButton>
                        </Tooltip>
                        <Tooltip title="Reject">
                          <IconButton size="small" color="error" onClick={() => openRejectDialog(w)}>
                            <Cancel fontSize="small" />
                          </IconButton>
                        </Tooltip>
                      </>
                    )}
                  </TableCell>
                </TableRow>
              ))}
              {displayWithdrawals.length === 0 && (
                <TableRow>
                  <TableCell colSpan={10} align="center">
                    {tab === 0 ? 'No pending withdrawals' : 'No withdrawals found'}
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Details Dialog */}
      <Dialog open={detailsDialog} onClose={() => setDetailsDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Withdrawal Details #{selectedWithdrawal?.id}</DialogTitle>
        <DialogContent>
          {selectedWithdrawal && (
            <Grid container spacing={2} sx={{ mt: 1 }}>
              <Grid item xs={6}>
                <Typography variant="subtitle2">User ID:</Typography>
                <Typography>{selectedWithdrawal.user_id}</Typography>
              </Grid>
              <Grid item xs={6}>
                <Typography variant="subtitle2">Currency:</Typography>
                <Typography>{selectedWithdrawal.currency}</Typography>
              </Grid>
              <Grid item xs={6}>
                <Typography variant="subtitle2">Amount:</Typography>
                <Typography>{parseFloat(selectedWithdrawal.amount).toFixed(8)}</Typography>
              </Grid>
              <Grid item xs={6}>
                <Typography variant="subtitle2">Fee:</Typography>
                <Typography>{parseFloat(selectedWithdrawal.fee || 0).toFixed(8)}</Typography>
              </Grid>
              <Grid item xs={12}>
                <Typography variant="subtitle2">Recipient Address:</Typography>
                <Typography sx={{ wordBreak: 'break-all', fontFamily: 'monospace', fontSize: '0.85rem' }}>
                  {selectedWithdrawal.to_address}
                </Typography>
              </Grid>
              {selectedWithdrawal.memo && (
                <Grid item xs={12}>
                  <Typography variant="subtitle2">Memo:</Typography>
                  <Typography>{selectedWithdrawal.memo}</Typography>
                </Grid>
              )}
              <Grid item xs={6}>
                <Typography variant="subtitle2">Status:</Typography>
                <Chip label={selectedWithdrawal.status || 'pending'} size="small" />
              </Grid>
              <Grid item xs={6}>
                <Typography variant="subtitle2">Created:</Typography>
                <Typography>{new Date(selectedWithdrawal.created_at).toLocaleString()}</Typography>
              </Grid>
              {selectedWithdrawal.two_factor_verified && (
                <Grid item xs={12}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, p: 1, bgcolor: 'success.50', borderRadius: 1 }}>
                    <CheckCircle color="success" fontSize="small" />
                    <Typography variant="body2">2FA Verified</Typography>
                  </Box>
                </Grid>
              )}
              {selectedWithdrawal.requires_manual_approval && (
                <Grid item xs={12}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, p: 1, bgcolor: 'warning.50', borderRadius: 1 }}>
                    <Warning color="warning" fontSize="small" />
                    <Typography variant="body2">Requires Manual Approval (High Amount)</Typography>
                  </Box>
                </Grid>
              )}
            </Grid>
          )}
        </DialogContent>
        <DialogActions>
          {selectedWithdrawal?.status === 'pending' && (
            <>
              <Button onClick={() => handleApprove(selectedWithdrawal)} color="success" variant="contained">
                Approve
              </Button>
              <Button onClick={() => { setDetailsDialog(false); openRejectDialog(selectedWithdrawal); }} color="error">
                Reject
              </Button>
            </>
          )}
          <Button onClick={() => setDetailsDialog(false)}>Close</Button>
        </DialogActions>
      </Dialog>

      {/* Reject Dialog */}
      <Dialog open={rejectDialog} onClose={() => setRejectDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Reject Withdrawal</DialogTitle>
        <DialogContent>
          <Typography gutterBottom>Please provide a reason for rejecting this withdrawal:</Typography>
          <TextField
            fullWidth
            multiline
            rows={3}
            value={rejectReason}
            onChange={(e) => setRejectReason(e.target.value)}
            placeholder="e.g., Suspicious activity, Invalid address, etc."
            margin="normal"
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setRejectDialog(false)}>Cancel</Button>
          <Button onClick={handleReject} color="error" variant="contained">Reject</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};
export default AdminWithdrawals;
