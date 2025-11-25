import React from 'react';
import { useSelector } from 'react-redux';
import { Box, Card, CardContent, Typography, Stepper, Step, StepLabel, Button } from '@mui/material';
import { RootState } from '../store';

const KYC: React.FC = () => {
  const { user } = useSelector((state: RootState) => state.auth);
  return (
    <Box>
      <Typography variant="h4" gutterBottom>KYC Verification</Typography>
      <Card><CardContent>
        <Stepper activeStep={user?.kyc_level || 0} alternativeLabel>
          <Step><StepLabel>Basic Info</StepLabel></Step>
          <Step><StepLabel>ID Verification</StepLabel></Step>
          <Step><StepLabel>Address Proof</StepLabel></Step>
        </Stepper>
        <Box sx={{ mt: 4, textAlign: 'center' }}>
          <Typography variant="h6">Current Level: {user?.kyc_level || 0}</Typography>
          {(user?.kyc_level || 0) < 3 && <Button variant="contained" sx={{ mt: 2 }}>Start Verification</Button>}
        </Box>
      </CardContent></Card>
    </Box>
  );
};
export default KYC;
