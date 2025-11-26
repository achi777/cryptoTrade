import React, { useState, useEffect } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { Box, Card, CardContent, Typography, TextField, Button, Grid } from '@mui/material';
import { RootState, AppDispatch } from '../store';
import { updateProfile } from '../store/slices/authSlice';
import toast from 'react-hot-toast';
import CountrySelect from '../components/CountrySelect';

const Profile: React.FC = () => {
  const dispatch = useDispatch<AppDispatch>();
  const { user } = useSelector((state: RootState) => state.auth);

  const [formData, setFormData] = useState({
    first_name: '',
    last_name: '',
    phone: '',
    country: '',
    city: '',
    address: '',
    postal_code: ''
  });

  useEffect(() => {
    if (user?.profile) {
      setFormData({
        first_name: user.profile.first_name || '',
        last_name: user.profile.last_name || '',
        phone: user.profile.phone || '',
        country: user.profile.country || '',
        city: user.profile.city || '',
        address: user.profile.address || '',
        postal_code: user.profile.postal_code || ''
      });
    }
  }, [user]);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await dispatch(updateProfile(formData)).unwrap();
      toast.success('Profile updated successfully');
    } catch (e) {
      toast.error('Failed to update profile');
    }
  };

  return (
    <Box>
      <Typography variant="h4" gutterBottom>Profile</Typography>
      <Card>
        <CardContent>
          <form onSubmit={handleSubmit}>
            <Grid container spacing={3}>
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  label="First Name"
                  name="first_name"
                  value={formData.first_name}
                  onChange={handleInputChange}
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  label="Last Name"
                  name="last_name"
                  value={formData.last_name}
                  onChange={handleInputChange}
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  label="Phone"
                  name="phone"
                  value={formData.phone}
                  onChange={handleInputChange}
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <CountrySelect
                  value={formData.country}
                  onChange={(value) => setFormData({ ...formData, country: value })}
                  label="Country"
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  label="City"
                  name="city"
                  value={formData.city}
                  onChange={handleInputChange}
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  label="Postal Code"
                  name="postal_code"
                  value={formData.postal_code}
                  onChange={handleInputChange}
                />
              </Grid>
              <Grid item xs={12}>
                <TextField
                  fullWidth
                  label="Address"
                  name="address"
                  value={formData.address}
                  onChange={handleInputChange}
                  multiline
                  rows={2}
                />
              </Grid>
              <Grid item xs={12}>
                <Button type="submit" variant="contained" size="large">
                  Save Changes
                </Button>
              </Grid>
            </Grid>
          </form>
        </CardContent>
      </Card>
    </Box>
  );
};

export default Profile;
