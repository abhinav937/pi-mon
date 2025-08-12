import React, { useState, useEffect, Suspense, lazy } from 'react';
import { QueryClient, QueryClientProvider } from 'react-query';
import { Toaster } from 'react-hot-toast';
import { AlertCircle, Wifi, WifiOff, Sun, Moon, Settings, RefreshCw, Menu, X } from 'lucide-react';

import { UnifiedClient } from './services/unifiedClient';
import ErrorBoundary from './components/ErrorBoundary';
import LoadingSpinner from './components/LoadingSpinner';
import ConnectionStatus from './components/ConnectionStatus';

// Tailwind CSS imports
import './index.css';
import 'material-symbols/outlined.css';

// Lazy load components for better performance
const Dashboard = lazy(() => import('./components/Dashboard'));
const SystemStatus = lazy(() => import('./components/SystemStatus'));
const ResourceChart = lazy(() => import('./components/ResourceChart'));
const PowerManagement = lazy(() => import('./components/PowerManagement'));
const ServiceManagement = lazy(() => import('./components/ServiceManagement'));
const NetworkMonitor = lazy(() => import('./components/NetworkMonitor'));
const LogViewer = lazy(() => import('./components/LogViewer'));
const SettingsPanel = lazy(() => import('./components/SettingsPanel'));

// Create a QueryClient instance with better error handling
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: (failureCount, error) => {
        // Don't retry on 4xx errors
        if (error?.response?.status >= 400 && error?.response?.status < 500) {
          return false;
        }
        return Math.min(failureCount, 3);
      },
      retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
      staleTime: 30000, // 30 seconds
      cacheTime: 5 * 60 * 1000, // 5 minutes
      refetchOnWindowFocus: false,
      refetchOnReconnect: true,
      refetchOnMount: true,
    },
    mutations: {
      retry: 1,
      onError: (error) => {
        console.error('Mutation error:', error);
      },
    },
  },
});

// Enhanced navigation tabs with more features
const TABS = [
  { id: 'dashboard', name: 'Dashboard', icon: 'dashboard', description: 'System overview and key metrics' },
  { id: 'system', name: 'System Status', icon: 'computer', description: 'Detailed system information' },
  { id: 'charts', name: 'Charts', icon: 'show_chart', description: 'Performance graphs and trends' },
  { id: 'power', name: 'Power', icon: 'bolt', description: 'Power management and monitoring' },
  { id: 'services', name: 'Services', icon: 'build', description: 'System service management' },
  { id: 'network', name: 'Network', icon: 'public', description: 'Network monitoring and diagnostics' },
  { id: 'logs', name: 'Logs', icon: 'description', description: 'System and application logs' },
  { id: 'settings', name: 'Settings', icon: 'settings', description: 'Configuration and preferences' },
];

function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  const [connectionStatus, setConnectionStatus] = useState('connecting');
  const [unifiedClient, setUnifiedClient] = useState(null);
  const [lastUpdate, setLastUpdate] = useState(null);
  const [isDarkMode, setIsDarkMode] = useState(() => {
    const saved = localStorage.getItem('darkMode');
    return saved ? JSON.parse(saved) : window.matchMedia('(prefers-color-scheme: dark)').matches;
  });
  const [showSettings, setShowSettings] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  // Initialize unified client with better error handling
  useEffect(() => {
    const client = new UnifiedClient({
      serverUrl: process.env.REACT_APP_SERVER_URL === 'dynamic' 
        ? `http://${window.location.hostname}:5001` 
        : (process.env.REACT_APP_SERVER_URL || `http://${window.location.hostname}:5001`),
      onConnectionChange: (status) => {
        setConnectionStatus(status);
        if (status === 'connected') {
          setLastUpdate(new Date());
        }
      },
      onDataUpdate: (data) => {
        setLastUpdate(new Date());
        console.log('Real-time update:', data);
      },
      onError: (error) => {
        console.error('Client error:', error);
        setConnectionStatus('error');
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

  // Handle dark mode toggle
  useEffect(() => {
    localStorage.setItem('darkMode', JSON.stringify(isDarkMode));
    document.documentElement.classList.toggle('dark', !!isDarkMode);
  }, [isDarkMode]);

  // Handle refresh
  const handleRefresh = async () => {
    setIsRefreshing(true);
    try {
      if (unifiedClient) {
        await unifiedClient.refresh();
      }
      // Force refetch all queries
      queryClient.invalidateQueries();
    } catch (error) {
      console.error('Refresh failed:', error);
    } finally {
      setIsRefreshing(false);
    }
  };

  // Handle mobile menu toggle
  const toggleMobileMenu = () => {
    setIsMobileMenuOpen(!isMobileMenuOpen);
  };

  // Close mobile menu when tab changes
  const handleTabChange = (tabId) => {
    setActiveTab(tabId);
    setIsMobileMenuOpen(false);
  };

  const renderActiveComponent = () => {
    const props = { unifiedClient, isDarkMode };
    
    switch (activeTab) {
      case 'dashboard':
        return <Dashboard {...props} />;
      case 'system':
        return <SystemStatus {...props} />;
      case 'charts':
        return <ResourceChart {...props} />;
      case 'power':
        return <PowerManagement {...props} />;
      case 'services':
        return <ServiceManagement {...props} />;
      case 'network':
        return <NetworkMonitor {...props} />;
      case 'logs':
        return <LogViewer {...props} />;
      case 'settings':
        return <SettingsPanel {...props} />;
      default:
        return <Dashboard {...props} />;
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
      case 'error':
        return 'text-red-600';
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
      <div className={`min-h-screen transition-colors duration-200 ${
        isDarkMode ? 'dark bg-gray-900' : 'bg-gray-50'
      }`}>
        {/* Header */}
        <header className="bg-white dark:bg-gray-800 shadow-sm border-b border-gray-200 dark:border-gray-700">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between items-center h-16">
              {/* Logo and Title */}
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <h1 className="text-xl sm:text-2xl font-bold text-gray-900 dark:text-white">
                    Pi Monitor
                  </h1>
                </div>
              </div>

              {/* Desktop Controls */}
              <div className="hidden md:flex items-center space-x-4">
                {/* Offline Banner */}
                {!isOnline && (
                  <div className="flex items-center space-x-2 px-3 py-1 bg-red-100 dark:bg-red-900 text-red-800 dark:text-red-200 rounded-full text-sm">
                    <AlertCircle className="h-4 w-4" />
                    <span>Offline</span>
                  </div>
                )}

                {/* Connection Status */}
                <ConnectionStatus 
                  status={connectionStatus}
                  isOnline={isOnline}
                  lastUpdate={lastUpdate}
                />

                {/* Refresh Button */}
                <button
                  onClick={handleRefresh}
                  disabled={isRefreshing}
                  className="p-2 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 rounded-md hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors duration-200"
                  title="Refresh data"
                >
                  <RefreshCw className={`h-4 w-4 ${isRefreshing ? 'animate-spin' : ''}`} />
                </button>

                {/* Theme Toggle */}
                <button
                  onClick={() => setIsDarkMode(!isDarkMode)}
                  className="p-2 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 rounded-md hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors duration-200"
                  title={`Switch to ${isDarkMode ? 'light' : 'dark'} mode`}
                >
                  {isDarkMode ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
                </button>

                {/* Settings Button */}
                <button
                  onClick={() => setShowSettings(!showSettings)}
                  className="p-2 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 rounded-md hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors duration-200"
                  title="Settings"
                >
                  <Settings className="h-4 w-4" />
                </button>
              </div>

              {/* Mobile Menu Button */}
              <div className="md:hidden flex items-center space-x-2">
                {/* Mobile Connection Status */}
                <ConnectionStatus 
                  status={connectionStatus}
                  isOnline={isOnline}
                  lastUpdate={lastUpdate}
                  isMobile={true}
                />

                {/* Mobile Menu Toggle */}
                <button
                  onClick={toggleMobileMenu}
                  className="p-2 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 rounded-md hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors duration-200"
                  title="Toggle menu"
                >
                  {isMobileMenuOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
                </button>
              </div>
            </div>
          </div>
        </header>

        {/* Mobile Menu Overlay */}
        {isMobileMenuOpen && (
          <div className="md:hidden fixed inset-0 z-50 bg-black bg-opacity-50">
            <div className="fixed inset-y-0 right-0 max-w-xs w-full bg-white dark:bg-gray-800 shadow-xl">
              <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Menu</h2>
                <button
                  onClick={toggleMobileMenu}
                  className="p-2 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 rounded-md"
                >
                  <X className="h-6 w-6" />
                </button>
              </div>
              
              {/* Mobile Navigation */}
              <nav className="p-4 space-y-2">
                {TABS.map((tab) => (
                  <button
                    key={tab.id}
                    onClick={() => handleTabChange(tab.id)}
                    className={`w-full text-left p-3 rounded-lg transition-colors duration-200 ${
                      activeTab === tab.id
                        ? 'bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300'
                        : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
                    }`}
                  >
                    <div className="flex items-center space-x-3">
                      <span className="material-symbols-outlined text-2xl">{tab.icon}</span>
                      <div>
                        <div className="font-medium">{tab.name}</div>
                        <div className="text-sm text-gray-500 dark:text-gray-400">{tab.description}</div>
                      </div>
                    </div>
                  </button>
                ))}
              </nav>

              {/* Mobile Controls */}
              <div className="p-4 border-t border-gray-200 dark:border-gray-700 space-y-3">
                {/* Offline Banner */}
                {!isOnline && (
                  <div className="flex items-center space-x-2 px-3 py-2 bg-red-100 dark:bg-red-900 text-red-800 dark:text-red-200 rounded-lg text-sm">
                    <AlertCircle className="h-4 w-4" />
                    <span>Offline</span>
                  </div>
                )}

                {/* Refresh Button */}
                <button
                  onClick={() => {
                    handleRefresh();
                    setIsMobileMenuOpen(false);
                  }}
                  disabled={isRefreshing}
                  className="w-full flex items-center justify-center space-x-2 p-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors duration-200 disabled:opacity-50"
                >
                  <RefreshCw className={`h-4 w-4 ${isRefreshing ? 'animate-spin' : ''}`} />
                  <span>Refresh Data</span>
                </button>

                {/* Theme Toggle */}
                <button
                  onClick={() => setIsDarkMode(!isDarkMode)}
                  className="w-full flex items-center justify-center space-x-2 p-3 bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 rounded-lg transition-colors duration-200"
                >
                  {isDarkMode ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
                  <span>Switch to {isDarkMode ? 'Light' : 'Dark'} Mode</span>
                </button>

                {/* Settings Button */}
                <button
                  onClick={() => {
                    setShowSettings(!showSettings);
                    setIsMobileMenuOpen(false);
                  }}
                  className="w-full flex items-center justify-center space-x-2 p-3 bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 rounded-lg transition-colors duration-200"
                >
                  <Settings className="h-4 w-4" />
                  <span>Settings</span>
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Desktop Navigation */}
        <nav className="hidden md:block bg-white dark:bg-gray-800 shadow-sm border-b border-gray-200 dark:border-gray-700">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex space-x-8 overflow-x-auto">
              {TABS.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`py-4 px-1 border-b-2 font-medium text-sm transition-colors duration-200 whitespace-nowrap ${
                    activeTab === tab.id
                      ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300'
                  }`}
                  title={tab.description}
                >
                  <span className="material-symbols-outlined text-xl mr-2">{tab.icon}</span>
                  {tab.name}
                </button>
              ))}
            </div>
          </div>
        </nav>

        {/* Main Content */}
        <main className="max-w-7xl mx-auto py-4 sm:py-6 px-4 sm:px-6 lg:px-8">
          <div className="py-4 sm:py-6">
            <ErrorBoundary>
              <Suspense fallback={<LoadingSpinner />}>
                {renderActiveComponent()}
              </Suspense>
            </ErrorBoundary>
          </div>
        </main>

        {/* Settings Panel */}
        {showSettings && (
          <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
            <div className="bg-white dark:bg-gray-800 rounded-lg p-4 sm:p-6 max-w-md w-full max-h-[90vh] overflow-y-auto">
              <Suspense fallback={<LoadingSpinner />}>
                <SettingsPanel 
                  isDarkMode={isDarkMode}
                  setIsDarkMode={setIsDarkMode}
                  onClose={() => setShowSettings(false)}
                />
              </Suspense>
            </div>
          </div>
        )}

        {/* Footer */}
        <footer className="bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700 mt-auto">
          <div className="max-w-7xl mx-auto py-4 px-4 sm:px-6 lg:px-8">
            <div className="flex flex-col sm:flex-row justify-between items-center space-y-2 sm:space-y-0 text-sm text-gray-500 dark:text-gray-400">
              <div className="text-center sm:text-left">
                © 2024 Pi Monitor - Raspberry Pi Monitoring Dashboard
              </div>
              <div className="flex items-center space-x-4">
                <span>Version 2.0.0</span>
                {process.env.NODE_ENV === 'development' && (
                  <span className="px-2 py-1 bg-yellow-100 dark:bg-yellow-900 text-yellow-800 dark:text-yellow-200 rounded text-xs">
                    DEV
                  </span>
                )}
              </div>
            </div>
          </div>
        </footer>

        {/* Toast Notifications */}
        <Toaster
          position="top-center"
          toastOptions={{
            duration: 4000,
            style: {
              background: isDarkMode ? '#374151' : '#fff',
              color: isDarkMode ? '#fff' : '#374151',
              border: isDarkMode ? '1px solid #4b5563' : '1px solid #e5e7eb',
              maxWidth: '90vw',
              fontSize: '14px',
            },
            success: {
              duration: 3000,
              style: {
                background: '#10b981',
                color: '#fff',
              },
            },
            error: {
              duration: 5000,
              style: {
                background: '#ef4444',
                color: '#fff',
              },
            },
          }}
        />
      </div>
    </QueryClientProvider>
  );
}

export default App;
