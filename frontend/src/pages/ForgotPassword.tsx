import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { Box, Card, CardContent, Typography, TextField, Button, Alert } from '@mui/material';
import api from '../services/api';

const ForgotPassword: React.FC = () => {
  const [email, setEmail] = useState('');
  const [sent, setSent] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await api.post('/auth/forgot-password', { email });
    setSent(true);
  };

  return (
    <Box sx={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <Card sx={{ maxWidth: 400 }}><CardContent sx={{ p: 4 }}>
        <Typography variant="h5" gutterBottom>Forgot Password</Typography>
        {sent ? <Alert severity="success">Check your email for reset link</Alert> : (
          <form onSubmit={handleSubmit}>
            <TextField fullWidth label="Email" value={email} onChange={(e) => setEmail(e.target.value)} margin="normal" />
            <Button type="submit" fullWidth variant="contained" sx={{ mt: 2 }}>Send Reset Link</Button>
          </form>
        )}
        <Box sx={{ mt: 2, textAlign: 'center' }}><Link to="/login">Back to login</Link></Box>
      </CardContent></Card>
    </Box>
  );
};
export default ForgotPassword;
