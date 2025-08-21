import { useState } from 'react';
import { styled } from '@mui/material/styles';
import { 
  AppBar, Toolbar, Typography, IconButton, 
  Drawer, Box, Divider, List, ListItem, 
  ListItemIcon, ListItemText, ListItemButton,
  FormControl, InputLabel, Select, MenuItem,
  useMediaQuery, useTheme
} from '@mui/material';
import MenuIcon from '@mui/icons-material/Menu';
import DirectionsCarIcon from '@mui/icons-material/DirectionsCar';
import DashboardIcon from '@mui/icons-material/Dashboard';
import NotificationsIcon from '@mui/icons-material/Notifications';
import BuildIcon from '@mui/icons-material/Build';
import SettingsIcon from '@mui/icons-material/Settings';
import ChatIcon from '@mui/icons-material/Chat';
import DisplaySettingsIcon from '@mui/icons-material/DisplaySettings';
import { Link } from 'react-router-dom';

const drawerWidth = 240;

// AppBar styled component that shifts when drawer is open
const AppBarStyled = styled(AppBar, { shouldForwardProp: (prop) => prop !== 'open' })(
  ({ theme, open }) => ({
    transition: theme.transitions.create(['margin', 'width'], {
      easing: theme.transitions.easing.sharp,
      duration: theme.transitions.duration.leavingScreen,
    }),
    ...(open && {
      width: `calc(100% - ${drawerWidth}px)`,
      marginLeft: `${drawerWidth}px`,
      transition: theme.transitions.create(['margin', 'width'], {
        easing: theme.transitions.easing.easeOut,
        duration: theme.transitions.duration.enteringScreen,
      }),
    }),
  }),
);

// Main content area that shifts when drawer is open
const Main = styled('main', { shouldForwardProp: (prop) => prop !== 'open' })(
  ({ theme, open }) => ({
    flexGrow: 1,
    padding: theme.spacing(3),
    // Add scroll
    height: '100vh',
    overflowY: 'auto',
    WebkitOverflowScrolling: 'touch',
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

// Offset content below AppBar
const DrawerHeader = styled('div')(({ theme }) => ({
  display: 'flex',
  alignItems: 'center',
  padding: theme.spacing(0, 1),
  // necessary for content to be below app bar
  ...theme.mixins.toolbar,
  justifyContent: 'flex-end',
}));

// Rename this file to DashboardLayout.js to prevent confusion
const DashboardLayout = ({ children, vehicles = [], selectedVehicle, onVehicleChange }) => {
  const [drawerOpen, setDrawerOpen] = useState(false);
  const theme = useTheme();
  // On mobile, we want the drawer to be temporarily displayed over content instead of pushing content
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'));

  const handleDrawerToggle = () => {
    setDrawerOpen(!drawerOpen);
  };

  const handleVehicleChange = (event) => {
    const selectedId = event.target.value;
    const vehicle = vehicles.find(v => 
      (v.vehicleId === selectedId) || (v.VehicleId === selectedId)
    );
    if (vehicle) {
      // Normalize the vehicle object to use consistent field names
      const normalizedVehicle = {
        ...vehicle,
        vehicleId: vehicle.vehicleId || vehicle.VehicleId,
        VehicleId: vehicle.VehicleId || vehicle.vehicleId
      };
      onVehicleChange(normalizedVehicle);
    }
  };

  return (
    <Box sx={{ display: 'flex', height: '100vh', overflow: 'hidden' }}>
      <AppBarStyled position="fixed" open={drawerOpen && !isMobile} className="dashboard-header">
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
                value={selectedVehicle?.vehicleId || selectedVehicle?.VehicleId || ''}
                label="Vehicle"
                onChange={handleVehicleChange}
                sx={{ color: 'white', '& .MuiOutlinedInput-notchedOutline': { borderColor: 'white' } }}
              >
                {vehicles.map((vehicle) => {
                  const vehicleId = vehicle.vehicleId || vehicle.VehicleId;
                  return (
                    <MenuItem key={vehicleId} value={vehicleId}>
                      {vehicle.Brand} {vehicle.VehicleModel} ({vehicleId})
                    </MenuItem>
                  );
                })}
              </Select>
            </FormControl>
          )}
        </Toolbar>
      </AppBarStyled>
      
      <Drawer
        variant={isMobile ? "temporary" : "persistent"}
        anchor="left"
        open={drawerOpen}
        onClose={isMobile ? handleDrawerToggle : undefined}
        sx={{
          width: drawerWidth,
          flexShrink: 0,
          '& .MuiDrawer-paper': {
            width: drawerWidth,
            boxSizing: 'border-box',
          },
        }}
      >
        <DrawerHeader />
        <Box sx={{ overflow: 'auto' }}>
          <List>            
            <ListItem disablePadding>
              <ListItemButton component={Link} to="/" onClick={isMobile ? handleDrawerToggle : undefined}>
                <ListItemIcon>
                  <DashboardIcon />
                </ListItemIcon>
                <ListItemText primary="Dashboard" />
              </ListItemButton>
            </ListItem>
            <ListItem disablePadding>
              <ListItemButton component={Link} to="/car-simulator" onClick={isMobile ? handleDrawerToggle : undefined}>
                <ListItemIcon>
                  <DirectionsCarIcon />
                </ListItemIcon>
                <ListItemText primary="Car Simulator" />
              </ListItemButton>
            </ListItem>
            <ListItem disablePadding>
              <ListItemButton component={Link} to="/vehicle-dashboard" onClick={isMobile ? handleDrawerToggle : undefined}>
                <ListItemIcon>
                  <DisplaySettingsIcon />
                </ListItemIcon>
                <ListItemText primary="Vehicle Display" />
              </ListItemButton>
            </ListItem>
            <ListItem disablePadding>
              <ListItemButton component={Link} to="/services" onClick={isMobile ? handleDrawerToggle : undefined}>
                <ListItemIcon>
                  <BuildIcon />
                </ListItemIcon>
                <ListItemText primary="Services" />
              </ListItemButton>
            </ListItem>
            <ListItem disablePadding>
              <ListItemButton component={Link} to="/notifications" onClick={isMobile ? handleDrawerToggle : undefined}>
                <ListItemIcon>
                  <NotificationsIcon />
                </ListItemIcon>
                <ListItemText primary="Notifications" />
              </ListItemButton>
            </ListItem>
            <ListItem disablePadding>
              <ListItemButton component={Link} to="/agent-chat" onClick={isMobile ? handleDrawerToggle : undefined}>
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
      
      <Main open={drawerOpen && !isMobile} className="dashboard-content">
        <DrawerHeader />
        {children}
      </Main>
    </Box>
  );
};

export default DashboardLayout;
