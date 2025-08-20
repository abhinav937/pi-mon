import React, { useState, useEffect } from 'react';
import { Close as X, Save, Refresh as RefreshCw, Monitor, DataObject as Database } from '@mui/icons-material';
import toast from 'react-hot-toast';

const SettingsPanel = ({ isDarkMode, setIsDarkMode, onClose, unifiedClient }) => {
  const [settings, setSettings] = useState({
    refreshInterval: 5000,
    theme: isDarkMode ? 'dark' : 'light',
    accentColor: 'blue',
    dataRetentionHours: 24
  });

  const [activeTab, setActiveTab] = useState('general');

  // Load saved settings on mount
  useEffect(() => {
    try {
      const saved = localStorage.getItem('pi-monitor-settings');
      if (saved) {
        const parsed = JSON.parse(saved);
        setSettings(prev => ({ ...prev, ...parsed }));
      }
      
      // Load current refresh interval from backend
      if (unifiedClient) {
        loadBackendSettings();
      }
    } catch (_) {}
  }, [unifiedClient]);

  const loadBackendSettings = async () => {
    try {
      if (!unifiedClient) return;
      
      // Get current metrics interval from backend
      const intervalResponse = await unifiedClient.getMetricsInterval();
      if (intervalResponse && intervalResponse.current_interval) {
        const backendInterval = intervalResponse.current_interval * 1000; // Convert to milliseconds
        setSettings(prev => ({ ...prev, refreshInterval: backendInterval }));
      }

      // Get current data retention from backend
      const retentionResponse = await unifiedClient.getDataRetention();
      if (retentionResponse && retentionResponse.current_retention_hours) {
        const backendRetention = retentionResponse.current_retention_hours;
        setSettings(prev => ({ ...prev, dataRetentionHours: backendRetention }));
      }

      // Update localStorage to match backend (preserve theme)
      try {
        const savedRaw = localStorage.getItem('pi-monitor-settings');
        const saved = savedRaw ? JSON.parse(savedRaw) : {};
        const backendInterval = intervalResponse?.current_interval ? intervalResponse.current_interval * 1000 : saved.refreshInterval;
        const backendRetention = retentionResponse?.current_retention_hours || saved.dataRetentionHours || 24;
        localStorage.setItem('pi-monitor-settings', JSON.stringify({
          theme: saved.theme ?? (isDarkMode ? 'dark' : 'light'),
          refreshInterval: backendInterval,
          accentColor: saved.accentColor ?? 'blue',
          dataRetentionHours: backendRetention
        }));
      } catch (_) {}
    } catch (error) {
      console.warn('Failed to load backend settings:', error);
    }
  };

  const handleSettingChange = (key, value) => {
    setSettings(prev => ({
      ...prev,
      [key]: value
    }));
  };

  const handleSave = async () => {
    try {
      // Save settings to localStorage
      localStorage.setItem('pi-monitor-settings', JSON.stringify(settings));
      
      // Apply accent color immediately
      try {
        const event = new Event('storage');
        window.dispatchEvent(event);
      } catch (_) {}

      // Send settings to backend
      if (unifiedClient) {
        // Update refresh interval
        if (settings.refreshInterval) {
          const intervalSeconds = settings.refreshInterval / 1000; // Convert from milliseconds to seconds
          await unifiedClient.updateMetricsInterval(intervalSeconds);
          // Also update frontend polling interval immediately
          if (unifiedClient.setFrontendPollingInterval) {
            unifiedClient.setFrontendPollingInterval(settings.refreshInterval);
          }
        }
        
        // Update data retention
        if (settings.dataRetentionHours) {
          await unifiedClient.updateDataRetention(settings.dataRetentionHours);
        }
        
        toast.success('Settings saved and backend updated successfully');
      } else {
        toast.success('Settings saved successfully');
      }
      
      // Apply theme change
      if (settings.theme !== (isDarkMode ? 'dark' : 'light')) {
        if (setIsDarkMode) {
          setIsDarkMode(settings.theme === 'dark');
        }
      }
    } catch (error) {
      console.error('Failed to save settings:', error);
      toast.error('Failed to save settings to backend');
    }
  };

  const handleReset = () => {
    if (window.confirm('Are you sure you want to reset all settings to default values?')) {
      const defaultSettings = {
        refreshInterval: 5000,
        theme: 'auto',
        accentColor: 'blue',
        dataRetentionHours: 24
      };
      setSettings(defaultSettings);
      toast.success('Settings reset to default');
    }
  };

  const tabs = [
    { id: 'general', name: 'General', icon: Monitor },
    { id: 'data', name: 'Data & Storage', icon: Database }
  ];

  const renderGeneralSettings = () => (
    <div className="space-y-6">
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Refresh Interval
        </label>
        <select
          value={settings.refreshInterval}
          onChange={(e) => handleSettingChange('refreshInterval', Number(e.target.value))}
          className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        >
          <option value={2000}>2 seconds</option>
          <option value={5000}>5 seconds</option>
          <option value={10000}>10 seconds</option>
          <option value={30000}>30 seconds</option>
          <option value={60000}>1 minute</option>
        </select>
        <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
          How often to refresh system data
        </p>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Theme</label>
        <select
          value={settings.theme}
          onChange={(e) => handleSettingChange('theme', e.target.value)}
          className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        >
          <option value="auto">Auto (System)</option>
          <option value="light">Light</option>
          <option value="dark">Dark</option>
        </select>
        <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">Current theme: {isDarkMode ? 'Dark' : 'Light'}</p>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Accent Color</label>
        <div className="grid grid-cols-6 gap-2">
          {[
            { id: 'blue', color: '#2563eb' },
            { id: 'green', color: '#16a34a' },
            { id: 'purple', color: '#7c3aed' },
            { id: 'red', color: '#dc2626' },
            { id: 'yellow', color: '#ca8a04' },
            { id: 'teal', color: '#0d9488' },
          ].map(opt => (
            <button
              key={opt.id}
              type="button"
              aria-label={`Accent ${opt.id}`}
              className={`w-8 h-8 rounded-full border-2 ${settings.accentColor === opt.id ? 'border-gray-900 dark:border-white' : 'border-gray-300 dark:border-gray-600'}`}
              style={{ backgroundColor: opt.color }}
              onClick={() => handleSettingChange('accentColor', opt.id)}
            />
          ))}
        </div>
        <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">Applies to primary buttons, highlights and badges.</p>
      </div>
    </div>
  );

  // Removed Notifications, Appearance extras, and Security settings for simplicity

  const renderDataSettings = () => (
    <div className="space-y-6">
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Data Retention (hours)
        </label>
        <select
          value={settings.dataRetentionHours}
          onChange={(e) => handleSettingChange('dataRetentionHours', Number(e.target.value))}
          className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        >
          <option value={1}>1 hour</option>
          <option value={6}>6 hours</option>
          <option value={12}>12 hours</option>
          <option value={24}>24 hours</option>
          <option value={48}>48 hours</option>
          <option value={168}>1 week</option>
        </select>
        <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
          How long to keep historical data
        </p>
      </div>

      <div className="flex items-center justify-between">
        <div>
          <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
            Export Data
          </label>
          <p className="text-xs text-gray-500 dark:text-gray-400">
            Download all collected data as JSON
          </p>
        </div>
        <button
          onClick={async () => {
            try {
              if (!unifiedClient) throw new Error('Client not ready');
              const data = await unifiedClient.exportMetrics();
              const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
              const url = URL.createObjectURL(blob);
              const a = document.createElement('a');
              a.href = url;
              a.download = `pi-monitor-metrics-${new Date().toISOString().replace(/[:.]/g,'-')}.json`;
              document.body.appendChild(a);
              a.click();
              document.body.removeChild(a);
              URL.revokeObjectURL(url);
              toast.success('Data exported');
            } catch (e) {
              toast.error('Export failed');
            }
          }}
          className="px-3 py-2 text-white text-sm font-medium rounded-md transition-colors duration-200"
          style={{ backgroundColor: 'var(--accent-600)' }}
        >
          Export
        </button>
      </div>

      <div className="flex items-center justify-between">
        <div>
          <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
            Clear All Data
          </label>
          <p className="text-xs text-gray-500 dark:text-gray-400">
            Remove all stored data (irreversible)
          </p>
        </div>
        <button
          onClick={async () => {
            try {
              if (!window.confirm('This will permanently delete all stored metrics. Continue?')) return;
              if (!unifiedClient) throw new Error('Client not ready');
              await unifiedClient.clearMetrics();
              toast.success('All data cleared');
            } catch (e) {
              toast.error('Failed to clear data');
            }
          }}
          className="px-3 py-2 bg-red-600 hover:bg-red-700 text-white text-sm font-medium rounded-md transition-colors duration-200"
        >
          Clear
        </button>
      </div>
    </div>
  );

  const renderTabContent = () => {
    switch (activeTab) {
      case 'general':
        return renderGeneralSettings();
      case 'data':
        return renderDataSettings();
      default:
        return renderGeneralSettings();
    }
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-4xl w-full mx-2 sm:mx-4">
      {/* Header */}
      <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
          Settings
        </h2>
        {onClose && (
          <button
            onClick={onClose}
            className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded-md hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors duration-200"
          >
            <X className="h-5 w-5" />
          </button>
        )}
      </div>

      {/* Content */}
      <div className="flex flex-col md:flex-row">
        {/* Sidebar */}
        <div className="w-full md:w-64 md:border-r border-gray-200 dark:border-gray-700">
          <nav className="p-2 md:p-4 flex md:block overflow-x-auto space-x-2 md:space-x-0">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex-shrink-0 w-auto md:w-full flex items-center space-x-3 px-3 py-2 text-sm font-medium rounded-md transition-colors duration-200 ${
                    activeTab === tab.id
                      ? 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300'
                      : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100 dark:text-gray-400 dark:hover:text-gray-300 dark:hover:bg-gray-700'
                  }`}
                >
                  <Icon className="h-5 w-5" />
                  <span>{tab.name}</span>
                </button>
              );
            })}
          </nav>
        </div>

        {/* Main Content */}
        <div className="flex-1 p-4 md:p-6">
          {renderTabContent()}
        </div>
      </div>

      {/* Footer */}
      <div className="flex items-center justify-between p-6 border-t border-gray-200 dark:border-gray-700">
        <button
          onClick={handleReset}
          className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 rounded-md transition-colors duration-200 flex items-center space-x-2"
        >
          <RefreshCw className="h-4 w-4" />
          <span>Reset to Default</span>
        </button>

        <div className="flex space-x-3">
          {onClose && (
            <button
              onClick={onClose}
              className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 rounded-md transition-colors duration-200"
            >
              Cancel
            </button>
          )}
          <button
            onClick={handleSave}
            className="px-4 py-2 text-sm font-medium text-white rounded-md transition-colors duration-200 flex items-center space-x-2"
            style={{ backgroundColor: 'var(--accent-600)' }}
          >
            <Save className="h-4 w-4" />
            <span>Save Settings</span>
          </button>
        </div>
      </div>
    </div>
  );
};

export default SettingsPanel;
