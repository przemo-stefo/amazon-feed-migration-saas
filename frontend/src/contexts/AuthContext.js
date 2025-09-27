import React, { createContext, useContext, useState, useEffect } from 'react';
import axios from 'axios';
import { toast } from 'react-toastify';

const AuthContext = createContext();

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [isLoading, setIsLoading] = useState(true);

  // Konfiguracja axios interceptors
  useEffect(() => {
    // Request interceptor - dodawanie tokenu do każdego zapytania
    const requestInterceptor = axios.interceptors.request.use(
      (config) => {
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => {
        return Promise.reject(error);
      }
    );

    // Response interceptor - obsługa błędów autoryzacji
    const responseInterceptor = axios.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response?.status === 401) {
          logout();
          toast.error('Sesja wygasła. Zaloguj się ponownie.');
        }
        return Promise.reject(error);
      }
    );

    return () => {
      axios.interceptors.request.eject(requestInterceptor);
      axios.interceptors.response.eject(responseInterceptor);
    };
  }, [token]);

  // Sprawdzenie ważności tokenu przy załadowaniu aplikacji
  useEffect(() => {
    const initializeAuth = async () => {
      if (token) {
        try {
          const response = await axios.get('/api/auth/me');
          setUser(response.data);
        } catch (error) {
          // Token jest nieważny
          localStorage.removeItem('token');
          setToken(null);
        }
      }
      setIsLoading(false);
    };

    initializeAuth();
  }, [token]);

  const login = async (email, password) => {
    try {
      const response = await axios.post('/api/auth/login', {
        username: email, // Endpoint może oczekiwać username zamiast email
        password,
      });

      const { access_token, user: userData } = response.data;

      setToken(access_token);
      setUser(userData);
      localStorage.setItem('token', access_token);

      toast.success('Zalogowano pomyślnie!');
      return { success: true };
    } catch (error) {
      const message = error.response?.data?.detail || 'Błąd logowania';
      toast.error(message);
      return { success: false, error: message };
    }
  };

  const register = async (userData) => {
    try {
      const response = await axios.post('/api/auth/register', userData);

      toast.success('Konto zostało utworzone! Możesz się teraz zalogować.');
      return { success: true };
    } catch (error) {
      const message = error.response?.data?.detail || 'Błąd rejestracji';
      toast.error(message);
      return { success: false, error: message };
    }
  };

  const logout = () => {
    setUser(null);
    setToken(null);
    localStorage.removeItem('token');
    toast.info('Wylogowano pomyślnie');
  };

  const updateProfile = async (profileData) => {
    try {
      const response = await axios.put('/api/users/profile', profileData);
      setUser(response.data);
      toast.success('Profil zaktualizowany pomyślnie!');
      return { success: true };
    } catch (error) {
      const message = error.response?.data?.detail || 'Błąd aktualizacji profilu';
      toast.error(message);
      return { success: false, error: message };
    }
  };

  const value = {
    user,
    token,
    isAuthenticated: !!user,
    isLoading,
    login,
    register,
    logout,
    updateProfile,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}