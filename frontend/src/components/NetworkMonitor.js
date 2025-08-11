import React, { useState, useEffect } from 'react';
import { useQuery } from 'react-query';
import { Wifi, WifiOff, Globe, Activity, Download, Upload, Signal, RefreshCw } from 'lucide-react';
import toast from 'react-hot-toast';

const NetworkMonitor = ({ unifiedClient }) => {
  const [selectedInterface, setSelectedInterface] = useState('all');

  // Query for network information
  const { data: networkData, isLoading, error, refetch } = useQuery(
    'networkInfo',
    async () => {
      if (!unifiedClient) return null;
      return await unifiedClient.getNetworkInfo();
    },
    {
      enabled: !!unifiedClient,
      refetchInterval: 10000, // Refetch every 10 seconds
      onError: (err) => {
        toast.error('Failed to fetch network information');
        console.error('Network info error:', err);
      },
    }
  );

  // Query for network statistics
  const { data: networkStats } = useQuery(
    'networkStats',
    async () => {
      if (!unifiedClient) return null;
      return await unifiedClient.getNetworkStats();
    },
    {
      enabled: !!unifiedClient,
      refetchInterval: 5000, // Refetch every 5 seconds
    }
  );

  const getInterfaceIcon = (type) => {
    switch (type?.toLowerCase()) {
      case 'wifi':
      case 'wireless':
        return <Wifi className="h-5 w-5 text-blue-600" />;
      case 'ethernet':
      case 'wired':
        return <Globe className="h-5 w-5 text-green-600" />;
      default:
        return <Activity className="h-5 w-5 text-gray-600" />;
    }
  };

  const getStatusColor = (status) => {
    switch (status?.toLowerCase()) {
      case 'up':
      case 'active':
        return 'text-green-600';
      case 'down':
      case 'inactive':
        return 'text-red-600';
      default:
        return 'text-yellow-600';
    }
  };

  const formatBytes = (bytes) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const formatSpeed = (bytesPerSecond) => {
    return formatBytes(bytesPerSecond) + '/s';
  };

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex justify-between items-center">
          <div className="skeleton h-8 w-48"></div>
          <div className="skeleton h-10 w-24"></div>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="metric-card">
              <div className="skeleton h-6 w-32 mb-4"></div>
              <div className="space-y-3">
                <div className="skeleton h-4 w-full"></div>
                <div className="skeleton h-4 w-3/4"></div>
                <div className="skeleton h-10 w-full"></div>
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="metric-card bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800">
        <div className="text-center">
          <WifiOff className="h-8 w-8 text-red-600 dark:text-red-400 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-red-800 dark:text-red-200 mb-2">
            Network Monitoring Unavailable
          </h3>
          <p className="text-red-600 dark:text-red-400 mb-4">
            {error.message || 'Unable to fetch network information'}
          </p>
          <button
            onClick={() => refetch()}
            className="button-primary bg-red-600 hover:bg-red-700"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  const interfaces = networkData?.interfaces || [];
  const stats = networkStats || {};
  const filteredInterfaces = selectedInterface === 'all' 
    ? interfaces 
    : interfaces.filter(iface => iface.name === selectedInterface);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
          Network Monitor
        </h2>
        <button
          onClick={() => refetch()}
          disabled={isLoading}
          className="button-primary flex items-center space-x-2"
        >
          <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
          <span>Refresh</span>
        </button>
      </div>

      {/* Network Overview */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="metric-card">
          <div className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">
            Active Interfaces
          </div>
          <div className="text-2xl font-bold text-green-600 dark:text-green-400">
            {interfaces.filter(i => i.status === 'up').length}
          </div>
        </div>
        
        <div className="metric-card">
          <div className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">
            Total Interfaces
          </div>
          <div className="text-2xl font-bold text-gray-900 dark:text-white">
            {interfaces.length}
          </div>
        </div>
        
        <div className="metric-card">
          <div className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">
            Download Speed
          </div>
          <div className="text-2xl font-bold text-blue-600 dark:text-blue-400">
            {stats.download ? formatSpeed(stats.download) : 'N/A'}
          </div>
        </div>
        
        <div className="metric-card">
          <div className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">
            Upload Speed
          </div>
          <div className="text-2xl font-bold text-purple-600 dark:text-purple-400">
            {stats.upload ? formatSpeed(stats.upload) : 'N/A'}
          </div>
        </div>
      </div>

      {/* Interface Filter */}
      <div className="flex items-center space-x-4">
        <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
          Interface:
        </label>
        <select
          value={selectedInterface}
          onChange={(e) => setSelectedInterface(e.target.value)}
          className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        >
          <option value="all">All Interfaces</option>
          {interfaces.map(iface => (
            <option key={iface.name} value={iface.name}>
              {iface.name} ({iface.type})
            </option>
          ))}
        </select>
      </div>

      {/* Network Interfaces */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {filteredInterfaces.map((iface) => (
          <div key={iface.name} className="metric-card">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center space-x-3">
                {getInterfaceIcon(iface.type)}
                <div>
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                    {iface.name}
                  </h3>
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    {iface.type || 'Unknown'}
                  </p>
                </div>
              </div>
              <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                iface.status === 'up' 
                  ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
                  : 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
              }`}>
                {iface.status}
              </span>
            </div>

            <div className="space-y-3">
              {iface.ip && (
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500 dark:text-gray-400">IP Address:</span>
                  <span className="font-mono text-gray-900 dark:text-white">{iface.ip}</span>
                </div>
              )}
              
              {iface.mac && (
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500 dark:text-gray-400">MAC Address:</span>
                  <span className="font-mono text-gray-900 dark:text-white">{iface.mac}</span>
                </div>
              )}
              
              {iface.speed && (
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500 dark:text-gray-400">Speed:</span>
                  <span className="text-gray-900 dark:text-white">{iface.speed}</span>
                </div>
              )}
              
              {iface.mtu && (
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500 dark:text-gray-400">MTU:</span>
                  <span className="text-gray-900 dark:text-white">{iface.mtu}</span>
                </div>
              )}
            </div>

            {/* Traffic Stats */}
            {stats[iface.name] && (
              <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-600">
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div className="flex items-center space-x-2">
                    <Download className="h-4 w-4 text-blue-600" />
                    <div>
                      <div className="text-gray-500 dark:text-gray-400">Download</div>
                      <div className="font-medium text-gray-900 dark:text-white">
                        {formatSpeed(stats[iface.name].download || 0)}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Upload className="h-4 w-4 text-purple-600" />
                    <div>
                      <div className="text-gray-500 dark:text-gray-400">Upload</div>
                      <div className="font-medium text-gray-900 dark:text-white">
                        {formatSpeed(stats[iface.name].upload || 0)}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Network Diagnostics */}
      <div className="metric-card">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          Network Diagnostics
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="space-y-3">
            <h4 className="font-medium text-gray-700 dark:text-gray-300">DNS Resolution</h4>
            <div className="text-sm text-gray-600 dark:text-gray-400">
              Primary DNS: {networkData?.dns?.primary || 'N/A'}
            </div>
            <div className="text-sm text-gray-600 dark:text-gray-400">
              Secondary DNS: {networkData?.dns?.secondary || 'N/A'}
            </div>
          </div>
          
          <div className="space-y-3">
            <h4 className="font-medium text-gray-700 dark:text-gray-300">Gateway</h4>
            <div className="text-sm text-gray-600 dark:text-gray-400">
              Default Gateway: {networkData?.gateway || 'N/A'}
            </div>
            <div className="text-sm text-gray-600 dark:text-gray-400">
              Route Status: {networkData?.routeStatus || 'N/A'}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default NetworkMonitor;
