import React, { useEffect, useState } from 'react';
import { Box, Grid, Card, CardContent, Typography, Table, TableBody, TableCell, TableHead, TableRow, Chip, LinearProgress } from '@mui/material';
import { People, AccountBalance, SwapHoriz, TrendingUp, Warning, CheckCircle, Schedule, Block } from '@mui/icons-material';
import { adminApi } from '../../services/api';

const AdminDashboard: React.FC = () => {
  const [stats, setStats] = useState<any>(null);
  const [recentActivity, setRecentActivity] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadData = async () => {
      try {
        const [statsRes, usersRes, withdrawalsRes, ordersRes] = await Promise.all([
          adminApi.get('/settings'),
          adminApi.get('/users'),
          adminApi.get('/wallets/withdrawals/pending'),
          adminApi.get('/trading/pairs')
        ]);

        const users = usersRes.data.users || [];
        const withdrawals = withdrawalsRes.data.withdrawals || [];

        setStats({
          users: {
            total: users.length,
            verified: users.filter((u: any) => u.is_verified).length,
            blocked: users.filter((u: any) => u.is_blocked).length,
            new_today: users.filter((u: any) => {
              const created = new Date(u.created_at);
              const today = new Date();
              return created.toDateString() === today.toDateString();
            }).length
          },
          withdrawals: {
            pending: withdrawals.length,
            total: withdrawals.reduce((sum: number, w: any) => sum + parseFloat(w.amount), 0).toFixed(2)
          },
          kyc: {
            pending: users.filter((u: any) => u.kyc_level === 0).length,
            verified: users.filter((u: any) => u.kyc_level >= 2).length
          },
          trading: {
            pairs: ordersRes.data.pairs?.length || 0
          }
        });

        setRecentActivity(users.slice(0, 5).map((u: any) => ({
          type: 'User Registration',
          email: u.email,
          time: u.created_at
        })));
      } catch (error) {
        console.error('Failed to load dashboard data', error);
      } finally {
        setLoading(false);
      }
    };
    loadData();
  }, []);

  if (loading) return <Box sx={{ p: 3 }}><LinearProgress /></Box>;

  return (
    <Box>
      <Typography variant="h4" gutterBottom>Admin Dashboard</Typography>

      {/* Main Stats */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' }}>
            <CardContent>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Box>
                  <Typography color="white" variant="body2">Total Users</Typography>
                  <Typography variant="h3" sx={{ color: 'white', fontWeight: 'bold' }}>
                    {stats?.users?.total || 0}
                  </Typography>
                  <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.8)' }}>
                    +{stats?.users?.new_today || 0} today
                  </Typography>
                </Box>
                <People sx={{ fontSize: 60, color: 'rgba(255,255,255,0.3)' }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ background: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)' }}>
            <CardContent>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Box>
                  <Typography color="white" variant="body2">Pending Withdrawals</Typography>
                  <Typography variant="h3" sx={{ color: 'white', fontWeight: 'bold' }}>
                    {stats?.withdrawals?.pending || 0}
                  </Typography>
                  <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.8)' }}>
                    ${stats?.withdrawals?.total || 0}
                  </Typography>
                </Box>
                <AccountBalance sx={{ fontSize: 60, color: 'rgba(255,255,255,0.3)' }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ background: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)' }}>
            <CardContent>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Box>
                  <Typography color="white" variant="body2">Pending KYC</Typography>
                  <Typography variant="h3" sx={{ color: 'white', fontWeight: 'bold' }}>
                    {stats?.kyc?.pending || 0}
                  </Typography>
                  <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.8)' }}>
                    {stats?.kyc?.verified || 0} verified
                  </Typography>
                </Box>
                <CheckCircle sx={{ fontSize: 60, color: 'rgba(255,255,255,0.3)' }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ background: 'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)' }}>
            <CardContent>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Box>
                  <Typography color="white" variant="body2">Trading Pairs</Typography>
                  <Typography variant="h3" sx={{ color: 'white', fontWeight: 'bold' }}>
                    {stats?.trading?.pairs || 0}
                  </Typography>
                  <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.8)' }}>
                    Active markets
                  </Typography>
                </Box>
                <SwapHoriz sx={{ fontSize: 60, color: 'rgba(255,255,255,0.3)' }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Additional Stats */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>User Statistics</Typography>
              <Grid container spacing={2}>
                <Grid item xs={6}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                    <CheckCircle color="success" />
                    <Box>
                      <Typography variant="body2" color="text.secondary">Verified</Typography>
                      <Typography variant="h6">{stats?.users?.verified || 0}</Typography>
                    </Box>
                  </Box>
                </Grid>
                <Grid item xs={6}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                    <Block color="error" />
                    <Box>
                      <Typography variant="body2" color="text.secondary">Blocked</Typography>
                      <Typography variant="h6">{stats?.users?.blocked || 0}</Typography>
                    </Box>
                  </Box>
                </Grid>
                <Grid item xs={6}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Schedule color="warning" />
                    <Box>
                      <Typography variant="body2" color="text.secondary">Pending KYC</Typography>
                      <Typography variant="h6">{stats?.kyc?.pending || 0}</Typography>
                    </Box>
                  </Box>
                </Grid>
                <Grid item xs={6}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <TrendingUp color="info" />
                    <Box>
                      <Typography variant="body2" color="text.secondary">New Today</Typography>
                      <Typography variant="h6">{stats?.users?.new_today || 0}</Typography>
                    </Box>
                  </Box>
                </Grid>
              </Grid>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>Quick Actions Needed</Typography>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                {stats?.withdrawals?.pending > 0 && (
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', p: 1, bgcolor: 'error.50', borderRadius: 1 }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Warning color="error" />
                      <Typography>{stats.withdrawals.pending} Withdrawals need approval</Typography>
                    </Box>
                    <Chip label="Urgent" color="error" size="small" />
                  </Box>
                )}
                {stats?.kyc?.pending > 0 && (
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', p: 1, bgcolor: 'warning.50', borderRadius: 1 }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Schedule color="warning" />
                      <Typography>{stats.kyc.pending} KYC requests pending</Typography>
                    </Box>
                    <Chip label="Review" color="warning" size="small" />
                  </Box>
                )}
                {stats?.withdrawals?.pending === 0 && stats?.kyc?.pending === 0 && (
                  <Box sx={{ textAlign: 'center', py: 3 }}>
                    <CheckCircle color="success" sx={{ fontSize: 48, mb: 1 }} />
                    <Typography color="text.secondary">All caught up! No pending actions.</Typography>
                  </Box>
                )}
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Recent Activity */}
      <Grid container spacing={3}>
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>Recent Activity</Typography>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Type</TableCell>
                    <TableCell>User/Details</TableCell>
                    <TableCell>Time</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {recentActivity.map((activity, idx) => (
                    <TableRow key={idx}>
                      <TableCell>
                        <Chip label={activity.type} size="small" color="primary" />
                      </TableCell>
                      <TableCell>{activity.email}</TableCell>
                      <TableCell>{new Date(activity.time).toLocaleString()}</TableCell>
                    </TableRow>
                  ))}
                  {recentActivity.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={3} align="center">No recent activity</TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};
export default AdminDashboard;
