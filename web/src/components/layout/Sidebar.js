import React from 'react';
import { NavLink } from 'react-router-dom';
import { List, ListItemButton, ListItemIcon, ListItemText, Paper } from '@mui/material';
import { 
  Dashboard,
  EmojiTransportation,
  SupportAgent,
  DirectionsCar,
  Build,
  Notifications,
  Settings,
  Security,
  Info
} from '@mui/icons-material';

const menuItems = [
  { title: 'Dashboard', icon: <Dashboard />, path: '/' },
  { title: 'Vehicle Dashboard', icon: <EmojiTransportation />, path: '/vehicle-dashboard' },
  { title: 'Agent Chat', icon: <SupportAgent />, path: '/agent-chat' },
  { title: 'Simulator', icon: <DirectionsCar />, path: '/simulator' },
  { title: 'Services', icon: <Build />, path: '/services' },
  { title: 'Notifications', icon: <Notifications />, path: '/notifications' },
  { title: 'Settings', icon: <Settings />, path: '/settings' },
  { title: 'Security', icon: <Security />, path: '/security' },
  { title: 'About', icon: <Info />, path: '/about' }
];

export default function Sidebar() {
  return (
    <Paper
      elevation={0}
      sx={{
        height: '100%',
        borderRadius: 0,
        borderRight: '1px solid rgba(255,255,255,0.14)',
        background: 'linear-gradient(180deg, rgba(255,255,255,0.04) 0%, rgba(255,255,255,0.02) 100%)',
        backdropFilter: 'blur(10px) saturate(140%)',
      }}
    >
      <List>
        {menuItems.map(item => (
          <NavLink to={item.path} key={item.title} style={{ textDecoration: 'none', color: 'inherit' }}>
            <ListItemButton>
              <ListItemIcon>{item.icon}</ListItemIcon>
              <ListItemText primary={item.title} />
            </ListItemButton>
          </NavLink>
        ))}
      </List>
    </Paper>
  );
}