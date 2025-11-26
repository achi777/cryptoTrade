import React, { useState } from 'react';
import { useSelector } from 'react-redux';
import { Box, Card, CardContent, Typography, Switch, List, ListItem, ListItemText, ListItemSecondaryAction, Button, Dialog, DialogTitle, DialogContent, DialogActions, TextField } from '@mui/material';
import { RootState } from '../store';
import api from '../services/api';
import toast from 'react-hot-toast';

const Settings: React.FC = () => {
  const { user } = useSelector((state: RootState) => state.auth);
  const [passwordDialogOpen, setPasswordDialogOpen] = useState(false);
  const [passwordData, setPasswordData] = useState({
    current_password: '',
    new_password: '',
    confirm_password: ''
  });
  const [loading, setLoading] = useState(false);

  const handlePasswordChange = async () => {
    if (passwordData.new_password !== passwordData.confirm_password) {
      toast.error('New passwords do not match');
      return;
    }

    if (passwordData.new_password.length < 8) {
      toast.error('Password must be at least 8 characters');
      return;
    }

    setLoading(true);
    try {
      await api.post('/user/change-password', {
        current_password: passwordData.current_password,
        new_password: passwordData.new_password
      });
      toast.success('Password changed successfully');
      setPasswordDialogOpen(false);
      setPasswordData({ current_password: '', new_password: '', confirm_password: '' });
    } catch (error: any) {
      toast.error(error.response?.data?.error || 'Failed to change password');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box>
      <Typography variant="h4" gutterBottom>Settings</Typography>
      <Card><CardContent>
        <List>
          <ListItem><ListItemText primary="Two-Factor Authentication" secondary={user?.two_factor_enabled ? 'Enabled' : 'Disabled'} />
            <ListItemSecondaryAction><Switch checked={user?.two_factor_enabled} /></ListItemSecondaryAction>
          </ListItem>
          <ListItem><ListItemText primary="Email Notifications" secondary="Receive notifications about your account" />
            <ListItemSecondaryAction><Switch defaultChecked /></ListItemSecondaryAction>
          </ListItem>
        </List>
        <Button
          variant="outlined"
          color="error"
          sx={{ mt: 2 }}
          onClick={() => setPasswordDialogOpen(true)}
        >
          Change Password
        </Button>
      </CardContent></Card>

      <Dialog open={passwordDialogOpen} onClose={() => setPasswordDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Change Password</DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 2, display: 'flex', flexDirection: 'column', gap: 2 }}>
            <TextField
              fullWidth
              type="password"
              label="Current Password"
              value={passwordData.current_password}
              onChange={(e) => setPasswordData({ ...passwordData, current_password: e.target.value })}
            />
            <TextField
              fullWidth
              type="password"
              label="New Password"
              value={passwordData.new_password}
              onChange={(e) => setPasswordData({ ...passwordData, new_password: e.target.value })}
              helperText="Must be at least 8 characters"
            />
            <TextField
              fullWidth
              type="password"
              label="Confirm New Password"
              value={passwordData.confirm_password}
              onChange={(e) => setPasswordData({ ...passwordData, confirm_password: e.target.value })}
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setPasswordDialogOpen(false)}>Cancel</Button>
          <Button
            onClick={handlePasswordChange}
            variant="contained"
            disabled={loading || !passwordData.current_password || !passwordData.new_password || !passwordData.confirm_password}
          >
            {loading ? 'Changing...' : 'Change Password'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};
export default Settings;
