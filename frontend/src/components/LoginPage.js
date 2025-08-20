import React, { useState, useEffect } from 'react';
import { 
  Fingerprint, 
  Security, 
  Smartphone, 
  Computer, 
  Lock,
  CheckCircle,
  ErrorOutline,
  Visibility,
  VisibilityOff
} from '@mui/icons-material';
import toast from 'react-hot-toast';
import WebAuthnClient from '../services/webauthnClient';

const LoginPage = ({ onAuthSuccess, unifiedClient }) => {
  const [webauthnClient] = useState(() => new WebAuthnClient());
  const [isLoading, setIsLoading] = useState(false);
  const [webauthnSupport, setWebauthnSupport] = useState(null);
  const [authStatus, setAuthStatus] = useState(null);
  const [isRegistering, setIsRegistering] = useState(false);
  const [username, setUsername] = useState('admin');
  const [showFallback, setShowFallback] = useState(false);
  const [apiKey, setApiKey] = useState('');

  useEffect(() => {
    const checkSupport = async () => {
      const support = await webauthnClient.checkWebAuthnSupport();
      setWebauthnSupport(support);
      
      const status = await webauthnClient.getAuthStatus();
      setAuthStatus(status);
    };
    
    checkSupport();
  }, [webauthnClient]);

  const handlePasskeyLogin = async () => {
    setIsLoading(true);
    try {
      const result = await webauthnClient.startAuthentication();
      
      if (result.success) {
        toast.success('🎉 Login successful!');
        
        // Update the unified client with the new token
        if (unifiedClient && result.token) {
          unifiedClient.apiKey = result.token;
          localStorage.setItem('pi-monitor-api-key', result.token);
        }
        
        onAuthSuccess(result);
      } else {
        toast.error(result.error || 'Authentication failed');
      }
    } catch (error) {
      toast.error(`Login failed: ${error.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  const handlePasskeyRegister = async () => {
    setIsLoading(true);
    setIsRegistering(true);
    
    try {
      const result = await webauthnClient.startRegistration(username);
      
      if (result.success) {
        toast.success('🎉 Passkey registered successfully! You can now login.');
        setIsRegistering(false);
      } else {
        toast.error(result.error || 'Registration failed');
      }
    } catch (error) {
      toast.error(`Registration failed: ${error.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  const handleFallbackLogin = async () => {
    if (!apiKey.trim()) {
      toast.error('Please enter an API key');
      return;
    }

    setIsLoading(true);
    try {
      // Use the existing unified client authentication
      if (unifiedClient) {
        const result = await unifiedClient.authenticate(apiKey);
        
        if (result.success) {
          toast.success('Login successful with API key!');
          onAuthSuccess({ success: true, fallback: true, apiKey });
        } else {
          toast.error('Invalid API key');
        }
      }
    } catch (error) {
      toast.error(`Login failed: ${error.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  const getSupportIcon = () => {
    if (!webauthnSupport?.supported) {
      return <ErrorOutline className="text-red-500" />;
    }
    if (webauthnSupport.platformAuthenticator) {
      return <CheckCircle className="text-green-500" />;
    }
    return <Security className="text-blue-500" />;
  };

  const getSupportText = () => {
    if (!webauthnSupport?.supported) {
      return 'Passkeys not supported in this browser';
    }
    if (webauthnSupport.platformAuthenticator) {
      return 'Device biometrics available (Touch ID, Face ID, Windows Hello)';
    }
    return 'Security key authentication available';
  };

  if (!webauthnSupport || !authStatus) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-gray-900 dark:to-gray-800 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600 dark:text-gray-300">Checking authentication support...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-gray-900 dark:to-gray-800 flex items-center justify-center p-4">
      <div className="max-w-md w-full space-y-8">
        {/* Header */}
        <div className="text-center">
          <div className="mx-auto h-16 w-16 bg-blue-600 rounded-full flex items-center justify-center mb-4">
            <Lock className="h-8 w-8 text-white" />
          </div>
          <h2 className="text-3xl font-bold text-gray-900 dark:text-white">
            Pi Monitor
          </h2>
          <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
            Secure authentication required
          </p>
        </div>

        {/* WebAuthn Support Status */}
        <div className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-lg">
          <div className="flex items-center space-x-3 mb-4">
            {getSupportIcon()}
            <div>
              <p className="text-sm font-medium text-gray-900 dark:text-white">
                Browser Support
              </p>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                {getSupportText()}
              </p>
            </div>
          </div>

          {/* Device Type Indicators */}
          <div className="grid grid-cols-3 gap-2 mb-6">
            <div className="text-center p-2 bg-gray-50 dark:bg-gray-700 rounded">
              <Smartphone className="h-6 w-6 mx-auto mb-1 text-blue-600" />
              <p className="text-xs text-gray-600 dark:text-gray-300">Mobile</p>
            </div>
            <div className="text-center p-2 bg-gray-50 dark:bg-gray-700 rounded">
              <Computer className="h-6 w-6 mx-auto mb-1 text-blue-600" />
              <p className="text-xs text-gray-600 dark:text-gray-300">Desktop</p>
            </div>
            <div className="text-center p-2 bg-gray-50 dark:bg-gray-700 rounded">
              <Security className="h-6 w-6 mx-auto mb-1 text-blue-600" />
              <p className="text-xs text-gray-600 dark:text-gray-300">Security Key</p>
            </div>
          </div>

          {webauthnSupport.supported && (
            <>
              {/* Username Input for Registration */}
              {isRegistering && (
                <div className="mb-4">
                  <label htmlFor="username" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Username
                  </label>
                  <input
                    type="text"
                    id="username"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
                    placeholder="Enter username"
                  />
                </div>
              )}

              {/* Login/Register Buttons */}
              <div className="space-y-3">
                {!isRegistering ? (
                  <>
                    <button
                      onClick={handlePasskeyLogin}
                      disabled={isLoading}
                      className="w-full flex items-center justify-center px-4 py-2 border border-transparent rounded-lg text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      <Fingerprint className="h-5 w-5 mr-2" />
                      {isLoading ? 'Authenticating...' : 'Login with Passkey'}
                    </button>

                    <button
                      onClick={() => setIsRegistering(true)}
                      disabled={isLoading}
                      className="w-full flex items-center justify-center px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                    >
                      Register New Passkey
                    </button>
                  </>
                ) : (
                  <>
                    <button
                      onClick={handlePasskeyRegister}
                      disabled={isLoading}
                      className="w-full flex items-center justify-center px-4 py-2 border border-transparent rounded-lg text-sm font-medium text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      <Security className="h-5 w-5 mr-2" />
                      {isLoading ? 'Registering...' : 'Create Passkey'}
                    </button>

                    <button
                      onClick={() => setIsRegistering(false)}
                      disabled={isLoading}
                      className="w-full flex items-center justify-center px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                    >
                      Back to Login
                    </button>
                  </>
                )}
              </div>
            </>
          )}

          {/* Fallback Authentication */}
          <div className="mt-6 pt-6 border-t border-gray-200 dark:border-gray-600">
            <button
              onClick={() => setShowFallback(!showFallback)}
              className="flex items-center text-sm text-blue-600 hover:text-blue-500"
            >
              {showFallback ? <VisibilityOff className="h-4 w-4 mr-1" /> : <Visibility className="h-4 w-4 mr-1" />}
              {showFallback ? 'Hide' : 'Show'} API Key Login
            </button>

            {showFallback && (
              <div className="mt-4 space-y-3">
                <input
                  type="password"
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  placeholder="Enter API Key"
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white text-sm"
                />
                <button
                  onClick={handleFallbackLogin}
                  disabled={isLoading}
                  className="w-full flex items-center justify-center px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
                >
                  Login with API Key
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Statistics */}
        {authStatus && (
          <div className="text-center text-xs text-gray-500 dark:text-gray-400">
            {authStatus.total_users > 0 && (
              <p>Registered users: {authStatus.total_users} • Active sessions: {authStatus.active_sessions || 0}</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default LoginPage;
