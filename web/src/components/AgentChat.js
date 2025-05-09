import React, { useState, useEffect, useRef } from 'react';
import { 
  Box, Typography, Container, Button, 
  TextField, Paper, CircularProgress,
  Select, MenuItem, FormControl, InputLabel,
  List, ListItem, Divider, Tooltip, IconButton
} from '@mui/material';
import DeleteIcon from '@mui/icons-material/Delete';
import LightbulbIcon from '@mui/icons-material/Lightbulb';
import { api } from '../api/apiClient';

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
      setSessionId(crypto.randomUUID ? crypto.randomUUID() : Math.random().toString(36).substring(2, 15));
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
      const response = await api.post(`/api/agent/ask`, {
        query: query,
        context: { 
          agentType: selectedAgent.type,
          vehicleId: vehicleId // Include vehicleId in all requests
        },
        session_id: sessionId,
        stream: false
      });
      
      // Add agent response to chat history
      const agentMessage = {
        type: 'agent',
        text: response.data.response || "Sorry, I couldn't process that request.",
        agentType: selectedAgent.type,
        agentTitle: selectedAgent.title,
        data: response.data.data,
        timestamp: new Date().toISOString()
      };
      
      setChatHistory(prev => [...prev, agentMessage]);
    } catch (error) {
      console.error(`Error querying ${selectedAgent.type}:`, error);
      
      // Add error response to chat history
      const errorMessage = {
        type: 'error',
        text: "Sorry, there was an error processing your request.",
        timestamp: new Date().toISOString()
      };
      
      setChatHistory(prev => [...prev, errorMessage]);
    } finally {
      setLoading(false);
      setQuery(''); // Clear input field after submission
    }
  };

  // Handle Enter key press
  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      submitQuery();
    }
  };

  return (
    <Container maxWidth="md" sx={{ my: 4, display: 'flex', flexDirection: 'column', height: 'calc(100vh - 120px)' }}>
      <Typography variant="h4" component="h1" gutterBottom>
        Connected Vehicle Agent Chat
        {vehicleId ? ` - Vehicle: ${vehicleId}` : ' - No vehicle selected'}
      </Typography>
      
      <Box sx={{ display: 'flex', gap: 2, alignItems: 'center', mb: 2 }}>
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
          <IconButton 
            color="error" 
            onClick={clearChatHistory}
            disabled={chatHistory.length === 0}
          >
            <DeleteIcon />
          </IconButton>
        </Tooltip>
      </Box>
      
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
        <Typography variant="body2" color="text.secondary" sx={{ flexGrow: 1 }}>
          {selectedAgent.description}
        </Typography>
        <Tooltip title="Use sample query">
          <IconButton 
            color="primary" 
            onClick={useSampleQuery}
            disabled={loading}
          >
            <LightbulbIcon />
          </IconButton>
        </Tooltip>
      </Box>
      
      {/* Chat message display area */}
      <Paper
        elevation={3}
        sx={{
          p: 2,
          mb: 2,
          flexGrow: 1,
          overflowY: 'auto',
          backgroundColor: '#f5f5f5',
          maxHeight: 'calc(100vh - 350px)'
        }}
      >
        <List>
          {chatHistory.length > 0 ? (
            chatHistory.map((message, index) => (
              <React.Fragment key={index}>
                <ListItem alignItems="flex-start" sx={{
                  justifyContent: message.type === 'user' ? 'flex-end' : 'flex-start',
                  mb: 1
                }}>
                  <Paper
                    elevation={1}
                    sx={{
                      p: 2,
                      maxWidth: '80%',
                      backgroundColor: message.type === 'user' ? '#e3f2fd' : 
                                      message.type === 'error' ? '#ffebee' : '#ffffff',
                      borderRadius: 2
                    }}
                  >
                    {message.type !== 'user' && (
                      <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                        {message.type === 'agent' ? message.agentTitle : 'System Message'}
                      </Typography>
                    )}
                    <Typography variant="body1" sx={{ whiteSpace: 'pre-wrap' }}>
                      {message.text}
                    </Typography>
                    {message.data && (
                      <Box sx={{ mt: 1, p: 1, bgcolor: 'rgba(0,0,0,0.04)', borderRadius: 1 }}>
                        <Typography variant="caption" color="text.secondary">
                          Additional Data:
                        </Typography>
                        <pre style={{ fontSize: '0.75rem', overflow: 'auto' }}>
                          {JSON.stringify(message.data, null, 2)}
                        </pre>
                      </Box>
                    )}
                  </Paper>
                </ListItem>
                {index < chatHistory.length - 1 && <Divider variant="middle" component="li" />}
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
      <Box sx={{ display: 'flex', gap: 1 }}>
        <TextField
          fullWidth
          multiline
          maxRows={3}
          placeholder={selectedAgent.placeholderText}
          variant="outlined"
          value={query}
          onChange={handleQueryChange}
          onKeyPress={handleKeyPress}
          disabled={loading}
        />
        <Button 
          variant="contained" 
          color="primary"
          onClick={submitQuery}
          disabled={loading || !query.trim()}
          sx={{ minWidth: '100px' }}
        >
          {loading ? <CircularProgress size={24} /> : 'Send'}
        </Button>
      </Box>
    </Container>
  );
};

export default AgentChat;
