import React, { useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { Box, Card, CardContent, Typography, TextField, Button } from '@mui/material';
import api from '../services/api';
import toast from 'react-hot-toast';

const ResetPassword: React.FC = () => {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const [password, setPassword] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.post('/auth/reset-password', { token: params.get('token'), password });
      toast.success('Password reset successful');
      navigate('/login');
    } catch { toast.error('Reset failed'); }
  };

  return (
    <Box sx={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <Card sx={{ maxWidth: 400 }}><CardContent sx={{ p: 4 }}>
        <Typography variant="h5" gutterBottom>Reset Password</Typography>
        <form onSubmit={handleSubmit}>
          <TextField fullWidth label="New Password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} margin="normal" />
          <Button type="submit" fullWidth variant="contained" sx={{ mt: 2 }}>Reset Password</Button>
        </form>
      </CardContent></Card>
    </Box>
  );
};
export default ResetPassword;
