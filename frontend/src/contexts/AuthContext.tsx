import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { getMe, UserInfo, AuthMeResponse } from '../api/auth';

interface AuthContextType {
  user: UserInfo | null;
  teams: { id: number; name: string; role: string }[];
  currentTeam: { id: number; name: string; role: string } | null;
  loading: boolean;
  setAuth: (data: { access_token: string; refresh_token: string }) => void;
  logout: () => void;
  refreshUser: () => Promise<void>;
  setCurrentTeam: (team: { id: number; name: string; role: string } | null) => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<UserInfo | null>(null);
  const [teams, setTeams] = useState<{ id: number; name: string; role: string }[]>([]);
  const [currentTeam, setCurrentTeam] = useState<{ id: number; name: string; role: string } | null>(null);
  const [loading, setLoading] = useState(true);

  const refreshUser = useCallback(async () => {
    const token = localStorage.getItem('access_token');
    if (!token) {
      setLoading(false);
      return;
    }
    try {
      const data: AuthMeResponse = await getMe();
      setUser(data.user);
      setTeams(data.teams);
      if (data.teams.length > 0 && !currentTeam) {
        setCurrentTeam(data.teams[0]);
      }
    } catch {
      localStorage.clear();
      setUser(null);
      setTeams([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshUser();
  }, [refreshUser]);

  const setAuth = (data: { access_token: string; refresh_token: string }) => {
    localStorage.setItem('access_token', data.access_token);
    localStorage.setItem('refresh_token', data.refresh_token);
    refreshUser();
  };

  const logout = () => {
    localStorage.clear();
    setUser(null);
    setTeams([]);
    setCurrentTeam(null);
  };

  return (
    <AuthContext.Provider value={{ user, teams, currentTeam, loading, setAuth, logout, refreshUser, setCurrentTeam }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
