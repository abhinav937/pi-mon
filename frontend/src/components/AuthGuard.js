import React, { useState, useEffect } from 'react';
import { Security } from '@mui/icons-material';
import toast from 'react-hot-toast';
import WebAuthnClient from '../services/webauthnClient';

const AuthGuard = ({ children, unifiedClient }) => {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [webauthnClient] = useState(() => new WebAuthnClient());

  useEffect(() => {
    checkAuthentication();
  }, []);

  const checkAuthentication = async () => {
    setIsLoading(true);
    
    try {
      // First check if we have a WebAuthn token
      const webauthnToken = webauthnClient.getToken();
      if (webauthnToken) {
        const userInfo = await webauthnClient.getUserInfo();
        if (userInfo.success) {
          // Valid WebAuthn session
          setIsAuthenticated(true);
          // Update unified client with the token
          if (unifiedClient) {
            unifiedClient.apiKey = webauthnToken;
          }
          setIsLoading(false);
          return;
        } else if (userInfo.error === 'Authentication expired') {
          toast.error('Session expired, please login again');
        }
      }

      // Fall back to checking existing API key authentication
      const existingApiKey = localStorage.getItem('pi-monitor-api-key');
      if (existingApiKey && existingApiKey !== 'pi-monitor-api-key-2024') {
        // We have a stored API key that's not the default, assume authenticated
        setIsAuthenticated(true);
        if (unifiedClient && !unifiedClient.apiKey) {
          unifiedClient.apiKey = existingApiKey;
        }
      } else {
        setIsAuthenticated(false);
      }
    } catch (error) {
      console.error('Authentication check failed:', error);
      setIsAuthenticated(false);
    }
    
    setIsLoading(false);
  };

  const handleAuthSuccess = (authResult) => {
    setIsAuthenticated(true);
    
    if (authResult.token) {
      // WebAuthn success
      if (unifiedClient) {
        unifiedClient.apiKey = authResult.token;
        localStorage.setItem('pi-monitor-api-key', authResult.token);
      }
      toast.success(`Welcome back, ${authResult.user?.display_name || authResult.user?.username || 'User'}!`);
    } else if (authResult.apiKey) {
      // API key fallback success
      if (unifiedClient) {
        unifiedClient.apiKey = authResult.apiKey;
        localStorage.setItem('pi-monitor-api-key', authResult.apiKey);
      }
      toast.success('Authenticated successfully!');
    }
  };

  const handleLogout = async () => {
    try {
      // Logout from WebAuthn if we have a token
      if (webauthnClient.getToken()) {
        await webauthnClient.logout();
      }
      
      // Clear all authentication data
      localStorage.removeItem('pi-monitor-api-key');
      localStorage.removeItem('webauthn-token');
      
      if (unifiedClient) {
        unifiedClient.apiKey = null;
      }
      
      setIsAuthenticated(false);
      toast.success('Logged out successfully');
    } catch (error) {
      console.error('Logout failed:', error);
      toast.error('Logout failed');
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-gray-900 dark:to-gray-800 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <Security className="h-8 w-8 text-blue-600 mx-auto mb-4" />
          <p className="text-gray-600 dark:text-gray-300">Checking authentication...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    // Dynamically import LoginPage to avoid circular dependencies
    const LoginPage = React.lazy(() => import('./LoginPage'));
    
    return (
      <React.Suspense fallback={
        <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-gray-900 dark:to-gray-800 flex items-center justify-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
        </div>
      }>
        <LoginPage 
          onAuthSuccess={handleAuthSuccess}
          unifiedClient={unifiedClient}
        />
      </React.Suspense>
    );
  }

  // User is authenticated, render the protected content
  return React.cloneElement(children, { 
    onLogout: handleLogout,
    webauthnClient,
    isWebAuthnAuthenticated: !!webauthnClient.getToken()
  });
};

export default AuthGuard;
