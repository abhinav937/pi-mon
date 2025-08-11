import React, { useState, useEffect } from 'react';
import { useQuery } from 'react-query';
import { FileText, Search, Filter, Download, RefreshCw, AlertTriangle, Info, XCircle } from 'lucide-react';
import toast from 'react-hot-toast';

const LogViewer = ({ unifiedClient }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedLog, setSelectedLog] = useState('system');
  const [logLevel, setLogLevel] = useState('all');
  const [maxLines, setMaxLines] = useState(100);
  const [autoRefresh, setAutoRefresh] = useState(true);

  // Query for available logs
  const { data: availableLogs, isLoading: logsLoading } = useQuery(
    'availableLogs',
    async () => {
      if (!unifiedClient) return [];
      return await unifiedClient.getAvailableLogs();
    },
    {
      enabled: !!unifiedClient,
      refetchInterval: 30000, // Refetch every 30 seconds
    }
  );

  // Query for log content
  const { data: logData, isLoading, error, refetch } = useQuery(
    ['logContent', selectedLog, maxLines],
    async () => {
      if (!unifiedClient) return null;
      return await unifiedClient.getLogContent(selectedLog, maxLines);
    },
    {
      enabled: !!unifiedClient && !!selectedLog,
      refetchInterval: autoRefresh ? 5000 : false, // Auto-refresh every 5 seconds if enabled
      onError: (err) => {
        toast.error('Failed to fetch log content');
        console.error('Log fetch error:', err);
      },
    }
  );

  const getLogIcon = (level) => {
    switch (level?.toLowerCase()) {
      case 'error':
      case 'err':
        return <XCircle className="h-4 w-4 text-red-600" />;
      case 'warning':
      case 'warn':
        return <AlertTriangle className="h-4 w-4 text-yellow-600" />;
      case 'info':
        return <Info className="h-4 w-4 text-blue-600" />;
      default:
        return <Info className="h-4 w-4 text-gray-600" />;
    }
  };

  const getLogLevelColor = (level) => {
    switch (level?.toLowerCase()) {
      case 'error':
      case 'err':
        return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200';
      case 'warning':
      case 'warn':
        return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200';
      case 'info':
        return 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200';
      default:
        return 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200';
    }
  };

  const filterLogs = (logs) => {
    if (!logs) return [];
    
    let filtered = logs;
    
    // Filter by log level
    if (logLevel !== 'all') {
      filtered = filtered.filter(log => 
        log.level?.toLowerCase().includes(logLevel.toLowerCase())
      );
    }
    
    // Filter by search term
    if (searchTerm) {
      filtered = filtered.filter(log => 
        log.message?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        log.timestamp?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        log.source?.toLowerCase().includes(searchTerm.toLowerCase())
      );
    }
    
    return filtered;
  };

  const downloadLog = async () => {
    try {
      if (!unifiedClient) return;
      const content = await unifiedClient.downloadLog(selectedLog);
      
      // Create and download file
      const blob = new Blob([content], { type: 'text/plain' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${selectedLog}_${new Date().toISOString().split('T')[0]}.log`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
      
      toast.success('Log downloaded successfully');
    } catch (error) {
      toast.error('Failed to download log');
      console.error('Download error:', error);
    }
  };

  const clearLog = async () => {
    if (!confirm('Are you sure you want to clear this log? This action cannot be undone.')) {
      return;
    }
    
    try {
      if (!unifiedClient) return;
      await unifiedClient.clearLog(selectedLog);
      toast.success('Log cleared successfully');
      refetch();
    } catch (error) {
      toast.error('Failed to clear log');
      console.error('Clear log error:', error);
    }
  };

  if (logsLoading) {
    return <LoadingSpinner text="Loading available logs..." />;
  }

  const logs = availableLogs || [];
  const filteredLogs = filterLogs(logData?.entries || []);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
          Log Viewer
        </h2>
        <div className="flex items-center space-x-3">
          <button
            onClick={() => setAutoRefresh(!autoRefresh)}
            className={`px-3 py-2 text-sm font-medium rounded-md transition-colors duration-200 ${
              autoRefresh 
                ? 'bg-green-600 text-white hover:bg-green-700' 
                : 'bg-gray-600 text-white hover:bg-gray-700'
            }`}
          >
            {autoRefresh ? 'Auto-refresh ON' : 'Auto-refresh OFF'}
          </button>
          <button
            onClick={() => refetch()}
            disabled={isLoading}
            className="button-primary flex items-center space-x-2"
          >
            <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Controls */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Log Selection */}
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Log File
          </label>
          <select
            value={selectedLog}
            onChange={(e) => setSelectedLog(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          >
            {logs.map(log => (
              <option key={log.name} value={log.name}>
                {log.name} ({log.size})
              </option>
            ))}
          </select>
        </div>

        {/* Log Level Filter */}
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Log Level
          </label>
          <select
            value={logLevel}
            onChange={(e) => setLogLevel(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          >
            <option value="all">All Levels</option>
            <option value="error">Error</option>
            <option value="warning">Warning</option>
            <option value="info">Info</option>
            <option value="debug">Debug</option>
          </select>
        </div>

        {/* Max Lines */}
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Max Lines
          </label>
          <select
            value={maxLines}
            onChange={(e) => setMaxLines(Number(e.target.value))}
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          >
            <option value={50}>50 lines</option>
            <option value={100}>100 lines</option>
            <option value={200}>200 lines</option>
            <option value={500}>500 lines</option>
            <option value={1000}>1000 lines</option>
          </select>
        </div>

        {/* Actions */}
        <div className="flex items-end space-x-2">
          <button
            onClick={downloadLog}
            className="px-3 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-md transition-colors duration-200 flex items-center space-x-2"
          >
            <Download className="h-4 w-4" />
            <span>Download</span>
          </button>
          <button
            onClick={clearLog}
            className="px-3 py-2 bg-red-600 hover:bg-red-700 text-white text-sm font-medium rounded-md transition-colors duration-200"
          >
            Clear
          </button>
        </div>
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
        <input
          type="text"
          placeholder="Search logs..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        />
      </div>

      {/* Log Content */}
      <div className="metric-card">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
            {selectedLog} Log
          </h3>
          <div className="text-sm text-gray-500 dark:text-gray-400">
            {filteredLogs.length} entries
          </div>
        </div>

        {isLoading ? (
          <LoadingSpinner text="Loading log content..." />
        ) : error ? (
          <div className="text-center py-8">
            <XCircle className="h-8 w-8 text-red-600 dark:text-red-400 mx-auto mb-4" />
            <p className="text-red-600 dark:text-red-400">
              Failed to load log content: {error.message}
            </p>
          </div>
        ) : filteredLogs.length === 0 ? (
          <div className="text-center py-8 text-gray-500 dark:text-gray-400">
            No log entries found matching the current filters.
          </div>
        ) : (
          <div className="space-y-2 max-h-96 overflow-y-auto">
            {filteredLogs.map((entry, index) => (
              <div
                key={index}
                className="p-3 bg-gray-50 dark:bg-gray-800 rounded-md border-l-4 border-gray-200 dark:border-gray-600"
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-center space-x-3 flex-1">
                    {getLogIcon(entry.level)}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center space-x-2 mb-1">
                        <span className={`px-2 py-1 text-xs font-medium rounded-full ${getLogLevelColor(entry.level)}`}>
                          {entry.level || 'INFO'}
                        </span>
                        {entry.timestamp && (
                          <span className="text-xs text-gray-500 dark:text-gray-400 font-mono">
                            {entry.timestamp}
                          </span>
                        )}
                        {entry.source && (
                          <span className="text-xs text-gray-500 dark:text-gray-400">
                            {entry.source}
                          </span>
                        )}
                      </div>
                      <p className="text-sm text-gray-900 dark:text-white font-mono break-words">
                        {entry.message}
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Log Statistics */}
      {logData && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="metric-card">
            <div className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">
              Total Entries
            </div>
            <div className="text-2xl font-bold text-gray-900 dark:text-white">
              {logData.totalEntries || 0}
            </div>
          </div>
          
          <div className="metric-card">
            <div className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">
              Error Entries
            </div>
            <div className="text-2xl font-bold text-red-600 dark:text-red-400">
              {logData.errorCount || 0}
            </div>
          </div>
          
          <div className="metric-card">
            <div className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">
              Warning Entries
            </div>
            <div className="text-2xl font-bold text-yellow-600 dark:text-yellow-400">
              {logData.warningCount || 0}
            </div>
          </div>
          
          <div className="metric-card">
            <div className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">
              Log Size
            </div>
            <div className="text-2xl font-bold text-blue-600 dark:text-blue-400">
              {logData.size || 'N/A'}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default LogViewer;
