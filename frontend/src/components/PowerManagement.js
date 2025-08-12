import React, { useState } from 'react';
import { useMutation } from 'react-query';
import { Power, RotateCcw, Clock, AlertTriangle, Bug } from 'lucide-react';
import toast from 'react-hot-toast';

const PowerManagement = ({ unifiedClient }) => {
  const [selectedAction, setSelectedAction] = useState('shutdown');
  const [delay, setDelay] = useState(0);
  const [showConfirmation, setShowConfirmation] = useState(false);
  const [debugInfo, setDebugInfo] = useState(null);
  const [showDebugPanel, setShowDebugPanel] = useState(false);

  // Debug function to log all relevant information
  const logDebugInfo = (message, data = null) => {
    const timestamp = new Date().toISOString();
    const debugEntry = {
      timestamp,
      message,
      data,
      action: selectedAction,
      delay,
      clientAvailable: !!unifiedClient,
      clientState: unifiedClient?.getConnectionState?.() || 'unknown'
    };
    
    console.log(`🔍 [PowerManagement Debug] ${message}`, debugEntry);
    setDebugInfo(debugEntry);
  };

  const powerMutation = useMutation(
    async ({ action, delay }) => {
      logDebugInfo('Starting power action execution', { action, delay });
      
      if (!unifiedClient) {
        const error = 'Client not available';
        logDebugInfo('Client not available error', { error });
        throw new Error(error);
      }

      logDebugInfo('Client available, checking connection state', {
        connectionState: unifiedClient.getConnectionState?.(),
        serverUrl: unifiedClient.serverUrl
      });

      try {
        logDebugInfo('Calling executePowerAction on unifiedClient', { action, delay });
        const result = await unifiedClient.executePowerAction(action, delay);
        logDebugInfo('Power action executed successfully', { result });
        return result;
      } catch (error) {
        logDebugInfo('Power action execution failed', { 
          error: error.message, 
          errorStack: error.stack,
          errorResponse: error.response?.data,
          errorStatus: error.response?.status
        });
        throw error;
      }
    },
    {
      onSuccess: (data) => {
        logDebugInfo('Power action mutation succeeded', { data });
        toast.success(data.message || `${selectedAction} initiated successfully`);
        setShowConfirmation(false);
        setDelay(0);
      },
      onError: (error) => {
        logDebugInfo('Power action mutation failed', { 
          error: error.message,
          errorResponse: error.response?.data,
          errorStatus: error.response?.status
        });
        toast.error(error.message || `Failed to ${selectedAction} system`);
        setShowConfirmation(false);
      },
    }
  );

  const handleExecutePowerAction = () => {
    logDebugInfo('User clicked execute power action button', {
      selectedAction,
      delay,
      clientAvailable: !!unifiedClient
    });
    powerMutation.mutate({ action: selectedAction, delay });
  };

  // Test connection function for debugging
  const testConnection = async () => {
    if (!unifiedClient) {
      logDebugInfo('Cannot test connection - no client available');
      return;
    }

    try {
      logDebugInfo('Testing connection to backend');
      const health = await unifiedClient.checkHealth();
      logDebugInfo('Health check successful', { health });
      
      const powerStatus = await unifiedClient.getPowerStatus();
      logDebugInfo('Power status check successful', { powerStatus });
      
      toast.success('Connection test successful!');
    } catch (error) {
      logDebugInfo('Connection test failed', { 
        error: error.message,
        errorResponse: error.response?.data,
        errorStatus: error.response?.status
      });
      toast.error(`Connection test failed: ${error.message}`);
    }
  };

  const formatDelay = (seconds) => {
    if (seconds === 0) return 'Immediately';
    if (seconds < 60) return `${seconds} second${seconds !== 1 ? 's' : ''}`;
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    if (remainingSeconds === 0) return `${minutes} minute${minutes !== 1 ? 's' : ''}`;
    return `${minutes}m ${remainingSeconds}s`;
  };

  const ConfirmationModal = () => (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white dark:bg-gray-800 rounded-lg p-6 max-w-md w-full mx-4">
        <div className="flex items-center space-x-3 mb-4">
          <div className="p-2 bg-red-100 dark:bg-red-900 rounded-full">
            <AlertTriangle className="h-6 w-6 text-red-600 dark:text-red-400" />
          </div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
            Confirm Power Action
          </h3>
        </div>
        
        <div className="mb-6">
          <p className="text-gray-600 dark:text-gray-400 mb-4">
            Are you sure you want to <strong>{selectedAction}</strong> the system?
          </p>
          
          {delay > 0 && (
            <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-md p-3">
              <p className="text-yellow-800 dark:text-yellow-200 text-sm">
                <Clock className="h-4 w-4 inline mr-1" />
                This action will execute in {formatDelay(delay)}
              </p>
            </div>
          )}
          
          {delay === 0 && (
            <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-md p-3">
              <p className="text-red-800 dark:text-red-200 text-sm font-medium">
                ⚠️ This action will execute immediately and cannot be undone!
              </p>
            </div>
          )}
        </div>
        
        <div className="flex space-x-3">
          <button
            onClick={() => setShowConfirmation(false)}
            className="button-secondary flex-1"
            disabled={powerMutation.isLoading}
          >
            Cancel
          </button>
          <button
            onClick={handleExecutePowerAction}
            className="button-danger flex-1"
            disabled={powerMutation.isLoading}
          >
            {powerMutation.isLoading ? (
              <>
                <div className="loading-spinner mr-2"></div>
                Executing...
              </>
            ) : (
              `Confirm ${selectedAction.charAt(0).toUpperCase() + selectedAction.slice(1)}`
            )}
          </button>
        </div>
      </div>
    </div>
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
          Power Management
        </h2>
        <div className="text-sm text-gray-500 dark:text-gray-400">
          System control actions
        </div>
      </div>

      {/* Debug Panel */}
      <div className="metric-card border-l-4 border-blue-500 bg-blue-50 dark:bg-blue-900/20">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-2">
            <Bug className="h-5 w-5 text-blue-600 dark:text-blue-400" />
            <h3 className="text-lg font-semibold text-blue-800 dark:text-blue-200">
              Debug Panel
            </h3>
          </div>
          <div className="flex space-x-2">
            <button
              onClick={() => setShowDebugPanel(!showDebugPanel)}
              className="px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
            >
              {showDebugPanel ? 'Hide' : 'Show'} Debug
            </button>
            <button
              onClick={testConnection}
              className="px-3 py-1 text-sm bg-green-600 text-white rounded hover:bg-green-700 transition-colors"
            >
              Test Connection
            </button>
          </div>
        </div>
        
        {showDebugPanel && (
          <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
              <div>
                <strong>Client Status:</strong>
                <div className="mt-1 space-y-1">
                  <div>Available: {unifiedClient ? '✅ Yes' : '❌ No'}</div>
                  <div>State: {unifiedClient?.getConnectionState?.() || 'Unknown'}</div>
                  <div>Server: {unifiedClient?.serverUrl || 'Not set'}</div>
                </div>
              </div>
              <div>
                <strong>Current Action:</strong>
                <div className="mt-1 space-y-1">
                  <div>Action: {selectedAction}</div>
                  <div>Delay: {delay}s</div>
                  <div>Loading: {powerMutation.isLoading ? '✅ Yes' : '❌ No'}</div>
                </div>
              </div>
            </div>
            
            {unifiedClient && (
              <div className="bg-gray-100 dark:bg-gray-800 rounded p-3">
                <div className="flex items-center justify-between mb-2">
                  <strong>Debug Logs Summary:</strong>
                  <button
                    onClick={() => {
                      unifiedClient.clearDebugLogs();
                      setDebugInfo(null);
                    }}
                    className="px-2 py-1 text-xs bg-red-600 text-white rounded hover:bg-red-700 transition-colors"
                  >
                    Clear Logs
                  </button>
                </div>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs">
                  {(() => {
                    const summary = unifiedClient.getDebugSummary();
                    return (
                      <>
                        <div>Total: {summary.totalLogs}</div>
                        <div>Errors: {summary.errorLogs}</div>
                        <div>Info: {summary.infoLogs}</div>
                        <div>Requests: {summary.recentRequests.length}</div>
                      </>
                    );
                  })()}
                </div>
                
                {(() => {
                  const summary = unifiedClient.getDebugSummary();
                  if (summary.recentErrors.length > 0) {
                    return (
                      <div className="mt-2">
                        <strong className="text-red-600">Recent Errors:</strong>
                        <div className="mt-1 space-y-1 max-h-20 overflow-auto">
                          {summary.recentErrors.map((log, index) => (
                            <div key={index} className="text-xs text-red-600 bg-red-50 dark:bg-red-900/20 p-1 rounded">
                              {log.message}: {JSON.stringify(log.data)}
                            </div>
                          ))}
                        </div>
                      </div>
                    );
                  }
                  return null;
                })()}
              </div>
            )}
            
            {debugInfo && (
              <div className="bg-gray-100 dark:bg-gray-800 rounded p-3">
                <strong>Last Debug Info:</strong>
                <div className="mt-2 text-xs font-mono bg-white dark:bg-gray-900 p-2 rounded overflow-auto max-h-32">
                  <div>Time: {debugInfo.timestamp}</div>
                  <div>Message: {debugInfo.message}</div>
                  <div>Data: {JSON.stringify(debugInfo.data, null, 2)}</div>
                </div>
              </div>
            )}
            
            <div className="text-xs text-blue-700 dark:text-blue-300">
              💡 Open Chrome DevTools (F12) and check the Console tab for detailed debug logs
            </div>
          </div>
        )}
      </div>

      {/* Warning Banner */}
      <div className="metric-card border-l-4 border-yellow-500 bg-yellow-50 dark:bg-yellow-900/20">
        <div className="flex items-start space-x-3">
          <AlertTriangle className="h-6 w-6 text-yellow-600 dark:text-yellow-400 flex-shrink-0 mt-0.5" />
          <div>
            <h3 className="text-lg font-semibold text-yellow-800 dark:text-yellow-200 mb-2">
              Important Notice
            </h3>
            <p className="text-yellow-700 dark:text-yellow-300 text-sm">
              Power management actions will affect the entire Raspberry Pi system. 
              Make sure to save any important work before proceeding. Remote connections 
              will be lost during shutdown or restart operations.
            </p>
          </div>
        </div>
      </div>

      {/* Power Action Selection */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Shutdown Card */}
        <div 
          className={`metric-card cursor-pointer transition-all duration-200 ${
            selectedAction === 'shutdown' 
              ? 'border-red-500 bg-red-50 dark:bg-red-900/20' 
              : 'hover:border-red-300'
          }`}
          onClick={() => setSelectedAction('shutdown')}
        >
          <div className="flex items-center space-x-4">
            <div className={`p-3 rounded-full ${
              selectedAction === 'shutdown' 
                ? 'bg-red-200 dark:bg-red-800' 
                : 'bg-red-100 dark:bg-red-900'
            }`}>
              <Power className="h-8 w-8 text-red-600 dark:text-red-400" />
            </div>
            <div>
              <h3 className="text-xl font-semibold text-gray-900 dark:text-white">
                Shutdown
              </h3>
              <p className="text-gray-600 dark:text-gray-400">
                Safely power off the system
              </p>
            </div>
            {selectedAction === 'shutdown' && (
              <div className="ml-auto">
                <div className="w-4 h-4 bg-red-500 rounded-full"></div>
              </div>
            )}
          </div>
        </div>

        {/* Restart Card */}
        <div 
          className={`metric-card cursor-pointer transition-all duration-200 ${
            selectedAction === 'restart' 
              ? 'border-orange-500 bg-orange-50 dark:bg-orange-900/20' 
              : 'hover:border-orange-300'
          }`}
          onClick={() => setSelectedAction('restart')}
        >
          <div className="flex items-center space-x-4">
            <div className={`p-3 rounded-full ${
              selectedAction === 'restart' 
                ? 'bg-orange-200 dark:bg-orange-800' 
                : 'bg-orange-100 dark:bg-orange-900'
            }`}>
              <RotateCcw className="h-8 w-8 text-orange-600 dark:text-orange-400" />
            </div>
            <div>
              <h3 className="text-xl font-semibold text-gray-900 dark:text-white">
                Restart
              </h3>
              <p className="text-gray-600 dark:text-gray-400">
                Reboot the system
              </p>
            </div>
            {selectedAction === 'restart' && (
              <div className="ml-auto">
                <div className="w-4 h-4 bg-orange-500 rounded-full"></div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Delay Configuration */}
      <div className="metric-card">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          <Clock className="h-5 w-5 inline mr-2" />
          Execution Timing
        </h3>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <label htmlFor="delay-input" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Delay (seconds)
            </label>
            <input
              id="delay-input"
              type="number"
              min="0"
              max="3600"
              step="1"
              value={delay}
              onChange={(e) => setDelay(Math.max(0, Math.min(3600, parseInt(e.target.value) || 0)))}
              className="input-field"
              placeholder="Enter delay in seconds"
            />
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
              0 = immediate, maximum 3600 seconds (1 hour)
            </p>
          </div>
          
          <div className="flex flex-col justify-center">
            <div className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Execution Time
            </div>
            <div className="text-lg font-semibold text-gray-900 dark:text-white">
              {formatDelay(delay)}
            </div>
            {delay > 0 && (
              <div className="text-sm text-gray-500 dark:text-gray-400">
                At: {new Date(Date.now() + delay * 1000).toLocaleTimeString()}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Execute Button */}
      <div className="metric-card border-t-4 border-gray-200 dark:border-gray-700">
        <div className="text-center">
          <button
            onClick={() => setShowConfirmation(true)}
            disabled={powerMutation.isLoading || !unifiedClient}
            className={`px-8 py-4 rounded-lg font-semibold text-white transition-all duration-200 ${
              selectedAction === 'shutdown'
                ? 'bg-red-600 hover:bg-red-700 focus:ring-red-500'
                : 'bg-orange-600 hover:bg-orange-700 focus:ring-orange-500'
            } focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed`}
          >
            {powerMutation.isLoading ? (
              <>
                <div className="loading-spinner mr-3"></div>
                Executing {selectedAction}...
              </>
            ) : (
              <>
                {selectedAction === 'shutdown' ? (
                  <Power className="h-5 w-5 inline mr-2" />
                ) : (
                  <RotateCcw className="h-5 w-5 inline mr-2" />
                )}
                {selectedAction === 'shutdown' ? 'Shutdown System' : 'Restart System'}
              </>
            )}
          </button>
          
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-3">
            Click to {selectedAction} the Raspberry Pi system
            {delay > 0 && ` in ${formatDelay(delay)}`}
          </p>
        </div>
      </div>

      {/* Confirmation Modal */}
      {showConfirmation && <ConfirmationModal />}
    </div>
  );
};

export default PowerManagement;
