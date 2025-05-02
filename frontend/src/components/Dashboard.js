import React, { useState } from 'react';
import { styled } from '@mui/material/styles';
import { 
  AppBar, Toolbar, Typography, IconButton, 
  Drawer, Box, Divider, List, ListItem, 
  ListItemIcon, ListItemText, ListItemButton,
  FormControl, InputLabel, Select, MenuItem
} from '@mui/material';
import MenuIcon from '@mui/icons-material/Menu';
import DirectionsCarIcon from '@mui/icons-material/DirectionsCar';
import DashboardIcon from '@mui/icons-material/Dashboard';
import NotificationsIcon from '@mui/icons-material/Notifications';
import BuildIcon from '@mui/icons-material/Build';
import SettingsIcon from '@mui/icons-material/Settings';
import ChatIcon from '@mui/icons-material/Chat';
import { Link } from 'react-router-dom';

const drawerWidth = 240;

const Main = styled('main', { shouldForwardProp: (prop) => prop !== 'open' })(
  ({ theme, open }) => ({
    flexGrow: 1,
    transition: theme.transitions.create('margin', {
      easing: theme.transitions.easing.sharp,
      duration: theme.transitions.duration.leavingScreen,
    }),
    marginLeft: 0,
    ...(open && {
      transition: theme.transitions.create('margin', {
        easing: theme.transitions.easing.easeOut,
        duration: theme.transitions.duration.enteringScreen,
      }),
      marginLeft: `${drawerWidth}px`,
    }),
  }),
);

const Dashboard = ({ children, vehicles = [], selectedVehicle, onVehicleChange }) => {
  const [drawerOpen, setDrawerOpen] = useState(false);

  const handleDrawerToggle = () => {
    setDrawerOpen(!drawerOpen);
  };

  const handleVehicleChange = (event) => {
    const selectedId = event.target.value;
    const vehicle = vehicles.find(v => v.VehicleId === selectedId);
    if (vehicle) {
      onVehicleChange(vehicle);
    }
  };

  return (
    <Box sx={{ display: 'flex' }}>
      <AppBar position="fixed" className="dashboard-header">
        <Toolbar>
          <IconButton
            color="inherit"
            aria-label="open drawer"
            edge="start"
            onClick={handleDrawerToggle}
            sx={{ mr: 2 }}
          >
            <MenuIcon />
          </IconButton>
          <Typography variant="h6" component="div" className="dashboard-title">
            Agentic Connected Vehicle Platform
          </Typography>
          {vehicles.length > 0 && (
            <FormControl sx={{ minWidth: 200, mr: 1 }} size="small">
              <InputLabel id="vehicle-select-label" sx={{ color: 'white' }}>Vehicle</InputLabel>
              <Select
                labelId="vehicle-select-label"
                value={selectedVehicle?.VehicleId || ''}
                label="Vehicle"
                onChange={handleVehicleChange}
                sx={{ color: 'white', '& .MuiOutlinedInput-notchedOutline': { borderColor: 'white' } }}
              >
                {vehicles.map((vehicle) => (
                  <MenuItem key={vehicle.VehicleId} value={vehicle.VehicleId}>
                    {vehicle.Brand} {vehicle.VehicleModel} ({vehicle.VehicleId})
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          )}
        </Toolbar>
      </AppBar>
      
      <Drawer
        variant="persistent"
        anchor="left"
        open={drawerOpen}
        sx={{
          width: drawerWidth,
          flexShrink: 0,
          '& .MuiDrawer-paper': {
            width: drawerWidth,
            boxSizing: 'border-box',
          },
        }}
      >
        <Toolbar />
        <Box sx={{ overflow: 'auto' }}>
          <List>            <ListItem disablePadding>
              <ListItemButton component={Link} to="/">
                <ListItemIcon>
                  <DashboardIcon />
                </ListItemIcon>
                <ListItemText primary="Dashboard" />
              </ListItemButton>
            </ListItem>
            <ListItem disablePadding>
              <ListItemButton component={Link} to="/car-simulator">
                <ListItemIcon>
                  <DirectionsCarIcon />
                </ListItemIcon>
                <ListItemText primary="Car Simulator" />
              </ListItemButton>
            </ListItem>
            <ListItem disablePadding>
              <ListItemButton>
                <ListItemIcon>
                  <BuildIcon />
                </ListItemIcon>
                <ListItemText primary="Services" />
              </ListItemButton>
            </ListItem>
            <ListItem disablePadding>
              <ListItemButton>
                <ListItemIcon>
                  <NotificationsIcon />
                </ListItemIcon>
                <ListItemText primary="Notifications" />
              </ListItemButton>
            </ListItem>
            <ListItem disablePadding>
              <ListItemButton component={Link} to="/agent-chat">
                <ListItemIcon>
                  <ChatIcon />
                </ListItemIcon>
                <ListItemText primary="Agent Chat" />
              </ListItemButton>
            </ListItem>
          </List>
          <Divider />
          <List>
            <ListItem disablePadding>
              <ListItemButton>
                <ListItemIcon>
                  <SettingsIcon />
                </ListItemIcon>
                <ListItemText primary="Settings" />
              </ListItemButton>
            </ListItem>
          </List>
        </Box>
      </Drawer>
      
      <Main open={drawerOpen} className="dashboard-content">
        <Toolbar />
        {children}
      </Main>
    </Box>
  );
};

export default Dashboard;
