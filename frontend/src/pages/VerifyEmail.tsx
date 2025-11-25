import React, { useEffect, useState } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { Box, Card, CardContent, Typography, CircularProgress } from '@mui/material';
import api from '../services/api';

const VerifyEmail: React.FC = () => {
  const [params] = useSearchParams();
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading');

  useEffect(() => {
    const token = params.get('token');
    if (token) {
      api.get(`/auth/verify-email/${token}`).then(() => setStatus('success')).catch(() => setStatus('error'));
    } else { setStatus('error'); }
  }, [params]);

  return (
    <Box sx={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <Card><CardContent sx={{ textAlign: 'center', p: 4 }}>
        {status === 'loading' && <CircularProgress />}
        {status === 'success' && <><Typography variant="h5">Email Verified!</Typography><Link to="/login">Continue to login</Link></>}
        {status === 'error' && <Typography color="error">Verification failed</Typography>}
      </CardContent></Card>
    </Box>
  );
};
export default VerifyEmail;
