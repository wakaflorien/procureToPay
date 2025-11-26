import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Button } from '@/components/ui/button';

const Navbar: React.FC = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = (): void => {
    logout();
    navigate('/login');
  };

  if (!user) {
    return null;
  }

  return (
    <nav className="bg-gray-900 text-white py-4 mb-6 shadow-md">
      <div className="container max-w-7xl mx-auto px-6 flex justify-between items-center">
        <div>
          <Link to="/" className="text-xl font-bold text-white hover:text-gray-200 transition-colors">
            Procure-to-Pay
          </Link>
        </div>
        <div className="flex gap-6 items-center">
          <span className="text-sm text-gray-300">Welcome, {user.username} ({user.role})</span>
          {user.role === 'staff' && (
            <Button asChild variant="ghost" className="text-white hover:text-gray-200 hover:bg-gray-800">
              <Link to="/requests/create">Create Request</Link>
            </Button>
          )}
          <Button onClick={handleLogout} variant="secondary" size="sm">
            Logout
          </Button>
        </div>
      </div>
    </nav>
  );
};

export default Navbar;

