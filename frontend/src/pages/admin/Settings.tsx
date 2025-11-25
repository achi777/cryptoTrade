import React, { useEffect, useState } from 'react';
import { Box, Card, CardContent, Typography, List, ListItem, ListItemText, Switch, ListItemSecondaryAction } from '@mui/material';
import { adminApi } from '../../services/api';

const AdminSettings: React.FC = () => {
  const [settings, setSettings] = useState<any[]>([]);
  useEffect(() => { adminApi.get('/settings').then((res) => setSettings(res.data.settings || [])); }, []);
  return (
    <Box>
      <Typography variant="h4" gutterBottom>System Settings</Typography>
      <Card><CardContent>
        <List>{settings.map((s) => (<ListItem key={s.key}><ListItemText primary={s.key.replace(/_/g, ' ')} secondary={s.description} /><ListItemSecondaryAction>{s.value === 'true' || s.value === 'false' ? <Switch checked={s.value === 'true'} /> : <Typography>{s.value}</Typography>}</ListItemSecondaryAction></ListItem>))}</List>
      </CardContent></Card>
    </Box>
  );
};
export default AdminSettings;
