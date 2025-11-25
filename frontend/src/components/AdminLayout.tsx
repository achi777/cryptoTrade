import React from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useDispatch } from 'react-redux';
import {
  AppBar,
  Box,
  Toolbar,
  Typography,
  Drawer,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Divider,
  Button,
} from '@mui/material';
import {
  Dashboard as DashboardIcon,
  People as UsersIcon,
  VerifiedUser as KYCIcon,
  AccountBalanceWallet as WalletIcon,
  TrendingUp as TradingIcon,
  Settings as SettingsIcon,
  ArrowBack as BackIcon,
} from '@mui/icons-material';

import { AppDispatch } from '../store';
import { logout } from '../store/slices/authSlice';

const drawerWidth = 240;

interface AdminLayoutProps {
  children: React.ReactNode;
}

const AdminLayout: React.FC<AdminLayoutProps> = ({ children }) => {
  const location = useLocation();
  const navigate = useNavigate();
  const dispatch = useDispatch<AppDispatch>();

  const menuItems = [
    { text: 'Dashboard', icon: <DashboardIcon />, path: '/admin' },
    { text: 'Users', icon: <UsersIcon />, path: '/admin/users' },
    { text: 'KYC', icon: <KYCIcon />, path: '/admin/kyc' },
    { text: 'Withdrawals', icon: <WalletIcon />, path: '/admin/withdrawals' },
    { text: 'Trading', icon: <TradingIcon />, path: '/admin/trading' },
    { text: 'Settings', icon: <SettingsIcon />, path: '/admin/settings' },
  ];

  return (
    <Box sx={{ display: 'flex' }}>
      <AppBar
        position="fixed"
        sx={{
          width: `calc(100% - ${drawerWidth}px)`,
          ml: `${drawerWidth}px`,
          backgroundColor: 'background.paper',
          borderBottom: '1px solid',
          borderColor: 'divider',
        }}
        elevation={0}
      >
        <Toolbar>
          <Typography variant="h6" sx={{ flexGrow: 1, color: 'error.main' }}>
            Admin Panel
          </Typography>
          <Button
            startIcon={<BackIcon />}
            onClick={() => navigate('/dashboard')}
          >
            Back to App
          </Button>
        </Toolbar>
      </AppBar>

      <Drawer
        variant="permanent"
        sx={{
          width: drawerWidth,
          flexShrink: 0,
          '& .MuiDrawer-paper': {
            width: drawerWidth,
            boxSizing: 'border-box',
            borderRight: '1px solid',
            borderColor: 'divider',
          },
        }}
      >
        <Toolbar>
          <Typography variant="h6" sx={{ fontWeight: 700, color: 'error.main' }}>
            CryptoTrade
          </Typography>
        </Toolbar>
        <Divider />
        <List>
          {menuItems.map((item) => (
            <ListItem
              button
              key={item.text}
              component={Link}
              to={item.path}
              selected={location.pathname === item.path}
              sx={{
                '&.Mui-selected': {
                  backgroundColor: 'rgba(248, 81, 73, 0.1)',
                  borderRight: '3px solid',
                  borderColor: 'error.main',
                },
              }}
            >
              <ListItemIcon sx={{ color: location.pathname === item.path ? 'error.main' : 'inherit' }}>
                {item.icon}
              </ListItemIcon>
              <ListItemText primary={item.text} />
            </ListItem>
          ))}
        </List>
      </Drawer>

      <Box
        component="main"
        sx={{
          flexGrow: 1,
          p: 3,
          width: `calc(100% - ${drawerWidth}px)`,
          mt: 8,
          minHeight: '100vh',
        }}
      >
        {children}
      </Box>
    </Box>
  );
};

export default AdminLayout;
