import React, { createContext, useContext, useState, useEffect } from 'react';
import { User, UserRole } from '../types';
import { api } from '../services/api';
import { indexDB } from '../db/indexdb';
import { purgeServiceWorkerCache } from '../serviceWorkerRegistration';

interface AuthContextType {
  user: User | null;
  role: UserRole | null;
  token: string | null;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (data: any) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [role, setRole] = useState<UserRole | null>(null);
  const [token, setToken] = useState<string | null>(() => localStorage.getItem('nexora_token'));

  useEffect(() => {
    if (token) {
      api.setToken(token);
      // Fetch profile
      api.request<User>('/users/me')
        .then(({ data }) => {
          setUser(data);
          setRole(data.role);
        })
        .catch(() => {
          logout();
        });
    }
  }, [token]);

  const login = async (email: string, password: string) => {
    const { data } = await api.request<any>('/auth/login', {
      method: 'POST',
      body: { email, password }
    });
    setToken(data.access_token);
    setRole(data.role);
    localStorage.setItem('nexora_token', data.access_token);
    api.setToken(data.access_token);

    // Refresh user profile
    const userRes = await api.request<User>('/users/me');
    setUser(userRes.data);
  };

  const register = async (registerData: any) => {
    await api.request('/auth/register', {
      method: 'POST',
      body: registerData
    });
    await login(registerData.email, registerData.password);
  };

  const logout = async () => {
    // RNF-21: Purge all local cache, IndexedDB, and ServiceWorker caches
    setUser(null);
    setRole(null);
    setToken(null);
    localStorage.removeItem('nexora_token');
    api.setToken(null);

    await indexDB.purgeAllLocalData();
    purgeServiceWorkerCache();
    console.log('[Auth] User logged out and local caches purged (RNF-21).');
  };

  return (
    <AuthContext.Provider value={{ user, role, token, isAuthenticated: !!token, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within AuthProvider');
  return context;
};
