import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from 'sonner';
import AuthProvider from './context/AuthProvider';
import { useAuth } from './context/AuthContext';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import RequestDetail from './pages/RequestDetail';
import CreateRequest from './pages/CreateRequest';
import Navbar from './components/Navbar';

interface PrivateRouteProps {
  children: React.ReactNode;
}

const PrivateRoute: React.FC<PrivateRouteProps> = ({ children }) => {
  const { user, loading } = useAuth();
  
  if (loading) {
    return <div className="container" style={{ textAlign: 'center', padding: '50px' }}>Loading...</div>;
  }
  
  return user ? <>{children}</> : <Navigate to="/login" />;
};

const AppRoutes: React.FC = () => {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        path="/"
        element={
          <PrivateRoute>
            <Dashboard />
          </PrivateRoute>
        }
      />
      <Route
        path="/requests/:id"
        element={
          <PrivateRoute>
            <RequestDetail />
          </PrivateRoute>
        }
      />
      <Route
        path="/requests/create"
        element={
          <PrivateRoute>
            <CreateRequest />
          </PrivateRoute>
        }
      />
    </Routes>
  );
};

function App() {
  return (
    <AuthProvider>
      <Router>
        <div className="App">
          <Navbar />
          <AppRoutes />
          <Toaster />
        </div>
      </Router>
    </AuthProvider>
  );
}

export default App;

