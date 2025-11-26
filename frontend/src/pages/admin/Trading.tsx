import React, { useEffect, useState } from 'react';
import { Box, Card, CardContent, Typography, Table, TableHead, TableRow, TableCell, TableBody, Switch, CircularProgress, TextField, IconButton } from '@mui/material';
import { Edit as EditIcon, Check as CheckIcon, Close as CloseIcon } from '@mui/icons-material';
import { adminApi } from '../../services/api';
import toast from 'react-hot-toast';

const AdminTrading: React.FC = () => {
  const [pairs, setPairs] = useState<any[]>([]);
  const [loadingPairId, setLoadingPairId] = useState<number | null>(null);
  const [editingPairId, setEditingPairId] = useState<number | null>(null);
  const [editValue, setEditValue] = useState<string>('');
  const [editingFeeField, setEditingFeeField] = useState<{pairId: number, field: 'maker' | 'taker'} | null>(null);
  const [feeValue, setFeeValue] = useState<string>('');

  const loadPairs = async () => {
    try {
      const res = await adminApi.get('/trading/pairs');
      setPairs(res.data.pairs || []);
    } catch (error) {
      toast.error('Failed to load trading pairs');
    }
  };

  const togglePairStatus = async (pairId: number, currentStatus: boolean) => {
    setLoadingPairId(pairId);
    try {
      await adminApi.patch(`/trading/pairs/${pairId}`, {
        is_active: !currentStatus
      });

      // Update state locally instead of reloading all pairs
      setPairs(prevPairs =>
        prevPairs.map(p =>
          p.id === pairId ? { ...p, is_active: !currentStatus } : p
        )
      );

      toast.success('Trading pair status updated');
    } catch (error) {
      toast.error('Failed to update trading pair status');
    } finally {
      setLoadingPairId(null);
    }
  };

  const startEditing = (pairId: number, currentValue: string) => {
    setEditingPairId(pairId);
    setEditValue(currentValue);
  };

  const cancelEditing = () => {
    setEditingPairId(null);
    setEditValue('');
  };

  const saveMinOrder = async (pairId: number) => {
    setLoadingPairId(pairId);
    try {
      await adminApi.patch(`/trading/pairs/${pairId}`, {
        min_order_size: editValue
      });

      setPairs(prevPairs =>
        prevPairs.map(p =>
          p.id === pairId ? { ...p, min_order_size: editValue } : p
        )
      );

      toast.success('Min order size updated');
      setEditingPairId(null);
      setEditValue('');
    } catch (error) {
      toast.error('Failed to update min order size');
    } finally {
      setLoadingPairId(null);
    }
  };

  const startEditingFee = (pairId: number, field: 'maker' | 'taker', currentValue: string | null) => {
    setEditingFeeField({ pairId, field });
    setFeeValue(currentValue || '0.1');
  };

  const cancelEditingFee = () => {
    setEditingFeeField(null);
    setFeeValue('');
  };

  const saveFee = async (pairId: number, field: 'maker' | 'taker') => {
    setLoadingPairId(pairId);
    try {
      const payload = field === 'maker'
        ? { maker_fee: feeValue }
        : { taker_fee: feeValue };

      await adminApi.patch(`/trading/pairs/${pairId}`, payload);

      setPairs(prevPairs =>
        prevPairs.map(p =>
          p.id === pairId
            ? { ...p, [field === 'maker' ? 'maker_fee' : 'taker_fee']: feeValue }
            : p
        )
      );

      toast.success(`${field === 'maker' ? 'Maker' : 'Taker'} fee updated`);
      setEditingFeeField(null);
      setFeeValue('');
    } catch (error) {
      toast.error('Failed to update fee');
    } finally {
      setLoadingPairId(null);
    }
  };

  useEffect(() => { loadPairs(); }, []);

  return (
    <Box>
      <Typography variant="h4" gutterBottom>Trading Configuration</Typography>
      <Card>
        <CardContent>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Pair</TableCell>
                <TableCell>Min Order</TableCell>
                <TableCell>Maker Fee (%)</TableCell>
                <TableCell>Taker Fee (%)</TableCell>
                <TableCell>Active</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {pairs.map((p) => (
                <TableRow key={p.id}>
                  <TableCell>{p.symbol}</TableCell>
                  <TableCell>
                    {editingPairId === p.id ? (
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <TextField
                          size="small"
                          type="number"
                          value={editValue}
                          onChange={(e) => setEditValue(e.target.value)}
                          inputProps={{ step: '0.00000001' }}
                          sx={{ width: 150 }}
                        />
                        <IconButton
                          size="small"
                          color="primary"
                          onClick={() => saveMinOrder(p.id)}
                          disabled={loadingPairId === p.id}
                        >
                          <CheckIcon />
                        </IconButton>
                        <IconButton
                          size="small"
                          onClick={cancelEditing}
                          disabled={loadingPairId === p.id}
                        >
                          <CloseIcon />
                        </IconButton>
                      </Box>
                    ) : (
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        {p.min_order_size}
                        <IconButton
                          size="small"
                          onClick={() => startEditing(p.id, p.min_order_size)}
                        >
                          <EditIcon fontSize="small" />
                        </IconButton>
                      </Box>
                    )}
                  </TableCell>
                  <TableCell>
                    {editingFeeField?.pairId === p.id && editingFeeField?.field === 'maker' ? (
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <TextField
                          size="small"
                          type="number"
                          value={feeValue}
                          onChange={(e) => setFeeValue(e.target.value)}
                          inputProps={{ step: '0.01', min: '0' }}
                          sx={{ width: 100 }}
                        />
                        <IconButton
                          size="small"
                          color="primary"
                          onClick={() => saveFee(p.id, 'maker')}
                          disabled={loadingPairId === p.id}
                        >
                          <CheckIcon />
                        </IconButton>
                        <IconButton
                          size="small"
                          onClick={cancelEditingFee}
                          disabled={loadingPairId === p.id}
                        >
                          <CloseIcon />
                        </IconButton>
                      </Box>
                    ) : (
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        {p.maker_fee || '0.10'}
                        <IconButton
                          size="small"
                          onClick={() => startEditingFee(p.id, 'maker', p.maker_fee)}
                        >
                          <EditIcon fontSize="small" />
                        </IconButton>
                      </Box>
                    )}
                  </TableCell>
                  <TableCell>
                    {editingFeeField?.pairId === p.id && editingFeeField?.field === 'taker' ? (
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <TextField
                          size="small"
                          type="number"
                          value={feeValue}
                          onChange={(e) => setFeeValue(e.target.value)}
                          inputProps={{ step: '0.01', min: '0' }}
                          sx={{ width: 100 }}
                        />
                        <IconButton
                          size="small"
                          color="primary"
                          onClick={() => saveFee(p.id, 'taker')}
                          disabled={loadingPairId === p.id}
                        >
                          <CheckIcon />
                        </IconButton>
                        <IconButton
                          size="small"
                          onClick={cancelEditingFee}
                          disabled={loadingPairId === p.id}
                        >
                          <CloseIcon />
                        </IconButton>
                      </Box>
                    ) : (
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        {p.taker_fee || '0.20'}
                        <IconButton
                          size="small"
                          onClick={() => startEditingFee(p.id, 'taker', p.taker_fee)}
                        >
                          <EditIcon fontSize="small" />
                        </IconButton>
                      </Box>
                    )}
                  </TableCell>
                  <TableCell>
                    {loadingPairId === p.id && !editingFeeField && editingPairId !== p.id ? (
                      <CircularProgress size={24} />
                    ) : (
                      <Switch
                        checked={p.is_active}
                        onChange={() => togglePairStatus(p.id, p.is_active)}
                        disabled={editingPairId === p.id || editingFeeField !== null}
                      />
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </Box>
  );
};
export default AdminTrading;
