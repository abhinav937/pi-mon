import React, { useState, useEffect } from 'react';
import { useQuery } from 'react-query';
import { RefreshCw, Server, HardDrive, Cpu, Monitor, Wifi } from 'lucide-react';
import toast from 'react-hot-toast';

const SystemStatus = ({ unifiedClient }) => {
  const [realTimeData, setRealTimeData] = useState(null);
  const [refreshing, setRefreshing] = useState(false);

  // Query for system stats
  const { data: systemStats, isLoading, refetch } = useQuery(
    'systemStatus',
    async () => {
      if (!unifiedClient) return null;
      return await unifiedClient.getSystemStats();
    },
    {
      enabled: !!unifiedClient,
      refetchInterval: 3000,
      onError: (err) => {
        toast.error('Failed to fetch system status');
        console.error('System status error:', err);
      },
    }
  );

  // Query for detailed system information
  const { data: detailedInfo } = useQuery(
    'detailedSystemInfo',
    async () => {
      if (!unifiedClient) return null;
      try {
        const response = await fetch(`${unifiedClient.serverUrl}/api/system/info`);
        return await response.json();
      } catch (error) {
        console.error('Failed to fetch detailed system info:', error);
        return null;
      }
    },
    {
      enabled: !!unifiedClient,
      refetchInterval: 30000, // Refresh every 30 seconds
    }
  );

  // Listen for real-time updates
  useEffect(() => {
    if (!unifiedClient) return;

    const originalOnDataUpdate = unifiedClient.onDataUpdate;
    unifiedClient.onDataUpdate = (data) => {
      if (data.type === 'initial_stats' || data.type === 'periodic_update' || data.type === 'mqtt_update') {
        setRealTimeData(data.data || data);
      }
      originalOnDataUpdate(data);
    };

    return () => {
      unifiedClient.onDataUpdate = originalOnDataUpdate;
    };
  }, [unifiedClient]);

  const currentData = realTimeData || systemStats;

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      await refetch();
      toast.success('System status refreshed');
    } catch (error) {
      toast.error('Failed to refresh system status');
    } finally {
      setRefreshing(false);
    }
  };

  const formatBytes = (bytes) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const formatUptime = (uptimeString) => {
    // Parse uptime string and provide additional context
    return uptimeString;
  };

  const getHealthStatus = () => {
    if (!currentData) return { status: 'unknown', color: 'gray' };
    
    const cpu = currentData.cpu_percent || 0;
    const memory = currentData.memory_percent || 0;
    const disk = currentData.disk_percent || 0;
    const temp = currentData.temperature || 0;

    if (cpu > 90 || memory > 90 || disk > 95 || temp > 80) {
      return { status: 'critical', color: 'red', message: 'System resources critical' };
    } else if (cpu > 70 || memory > 70 || disk > 80 || temp > 70) {
      return { status: 'warning', color: 'yellow', message: 'Some resources need attention' };
    } else {
      return { status: 'healthy', color: 'green', message: 'All systems operating normally' };
    }
  };

  const health = getHealthStatus();

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex justify-between items-center">
          <div className="skeleton h-8 w-48"></div>
          <div className="skeleton h-10 w-24"></div>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="metric-card">
              <div className="skeleton h-6 w-32 mb-4"></div>
              <div className="space-y-3">
                <div className="skeleton h-4 w-full"></div>
                <div className="skeleton h-4 w-3/4"></div>
                <div className="skeleton h-4 w-1/2"></div>
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
          System Status
        </h2>
        <button
          onClick={handleRefresh}
          disabled={refreshing}
          className="button-primary flex items-center space-x-2"
        >
          <RefreshCw className={`h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} />
          <span>{refreshing ? 'Refreshing...' : 'Refresh'}</span>
        </button>
      </div>

      {/* Health Status Banner */}
      <div className={`metric-card border-l-4 ${
        health.color === 'green' ? 'border-green-500 bg-green-50 dark:bg-green-900/20' :
        health.color === 'yellow' ? 'border-yellow-500 bg-yellow-50 dark:bg-yellow-900/20' :
        'border-red-500 bg-red-50 dark:bg-red-900/20'
      }`}>
        <div className="flex items-center space-x-4">
          <div className={`p-2 rounded-full ${
            health.color === 'green' ? 'bg-green-100 dark:bg-green-800' :
            health.color === 'yellow' ? 'bg-yellow-100 dark:bg-yellow-800' :
            'bg-red-100 dark:bg-red-800'
          }`}>
            <Monitor className={`h-6 w-6 ${
              health.color === 'green' ? 'text-green-600 dark:text-green-400' :
              health.color === 'yellow' ? 'text-yellow-600 dark:text-yellow-400' :
              'text-red-600 dark:text-red-400'
            }`} />
          </div>
          <div>
            <h3 className={`text-lg font-semibold ${
              health.color === 'green' ? 'text-green-800 dark:text-green-200' :
              health.color === 'yellow' ? 'text-yellow-800 dark:text-yellow-200' :
              'text-red-800 dark:text-red-200'
            }`}>
              System {health.status.charAt(0).toUpperCase() + health.status.slice(1)}
            </h3>
            <p className={`text-sm ${
              health.color === 'green' ? 'text-green-600 dark:text-green-400' :
              health.color === 'yellow' ? 'text-yellow-600 dark:text-yellow-400' :
              'text-red-600 dark:text-red-400'
            }`}>
              {health.message}
            </p>
          </div>
        </div>
      </div>

      {/* Detailed Status Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* CPU Information */}
        <div className="metric-card">
          <div className="flex items-center space-x-3 mb-4">
            <Cpu className="h-6 w-6 text-blue-600 dark:text-blue-400" />
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">CPU Status</h3>
          </div>
          <div className="space-y-3">
            <div className="flex justify-between">
              <span className="text-sm font-medium text-gray-500 dark:text-gray-400">Usage</span>
              <span className={`text-sm font-semibold ${
                currentData?.cpu_percent > 80 ? 'text-red-600' : 
                currentData?.cpu_percent > 60 ? 'text-yellow-600' : 'text-green-600'
              }`}>
                {currentData?.cpu_percent?.toFixed(1)}%
              </span>
            </div>
            <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
              <div
                className={`h-2 rounded-full transition-all duration-300 ${
                  currentData?.cpu_percent > 80 ? 'bg-red-500' :
                  currentData?.cpu_percent > 60 ? 'bg-yellow-500' : 'bg-green-500'
                }`}
                style={{ width: `${Math.min(currentData?.cpu_percent || 0, 100)}%` }}
              />
            </div>
            <div className="text-xs text-gray-500 dark:text-gray-400">
              Multi-core processor utilization
            </div>
          </div>
        </div>

        {/* Memory Information */}
        <div className="metric-card">
          <div className="flex items-center space-x-3 mb-4">
            <Server className="h-6 w-6 text-purple-600 dark:text-purple-400" />
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Memory Status</h3>
          </div>
          <div className="space-y-3">
            <div className="flex justify-between">
              <span className="text-sm font-medium text-gray-500 dark:text-gray-400">Usage</span>
              <span className={`text-sm font-semibold ${
                currentData?.memory_percent > 80 ? 'text-red-600' : 
                currentData?.memory_percent > 60 ? 'text-yellow-600' : 'text-green-600'
              }`}>
                {currentData?.memory_percent?.toFixed(1)}%
              </span>
            </div>
            <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
              <div
                className={`h-2 rounded-full transition-all duration-300 ${
                  currentData?.memory_percent > 80 ? 'bg-red-500' :
                  currentData?.memory_percent > 60 ? 'bg-yellow-500' : 'bg-green-500'
                }`}
                style={{ width: `${Math.min(currentData?.memory_percent || 0, 100)}%` }}
              />
            </div>
            <div className="text-xs text-gray-500 dark:text-gray-400">
              RAM utilization
            </div>
          </div>
        </div>

        {/* Storage Information */}
        <div className="metric-card">
          <div className="flex items-center space-x-3 mb-4">
            <HardDrive className="h-6 w-6 text-green-600 dark:text-green-400" />
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Storage Status</h3>
          </div>
          <div className="space-y-3">
            <div className="flex justify-between">
              <span className="text-sm font-medium text-gray-500 dark:text-gray-400">Usage</span>
              <span className={`text-sm font-semibold ${
                currentData?.disk_percent > 90 ? 'text-red-600' : 
                currentData?.disk_percent > 70 ? 'text-yellow-600' : 'text-green-600'
              }`}>
                {currentData?.disk_percent?.toFixed(1)}%
              </span>
            </div>
            <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
              <div
                className={`h-2 rounded-full transition-all duration-300 ${
                  currentData?.disk_percent > 90 ? 'bg-red-500' :
                  currentData?.disk_percent > 70 ? 'bg-yellow-500' : 'bg-green-500'
                }`}
                style={{ width: `${Math.min(currentData?.disk_percent || 0, 100)}%` }}
              />
            </div>
            <div className="text-xs text-gray-500 dark:text-gray-400">
              Root filesystem utilization
            </div>
          </div>
        </div>

        {/* Network Information */}
        <div className="metric-card">
          <div className="flex items-center space-x-3 mb-4">
            <Wifi className="h-6 w-6 text-cyan-600 dark:text-cyan-400" />
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Network Status</h3>
          </div>
          <div className="space-y-3">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">Bytes Sent</div>
                <div className="text-sm font-semibold text-green-600 dark:text-green-400">
                  {formatBytes(currentData?.network?.bytes_sent || 0)}
                </div>
              </div>
              <div>
                <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">Bytes Received</div>
                <div className="text-sm font-semibold text-blue-600 dark:text-blue-400">
                  {formatBytes(currentData?.network?.bytes_recv || 0)}
                </div>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">Packets Sent</div>
                <div className="text-sm font-semibold text-gray-700 dark:text-gray-300">
                  {(currentData?.network?.packets_sent || 0).toLocaleString()}
                </div>
              </div>
              <div>
                <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">Packets Received</div>
                <div className="text-sm font-semibold text-gray-700 dark:text-gray-300">
                  {(currentData?.network?.packets_recv || 0).toLocaleString()}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* System Information */}
      <div className="metric-card">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          System Information
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          <div>
            <div className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">
              System Uptime
            </div>
            <div className="text-base font-semibold text-gray-900 dark:text-white">
              {formatUptime(currentData?.uptime || 'Unknown')}
            </div>
          </div>
          <div>
            <div className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">
              Temperature
            </div>
            <div className={`text-base font-semibold ${
              currentData?.temperature > 70 ? 'text-red-600' : 
              currentData?.temperature > 60 ? 'text-yellow-600' : 'text-green-600'
            }`}>
              {currentData?.temperature?.toFixed(1)}°C
            </div>
          </div>
          <div>
            <div className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">
              Last Updated
            </div>
            <div className="text-base font-semibold text-gray-900 dark:text-white">
              {currentData?.timestamp ? 
                new Date(currentData.timestamp).toLocaleTimeString() : 
                'Never'
              }
            </div>
          </div>
        </div>
      </div>

      {/* Detailed System Information */}
      {detailedInfo && (
        <div className="metric-card">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            Detailed System Information
          </h3>
          
          {/* CPU Information */}
          {detailedInfo.cpu_info && (
            <div className="mb-6">
              <h4 className="text-md font-medium text-gray-700 dark:text-gray-300 mb-3">CPU Details</h4>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="text-center p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
                  <div className="text-lg font-bold text-blue-600 dark:text-blue-400">
                    {detailedInfo.cpu_info.current_freq || 0} MHz
                  </div>
                  <div className="text-xs text-gray-500 dark:text-gray-400">Current Frequency</div>
                </div>
                <div className="text-center p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
                  <div className="text-lg font-bold text-green-600 dark:text-green-400">
                    {detailedInfo.cpu_info.model || 'Unknown'}
                  </div>
                  <div className="text-xs text-gray-500 dark:text-gray-400">CPU Model</div>
                </div>
                <div className="text-center p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
                  <div className="text-lg font-bold text-purple-600 dark:text-purple-400">
                    {detailedInfo.cpu_info.max_freq || 0} MHz
                  </div>
                  <div className="text-xs text-gray-500 dark:text-gray-400">Max Frequency</div>
                </div>
              </div>
            </div>
          )}

          {/* Memory Information */}
          {detailedInfo.memory_info && (
            <div className="mb-6">
              <h4 className="text-md font-medium text-gray-700 dark:text-gray-300 mb-3">Memory Details</h4>
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div className="text-center p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
                  <div className="text-lg font-bold text-blue-600 dark:text-blue-400">
                    {detailedInfo.memory_info.total} GB
                  </div>
                  <div className="text-xs text-gray-500 dark:text-gray-400">Total RAM</div>
                </div>
                <div className="text-center p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
                  <div className="text-lg font-bold text-green-600 dark:text-green-400">
                    {detailedInfo.memory_info.available} GB
                  </div>
                  <div className="text-xs text-gray-500 dark:text-gray-400">Available</div>
                </div>
                <div className="text-center p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
                  <div className="text-lg font-bold text-red-600 dark:text-red-400">
                    {detailedInfo.memory_info.used} GB
                  </div>
                  <div className="text-xs text-gray-500 dark:text-gray-400">Used</div>
                </div>
                <div className="text-center p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
                  <div className="text-lg font-bold text-purple-600 dark:text-purple-400">
                    {detailedInfo.memory_info.percent}%
                  </div>
                  <div className="text-xs text-gray-500 dark:text-gray-400">Usage</div>
                </div>
              </div>
            </div>
          )}

          {/* Network Interfaces */}
          {detailedInfo.network_interfaces && (
            <div className="mb-6">
              <h4 className="text-md font-medium text-gray-700 dark:text-gray-300 mb-3">Network Interfaces</h4>
              <div className="space-y-3">
                {Object.entries(detailedInfo.network_interfaces).map(([iface, config]) => (
                  <div key={iface} className="p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
                    <div className="font-medium text-gray-900 dark:text-white mb-2">{iface}</div>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-2 text-sm">
                      {config.addrs.map((addr, idx) => (
                        <div key={idx} className="text-gray-600 dark:text-gray-400">
                          <div>IP: {addr.addr}</div>
                          <div>Netmask: {addr.netmask}</div>
                          {addr.broadcast && <div>Broadcast: {addr.broadcast}</div>}
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default SystemStatus;
