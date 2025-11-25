import React from 'react';
import { useSelector } from 'react-redux';
import { Box, Card, CardContent, Typography, Switch, List, ListItem, ListItemText, ListItemSecondaryAction, Button } from '@mui/material';
import { RootState } from '../store';

const Settings: React.FC = () => {
  const { user } = useSelector((state: RootState) => state.auth);
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
        <Button variant="outlined" color="error" sx={{ mt: 2 }}>Change Password</Button>
      </CardContent></Card>
    </Box>
  );
};
export default Settings;
