import React, { useEffect, useState } from 'react';
import { Box, Card, CardContent, Typography, Table, TableHead, TableRow, TableCell, TableBody, Button, Chip } from '@mui/material';
import { adminApi } from '../../services/api';
import toast from 'react-hot-toast';

const AdminKYC: React.FC = () => {
  const [requests, setRequests] = useState<any[]>([]);
  useEffect(() => {
    adminApi.get('/kyc/requests/pending')
      .then((res) => setRequests(res.data.requests || []))
      .catch((err) => {
        console.error('Failed to load KYC requests:', err);
        toast.error(err.response?.data?.error || 'Failed to load KYC requests');
      });
  }, []);
  const handleAction = async (id: number, action: string) => {
    try {
      await adminApi.post(`/kyc/requests/${id}/${action}`, action === 'reject' ? { reason: 'Document unclear' } : {});
      setRequests(requests.filter((r) => r.id !== id));
      toast.success(`KYC ${action}d`);
    } catch (err: any) {
      toast.error(err.response?.data?.error || `Failed to ${action} KYC request`);
    }
  };
  return (
    <Box>
      <Typography variant="h4" gutterBottom>KYC Management</Typography>
      <Card><CardContent>
        <Table><TableHead><TableRow><TableCell>User</TableCell><TableCell>Level</TableCell><TableCell>Status</TableCell><TableCell>Actions</TableCell></TableRow></TableHead>
          <TableBody>{requests.map((r) => (<TableRow key={r.id}><TableCell>{r.user_id}</TableCell><TableCell>{r.level}</TableCell><TableCell><Chip label={r.status} size="small" /></TableCell><TableCell><Button size="small" color="success" onClick={() => handleAction(r.id, 'approve')}>Approve</Button><Button size="small" color="error" onClick={() => handleAction(r.id, 'reject')}>Reject</Button></TableCell></TableRow>))}</TableBody>
        </Table>
      </CardContent></Card>
    </Box>
  );
};
export default AdminKYC;
