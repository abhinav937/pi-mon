/* eslint-disable no-console */
import React, { useState, useEffect, Suspense, lazy } from 'react';
import { QueryClient, QueryClientProvider } from 'react-query';
import { Toaster } from 'react-hot-toast';
import { ErrorOutline as AlertCircle, Wifi, WifiOff, LightMode as Sun, DarkMode as Moon, Settings, Refresh as RefreshCw, Menu, Close as X, Dashboard as LayoutDashboard, BarChart, Bolt as Zap, Build as Wrench, Public as Globe, Article as FileText, Logout } from '@mui/icons-material';

import { UnifiedClient } from './services/unifiedClient';
import ErrorBoundary from './components/ErrorBoundary';
import LoadingSpinner from './components/LoadingSpinner';
import ConnectionStatus from './components/ConnectionStatus';
import AuthGuard from './components/AuthGuard';

// Tailwind CSS imports
import './index.css';

// Lazy load components for better performance
const Dashboard = lazy(() => import('./components/Dashboard'));
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
  { id: 'dashboard', name: 'Dashboard', icon: LayoutDashboard, description: 'System overview and key metrics' },
  { id: 'charts', name: 'Charts', icon: BarChart, description: 'Performance graphs and trends' },
  { id: 'power', name: 'Power', icon: Zap, description: 'Power management and monitoring' },
  { id: 'services', name: 'Services', icon: Wrench, description: 'System service management' },
  { id: 'network', name: 'Network', icon: Globe, description: 'Network monitoring and diagnostics' },
  { id: 'logs', name: 'Logs', icon: FileText, description: 'System and application logs' },
  { id: 'settings', name: 'Settings', icon: Settings, description: 'Configuration and preferences' },
];

function App({ onLogout, isWebAuthnAuthenticated }) {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  const [connectionStatus, setConnectionStatus] = useState('connecting');
  const [unifiedClient, setUnifiedClient] = useState(null);
  const [lastUpdate, setLastUpdate] = useState(null);
  const [backendInfo, setBackendInfo] = useState(null);
  const [isDarkMode, setIsDarkMode] = useState(() => {
    const saved = localStorage.getItem('darkMode');
    return saved ? JSON.parse(saved) : window.matchMedia('(prefers-color-scheme: dark)').matches;
  });
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [frontendVersion, setFrontendVersion] = useState(process.env.REACT_APP_VERSION || '2.0.0');

  // Initialize unified client with better error handling
  useEffect(() => {
    const client = new UnifiedClient({
      // Prefer same-origin so protocol/port match the page (avoids mixed content over HTTPS)
      serverUrl: process.env.REACT_APP_SERVER_URL === 'dynamic'
        ? `${window.location.protocol}//${window.location.host}`
        : (process.env.REACT_APP_SERVER_URL || `${window.location.protocol}//${window.location.host}`),
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

  // Apply accent color from settings on load and when it changes
  useEffect(() => {
    try {
      const applyAccent = () => {
        const savedRaw = localStorage.getItem('pi-monitor-settings');
        const saved = savedRaw ? JSON.parse(savedRaw) : {};
        const accent = saved.accentColor || 'blue';
        const palettes = {
          blue: ['#eff6ff','#dbeafe','#bfdbfe','#93c5fd','#60a5fa','#3b82f6','#2563eb','#1d4ed8','#1e40af','#1e3a8a'],
          green: ['#ecfdf5','#d1fae5','#a7f3d0','#6ee7b7','#34d399','#10b981','#059669','#047857','#065f46','#064e3b'],
          purple: ['#f5f3ff','#ede9fe','#ddd6fe','#c4b5fd','#a78bfa','#8b5cf6','#7c3aed','#6d28d9','#5b21b6','#4c1d95'],
          red: ['#fef2f2','#fee2e2','#fecaca','#fca5a5','#f87171','#ef4444','#dc2626','#b91c1c','#991b1b','#7f1d1d'],
          yellow: ['#fffbeb','#fef3c7','#fde68a','#fcd34d','#fbbf24','#f59e0b','#d97706','#b45309','#92400e','#78350f'],
          teal: ['#f0fdfa','#ccfbf1','#99f6e4','#5eead4','#2dd4bf','#14b8a6','#0d9488','#0f766e','#115e59','#134e4a'],
        };
        const p = palettes[accent] || palettes.blue;
        const root = document.documentElement;
        root.style.setProperty('--accent-50', p[0]);
        root.style.setProperty('--accent-100', p[1]);
        root.style.setProperty('--accent-200', p[2]);
        root.style.setProperty('--accent-300', p[3]);
        root.style.setProperty('--accent-400', p[4]);
        root.style.setProperty('--accent-500', p[5]);
        root.style.setProperty('--accent-600', p[6]);
        root.style.setProperty('--accent-700', p[7]);
        root.style.setProperty('--accent-800', p[8]);
        root.style.setProperty('--accent-900', p[9]);
      };
      applyAccent();
      const interval = setInterval(applyAccent, 1000);
      return () => clearInterval(interval);
    } catch (_) {}
  }, []);

  // Load frontend version from public/version.json if available
  useEffect(() => {
    const loadFrontendVersion = async () => {
      try {
        const url = `${process.env.PUBLIC_URL || ''}/version.json`;
        const res = await fetch(url, { cache: 'no-store' });
        if (res.ok) {
          const v = await res.json();
          if (v?.version) {
            setFrontendVersion(v.version);
          }
        }
      } catch (_) {}
    };
    loadFrontendVersion();
  }, []);

  // When connected, fetch backend version info
  useEffect(() => {
    const fetchBackendInfo = async () => {
      if (!unifiedClient || connectionStatus !== 'connected') return;
      try {
        const info = await unifiedClient.getVersion();
        setBackendInfo(info);
      } catch (e) {
        // Fallback: try to use headers from last health check if available
        const meta = unifiedClient.getBackendInfo();
        if (meta && meta.headers) {
          setBackendInfo({
            version: meta.headers['x-pimonitor-version'] || meta.headers['X-PiMonitor-Version']
          });
        }
      }
    };
    fetchBackendInfo();
  }, [unifiedClient, connectionStatus]);

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
    const props = { unifiedClient, isDarkMode, setIsDarkMode };
    
    switch (activeTab) {
      case 'dashboard':
        return <Dashboard {...props} />;
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
      <AuthGuard unifiedClient={unifiedClient}>
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
                  backendVersion={backendInfo?.version}
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

                {/* Logout Button */}
                {onLogout && (
                  <button
                    onClick={onLogout}
                    className="p-2 text-gray-500 hover:text-red-500 dark:text-gray-400 dark:hover:text-red-400 rounded-md hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors duration-200"
                    title="Logout"
                  >
                    <Logout className="h-4 w-4" />
                  </button>
                )}

                
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
                  aria-label="Toggle menu"
                  aria-expanded={isMobileMenuOpen}
                >
                  {isMobileMenuOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
                </button>
              </div>
            </div>
          </div>
        </header>

        {/* Mobile Menu Overlay */}
        {isMobileMenuOpen && (
          <div className="md:hidden fixed inset-0 z-50 bg-black bg-opacity-50" onClick={toggleMobileMenu} role="dialog" aria-modal="true" aria-label="Mobile menu">
            <div
              className="fixed inset-y-0 right-0 max-w-xs w-full bg-white dark:bg-gray-800 shadow-xl flex flex-col"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Menu</h2>
                <button
                  onClick={toggleMobileMenu}
                  className="p-2 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 rounded-md"
                  aria-label="Close menu"
                >
                  <X className="h-6 w-6" />
                </button>
              </div>
              
              {/* Mobile Navigation */}
              <nav className="p-4 space-y-2 flex-1 overflow-y-auto">
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
                      <tab.icon className="h-6 w-6" />
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
                  <tab.icon className="inline-block h-5 w-5 mr-2" />
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

        

        {/* Footer */}
        <footer className="bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700 mt-auto">
          <div className="max-w-7xl mx-auto py-4 px-4 sm:px-6 lg:px-8">
            <div className="flex flex-col sm:flex-row justify-between items-center space-y-2 sm:space-y-0 text-sm text-gray-500 dark:text-gray-400">
              <div className="text-center sm:text-left">
                © 2024 Pi Monitor - Raspberry Pi Monitoring Dashboard
              </div>
              <div className="flex items-center space-x-4">
                <span>Frontend v{frontendVersion}</span>
                {backendInfo?.version && (
                  <span>Backend v{backendInfo.version}</span>
                )}
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
      </AuthGuard>
    </QueryClientProvider>
  );
}

export default App;
