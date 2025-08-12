import React, { useState, useEffect } from 'react';
import { useQuery } from 'react-query';
import { Cpu, HardDrive, Thermometer, Activity, Clock, Wifi, TrendingUp, Database, Zap } from 'lucide-react';
import toast from 'react-hot-toast';

const Dashboard = ({ unifiedClient }) => {
  const [realTimeData, setRealTimeData] = useState(null);

  // Query for system stats
  const { data: systemStats, isLoading, error, refetch } = useQuery(
    'systemStats',
    async () => {
      if (!unifiedClient) return null;
      return await unifiedClient.getEnhancedSystemStats();
    },
    {
      enabled: !!unifiedClient,
      refetchInterval: 5000, // Refetch every 5 seconds as fallback
      onError: (err) => {
        toast.error('Failed to fetch system statistics');
        console.error('System stats error:', err);
      },
    }
  );

  // Query for historical metrics
  const { data: metricsHistory } = useQuery(
    'metricsHistory',
    async () => {
      if (!unifiedClient) return null;
      return await unifiedClient.getMetricsHistory(60); // Last 60 minutes
    },
    {
      enabled: !!unifiedClient,
      refetchInterval: 30000, // Refetch every 30 seconds
      onError: (err) => {
        console.error('Metrics history error:', err);
      },
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

  // Use real-time data if available, otherwise fall back to query data
  const currentData = realTimeData || systemStats;

  const getStatusColor = (percentage) => {
    if (percentage === null || percentage === undefined || isNaN(percentage)) return 'text-gray-500';
    if (percentage >= 90) return 'text-red-600';
    if (percentage >= 70) return 'text-yellow-600';
    return 'text-green-600';
  };

  const getProgressBarColor = (percentage) => {
    if (percentage === null || percentage === undefined || isNaN(percentage)) return 'bg-gray-400';
    if (percentage >= 90) return 'bg-red-500';
    if (percentage >= 70) return 'bg-yellow-500';
    return 'bg-green-500';
  };

  const formatBytes = (bytes) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const formatNetworkRate = (bytesPerSecond) => {
    return formatBytes(bytesPerSecond) + '/s';
  };

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6">
        {[...Array(6)].map((_, i) => (
          <div key={i} className="metric-card animate-pulse">
            <div className="skeleton h-6 sm:h-8 w-20 sm:w-24 mb-2"></div>
            <div className="skeleton h-10 sm:h-12 w-28 sm:w-32 mb-4"></div>
            <div className="skeleton h-2 w-full"></div>
          </div>
        ))}
      </div>
    );
  }

  if (error && !currentData) {
    return (
      <div className="metric-card bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800">
        <div className="text-center">
          <div className="text-red-600 dark:text-red-400 text-3xl sm:text-4xl mb-4">⚠️</div>
          <h3 className="text-base sm:text-lg font-semibold text-red-800 dark:text-red-200 mb-2">
            Unable to load system data
          </h3>
          <p className="text-red-600 dark:text-red-400 mb-4 text-sm sm:text-base">
            {error.message || 'Failed to connect to the Pi Monitor server'}
          </p>
          <button
            onClick={() => refetch()}
            className="button-primary bg-red-600 hover:bg-red-700 px-4 py-2 sm:px-6 sm:py-3 text-sm sm:text-base"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (!currentData) {
    return (
      <div className="metric-card">
        <div className="text-center text-gray-500 dark:text-gray-400 text-sm sm:text-base">
          No system data available
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4 sm:space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between space-y-2 sm:space-y-0">
        <h2 className="text-xl sm:text-2xl font-bold text-gray-900 dark:text-white">
          System Overview
        </h2>
        <div className="flex items-center space-x-2 text-xs sm:text-sm text-gray-500 dark:text-gray-400">
          <Activity className="h-3 w-3 sm:h-4 sm:w-4" />
          <span>Live Data</span>
        </div>
      </div>

      {/* Main Metrics Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6">
        {/* CPU Usage */}
        <div className="metric-card p-4 sm:p-6">
          <div className="flex items-center justify-between mb-3 sm:mb-4">
            <div className="flex items-center space-x-2 sm:space-x-3">
              <div className="p-1.5 sm:p-2 bg-blue-100 dark:bg-blue-900 rounded-lg">
                <Cpu className="h-4 w-4 sm:h-6 sm:w-6 text-blue-600 dark:text-blue-400" />
              </div>
              <div>
                <p className="metric-label text-xs sm:text-sm">CPU Usage</p>
                <p className={`metric-value text-xl sm:text-3xl ${getStatusColor(currentData.cpu_percent)}`}>
                  {currentData.cpu_percent !== null && currentData.cpu_percent !== undefined && !isNaN(currentData.cpu_percent)
                    ? `${currentData.cpu_percent.toFixed(1)}%`
                    : 'N/A'
                  }
                </p>
              </div>
            </div>
          </div>
          <div className="progress-bar">
            <div
              className={`progress-bar-fill ${getProgressBarColor(currentData.cpu_percent)}`}
              style={{ width: `${Math.min(currentData.cpu_percent || 0, 100)}%` }}
            />
          </div>
        </div>

        {/* Memory Usage */}
        <div className="metric-card p-4 sm:p-6">
          <div className="flex items-center justify-between mb-3 sm:mb-4">
            <div className="flex items-center space-x-2 sm:space-x-3">
              <div className="p-1.5 sm:p-2 bg-purple-100 dark:bg-purple-900 rounded-lg">
                <Activity className="h-4 w-4 sm:h-6 sm:w-6 text-purple-600 dark:text-purple-400" />
              </div>
              <div>
                <p className="metric-label text-xs sm:text-sm">Memory</p>
                <p className={`metric-value text-xl sm:text-3xl ${getStatusColor(currentData.memory_percent)}`}>
                  {currentData.memory_percent !== null && currentData.memory_percent !== undefined && !isNaN(currentData.memory_percent)
                    ? `${currentData.memory_percent.toFixed(1)}%`
                    : 'N/A'
                  }
                </p>
              </div>
            </div>
          </div>
          <div className="progress-bar">
            <div
              className={`progress-bar-fill ${getProgressBarColor(currentData.memory_percent)}`}
              style={{ width: `${Math.min(currentData.memory_percent || 0, 100)}%` }}
            />
          </div>
        </div>

        {/* Disk Usage */}
        <div className="metric-card p-4 sm:p-6">
          <div className="flex items-center justify-between mb-3 sm:mb-4">
            <div className="flex items-center space-x-2 sm:space-x-3">
              <div className="p-1.5 sm:p-2 bg-green-100 dark:bg-green-900 rounded-lg">
                <HardDrive className="h-4 w-4 sm:h-6 sm:w-6 text-green-600 dark:text-green-400" />
              </div>
              <div>
                <p className="metric-label text-xs sm:text-sm">Disk Space</p>
                <p className={`metric-value text-xl sm:text-3xl ${getStatusColor(currentData.disk_percent)}`}>
                  {currentData.disk_percent !== null && currentData.disk_percent !== undefined && !isNaN(currentData.disk_percent) 
                    ? `${currentData.disk_percent.toFixed(1)}%` 
                    : 'N/A'
                  }
                </p>
              </div>
            </div>
          </div>
          <div className="progress-bar">
            <div
              className={`progress-bar-fill ${getProgressBarColor(currentData.disk_percent)}`}
              style={{ width: `${Math.min(currentData.disk_percent || 0, 100)}%` }}
            />
          </div>
        </div>

        {/* Temperature */}
        <div className="metric-card p-4 sm:p-6">
          <div className="flex items-center justify-between mb-3 sm:mb-4">
            <div className="flex items-center space-x-2 sm:space-x-3">
              <div className="p-1.5 sm:p-2 bg-red-100 dark:bg-red-900 rounded-lg">
                <Thermometer className="h-4 w-4 sm:h-6 sm:w-6 text-red-600 dark:text-red-400" />
              </div>
              <div>
                <p className="metric-label text-xs sm:text-sm">Temperature</p>
                <p className={`metric-value text-xl sm:text-3xl ${(currentData.temperature || 0) > 70 ? 'text-red-600' : (currentData.temperature || 0) > 60 ? 'text-yellow-600' : 'text-green-600'}`}>
                  {currentData.temperature !== null && currentData.temperature !== undefined && !isNaN(currentData.temperature)
                    ? `${currentData.temperature.toFixed(1)}°C`
                    : 'N/A'
                  }
                </p>
              </div>
            </div>
          </div>
          <div className="text-sm text-gray-500 dark:text-gray-400">
            {currentData.temperature !== null && currentData.temperature !== undefined && !isNaN(currentData.temperature) && currentData.temperature > 80 && (
              <span className="status-badge-error">High Temperature</span>
            )}
            {currentData.temperature !== null && currentData.temperature !== undefined && !isNaN(currentData.temperature) && currentData.temperature <= 80 && currentData.temperature > 70 && (
              <span className="status-badge-warning">Warm</span>
            )}
            {currentData.temperature !== null && currentData.temperature !== undefined && !isNaN(currentData.temperature) && currentData.temperature <= 70 && (
              <span className="status-badge-success">Normal</span>
            )}
          </div>
        </div>

        {/* Uptime */}
        <div className="metric-card p-4 sm:p-6">
          <div className="flex items-center justify-between mb-3 sm:mb-4">
            <div className="flex items-center space-x-2 sm:space-x-3">
              <div className="p-1.5 sm:p-2 bg-indigo-100 dark:bg-indigo-900 rounded-lg">
                <Clock className="h-4 w-4 sm:h-6 sm:w-6 text-indigo-600 dark:text-indigo-400" />
              </div>
              <div>
                <p className="metric-label text-xs sm:text-sm">Uptime</p>
                <p className="metric-value text-indigo-600 dark:text-indigo-400">
                  {currentData.system?.uptime || currentData.uptime || 'Unknown'}
                </p>
              </div>
            </div>
          </div>
          <div className="text-sm text-gray-500 dark:text-gray-400">
            System running stable
          </div>
        </div>

        {/* Network Activity */}
        <div className="metric-card p-4 sm:p-6">
          <div className="flex items-center justify-between mb-3 sm:mb-4">
            <div className="flex items-center space-x-2 sm:space-x-3">
              <div className="p-1.5 sm:p-2 bg-cyan-100 dark:bg-cyan-900 rounded-lg">
                <Wifi className="h-4 w-4 sm:h-6 sm:w-6 text-cyan-600 dark:text-cyan-400" />
              </div>
              <div>
                <p className="metric-label text-xs sm:text-sm">Network</p>
                <p className="text-lg font-semibold text-gray-900 dark:text-white">
                  Active
                </p>
              </div>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-2 text-sm">
            <div>
              <span className="text-gray-500 dark:text-gray-400">↑ TX:</span>
              <span className="ml-1 font-medium text-green-600 dark:text-green-400">
                {currentData.network?.bytes_sent_rate ? formatNetworkRate(currentData.network.bytes_sent_rate) : formatBytes(currentData.network?.bytes_sent || 0)}
              </span>
            </div>
            <div>
              <span className="text-gray-500 dark:text-gray-400">↓ RX:</span>
              <span className="ml-1 font-medium text-blue-600 dark:text-blue-400">
                {currentData.network?.bytes_recv_rate ? formatNetworkRate(currentData.network.bytes_recv_rate) : formatBytes(currentData.network?.bytes_recv || 0)}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Metrics Overview */}
      {metricsHistory && metricsHistory.metrics && metricsHistory.metrics.length > 0 && (
        <div className="metric-card">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
              <TrendingUp className="inline h-5 w-5 mr-2" />
              Real-time Metrics Overview
            </h3>
            <div className="flex items-center space-x-2 text-sm text-gray-500 dark:text-gray-400">
              <Database className="h-4 w-4" />
              <span>{metricsHistory.collection_status?.total_points || 0} data points</span>
            </div>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
            <div className="text-center p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
              <div className="text-2xl font-bold text-blue-600 dark:text-blue-400">
                {metricsHistory.collection_status?.active ? (
                  <div className="w-3 h-3 sm:w-4 sm:h-4 rounded-full bg-green-500" />
                ) : (
                  <div className="w-3 h-3 sm:w-4 sm:h-4 rounded-full bg-red-500" />
                )}
              </div>
              <div className="text-sm font-medium text-gray-700 dark:text-gray-300">
                Collection Status
              </div>
              <div className="text-xs text-gray-500 dark:text-gray-400">
                {metricsHistory.collection_status?.active ? 'Active' : 'Inactive'}
              </div>
            </div>
            
            <div className="text-center p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
              <div className="text-2xl font-bold text-green-600 dark:text-green-400">
                {metricsHistory.collection_status?.interval || 5}s
              </div>
              <div className="text-sm font-medium text-gray-700 dark:text-gray-300">
                Update Interval
              </div>
              <div className="text-xs text-gray-500 dark:text-gray-400">
                Real-time updates
              </div>
            </div>
            
            <div className="text-center p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
              <div className="text-2xl font-bold text-purple-600 dark:text-purple-400">
                {metricsHistory.metrics.length}
              </div>
              <div className="text-sm font-medium text-gray-700 dark:text-gray-300">
                Recent Data Points
              </div>
              <div className="text-xs text-gray-500 dark:text-gray-400">
                Last 60 minutes
              </div>
            </div>
          </div>
          
          {metricsHistory.metrics.length > 1 && (
            <div className="space-y-3">
              <h4 className="text-md font-medium text-gray-700 dark:text-gray-300">
                <Zap className="inline h-4 w-4 mr-2" />
                Performance Trends
              </h4>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
                <div className="text-center">
                  <div className="font-medium text-gray-900 dark:text-white">
                    {(() => {
                      const value = metricsHistory.metrics[metricsHistory.metrics.length - 1]?.cpu_percent;
                      return value !== null && value !== undefined && !isNaN(value) ? `${value.toFixed(1)}%` : 'N/A';
                    })()}
                  </div>
                  <div className="text-gray-500 dark:text-gray-400">Current CPU</div>
                </div>
                <div className="text-center">
                  <div className="font-medium text-gray-900 dark:text-white">
                    {(() => {
                      const value = metricsHistory.metrics[metricsHistory.metrics.length - 1]?.memory_percent;
                      return value !== null && value !== undefined && !isNaN(value) ? `${value.toFixed(1)}%` : 'N/A';
                    })()}
                  </div>
                  <div className="text-gray-500 dark:text-gray-400">Current Memory</div>
                </div>
                <div className="text-center">
                  <div className="font-medium text-gray-900 dark:text-white">
                    {(() => {
                      const value = metricsHistory.metrics[metricsHistory.metrics.length - 1]?.temperature;
                      return value !== null && value !== undefined && !isNaN(value) ? `${value.toFixed(1)}°C` : 'N/A';
                    })()}
                  </div>
                  <div className="text-gray-500 dark:text-gray-400">Current Temp</div>
                </div>
                <div className="text-center">
                  <div className="font-medium text-gray-900 dark:text-white">
                    {(() => {
                      const value = metricsHistory.metrics[metricsHistory.metrics.length - 1]?.disk_percent;
                      return value !== null && value !== undefined && !isNaN(value) ? `${value.toFixed(1)}%` : 'N/A';
                    })()}
                  </div>
                  <div className="text-gray-500 dark:text-gray-400">Current Disk</div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* System Status Summary */}
      <div className="metric-card">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          System Status
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="flex items-center space-x-3">
            <div className={`w-3 h-3 rounded-full ${(currentData.cpu_percent || 0) > 80 ? 'bg-red-500' : (currentData.cpu_percent || 0) > 60 ? 'bg-yellow-500' : 'bg-green-500'}`}></div>
            <span className="text-sm font-medium text-gray-700 dark:text-gray-300">CPU</span>
          </div>
          <div className="flex items-center space-x-3">
            <div className={`w-3 h-3 rounded-full ${(currentData.memory_percent || 0) > 80 ? 'bg-red-500' : (currentData.memory_percent || 0) > 60 ? 'bg-yellow-500' : 'bg-green-500'}`}></div>
            <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Memory</span>
          </div>
          <div className="flex items-center space-x-3">
            <div className={`w-3 h-3 rounded-full ${(currentData.disk_percent || 0) > 90 ? 'bg-red-500' : (currentData.disk_percent || 0) > 70 ? 'bg-yellow-500' : 'bg-green-500'}`}></div>
            <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Storage</span>
          </div>
          <div className="flex items-center space-x-3">
            <div className={`w-3 h-3 rounded-full ${(currentData.temperature || 0) > 70 ? 'bg-red-500' : (currentData.temperature || 0) > 60 ? 'bg-yellow-500' : 'bg-green-500'}`}></div>
            <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Temperature</span>
          </div>
        </div>
        <div className="mt-4 text-sm text-gray-500 dark:text-gray-400">
          Last updated: {currentData.timestamp ? new Date(currentData.timestamp).toLocaleString() : 'Unknown'}
        </div>
      </div>
    </div>
  );
};

export default Dashboard;