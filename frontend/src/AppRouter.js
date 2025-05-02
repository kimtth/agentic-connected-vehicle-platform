import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import App from './App';
import AgentChat from './components/AgentChat';
import CarSimulator from './components/CarSimulator';

const AppRouter = () => {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<App />} />
        <Route path="/agent-chat" element={<AgentChat />} />
        <Route path="/car-simulator" element={<CarSimulator />} />
      </Routes>
    </Router>
  );
};

export default AppRouter;
