import React, { useState, useEffect } from 'react';
import { Close as X, Save, Refresh as RefreshCw, Monitor, Notifications as Bell, Shield, Palette, DataObject as Database } from '@mui/icons-material';
import toast from 'react-hot-toast';

const SettingsPanel = ({ isDarkMode, setIsDarkMode, onClose, unifiedClient }) => {
  const [settings, setSettings] = useState({
    refreshInterval: 5000,
    notifications: true,
    soundAlerts: false,
    autoRefresh: true,
    dataRetention: 24,
    theme: isDarkMode ? 'dark' : 'light',
    language: 'en',
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
    dateFormat: 'MM/DD/YYYY',
    timeFormat: '12h'
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
        setSettings(prev => ({
          ...prev,
          refreshInterval: backendInterval
        }));
        // Update localStorage to match backend
        localStorage.setItem('pi-monitor-settings', JSON.stringify({
          ...settings,
          refreshInterval: backendInterval
        }));
      }
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
      
      // Send refresh interval to backend
      if (unifiedClient && settings.refreshInterval) {
        const intervalSeconds = settings.refreshInterval / 1000; // Convert from milliseconds to seconds
        await unifiedClient.updateMetricsInterval(intervalSeconds);
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
        notifications: true,
        soundAlerts: false,
        autoRefresh: true,
        dataRetention: 24,
        theme: 'auto',
        language: 'en',
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
        dateFormat: 'MM/DD/YYYY',
        timeFormat: '12h'
      };
      setSettings(defaultSettings);
      toast.success('Settings reset to default');
    }
  };

  const tabs = [
    { id: 'general', name: 'General', icon: Monitor },
    { id: 'notifications', name: 'Notifications', icon: Bell },
    { id: 'appearance', name: 'Appearance', icon: Palette },
    { id: 'data', name: 'Data & Storage', icon: Database },
    { id: 'security', name: 'Security', icon: Shield }
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
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Language
        </label>
        <select
          value={settings.language}
          onChange={(e) => handleSettingChange('language', e.target.value)}
          className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        >
          <option value="en">English</option>
          <option value="es">Español</option>
          <option value="fr">Français</option>
          <option value="de">Deutsch</option>
          <option value="it">Italiano</option>
        </select>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Timezone
        </label>
        <select
          value={settings.timezone}
          onChange={(e) => handleSettingChange('timezone', e.target.value)}
          className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        >
          <option value="UTC">UTC</option>
          <option value="America/New_York">Eastern Time</option>
          <option value="America/Chicago">Central Time</option>
          <option value="America/Denver">Mountain Time</option>
          <option value="America/Los_Angeles">Pacific Time</option>
          <option value="Europe/London">London</option>
          <option value="Europe/Paris">Paris</option>
          <option value="Asia/Tokyo">Tokyo</option>
        </select>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Date Format
          </label>
          <select
            value={settings.dateFormat}
            onChange={(e) => handleSettingChange('dateFormat', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          >
            <option value="MM/DD/YYYY">MM/DD/YYYY</option>
            <option value="DD/MM/YYYY">DD/MM/YYYY</option>
            <option value="YYYY-MM-DD">YYYY-MM-DD</option>
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Time Format
          </label>
          <select
            value={settings.timeFormat}
            onChange={(e) => handleSettingChange('timeFormat', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          >
            <option value="12h">12-hour</option>
            <option value="24h">24-hour</option>
          </select>
        </div>
      </div>
    </div>
  );

  const renderNotificationSettings = () => (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
            Enable Notifications
          </label>
          <p className="text-xs text-gray-500 dark:text-gray-400">
            Show toast notifications for system events
          </p>
        </div>
        <input
          type="checkbox"
          checked={settings.notifications}
          onChange={(e) => handleSettingChange('notifications', e.target.checked)}
          className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
        />
      </div>

      <div className="flex items-center justify-between">
        <div>
          <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
            Sound Alerts
          </label>
          <p className="text-xs text-gray-500 dark:text-gray-400">
            Play sounds for important notifications
          </p>
        </div>
        <input
          type="checkbox"
          checked={settings.soundAlerts}
          onChange={(e) => handleSettingChange('soundAlerts', e.target.checked)}
          className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
        />
      </div>

      <div className="flex items-center justify-between">
        <div>
          <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
            Auto-refresh
          </label>
          <p className="text-xs text-gray-500 dark:text-gray-400">
            Automatically refresh data in background
          </p>
        </div>
        <input
          type="checkbox"
          checked={settings.autoRefresh}
          onChange={(e) => handleSettingChange('autoRefresh', e.target.checked)}
          className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
        />
      </div>
    </div>
  );

  const renderAppearanceSettings = () => (
    <div className="space-y-6">
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Theme
        </label>
        <select
          value={settings.theme}
          onChange={(e) => handleSettingChange('theme', e.target.value)}
          className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        >
          <option value="auto">Auto (System)</option>
          <option value="light">Light</option>
          <option value="dark">Dark</option>
        </select>
        <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
          Current theme: {isDarkMode ? 'Dark' : 'Light'}
        </p>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Accent Color
        </label>
        <div className="grid grid-cols-5 gap-2">
          {['blue', 'green', 'purple', 'red', 'yellow'].map(color => (
            <button
              key={color}
              className={`w-8 h-8 rounded-full border-2 ${
                settings.accentColor === color 
                  ? 'border-gray-900 dark:border-white' 
                  : 'border-gray-300 dark:border-gray-600'
              } ${
                color === 'blue' ? 'bg-blue-500' :
                color === 'green' ? 'bg-green-500' :
                color === 'purple' ? 'bg-purple-500' :
                color === 'red' ? 'bg-red-500' :
                'bg-yellow-500'
              }`}
              onClick={() => handleSettingChange('accentColor', color)}
            />
          ))}
        </div>
      </div>
    </div>
  );

  const renderDataSettings = () => (
    <div className="space-y-6">
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Data Retention (hours)
        </label>
        <select
          value={settings.dataRetention}
          onChange={(e) => handleSettingChange('dataRetention', Number(e.target.value))}
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
          className="px-3 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-md transition-colors duration-200"
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

  const renderSecuritySettings = () => (
    <div className="space-y-6">
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Session Timeout (minutes)
        </label>
        <select
          value={settings.sessionTimeout || 30}
          onChange={(e) => handleSettingChange('sessionTimeout', Number(e.target.value))}
          className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        >
          <option value={15}>15 minutes</option>
          <option value={30}>30 minutes</option>
          <option value={60}>1 hour</option>
          <option value={120}>2 hours</option>
          <option value={0}>Never</option>
        </select>
      </div>

      <div className="flex items-center justify-between">
        <div>
          <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
            Require Authentication
          </label>
          <p className="text-xs text-gray-500 dark:text-gray-400">
            Force login for all users
          </p>
        </div>
        <input
          type="checkbox"
          checked={settings.requireAuth || false}
          onChange={(e) => handleSettingChange('requireAuth', e.target.checked)}
          className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
        />
      </div>

      <div className="flex items-center justify-between">
        <div>
          <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
            HTTPS Only
          </label>
          <p className="text-xs text-gray-500 dark:text-gray-400">
            Require secure connections
          </p>
        </div>
        <input
          type="checkbox"
          checked={settings.httpsOnly || false}
          onChange={(e) => handleSettingChange('httpsOnly', e.target.checked)}
          className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
        />
      </div>
    </div>
  );

  const renderTabContent = () => {
    switch (activeTab) {
      case 'general':
        return renderGeneralSettings();
      case 'notifications':
        return renderNotificationSettings();
      case 'appearance':
        return renderAppearanceSettings();
      case 'data':
        return renderDataSettings();
      case 'security':
        return renderSecuritySettings();
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
            className="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-md transition-colors duration-200 flex items-center space-x-2"
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
