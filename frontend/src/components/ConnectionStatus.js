import React from 'react';
import { Wifi, WifiOff, AccessTime as Clock } from '@mui/icons-material';

const ConnectionStatus = ({ status, isOnline, lastUpdate, isMobile = false }) => {
  const getStatusColor = () => {
    switch (status) {
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

  const getStatusIcon = () => {
    if (!isOnline) return <WifiOff className="h-4 w-4 text-red-500" />;
    return status === 'connected' ? 
      <Wifi className="h-4 w-4 text-green-500" /> :
      <WifiOff className={`h-4 w-4 ${getStatusColor()}`} />;
  };

  const getStatusText = () => {
    if (!isOnline) return 'Offline';
    return status.charAt(0).toUpperCase() + status.slice(1);
  };

  // Mobile compact version
  if (isMobile) {
    return (
      <div className="flex items-center space-x-2">
        {getStatusIcon()}
        <span className={`text-xs font-medium ${getStatusColor()}`}>
          {getStatusText()}
        </span>
      </div>
    );
  }

  // Desktop full version
  return (
    <div className="flex items-center space-x-4">
      {/* Connection Status */}
      <div className="flex items-center space-x-2">
        {getStatusIcon()}
        <span className={`text-sm font-medium ${getStatusColor()}`}>
          {getStatusText()}
        </span>
      </div>

      {/* Last Update */}
      {lastUpdate && status === 'connected' && (
        <div className="flex items-center space-x-2 text-sm text-gray-500 dark:text-gray-400">
          <Clock className="h-4 w-4" />
          <span>Last update: {lastUpdate.toLocaleTimeString()}</span>
        </div>
      )}
    </div>
  );
};

export default ConnectionStatus;
