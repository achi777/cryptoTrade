import React, { useEffect, useState } from 'react';
import { Box, Card, CardContent, Typography, Table, TableHead, TableRow, TableCell, TableBody, Switch } from '@mui/material';
import { adminApi } from '../../services/api';

const AdminTrading: React.FC = () => {
  const [pairs, setPairs] = useState<any[]>([]);
  useEffect(() => { adminApi.get('/trading/pairs').then((res) => setPairs(res.data.pairs || [])); }, []);
  return (
    <Box>
      <Typography variant="h4" gutterBottom>Trading Configuration</Typography>
      <Card><CardContent>
        <Table><TableHead><TableRow><TableCell>Pair</TableCell><TableCell>Min Order</TableCell><TableCell>Active</TableCell></TableRow></TableHead>
          <TableBody>{pairs.map((p) => (<TableRow key={p.id}><TableCell>{p.symbol}</TableCell><TableCell>{p.min_order_size}</TableCell><TableCell><Switch checked={p.is_active} /></TableCell></TableRow>))}</TableBody>
        </Table>
      </CardContent></Card>
    </Box>
  );
};
export default AdminTrading;
