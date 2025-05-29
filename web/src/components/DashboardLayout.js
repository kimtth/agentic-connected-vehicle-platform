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
import SecurityIcon from '@mui/icons-material/Security';
import InfoIcon from '@mui/icons-material/Info';
import PersonOutlineIcon from '@mui/icons-material/PersonOutline';
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
    padding: 0,
    transition: theme.transitions.create('margin', {
      easing: theme.transitions.easing.sharp,
      duration: theme.transitions.duration.leavingScreen,
    }),
    marginLeft: 0,
    height: '100vh',
    overflow: 'hidden',
    display: 'flex',
    flexDirection: 'column',
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
    const vehicle = vehicles.find(v => v.VehicleId === selectedId);
    if (vehicle) {
      onVehicleChange(vehicle);
    }
  };

  // Navigation items for sidebar
  const navigationItems = [
    { path: '/', icon: <DashboardIcon />, text: 'Dashboard' },
    { path: '/simulator', icon: <DirectionsCarIcon />, text: 'Car Simulator' },
    { path: '/vehicle-dashboard', icon: <DisplaySettingsIcon />, text: 'Vehicle Display' },
    { path: '/services', icon: <BuildIcon />, text: 'Services' },
    { path: '/notifications', icon: <NotificationsIcon />, text: 'Notifications' },
    { path: '/agent-chat', icon: <ChatIcon />, text: 'Agent Chat' },
  ];

  // System items for sidebar
  const systemItems = [
    { path: '/settings', icon: <SettingsIcon />, text: 'Settings' },
    { path: '/security', icon: <SecurityIcon />, text: 'Security' },
    { path: '/about', icon: <InfoIcon />, text: 'About' },
    { path: '/profile', icon: <PersonOutlineIcon />, text: 'Profile' },
  ];

  return (
    <Box sx={{ display: 'flex' }}>
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
                value={selectedVehicle?.VehicleId || ''}
                label="Vehicle"
                onChange={handleVehicleChange}
                sx={{ color: 'white', '& .MuiOutlinedInput-notchedOutline': { borderColor: 'white' } }}
              >
                {vehicles.map((vehicle) => (
                  <MenuItem key={vehicle.VehicleId} value={vehicle.VehicleId}>
                    {vehicle.Brand || vehicle.Make} {vehicle.VehicleModel || vehicle.Model} ({vehicle.VehicleId})
                  </MenuItem>
                ))}
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
          {/* Main navigation items */}
          <List>
            {navigationItems.map((item) => (
              <ListItem key={item.path} disablePadding>
                <ListItemButton 
                  component={Link} 
                  to={item.path} 
                  onClick={isMobile ? handleDrawerToggle : undefined}
                >
                  <ListItemIcon>{item.icon}</ListItemIcon>
                  <ListItemText primary={item.text} />
                </ListItemButton>
              </ListItem>
            ))}
          </List>
          
          <Divider />
          
          {/* System items */}
          <List>
            {systemItems.map((item) => (
              <ListItem key={item.path} disablePadding>
                <ListItemButton 
                  component={Link} 
                  to={item.path} 
                  onClick={isMobile ? handleDrawerToggle : undefined}
                >
                  <ListItemIcon>{item.icon}</ListItemIcon>
                  <ListItemText primary={item.text} />
                </ListItemButton>
              </ListItem>
            ))}
          </List>
        </Box>
      </Drawer>
      
      <Main open={drawerOpen && !isMobile} className="dashboard-content">
        <DrawerHeader />
        <Box sx={{ 
          height: 'calc(100vh - 64px)', 
          overflow: 'auto', 
          display: 'flex',
          flexDirection: 'column',
          width: '100%'
        }}>
          <Box sx={{ width: '100%', maxWidth: '1400px', mx: 'auto', p: 3, flexGrow: 1 }}>
            {children}
          </Box>
        </Box>
      </Main>
    </Box>
  );
};

export default DashboardLayout;
