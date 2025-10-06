import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import App from './App';
import { AuthProvider } from './auth/AuthProvider';

const AppRouter = () => {
  return (
    <AuthProvider>
      <Router
        future={{
          v7_startTransition: true, // Opt-in to upcoming v7 behavior to remove warning
          v7_relativeSplatPath: true, // Opt-in to upcoming relative splat path resolution
        }}
      >
        <Routes>
          {/* Route all paths through the App component to maintain consistent layout */}
          <Route path="/*" element={<App />} />
        </Routes>
      </Router>
    </AuthProvider>
  );
};

export default AppRouter;
