import React, { useState } from 'react';
import { useSelector } from 'react-redux';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Stepper,
  Step,
  StepLabel,
  Button,
  TextField,
  Grid,
  MenuItem,
  Alert,
  LinearProgress,
  Chip
} from '@mui/material';
import { Upload, CheckCircle, HourglassEmpty } from '@mui/icons-material';
import { RootState } from '../store';
import toast from 'react-hot-toast';
import api from '../services/api';

const KYC: React.FC = () => {
  const { user } = useSelector((state: RootState) => state.auth);
  const [activeStep, setActiveStep] = useState(user?.kyc_level || 0);
  const [loading, setLoading] = useState(false);

  // Level 1 - Basic Info
  const [basicInfo, setBasicInfo] = useState({
    firstName: '',
    lastName: '',
    dateOfBirth: '',
    nationality: '',
    phoneNumber: ''
  });

  // Level 2 - ID Verification
  const [idInfo, setIdInfo] = useState({
    idType: 'passport',
    idNumber: '',
    idFrontImage: null as File | null,
    idBackImage: null as File | null,
    selfieImage: null as File | null
  });

  // Level 3 - Address Proof
  const [addressInfo, setAddressInfo] = useState({
    address: '',
    city: '',
    postalCode: '',
    country: '',
    proofDocument: null as File | null
  });

  const handleFileUpload = (field: string, file: File) => {
    if (activeStep === 1) {
      setIdInfo({ ...idInfo, [field]: file });
    } else if (activeStep === 2) {
      setAddressInfo({ ...addressInfo, [field]: file });
    }
  };

  const submitLevel1 = async () => {
    try {
      setLoading(true);
      await api.post('/kyc/basic-info', basicInfo);
      toast.success('Basic information submitted successfully');
      setActiveStep(1);
    } catch (error: any) {
      toast.error(error.response?.data?.error || 'Failed to submit basic info');
    } finally {
      setLoading(false);
    }
  };

  const submitLevel2 = async () => {
    try {
      setLoading(true);
      const formData = new FormData();
      formData.append('id_type', idInfo.idType);
      formData.append('id_number', idInfo.idNumber);
      if (idInfo.idFrontImage) formData.append('id_front', idInfo.idFrontImage);
      if (idInfo.idBackImage) formData.append('id_back', idInfo.idBackImage);
      if (idInfo.selfieImage) formData.append('selfie', idInfo.selfieImage);

      await api.post('/kyc/id-verification', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      toast.success('ID verification submitted for review');
      setActiveStep(2);
    } catch (error: any) {
      toast.error(error.response?.data?.error || 'Failed to submit ID verification');
    } finally {
      setLoading(false);
    }
  };

  const submitLevel3 = async () => {
    try {
      setLoading(true);
      const formData = new FormData();
      formData.append('address', addressInfo.address);
      formData.append('city', addressInfo.city);
      formData.append('postal_code', addressInfo.postalCode);
      formData.append('country', addressInfo.country);
      if (addressInfo.proofDocument) formData.append('proof_document', addressInfo.proofDocument);

      await api.post('/kyc/address-verification', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      toast.success('Address verification submitted for review');
    } catch (error: any) {
      toast.error(error.response?.data?.error || 'Failed to submit address proof');
    } finally {
      setLoading(false);
    }
  };

  const getStatusChip = () => {
    const level = user?.kyc_level || 0;
    if (level === 0) return <Chip label="Unverified" color="error" size="small" icon={<HourglassEmpty />} />;
    if (level === 1) return <Chip label="Level 1 - Basic" color="warning" size="small" />;
    if (level === 2) return <Chip label="Level 2 - Verified" color="info" size="small" />;
    if (level === 3) return <Chip label="Level 3 - Advanced" color="success" size="small" icon={<CheckCircle />} />;
    return null;
  };

  return (
    <Box sx={{ maxWidth: 1000, mx: 'auto', p: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" fontWeight={700}>KYC Verification</Typography>
        {getStatusChip()}
      </Box>

      <Alert severity="info" sx={{ mb: 3 }}>
        Complete KYC verification to unlock higher trading limits, withdrawals, and margin trading.
      </Alert>

      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Stepper activeStep={activeStep} alternativeLabel>
            <Step>
              <StepLabel>Basic Information</StepLabel>
            </Step>
            <Step>
              <StepLabel>ID Verification</StepLabel>
            </Step>
            <Step>
              <StepLabel>Address Proof</StepLabel>
            </Step>
          </Stepper>
        </CardContent>
      </Card>

      {/* Level 1 - Basic Information */}
      {activeStep === 0 && (
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom fontWeight={600}>
              Level 1: Basic Information
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
              Provide your personal details to get started.
            </Typography>

            <Grid container spacing={2}>
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  label="First Name"
                  value={basicInfo.firstName}
                  onChange={(e) => setBasicInfo({ ...basicInfo, firstName: e.target.value })}
                  required
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  label="Last Name"
                  value={basicInfo.lastName}
                  onChange={(e) => setBasicInfo({ ...basicInfo, lastName: e.target.value })}
                  required
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  label="Date of Birth"
                  type="date"
                  value={basicInfo.dateOfBirth}
                  onChange={(e) => setBasicInfo({ ...basicInfo, dateOfBirth: e.target.value })}
                  InputLabelProps={{ shrink: true }}
                  required
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  label="Nationality"
                  value={basicInfo.nationality}
                  onChange={(e) => setBasicInfo({ ...basicInfo, nationality: e.target.value })}
                  required
                />
              </Grid>
              <Grid item xs={12}>
                <TextField
                  fullWidth
                  label="Phone Number"
                  value={basicInfo.phoneNumber}
                  onChange={(e) => setBasicInfo({ ...basicInfo, phoneNumber: e.target.value })}
                  placeholder="+995 XXX XXX XXX"
                  required
                />
              </Grid>
            </Grid>

            <Box sx={{ mt: 3, display: 'flex', justifyContent: 'flex-end' }}>
              <Button
                variant="contained"
                size="large"
                onClick={submitLevel1}
                disabled={loading}
              >
                {loading ? 'Submitting...' : 'Submit & Continue'}
              </Button>
            </Box>
          </CardContent>
        </Card>
      )}

      {/* Level 2 - ID Verification */}
      {activeStep === 1 && (
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom fontWeight={600}>
              Level 2: ID Verification
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
              Upload a government-issued ID and a selfie holding the ID.
            </Typography>

            <Grid container spacing={3}>
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  select
                  label="ID Type"
                  value={idInfo.idType}
                  onChange={(e) => setIdInfo({ ...idInfo, idType: e.target.value })}
                >
                  <MenuItem value="passport">Passport</MenuItem>
                  <MenuItem value="national_id">National ID Card</MenuItem>
                  <MenuItem value="drivers_license">Driver's License</MenuItem>
                </TextField>
              </Grid>
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  label="ID Number"
                  value={idInfo.idNumber}
                  onChange={(e) => setIdInfo({ ...idInfo, idNumber: e.target.value })}
                  required
                />
              </Grid>

              <Grid item xs={12} md={4}>
                <Button
                  fullWidth
                  variant="outlined"
                  component="label"
                  startIcon={<Upload />}
                  sx={{ height: 120, flexDirection: 'column' }}
                >
                  {idInfo.idFrontImage ? '✓ Front Uploaded' : 'Upload ID Front'}
                  <input
                    type="file"
                    hidden
                    accept="image/*"
                    onChange={(e) => e.target.files?.[0] && handleFileUpload('idFrontImage', e.target.files[0])}
                  />
                </Button>
                {idInfo.idFrontImage && (
                  <Typography variant="caption" sx={{ mt: 1, display: 'block', textAlign: 'center' }}>
                    {idInfo.idFrontImage.name}
                  </Typography>
                )}
              </Grid>

              <Grid item xs={12} md={4}>
                <Button
                  fullWidth
                  variant="outlined"
                  component="label"
                  startIcon={<Upload />}
                  sx={{ height: 120, flexDirection: 'column' }}
                >
                  {idInfo.idBackImage ? '✓ Back Uploaded' : 'Upload ID Back'}
                  <input
                    type="file"
                    hidden
                    accept="image/*"
                    onChange={(e) => e.target.files?.[0] && handleFileUpload('idBackImage', e.target.files[0])}
                  />
                </Button>
                {idInfo.idBackImage && (
                  <Typography variant="caption" sx={{ mt: 1, display: 'block', textAlign: 'center' }}>
                    {idInfo.idBackImage.name}
                  </Typography>
                )}
              </Grid>

              <Grid item xs={12} md={4}>
                <Button
                  fullWidth
                  variant="outlined"
                  component="label"
                  startIcon={<Upload />}
                  sx={{ height: 120, flexDirection: 'column' }}
                >
                  {idInfo.selfieImage ? '✓ Selfie Uploaded' : 'Upload Selfie with ID'}
                  <input
                    type="file"
                    hidden
                    accept="image/*"
                    onChange={(e) => e.target.files?.[0] && handleFileUpload('selfieImage', e.target.files[0])}
                  />
                </Button>
                {idInfo.selfieImage && (
                  <Typography variant="caption" sx={{ mt: 1, display: 'block', textAlign: 'center' }}>
                    {idInfo.selfieImage.name}
                  </Typography>
                )}
              </Grid>

              <Grid item xs={12}>
                <Alert severity="warning">
                  <strong>Important:</strong> Make sure all text on your ID is clearly visible and readable.
                  Your selfie should show your face and the ID document clearly.
                </Alert>
              </Grid>
            </Grid>

            <Box sx={{ mt: 3, display: 'flex', justifyContent: 'space-between' }}>
              <Button onClick={() => setActiveStep(0)}>Back</Button>
              <Button
                variant="contained"
                size="large"
                onClick={submitLevel2}
                disabled={loading || !idInfo.idFrontImage || !idInfo.selfieImage}
              >
                {loading ? 'Submitting...' : 'Submit for Review'}
              </Button>
            </Box>
          </CardContent>
        </Card>
      )}

      {/* Level 3 - Address Proof */}
      {activeStep === 2 && (
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom fontWeight={600}>
              Level 3: Proof of Address
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
              Upload a recent utility bill, bank statement, or government document showing your address.
            </Typography>

            <Grid container spacing={2}>
              <Grid item xs={12}>
                <TextField
                  fullWidth
                  label="Street Address"
                  value={addressInfo.address}
                  onChange={(e) => setAddressInfo({ ...addressInfo, address: e.target.value })}
                  multiline
                  rows={2}
                  required
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  label="City"
                  value={addressInfo.city}
                  onChange={(e) => setAddressInfo({ ...addressInfo, city: e.target.value })}
                  required
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  label="Postal Code"
                  value={addressInfo.postalCode}
                  onChange={(e) => setAddressInfo({ ...addressInfo, postalCode: e.target.value })}
                  required
                />
              </Grid>
              <Grid item xs={12}>
                <TextField
                  fullWidth
                  label="Country"
                  value={addressInfo.country}
                  onChange={(e) => setAddressInfo({ ...addressInfo, country: e.target.value })}
                  required
                />
              </Grid>

              <Grid item xs={12}>
                <Button
                  fullWidth
                  variant="outlined"
                  component="label"
                  startIcon={<Upload />}
                  sx={{ height: 120, flexDirection: 'column' }}
                >
                  {addressInfo.proofDocument ? '✓ Document Uploaded' : 'Upload Proof of Address'}
                  <input
                    type="file"
                    hidden
                    accept="image/*,.pdf"
                    onChange={(e) => e.target.files?.[0] && handleFileUpload('proofDocument', e.target.files[0])}
                  />
                </Button>
                {addressInfo.proofDocument && (
                  <Typography variant="caption" sx={{ mt: 1, display: 'block', textAlign: 'center' }}>
                    {addressInfo.proofDocument.name}
                  </Typography>
                )}
              </Grid>

              <Grid item xs={12}>
                <Alert severity="info">
                  Accepted documents: Utility bill (electricity, water, gas), bank statement, or government-issued document.
                  Document must be dated within the last 3 months.
                </Alert>
              </Grid>
            </Grid>

            <Box sx={{ mt: 3, display: 'flex', justifyContent: 'space-between' }}>
              <Button onClick={() => setActiveStep(1)}>Back</Button>
              <Button
                variant="contained"
                size="large"
                onClick={submitLevel3}
                disabled={loading || !addressInfo.proofDocument}
              >
                {loading ? 'Submitting...' : 'Submit for Review'}
              </Button>
            </Box>
          </CardContent>
        </Card>
      )}

      {loading && <LinearProgress sx={{ mt: 2 }} />}

      {/* Benefits Section */}
      <Card sx={{ mt: 3, bgcolor: '#f5f5f5' }}>
        <CardContent>
          <Typography variant="h6" gutterBottom fontWeight={600}>
            Verification Benefits
          </Typography>
          <Grid container spacing={2}>
            <Grid item xs={12} md={4}>
              <Typography variant="subtitle2" fontWeight={600}>Level 1</Typography>
              <Typography variant="body2" color="text.secondary">• Basic trading</Typography>
              <Typography variant="body2" color="text.secondary">• $1,000 daily limit</Typography>
            </Grid>
            <Grid item xs={12} md={4}>
              <Typography variant="subtitle2" fontWeight={600}>Level 2</Typography>
              <Typography variant="body2" color="text.secondary">• $50,000 daily limit</Typography>
              <Typography variant="body2" color="text.secondary">• Withdrawals enabled</Typography>
            </Grid>
            <Grid item xs={12} md={4}>
              <Typography variant="subtitle2" fontWeight={600}>Level 3</Typography>
              <Typography variant="body2" color="text.secondary">• Unlimited trading</Typography>
              <Typography variant="body2" color="text.secondary">• Margin trading access</Typography>
            </Grid>
          </Grid>
        </CardContent>
      </Card>
    </Box>
  );
};

export default KYC;
