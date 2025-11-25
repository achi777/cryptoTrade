import React from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { Box, Card, CardContent, Typography, TextField, Button, Grid } from '@mui/material';
import { useForm } from 'react-hook-form';
import { RootState, AppDispatch } from '../store';
import { updateProfile } from '../store/slices/authSlice';
import toast from 'react-hot-toast';

const Profile: React.FC = () => {
  const dispatch = useDispatch<AppDispatch>();
  const { user } = useSelector((state: RootState) => state.auth);
  const { register, handleSubmit } = useForm<any>({ defaultValues: user?.profile || {} });

  const onSubmit = async (data: any) => {
    try { await dispatch(updateProfile(data)).unwrap(); toast.success('Profile updated'); } catch (e) { toast.error('Update failed'); }
  };

  return (
    <Box>
      <Typography variant="h4" gutterBottom>Profile</Typography>
      <Card><CardContent>
        <form onSubmit={handleSubmit(onSubmit)}>
          <Grid container spacing={2}>
            <Grid item xs={12} md={6}><TextField fullWidth label="First Name" {...register('first_name')} /></Grid>
            <Grid item xs={12} md={6}><TextField fullWidth label="Last Name" {...register('last_name')} /></Grid>
            <Grid item xs={12} md={6}><TextField fullWidth label="Phone" {...register('phone')} /></Grid>
            <Grid item xs={12} md={6}><TextField fullWidth label="Country" {...register('country')} /></Grid>
            <Grid item xs={12}><Button type="submit" variant="contained">Save Changes</Button></Grid>
          </Grid>
        </form>
      </CardContent></Card>
    </Box>
  );
};
export default Profile;
