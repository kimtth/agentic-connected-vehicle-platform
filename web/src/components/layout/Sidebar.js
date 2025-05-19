import React from 'react';
import { NavLink } from 'react-router-dom';
import { 
  List, ListItem, ListItemButton, ListItemIcon, ListItemText, Divider, 
  Box, Typography, Avatar, Badge, Paper
} from '@mui/material';
import { styled } from '@mui/material/styles';
import {
  Dashboard as DashboardIcon,
  DirectionsCar,
  EmojiTransportation,
  Notifications,
  Build,
  SupportAgent,
  Settings,
  Security,
  Info,
  PersonOutline
} from '@mui/icons-material';

// Styled components for enhanced sidebar
const SidebarContainer = styled(Paper)(({ theme }) => ({
  height: '100%',
  borderRadius: 0,
  backgroundColor: theme.palette.background.paper,
  boxShadow: 'none',
  border: 'none',
  borderRight: `1px solid ${theme.palette.divider}`
}));

const StyledNavLink = styled(NavLink)(({ theme }) => ({
  textDecoration: 'none',
  color: theme.palette.text.primary,
  display: 'block',
  '&.active .MuiListItem-root': {
    backgroundColor: theme.palette.action.selected,
    borderLeft: `4px solid ${theme.palette.primary.main}`,
    '& .MuiListItemIcon-root': {
      color: theme.palette.primary.main
    }
  },
  '&:not(.active) .MuiListItem-root': {
    borderLeft: '4px solid transparent',
  }
}));

const UserSection = styled(Box)(({ theme }) => ({
  padding: theme.spacing(2),
  display: 'flex',
  alignItems: 'center',
  borderBottom: `1px solid ${theme.palette.divider}`
}));

const CategoryLabel = styled(Typography)(({ theme }) => ({
  padding: theme.spacing(1, 2),
  fontSize: '0.75rem',
  color: theme.palette.text.secondary,
  textTransform: 'uppercase',
  fontWeight: 'bold',
  letterSpacing: '0.5px',
  marginTop: theme.spacing(1)
}));

const Sidebar = () => {
  // Define all menu items with icons and descriptions
  const menuItems = [
    {
      title: 'Dashboard',
      icon: <DashboardIcon />,
      path: '/',
      description: 'View vehicle status and analytics',
      category: 'main'
    },
    {
      title: 'Vehicle Dashboard',
      icon: <EmojiTransportation />,
      path: '/vehicle-dashboard',
      description: 'Control and monitor vehicle',
      category: 'main'
    },
    {
      title: 'Agent Chat',
      icon: <SupportAgent />,
      path: '/agent-chat',
      description: 'Chat with smart agent',
      category: 'main'
    },
    {
      title: 'Car Simulator',
      icon: <DirectionsCar />,
      path: '/simulator',
      description: 'Test vehicle commands and communication',
      category: 'tools'
    },
    {
      title: 'Services',
      icon: <Build />,
      path: '/services',
      description: 'View and manage services',
      category: 'tools'
    },
    {
      title: 'Notifications',
      icon: <Notifications />,
      path: '/notifications',
      description: 'View all notifications',
      badge: 3,
      category: 'tools'
    },
    {
      title: 'Settings',
      icon: <Settings />,
      path: '/settings',
      description: 'Configure application settings',
      category: 'system'
    },
    {
      title: 'Security',
      icon: <Security />,
      path: '/security',
      description: 'Manage security settings',
      category: 'system'
    },
    {
      title: 'About',
      icon: <Info />,
      path: '/about',
      description: 'View application information',
      category: 'system'
    }
  ];

  // Group menu items by category
  const mainNavItems = menuItems.filter(item => item.category === 'main');
  const toolsItems = menuItems.filter(item => item.category === 'tools');
  const systemItems = menuItems.filter(item => item.category === 'system');

  return (
    <SidebarContainer>
      <UserSection>
        <Avatar sx={{ bgcolor: 'primary.main', mr: 2 }}>U</Avatar>
        <Box>
          <Typography variant="subtitle1">User Name</Typography>
          <Typography variant="body2" color="textSecondary">Administrator</Typography>
        </Box>
      </UserSection>
      
      <List>
        {mainNavItems.map((item) => (
          <StyledNavLink to={item.path} key={item.title}>
            <ListItem disablePadding>
              <ListItemButton sx={{ py: 1.5, px: 2 }}>
                <ListItemIcon>{item.icon}</ListItemIcon>
                <ListItemText 
                  primary={item.title} 
                  secondary={item.description}
                  primaryTypographyProps={{ variant: 'subtitle2' }}
                  secondaryTypographyProps={{ variant: 'caption' }}
                />
                {item.badge && (
                  <Badge badgeContent={item.badge} color="error" />
                )}
              </ListItemButton>
            </ListItem>
          </StyledNavLink>
        ))}
      </List>
      
      <Divider />
      <CategoryLabel>Tools</CategoryLabel>
      
      <List>
        {toolsItems.map((item) => (
          <StyledNavLink to={item.path} key={item.title}>
            <ListItem disablePadding>
              <ListItemButton sx={{ py: 1, px: 2 }}>
                <ListItemIcon>{item.icon}</ListItemIcon>
                <ListItemText 
                  primary={item.title} 
                  secondary={item.description} 
                  primaryTypographyProps={{ variant: 'subtitle2' }}
                  secondaryTypographyProps={{ variant: 'caption' }}
                />
                {item.badge && (
                  <Badge badgeContent={item.badge} color="error" />
                )}
              </ListItemButton>
            </ListItem>
          </StyledNavLink>
        ))}
      </List>
      
      <Divider />
      <CategoryLabel>System</CategoryLabel>
      
      <List>
        {systemItems.map((item) => (
          <StyledNavLink to={item.path} key={item.title}>
            <ListItem disablePadding>
              <ListItemButton sx={{ py: 1, px: 2 }}>
                <ListItemIcon>{item.icon}</ListItemIcon>
                <ListItemText 
                  primary={item.title}
                  primaryTypographyProps={{ variant: 'subtitle2' }}
                />
              </ListItemButton>
            </ListItem>
          </StyledNavLink>
        ))}
      </List>
      
      <Box sx={{ mt: 'auto', p: 2, borderTop: '1px solid', borderColor: 'divider' }}>
        <StyledNavLink to="/profile">
          <ListItem disablePadding>
            <ListItemButton>
              <ListItemIcon><PersonOutline /></ListItemIcon>
              <ListItemText primary="Profile" />
            </ListItemButton>
          </ListItem>
        </StyledNavLink>
      </Box>
    </SidebarContainer>
  );
};

export default Sidebar;