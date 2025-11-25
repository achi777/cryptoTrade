import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useDispatch, useSelector } from 'react-redux';
import { Box, Card, CardContent, TextField, Button, Typography, Alert } from '@mui/material';
import { useForm } from 'react-hook-form';
import { RootState, AppDispatch } from '../store';
import { register as registerUser } from '../store/slices/authSlice';
import toast from 'react-hot-toast';

const Register: React.FC = () => {
  const dispatch = useDispatch<AppDispatch>();
  const navigate = useNavigate();
  const { loading, error } = useSelector((state: RootState) => state.auth);
  const { register, handleSubmit, watch, formState: { errors } } = useForm();

  const onSubmit = async (data: any) => {
    if (data.password !== data.confirmPassword) {
      toast.error('Passwords do not match');
      return;
    }
    const result = await dispatch(registerUser({ email: data.email, password: data.password }));
    if (registerUser.fulfilled.match(result)) {
      toast.success('Registration successful! Please check your email.');
      navigate('/login');
    }
  };

  return (
    <Box sx={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', bgcolor: 'background.default', p: 2 }}>
      <Card sx={{ maxWidth: 400, width: '100%' }}>
        <CardContent sx={{ p: 4 }}>
          <Typography variant="h4" align="center" gutterBottom>Sign Up</Typography>
          {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
          <form onSubmit={handleSubmit(onSubmit)}>
            <TextField fullWidth label="Email" type="email" margin="normal" {...register('email', { required: true })} />
            <TextField fullWidth label="Password" type="password" margin="normal" {...register('password', { required: true, minLength: 8 })} />
            <TextField fullWidth label="Confirm Password" type="password" margin="normal" {...register('confirmPassword', { required: true })} />
            <Button type="submit" fullWidth variant="contained" size="large" disabled={loading} sx={{ mt: 3 }}>Create Account</Button>
          </form>
          <Box sx={{ mt: 2, textAlign: 'center' }}>
            <Typography variant="body2" color="text.secondary">Already have an account? <Link to="/login"><Typography component="span" color="primary">Sign in</Typography></Link></Typography>
          </Box>
        </CardContent>
      </Card>
    </Box>
  );
};
export default Register;
