import React, { useState, useEffect, useRef } from 'react';
import { 
  Box, Typography, Button, 
  TextField, Paper, CircularProgress,
  Select, MenuItem, FormControl, InputLabel,
  List, ListItem, Divider, Tooltip, IconButton
} from '@mui/material';
import DeleteIcon from '@mui/icons-material/Delete';
import LightbulbIcon from '@mui/icons-material/Lightbulb';
import { askAgent } from '../api/agent';
import { styled } from '@mui/system';

// Define available agents with their details
const AVAILABLE_AGENTS = [
  {
    type: "remote-access",
    title: "Remote Access",
    description: "Control vehicle access and remote operations such as door locking, engine start, and syncing personal data.",
    placeholderText: "E.g., 'Lock all doors on my car' or 'Start the engine remotely'"
  },
  {
    type: "safety-emergency",
    title: "Safety & Emergency",
    description: "Handle emergency-related features including collision alerts, eCalls, and theft notifications.",
    placeholderText: "E.g., 'What should I do in case of an accident?' or 'Report my vehicle as stolen'"
  },
  {
    type: "charging-energy",
    title: "Charging & Energy",
    description: "Manage electric vehicle charging operations, energy usage tracking, and charging station information.",
    placeholderText: "E.g., 'Find nearby charging stations' or 'Start charging my vehicle'"
  },
  {
    type: "information-services",
    title: "Information Services",
    description: "Get real-time vehicle-related information such as weather, traffic, and points of interest.",
    placeholderText: "E.g., 'What's the traffic like on my route?' or 'Find restaurants near me'"
  },
  {
    type: "feature-control",
    title: "Vehicle Feature Control",
    description: "Manage in-car features like climate settings, temperature control, and service subscriptions.",
    placeholderText: "E.g., 'Set the temperature to 22 degrees' or 'Show my active subscriptions'"
  },
  {
    type: "diagnostics-battery",
    title: "Diagnostics & Battery",
    description: "Oversee vehicle diagnostics, battery status, and system health reports.",
    placeholderText: "E.g., 'Run a diagnostic check on my car' or 'What's my battery level?'"
  },
  {
    type: "alerts-notifications",
    title: "Alerts & Notifications",
    description: "Manage critical alerts such as speed violations, curfew breaches, and battery warnings.",
    placeholderText: "E.g., 'Set a speed alert for 120 km/h' or 'Show my active alerts'"
  }
];

// Generate a simple unique session ID using timestamp and a random string
const generateSessionId = () =>
  `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

const QuickActionsPanel = styled(Paper)(({ theme }) => ({
  padding: theme.spacing(2),
  marginBottom: theme.spacing(2),
  backgroundColor: theme.palette.background.default,
}));

const QuickActionButton = styled(Button)(({ theme, category }) => {
  const colors = {
    features: theme.palette.primary.main,
    remote: theme.palette.info.main,
    emergency: theme.palette.error.main,
    charging: theme.palette.success.main,
    info: theme.palette.warning.main,
    diagnostics: theme.palette.secondary.main
  };

  return {
    margin: theme.spacing(0.5),
    backgroundColor: colors[category] || theme.palette.primary.main,
    color: 'white',
    '&:hover': {
      backgroundColor: theme.palette.action.hover,
    },
  };
});

// Modified component to accept vehicleId prop
const AgentChat = ({ vehicleId }) => {
  const [selectedAgent, setSelectedAgent] = useState(AVAILABLE_AGENTS[0]);
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const [chatHistory, setChatHistory] = useState([]);
  const messagesEndRef = useRef(null);
  
  // Generate a session ID if we don't have one
  useEffect(() => {
    if (!sessionId) {
      setSessionId(generateSessionId());
    }
  }, [sessionId]);
    
  // Load chat history from localStorage when selected agent changes
  useEffect(() => {
    if (selectedAgent) {
      const storedHistory = localStorage.getItem(`chat_history_${selectedAgent.type}`);
      if (storedHistory) {
        try {
          setChatHistory(JSON.parse(storedHistory));
        } catch (e) {
          console.error('Error parsing stored chat history:', e);
          setChatHistory([]);
        }
      } else {
        setChatHistory([]);
      }
    }
  }, [selectedAgent]);
  
  // Save chat history to localStorage whenever it changes
  useEffect(() => {
    if (selectedAgent && chatHistory.length > 0) {
      localStorage.setItem(`chat_history_${selectedAgent.type}`, JSON.stringify(chatHistory));
    }
  }, [chatHistory, selectedAgent]);
  
  // Scroll to bottom of chat whenever history changes
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [chatHistory]);

  const handleAgentChange = (event) => {
    const selectedType = event.target.value;
    const agent = AVAILABLE_AGENTS.find(a => a.type === selectedType);
    setSelectedAgent(agent);
  };

  const handleQueryChange = (e) => {
    setQuery(e.target.value);
  };

  const clearChatHistory = () => {
    if (selectedAgent) {
      localStorage.removeItem(`chat_history_${selectedAgent.type}`);
      setChatHistory([]);
    }
  };
  
  const useSampleQuery = () => {
    if (selectedAgent && selectedAgent.placeholderText) {
      // Extract an example from the placeholder text by removing 'E.g., ' prefix and selecting the first example
      const placeholderText = selectedAgent.placeholderText;
      const exampleMatch = placeholderText.match(/'([^']+)'/);
      if (exampleMatch && exampleMatch[1]) {
        setQuery(exampleMatch[1]);
      } else {
        // Fallback to the whole placeholder text
        setQuery(placeholderText);
      }
    }
  };

  const submitQuery = async () => {
    if (!query.trim()) return;
    
    // Add user message to chat history
    const userMessage = {
      type: 'user',
      text: query,
      timestamp: new Date().toISOString()
    };
    setChatHistory(prev => [...prev, userMessage]);
    
    setLoading(true);
    
    try {
      // Prepare the request payload with proper structure
      const requestPayload = {
        query: query,
        context: { 
          agentType: selectedAgent.type, // Frontend agent type
          vehicleId: vehicleId, // Include vehicleId in all requests
          timestamp: new Date().toISOString()
        },
        session_id: sessionId,
        stream: false
      };

      // Log the API call in development
      if (process.env.NODE_ENV === 'development') {
        console.log('🚀 Sending agent request:', requestPayload);
      }
      
      const responseData = await askAgent(requestPayload);
      
      // Log the response in development
      if (process.env.NODE_ENV === 'development') {
        console.log('✅ Agent response received:', responseData);
      }
      
      // Add agent response to chat history
      const agentMessage = {
        type: 'agent',
        text: responseData.response || "Sorry, I couldn't process that request.",
        agentType: selectedAgent.type,
        agentTitle: selectedAgent.title,
        data: responseData.data,
        pluginsUsed: responseData.plugins_used || [],
        executionTime: responseData.execution_time || 0,
        success: responseData.success !== false,
        timestamp: new Date().toISOString()
      };
      
      setChatHistory(prev => [...prev, agentMessage]);
    } catch (error) {
      console.error(`Error querying ${selectedAgent.type}:`, error);
      
      // More detailed error handling
      let errorMessage = "Sorry, there was an error processing your request.";
      let errorDetails = null;
      
      if (error.response) {
        // Server responded with error status
        const status = error.response.status;
        const data = error.response.data;
        
        switch (status) {
          case 503:
            errorMessage = "The agent service is temporarily unavailable. Please try again in a moment.";
            break;
          case 404:
            errorMessage = "The requested agent endpoint was not found. Please check your configuration.";
            break;
          case 500:
            errorMessage = "Internal server error. Please try again later.";
            break;
          default:
            errorMessage = `Server error (${status}): ${data?.detail || data?.message || error.response.statusText}`;
        }
        
        errorDetails = {
          status: status,
          endpoint: '/agent/ask',
          agentType: selectedAgent.type,
          timestamp: new Date().toISOString()
        };
      } else if (error.request) {
        // Request was made but no response received
        errorMessage = "Unable to connect to the server. Please check your internet connection and try again.";
        errorDetails = {
          type: 'network_error',
          endpoint: '/agent/ask',
          agentType: selectedAgent.type,
          timestamp: new Date().toISOString()
        };
      } else {
        // Something else happened
        errorMessage = `Request error: ${error.message}`;
        errorDetails = {
          type: 'client_error',
          message: error.message,
          agentType: selectedAgent.type,
          timestamp: new Date().toISOString()
        };
      }
      
      // Add error response to chat history
      const errorResponseMessage = {
        type: 'error',
        text: errorMessage,
        errorDetails: errorDetails,
        timestamp: new Date().toISOString()
      };
      
      setChatHistory(prev => [...prev, errorResponseMessage]);
    } finally {
      setLoading(false);
      setQuery(''); // Clear input field after submission
    }
  };

  const handleQuickAction = (message) => {
    setQuery(message);
    submitQuery(message);
  };

  // Handle Enter key press
  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      submitQuery();
    }
  };

  const quickActions = [
    {
      category: 'features',
      title: 'Vehicle Features',
      actions: [
        { text: 'Turn on headlights', message: 'Please turn on the headlights' },
        { text: 'Set climate to 22°C', message: 'Set the climate control to 22 degrees' },
        { text: 'Roll up all windows', message: 'Please roll up all the windows' },
        { text: 'Turn on interior lights', message: 'Turn on the interior lights' }
      ]
    },
    {
      category: 'remote',
      title: 'Remote Access',
      actions: [
        { text: 'Lock doors', message: 'Lock all the doors' },
        { text: 'Start engine', message: 'Start the engine remotely' },
        { text: 'Unlock vehicle', message: 'Unlock the vehicle doors' },
        { text: 'Locate vehicle', message: 'Help me find my vehicle with horn and lights' }
      ]
    },
    {
      category: 'emergency',
      title: 'Emergency & Safety',
      actions: [
        { text: 'Emergency SOS', message: 'EMERGENCY SOS - I need immediate help' },
        { text: 'Report collision', message: 'I need to report a collision' },
        { text: 'Call emergency services', message: 'I need to call emergency services' },
        { text: 'Report theft', message: 'I need to report my vehicle as stolen' }
      ]
    },
    {
      category: 'charging',
      title: 'Charging & Energy',
      actions: [
        { text: 'Find charging stations', message: 'Find nearby charging stations' },
        { text: 'Check battery status', message: 'What is my current battery level and range?' },
        { text: 'Start charging', message: 'Start charging the vehicle' },
        { text: 'Set charging schedule', message: 'Set up a charging schedule for overnight' }
      ]
    },
    {
      category: 'info',
      title: 'Information Services',
      actions: [
        { text: 'Weather update', message: 'What is the current weather?' },
        { text: 'Traffic conditions', message: 'Check traffic conditions on my route' },
        { text: 'Find restaurants', message: 'Find restaurants near my location' },
        { text: 'Navigation help', message: 'Help me navigate to the nearest gas station' }
      ]
    },
    {
      category: 'diagnostics',
      title: 'Diagnostics & Alerts',
      actions: [
        { text: 'Vehicle diagnostics', message: 'Run a full vehicle diagnostic check' },
        { text: 'Check alerts', message: 'Show me any active alerts or warnings' },
        { text: 'Battery health', message: 'Check my vehicle battery health status' },
        { text: 'Maintenance status', message: 'When is my next scheduled maintenance?' }
      ]
    }
  ];

  return (
    <Box sx={{ 
      width: '100%', 
      height: 'calc(100vh - 120px)', 
      display: 'flex', 
      flexDirection: 'column',
      maxWidth: '1800px',
      mx: 'auto'
    }}>
      <Typography variant="h5" component="h1" gutterBottom>
        Connected Vehicle Agent Chat
        {vehicleId ? ` - Vehicle: ${vehicleId}` : ' - No vehicle selected'}
      </Typography>
      
      <Box sx={{ display: 'flex', gap: 2, alignItems: 'center', mb: 1 }}>
        <FormControl fullWidth>
          <InputLabel id="agent-select-label">Select Agent</InputLabel>
          <Select
            labelId="agent-select-label"
            id="agent-select"
            value={selectedAgent.type}
            label="Select Agent"
            onChange={handleAgentChange}
          >
            {AVAILABLE_AGENTS.map((agent) => (
              <MenuItem key={agent.type} value={agent.type}>
                {agent.title}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
        
        <Tooltip title="Clear chat history">
          <span>
            <IconButton 
              color="error" 
              onClick={clearChatHistory}
              disabled={chatHistory.length === 0}
            >
              <DeleteIcon />
            </IconButton>
          </span>
        </Tooltip>
      </Box>
      
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
        <Typography variant="body2" color="text.secondary" sx={{ flexGrow: 1 }}>
          {selectedAgent.description}
        </Typography>
        <Tooltip title="Use sample query">
          <span>
            <IconButton 
              color="primary" 
              onClick={useSampleQuery}
              disabled={loading}
            >
              <LightbulbIcon />
            </IconButton>
          </span>
        </Tooltip>
      </Box>
      
      {/* Main content area with chat on left and quick actions on right - Optimized for large screens */}
      <Box sx={{ display: 'flex', gap: 3, flexGrow: 1, minHeight: 0 }}>
        {/* Left side - Chat area */}
        <Box sx={{ flex: '1 1 65%', display: 'flex', flexDirection: 'column', minWidth: 0 }}>
          {/* Chat message display area */}
          <Paper
            elevation={3}
            sx={{
              mb: 2,
              flexGrow: 1,
              overflowY: 'auto',
              backgroundColor: '#f5f5f5',
              minHeight: { xs: 400, lg: 600, xl: 700 }
            }}
          >
            <List>
              {chatHistory.length > 0 ? (
                chatHistory.map((message, index) => (
                  <React.Fragment key={index}>
                    <ListItem alignItems="flex-start" sx={{
                      justifyContent: message.type === 'user' ? 'flex-end' : 'flex-start',
                      mb: 2,
                      px: 2
                    }}>
                      <Paper
                        elevation={1}
                        sx={{
                          maxWidth: '80%',
                          p: 2,
                          backgroundColor: message.type === 'user' ? '#e3f2fd' : 
                                          message.type === 'error' ? '#ffebee' : '#ffffff',
                          borderRadius: 2
                        }}
                      >
                        {message.type !== 'user' && (
                          <Typography variant="subtitle2" color="text.secondary" gutterBottom sx={{ mb: 1 }}>
                            {message.type === 'agent' ? message.agentTitle : 'System Message'}
                          </Typography>
                        )}
                        <Typography variant="body1" sx={{ whiteSpace: 'pre-wrap', lineHeight: 1.6 }}>
                          {message.text}
                        </Typography>
                        {message.data && (
                          <Box sx={{ mt: 2, p: 1.5, bgcolor: 'rgba(0,0,0,0.04)', borderRadius: 1 }}>
                            <Typography variant="caption" color="text.secondary" sx={{ mb: 1, display: 'block' }}>
                              Additional Data:
                            </Typography>
                            <pre style={{ fontSize: '0.75rem', overflow: 'auto', margin: 0 }}>
                              {JSON.stringify(message.data, null, 2)}
                            </pre>
                          </Box>
                        )}
                      </Paper>
                    </ListItem>
                    {index < chatHistory.length - 1 && <Divider variant="middle" component="li" sx={{ my: 1 }} />}
                  </React.Fragment>
                ))
              ) : (
                <ListItem>
                  <Typography variant="body2" color="text.secondary" align="center" sx={{ width: '100%' }}>
                    No messages yet. Start a conversation with the {selectedAgent.title} agent.
                  </Typography>
                </ListItem>
              )}
              <div ref={messagesEndRef} />
            </List>
          </Paper>
          
          {/* Input area */}
          <Box sx={{ display: 'flex', gap: 2 }}>
            <TextField
              fullWidth
              multiline
              maxRows={4}
              placeholder={selectedAgent.placeholderText}
              variant="outlined"
              value={query}
              onChange={handleQueryChange}
              onKeyDown={handleKeyPress}
              disabled={loading}
              sx={{ 
                '& .MuiOutlinedInput-root': {
                  fontSize: { xs: '14px', lg: '16px' }
                }
              }}
            />
            <Button 
              variant="contained" 
              color="primary"
              onClick={submitQuery}
              disabled={loading || !query.trim()}
              sx={{ minWidth: '120px', height: 'fit-content' }}
            >
              {loading ? <CircularProgress size={24} /> : 'Send'}
            </Button>
          </Box>
        </Box>

        {/* Right side - Quick Actions Panel - Optimized for large screens */}
        <Box sx={{ flex: '0 0 35%', minWidth: { xs: 300, lg: 400, xl: 500 } }}>
          <QuickActionsPanel sx={{ 
            height: '100%', 
            overflow: 'hidden', 
            display: 'flex', 
            flexDirection: 'column',
            p: { xs: 2, lg: 3 }
          }}>
            <Typography variant="h6" gutterBottom>
              Quick Actions
            </Typography>
            <Box sx={{ flexGrow: 1, overflowY: 'auto', pr: 1 }}>
              {quickActions.map((group) => (
                <Box key={group.category} sx={{ mb: 3 }}>
                  <Typography variant="subtitle2" gutterBottom color="text.secondary">
                    {group.title}
                  </Typography>
                  <Box sx={{ 
                    display: 'grid', 
                    gridTemplateColumns: { xs: '1fr', lg: '1fr 1fr', xl: '1fr 1fr 1fr' },
                    gap: 1 
                  }}>
                    {group.actions.map((action, index) => (
                      <QuickActionButton
                        key={index}
                        category={group.category}
                        size="small"
                        onClick={() => handleQuickAction(action.message)}
                        disabled={loading}
                        sx={{ 
                          fontSize: { xs: '0.75rem', lg: '0.8rem' },
                          p: { xs: '6px 8px', lg: '8px 12px' }
                        }}
                      >
                        {action.text}
                      </QuickActionButton>
                    ))}
                  </Box>
                </Box>
              ))}
            </Box>
          </QuickActionsPanel>
        </Box>
      </Box>
    </Box>
  );
};

export default AgentChat;
