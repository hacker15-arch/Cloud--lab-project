import React, { createContext, useContext, useState } from 'react';
import apiClient from '../api/client';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    const saved = localStorage.getItem('vault_user');
    if (saved) {
      try { return JSON.parse(saved); } catch (e) { return null; }
    }
    return null;
  });

  const login = async (email, password) => {
    const cleanEmail = (email || '').trim().toLowerCase();
    const response = await apiClient.post('/auth/login', {
      email: cleanEmail,
      password,
    });

    const userObj = {
      id: response.user_id,
      name: response.name,
      email: response.email,
      role: response.role,
      token: response.token,
      created_at: response.created_at,
    };

    setUser(userObj);
    localStorage.setItem('vault_user', JSON.stringify(userObj));
    return userObj;
  };

  const register = async (name, email, password) => {
    const cleanEmail = (email || '').trim().toLowerCase();
    const response = await apiClient.post('/auth/register', {
      name,
      email: cleanEmail,
      password,
    });

    const userObj = {
      id: response.user_id,
      name: response.name,
      email: response.email,
      role: response.role,
      token: response.token,
      created_at: response.created_at,
    };

    setUser(userObj);
    localStorage.setItem('vault_user', JSON.stringify(userObj));
    return userObj;
  };

  const logout = () => {
    setUser(null);
    localStorage.removeItem('vault_user');
  };

  return (
    <AuthContext.Provider value={{ user, login, register, logout, isAuthenticated: !!user }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
