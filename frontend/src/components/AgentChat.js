import React, { useState, useEffect } from 'react';
import { 
  Box, Typography, Container, Button, 
  TextField, Card, CardContent,
  Dialog, DialogTitle, DialogContent, 
  DialogActions, CircularProgress
} from '@mui/material';
import { api } from '../api/apiClient';

const AgentInteraction = ({ agentType, title, description, placeholderText }) => {
  const [query, setQuery] = useState('');
  const [response, setResponse] = useState(null);
  const [loading, setLoading] = useState(false);
  const [responseDialog, setResponseDialog] = useState(false);
  const [streamingResponse, setStreamingResponse] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [sessionId, setSessionId] = useState(null);

  // Generate a session ID if we don't have one
  useEffect(() => {
    if (!sessionId) {
      setSessionId(crypto.randomUUID ? crypto.randomUUID() : Math.random().toString(36).substring(2, 15));
    }
  }, [sessionId]);

  const handleQueryChange = (e) => {
    setQuery(e.target.value);
  };

  const submitQuery = async (useStreaming = false) => {
    if (!query.trim()) return;
    
    setLoading(true);
    
    if (useStreaming) {
      await streamResponse();
    } else {
      await normalResponse();
    }
  };

  const normalResponse = async () => {
    try {
      const response = await api.post(`/agent/${agentType}`, {
        query: query,
        context: {},
        session_id: sessionId,
        stream: false
      });
      
      setResponse(response.data);
      setResponseDialog(true);
    } catch (error) {
      console.error(`Error querying ${agentType}:`, error);
      setResponse({
        response: "Sorry, there was an error processing your request.",
        success: false
      });
      setResponseDialog(true);
    } finally {
      setLoading(false);
    }
  };

  const streamResponse = async () => {
    setIsStreaming(true);
    setStreamingResponse('');
    setResponseDialog(true);
    
    try {
      const response = await fetch(`/api/agent/${agentType}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query: query,
          context: {},
          session_id: sessionId,
          stream: true
        })
      });

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      
      let done = false;
      let fullText = '';
      
      while (!done) {
        const { value, done: readerDone } = await reader.read();
        done = readerDone;
        
        if (value) {
          const text = decoder.decode(value);
          const lines = text.split('\n');
          
          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6));
                fullText += data.response + ' ';
                setStreamingResponse(fullText);
              } catch (e) {
                console.error('Error parsing SSE data:', e);
              }
            }
          }
        }
      }
      
      setIsStreaming(false);
      setResponse({ response: fullText, success: true });
    } catch (error) {
      console.error(`Error streaming from ${agentType}:`, error);
      setResponse({
        response: "Sorry, there was an error processing your streaming request.",
        success: false
      });
      setIsStreaming(false);
    } finally {
      setLoading(false);
    }
  };

  const handleCloseDialog = () => {
    setResponseDialog(false);
    setIsStreaming(false);
  };

  return (
    <Card sx={{ mb: 3 }}>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          {title}
        </Typography>
        <Typography variant="body2" color="text.secondary" paragraph>
          {description}
        </Typography>
        
        <TextField
          fullWidth
          multiline
          rows={2}
          placeholder={placeholderText}
          variant="outlined"
          value={query}
          onChange={handleQueryChange}
          sx={{ mb: 2 }}
        />
        
        <Box sx={{ display: 'flex', gap: 2 }}>
          <Button 
            variant="contained" 
            color="primary"
            onClick={() => submitQuery(false)}
            disabled={loading || !query.trim()}
          >
            {loading && !isStreaming ? <CircularProgress size={24} /> : 'Ask Agent'}
          </Button>
          
          <Button 
            variant="outlined" 
            color="secondary"
            onClick={() => submitQuery(true)}
            disabled={loading || !query.trim()}
          >
            {loading && isStreaming ? <CircularProgress size={24} /> : 'Stream Response'}
          </Button>
        </Box>
        
        <Dialog open={responseDialog} onClose={handleCloseDialog} maxWidth="md" fullWidth>
          <DialogTitle>{title} Response</DialogTitle>
          <DialogContent dividers>
            {isStreaming ? (
              <Typography variant="body1" paragraph>
                {streamingResponse || "Waiting for response..."}
              </Typography>
            ) : response ? (
              <Typography variant="body1" paragraph>
                {response.response}
              </Typography>
            ) : (
              <CircularProgress />
            )}
            
            {!isStreaming && response && response.data && (
              <Box sx={{ mt: 2, p: 1, bgcolor: 'rgba(0,0,0,0.04)', borderRadius: 1 }}>
                <Typography variant="subtitle2" color="text.secondary">
                  Additional Data:
                </Typography>
                <pre style={{ overflow: 'auto' }}>
                  {JSON.stringify(response.data, null, 2)}
                </pre>
              </Box>
            )}
          </DialogContent>
          <DialogActions>
            <Button onClick={handleCloseDialog}>Close</Button>
          </DialogActions>
        </Dialog>
      </CardContent>
    </Card>
  );
};

const AgentChat = () => {
  return (
    <Container maxWidth="md" sx={{ my: 4 }}>
      <Typography variant="h4" component="h1" gutterBottom>
        Connected Vehicle Agent Interaction
      </Typography>
      <Typography variant="subtitle1" color="text.secondary" paragraph>
        Each component of the connected vehicle platform operates as a specialized agent.
        Ask questions or give commands to interact with the vehicle systems.
      </Typography>
      
      <AgentInteraction 
        agentType="remote-access"
        title="Remote Access"
        description="Control vehicle access and remote operations such as door locking, engine start, and syncing personal data."
        placeholderText="E.g., 'Lock all doors on my car' or 'Start the engine remotely'"
      />
      
      <AgentInteraction 
        agentType="safety-emergency"
        title="Safety & Emergency"
        description="Handle emergency-related features including collision alerts, eCalls, and theft notifications."
        placeholderText="E.g., 'What should I do in case of an accident?' or 'Report my vehicle as stolen'"
      />
      
      <AgentInteraction 
        agentType="charging-energy"
        title="Charging & Energy"
        description="Manage electric vehicle charging operations, energy usage tracking, and charging station information."
        placeholderText="E.g., 'Find nearby charging stations' or 'Start charging my vehicle'"
      />
      
      <AgentInteraction 
        agentType="information-services"
        title="Information Services"
        description="Get real-time vehicle-related information such as weather, traffic, and points of interest."
        placeholderText="E.g., 'What's the traffic like on my route?' or 'Find restaurants near me'"
      />
      
      <AgentInteraction 
        agentType="feature-control"
        title="Vehicle Feature Control"
        description="Manage in-car features like climate settings, temperature control, and service subscriptions."
        placeholderText="E.g., 'Set the temperature to 22 degrees' or 'Show my active subscriptions'"
      />
      
      <AgentInteraction 
        agentType="diagnostics-battery"
        title="Diagnostics & Battery"
        description="Oversee vehicle diagnostics, battery status, and system health reports."
        placeholderText="E.g., 'Run a diagnostic check on my car' or 'What's my battery level?'"
      />
      
      <AgentInteraction 
        agentType="alerts-notifications"
        title="Alerts & Notifications"
        description="Manage critical alerts such as speed violations, curfew breaches, and battery warnings."
        placeholderText="E.g., 'Set a speed alert for 120 km/h' or 'Show my active alerts'"
      />
    </Container>
  );
};

export default AgentChat;
