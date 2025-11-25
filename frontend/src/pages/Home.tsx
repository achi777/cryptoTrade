import React from 'react';
import { Link } from 'react-router-dom';
import { Box, Button, Typography, Container } from '@mui/material';

const Home: React.FC = () => (
  <Box sx={{ minHeight: '100vh', display: 'flex', alignItems: 'center', bgcolor: 'background.default' }}>
    <Container maxWidth="md" sx={{ textAlign: 'center' }}>
      <Typography variant="h2" gutterBottom sx={{ fontWeight: 700 }}>CryptoTrade</Typography>
      <Typography variant="h5" color="text.secondary" gutterBottom>
        Secure Cryptocurrency Trading Platform
      </Typography>
      <Box sx={{ mt: 4 }}>
        <Button component={Link} to="/register" variant="contained" size="large" sx={{ mr: 2 }}>Get Started</Button>
        <Button component={Link} to="/login" variant="outlined" size="large">Sign In</Button>
      </Box>
    </Container>
  </Box>
);

export default Home;
