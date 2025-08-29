import React, { useState, useEffect, useRef } from 'react';
import { 
  Box, Typography, Button, 
  TextField, Paper, CircularProgress,
  Select, MenuItem, FormControl, InputLabel,
  List, ListItem, Divider, Tooltip, IconButton
} from '@mui/material';
import DeleteIcon from '@mui/icons-material/Delete';
import { askAgent } from '../api/apiClient';  // Changed from '../api/agent' to '../api/apiClient'
import { styled } from '@mui/system';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

// Define available agents with their details
const AVAILABLE_AGENTS = [
  {
    type: "auto-select",
    title: "Auto-Select Agent",
    description: "Automatically choose the best agent based on your query.",
    placeholderText: "E.g., 'What is the status of my vehicle?' or 'Find nearby charging stations'"
  },
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
  backgroundColor: theme.palette.background.paper, // white surface
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

// Markdown renderer with basic styling
const MarkdownText = ({ children }) => (
  <Box sx={(theme) => ({
    '& p': { m: 0 },
    '& code': {
      bgcolor: theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.04)',
      px: 0.5, py: 0.25, borderRadius: 0.5,
      fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace',
      fontSize: '0.85em'
    },
    '& pre': {
      bgcolor: theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.04)',
      p: 1.5, borderRadius: 1, overflow: 'auto'
    },
    '& a': { color: 'primary.main' },
    '& ul, & ol': { pl: 2, my: 1 },
    '& h1, & h2, & h3': { mt: 0, mb: 1 }
  })}>
    <ReactMarkdown remarkPlugins={[remarkGfm]}>
      {children || ''}
    </ReactMarkdown>
  </Box>
);

// Modified component to accept vehicleId prop
const AgentChat = ({ vehicleId }) => {
  const [selectedAgent, setSelectedAgent] = useState(AVAILABLE_AGENTS[0]);
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const [chatHistory, setChatHistory] = useState([]);
  const [chatAreaHeight, setChatAreaHeight] = useState(0); // dynamic chat history height
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

  // Hide window scrollbar while AgentChat is mounted
  useEffect(() => {
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    
    // Add a class to hide scrollbars globally
    document.documentElement.style.overflow = 'hidden';
    
    return () => {
      document.body.style.overflow = prevOverflow;
      document.documentElement.style.overflow = '';
    };
  }, []);

  // NEW: dynamically size chat history area
  useEffect(() => {
    const OFFSET = 280; // header + agent selector + description + input area padding
    const calcHeight = () => {
      setChatAreaHeight(Math.max(320, window.innerHeight - OFFSET));
    };
    calcHeight();
    window.addEventListener('resize', calcHeight);
    return () => window.removeEventListener('resize', calcHeight);
  }, []);

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
  
  const submitQuery = async (textParam) => {
    const textToSend = (typeof textParam === 'string' ? textParam : query).trim();
    if (!textToSend) return;

    // Add user message to chat history
    const userMessage = {
      type: 'user',
      text: textToSend,
      timestamp: new Date().toISOString()
    };

    setChatHistory(prev => [...prev, userMessage]);
    
    setLoading(true);
    
    try {
      // Include last 10 messages (including this new user message) in the query so backend has recent context
      // const combinedHistory = [...chatHistory, userMessage];
      // const lastItems = combinedHistory.slice(-10);
      // const historyText = lastItems
      //   .map(m => {
      //     const who = m.type === 'user' ? 'User' : m.type === 'agent' ? `Agent(${m.agentType || selectedAgent.type})` : m.type;
      //     return `[${new Date(m.timestamp).toISOString()}] ${who}: ${m.text}`;
      //   })
      //   .join('\n');

      const requestPayload = {
        query: `${textToSend}`,
        context: {
          agentType: selectedAgent.type,
          vehicleId: vehicleId,
          timestamp: new Date().toISOString()
        },
        sessionId: sessionId,
        stream: false
      };

      // Log the API call in development
      if (process.env.NODE_ENV === 'development') {
        console.log('🚀 Sending agent request:', requestPayload);
      }
      
      const responseData = await askAgent(requestPayload);
      const agentMsg = responseData.response || "Sorry, I couldn't process that request.";
      const dataBlock = responseData.data;
      const plugins = responseData.pluginsUsed || []; // enforce camelCase only
      const execTime = responseData.executionTime || 0;
      const success = responseData.success === true;
      
      // Log the response in development
      if (process.env.NODE_ENV === 'development') {
        console.log('✅ Agent response received:', responseData);
      }
      
      // Add agent response to chat history
      const agentMessage = {
        type: 'agent',
        text: agentMsg,
        agentType: selectedAgent.type,
        agentTitle: selectedAgent.title,
        data: dataBlock,
        pluginsUsed: plugins,
        executionTime: execTime,
        success,
        timestamp: new Date().toISOString()
      };
      
      setChatHistory(prev => [...prev, agentMessage]);
    } catch (error) {
      console.error(`Error querying ${selectedAgent.type}:`, error);
      
      // More detailed error handling
      let errorMessage = "Sorry, there was an error processing your request.";
      let errorDetails = null;
      
      // Check for custom error messages from the API client
      if (error.userMessage) {
        errorMessage = error.userMessage;
        errorDetails = {
          type: error.isTimeout ? 'timeout' : error.isNetworkError ? 'network_error' : 'api_error',
          agentType: selectedAgent.type,
          timestamp: new Date().toISOString()
        };
      } else if (error.response) {
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
          case 504:
            errorMessage = "Gateway timeout - the request took too long. Please try again with a simpler query.";
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
        if (error.code === 'ECONNABORTED' && error.message.includes('timeout')) {
          errorMessage = "The request is taking longer than expected. The agent might be processing a complex operation. Please try again or simplify your request.";
          errorDetails = {
            type: 'timeout',
            endpoint: '/agent/ask',
            agentType: selectedAgent.type,
            timestamp: new Date().toISOString(),
            hint: 'Agent operations can take 10-30 seconds. Consider increasing timeout if this persists.'
          };
        } else {
          errorMessage = "Unable to connect to the server. Please ensure the backend service is running on port 8000.";
          errorDetails = {
            type: 'network_error',
            endpoint: '/agent/ask',
            agentType: selectedAgent.type,
            timestamp: new Date().toISOString(),
            hint: 'Check if the backend is running: python main.py'
          };
        }
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
      
      // Add error response to chat history with more detail
      const errorResponseMessage = {
        type: 'error',
        text: errorMessage,
        errorDetails: errorDetails,
        timestamp: new Date().toISOString()
      };
      
      setChatHistory(prev => [...prev, errorResponseMessage]);
      
      // Show hint in development mode
      if (process.env.NODE_ENV === 'development' && errorDetails?.hint) {
        console.log('💡 Hint:', errorDetails.hint);
      }
    } finally {
      setLoading(false);
      setQuery(''); // Clear input field after submission
    }
  };

  const handleQuickAction = (message) => {
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
    }
  ];

  return (
    <Box sx={{ 
      width: '100%', // full viewport width
      height: 'calc(100vh - 120px)', 
      display: 'flex', 
      flexDirection: 'column',
      mx: 'auto',
      overflow: 'hidden',
      '&::-webkit-scrollbar': { display: 'none' },
      msOverflowStyle: 'none',
      scrollbarWidth: 'none',
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
      
      <Box sx={{ display: 'flex', gap: 3, flexGrow: 1, minHeight: 0, flexDirection: { xs: 'column', md: 'row' } }}>
        {/* Left side - Chat area (responsive ~60% on md+) */}
        <Box sx={{ flex: { xs: '1 1 100%', md: '1 1 60%' }, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
          <Paper
            elevation={3}
            sx={{
              mb: 2,
              height: chatAreaHeight,
              overflowY: 'auto',
              backgroundColor: 'background.paper'
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
                        sx={(theme) => ({
                          maxWidth: '80%',
                          p: 2,
                          background: theme.palette.mode === 'dark'
                            ? (message.type === 'user'
                                ? 'linear-gradient(180deg, rgba(0,230,255,0.12), rgba(0,151,209,0.08))'
                                : message.type === 'error'
                                  ? 'linear-gradient(180deg, rgba(255,92,124,0.12), rgba(255,92,124,0.08))'
                                  : 'linear-gradient(180deg, rgba(255,255,255,0.06), rgba(255,255,255,0.03))')
                            : (message.type === 'user'
                                ? 'rgba(25,118,210,0.08)'
                                : message.type === 'error'
                                  ? 'rgba(211,47,47,0.08)'
                                  : theme.palette.background.paper),
                          border: theme.palette.mode === 'dark' ? '1px solid rgba(255,255,255,0.14)' : '1px solid #e5e7eb',
                          borderRadius: 2
                        })}
                      >
                        {message.type !== 'user' && (
                          <Typography variant="subtitle2" color="text.secondary" gutterBottom sx={{ mb: 1 }}>
                            {message.type === 'agent' ? message.agentTitle : 'System Message'}
                          </Typography>
                        )}
                        {message.type === 'agent' ? (
                          <MarkdownText>{message.text}</MarkdownText>
                        ) : (
                          <Typography variant="body1" sx={{ whiteSpace: 'pre-wrap', lineHeight: 1.6 }}>
                            {message.text}
                          </Typography>
                        )}
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
          
          <Box sx={{ display: 'flex', gap: 2 }}>
            <TextField
              fullWidth
              multiline
              maxRows={2}
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

        {/* Right side - Quick Actions Panel (responsive ~40% on md+, stacks below on xs) */}
        <Box sx={{ flex: { xs: '1 1 100%', md: '0 0 40%' }, minWidth: { xs: '100%', md: 360 } }}>
          <QuickActionsPanel sx={{ 
            height: { xs: 'auto', md: '100%' }, 
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
                    // UPDATED: cap at 2 columns max
                    gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr' },
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
