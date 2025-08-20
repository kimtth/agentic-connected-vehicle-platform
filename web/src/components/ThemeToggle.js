import React from 'react';
import { 
  Box, 
  FormControlLabel, 
  Switch, 
  Typography,
  Paper,
  useTheme
} from '@mui/material';
import { 
  LightMode as LightModeIcon, 
  DarkMode as DarkModeIcon 
} from '@mui/icons-material';

const ThemeToggle = ({ currentTheme, onToggleTheme }) => {
  const theme = useTheme();
  const isDark = currentTheme === 'dark';

  return (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
      <Paper 
        sx={{ 
          p: 2, 
          display: 'flex', 
          alignItems: 'center', 
          gap: 2,
          backgroundColor: theme.palette.mode === 'dark' 
            ? 'rgba(255,255,255,0.08)' 
            : '#f5f5f5',
          border: `1px solid ${theme.palette.mode === 'dark' 
            ? 'rgba(255,255,255,0.14)' 
            : '#e0e0e0'}`
        }}
      >
        <LightModeIcon 
          sx={{ 
            color: !isDark ? theme.palette.primary.main : theme.palette.text.secondary 
          }} 
        />
        <FormControlLabel
          control={
            <Switch
              checked={isDark}
              onChange={onToggleTheme}
              sx={{
                '& .MuiSwitch-switchBase.Mui-checked': {
                  color: theme.palette.primary.main,
                },
                '& .MuiSwitch-switchBase.Mui-checked + .MuiSwitch-track': {
                  backgroundColor: theme.palette.primary.main,
                },
              }}
            />
          }
          label=""
        />
        <DarkModeIcon 
          sx={{ 
            color: isDark ? theme.palette.primary.main : theme.palette.text.secondary 
          }} 
        />
      </Paper>
      
      <Box>
        <Typography variant="subtitle1" fontWeight="medium">
          {isDark ? 'Dark' : 'Light'} Theme
        </Typography>
        <Typography variant="body2" color="text.secondary">
          {isDark 
            ? 'Perfect for low-light environments and reduced eye strain' 
            : 'Clean and bright interface for better readability'
          }
        </Typography>
      </Box>
    </Box>
  );
};

export default ThemeToggle;
