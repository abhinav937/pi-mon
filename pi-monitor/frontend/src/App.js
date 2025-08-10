import React, { useState, useEffect } from 'react';
import { QueryClient, QueryClientProvider } from 'react-query';
import { Toaster } from 'react-hot-toast';
import { AlertCircle, Wifi, WifiOff } from 'lucide-react';

import Dashboard from './components/Dashboard';
import SystemStatus from './components/SystemStatus';
import ResourceChart from './components/ResourceChart';
import PowerManagement from './components/PowerManagement';
import ServiceManagement from './components/ServiceManagement';
import { UnifiedClient } from './services/unifiedClient';

// Tailwind CSS imports
import './index.css';

// Create a QueryClient instance
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 3,
      retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
      staleTime: 30000, // 30 seconds
      cacheTime: 5 * 60 * 1000, // 5 minutes
      refetchOnWindowFocus: false,
      refetchOnReconnect: true,
    },
    mutations: {
      retry: 1,
    },
  },
});

// Navigation tabs
const TABS = [
  { id: 'dashboard', name: 'Dashboard', icon: '📊' },
  { id: 'system', name: 'System Status', icon: '💻' },
  { id: 'charts', name: 'Charts', icon: '📈' },
  { id: 'power', name: 'Power', icon: '⚡' },
  { id: 'services', name: 'Services', icon: '🔧' },
];

function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  const [connectionStatus, setConnectionStatus] = useState('connecting');
  const [unifiedClient, setUnifiedClient] = useState(null);
  const [lastUpdate, setLastUpdate] = useState(null);

  // Initialize unified client
  useEffect(() => {
    const client = new UnifiedClient({
      serverUrl: process.env.REACT_APP_SERVER_URL || 'http://localhost:5000',
      onConnectionChange: (status) => {
        setConnectionStatus(status);
      },
      onDataUpdate: (data) => {
        setLastUpdate(new Date());
        // Handle real-time data updates
        console.log('Real-time update:', data);
      },
    });

    setUnifiedClient(client);

    return () => {
      client.disconnect();
    };
  }, []);

  // Handle online/offline status
  useEffect(() => {
    const handleOnline = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  const renderActiveComponent = () => {
    switch (activeTab) {
      case 'dashboard':
        return <Dashboard unifiedClient={unifiedClient} />;
      case 'system':
        return <SystemStatus unifiedClient={unifiedClient} />;
      case 'charts':
        return <ResourceChart unifiedClient={unifiedClient} />;
      case 'power':
        return <PowerManagement unifiedClient={unifiedClient} />;
      case 'services':
        return <ServiceManagement unifiedClient={unifiedClient} />;
      default:
        return <Dashboard unifiedClient={unifiedClient} />;
    }
  };

  const getConnectionStatusColor = () => {
    switch (connectionStatus) {
      case 'connected':
        return 'text-green-500';
      case 'disconnected':
        return 'text-red-500';
      case 'connecting':
        return 'text-yellow-500';
      default:
        return 'text-gray-500';
    }
  };

  const getConnectionStatusIcon = () => {
    if (!isOnline) return <WifiOff className="h-4 w-4 text-red-500" />;
    return connectionStatus === 'connected' ? 
      <Wifi className="h-4 w-4 text-green-500" /> :
      <WifiOff className={`h-4 w-4 ${getConnectionStatusColor()}`} />;
  };

  return (
    <QueryClientProvider client={queryClient}>
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
        {/* Header */}
        <header className="bg-white dark:bg-gray-800 shadow-sm border-b border-gray-200 dark:border-gray-700">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between items-center h-16">
              {/* Logo and Title */}
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
                    🥧 Pi Monitor
                  </h1>
                </div>
              </div>

              {/* Connection Status and Info */}
              <div className="flex items-center space-x-4">
                {/* Offline Banner */}
                {!isOnline && (
                  <div className="flex items-center space-x-2 px-3 py-1 bg-red-100 text-red-800 rounded-full text-sm">
                    <AlertCircle className="h-4 w-4" />
                    <span>Offline</span>
                  </div>
                )}

                {/* Connection Status */}
                <div className="flex items-center space-x-2">
                  {getConnectionStatusIcon()}
                  <span className={`text-sm font-medium ${getConnectionStatusColor()}`}>
                    {connectionStatus.charAt(0).toUpperCase() + connectionStatus.slice(1)}
                  </span>
                </div>

                {/* Last Update */}
                {lastUpdate && (
                  <div className="text-sm text-gray-500 dark:text-gray-400">
                    Last update: {lastUpdate.toLocaleTimeString()}
                  </div>
                )}
              </div>
            </div>
          </div>
        </header>

        {/* Navigation */}
        <nav className="bg-white dark:bg-gray-800 shadow-sm">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex space-x-8">
              {TABS.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`py-4 px-1 border-b-2 font-medium text-sm transition-colors duration-200 ${
                    activeTab === tab.id
                      ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300'
                  }`}
                >
                  <span className="mr-2">{tab.icon}</span>
                  {tab.name}
                </button>
              ))}
            </div>
          </div>
        </nav>

        {/* Main Content */}
        <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
          <div className="px-4 py-6 sm:px-0">
            {renderActiveComponent()}
          </div>
        </main>

        {/* Footer */}
        <footer className="bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700 mt-auto">
          <div className="max-w-7xl mx-auto py-4 px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between items-center text-sm text-gray-500 dark:text-gray-400">
              <div>
                © 2024 Pi Monitor - Raspberry Pi Monitoring Dashboard
              </div>
              <div className="flex items-center space-x-4">
                <span>Version 1.0.0</span>
                {process.env.NODE_ENV === 'development' && (
                  <span className="px-2 py-1 bg-yellow-100 text-yellow-800 rounded text-xs">
                    DEV
                  </span>
                )}
              </div>
            </div>
          </div>
        </footer>

        {/* Toast Notifications */}
        <Toaster
          position="top-right"
          toastOptions={{
            duration: 4000,
            style: {
              background: '#374151',
              color: '#fff',
            },
            success: {
              duration: 3000,
              style: {
                background: '#10b981',
              },
            },
            error: {
              duration: 5000,
              style: {
                background: '#ef4444',
              },
            },
          }}
        />
      </div>
    </QueryClientProvider>
  );
}

export default App;