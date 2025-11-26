import React, { useState, useEffect, useCallback, ReactNode } from 'react';
import { authAPI } from '../services/api';
import type { User, AuthResponse } from '../types';
import { AuthContext, type AuthContextType } from './AuthContext';

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  const loadUser = useCallback(async () => {
    try {
      const response = await authAPI.getProfile();
      setUser(response.data);
    } catch (error) {
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (token) {
      void loadUser();
    } else {
      setLoading(false);
    }
  }, [loadUser]);

  const login = async (username: string, password: string): Promise<AuthResponse> => {
    const response = await authAPI.login(username, password);
    const { access, refresh } = response.data;
    localStorage.setItem('access_token', access);
    localStorage.setItem('refresh_token', refresh);
    await loadUser();
    return response.data;
  };

  const logout = (): void => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    setUser(null);
  };

  const value: AuthContextType = {
    user,
    loading,
    login,
    logout,
    loadUser,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export default AuthProvider;


