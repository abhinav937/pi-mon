import React, { useState } from 'react';
import { useMutation } from 'react-query';
import { Power, RotateCcw, Clock, AlertTriangle } from 'lucide-react';
import toast from 'react-hot-toast';

const PowerManagement = ({ unifiedClient }) => {
  const [selectedAction, setSelectedAction] = useState('shutdown');
  const [delay, setDelay] = useState(0);
  const [showConfirmation, setShowConfirmation] = useState(false);

  const powerMutation = useMutation(
    async ({ action, delay }) => {
      if (!unifiedClient) throw new Error('Client not available');
      return await unifiedClient.executePowerAction(action, delay);
    },
    {
      onSuccess: (data) => {
        toast.success(data.message || `${selectedAction} initiated successfully`);
        setShowConfirmation(false);
        setDelay(0);
      },
      onError: (error) => {
        toast.error(error.message || `Failed to ${selectedAction} system`);
        setShowConfirmation(false);
      },
    }
  );

  const handleExecutePowerAction = () => {
    powerMutation.mutate({ action: selectedAction, delay });
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
