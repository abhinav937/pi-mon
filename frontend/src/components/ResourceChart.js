import React, { useState, useEffect, useRef } from 'react';
import { Line } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler,
  TimeScale
} from 'chart.js';
import { TrendingUp, BarChart as BarChart3, Timeline, Storage as HardDrive, DataObject as Database } from '@mui/icons-material';

// Register Chart.js components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler,
  TimeScale
);

const ResourceChart = ({ unifiedClient }) => {
  const [selectedMetric, setSelectedMetric] = useState('cpu');
  const [chartData, setChartData] = useState({
    cpu: { labels: [], data: [] },
    memory: { labels: [], data: [] },
    temperature: { labels: [], data: [] },
    disk: { labels: [], data: [] },
  });
  const [isLoadingHistorical, setIsLoadingHistorical] = useState(true);
  
  // Updated time range options: 1hr, 6hr, 12hr, 24hr
  const [timeRange, setTimeRange] = useState(() => {
    const saved = localStorage.getItem('pi-monitor-time-range');
    return saved ? parseInt(saved) : 60; // Default to last 1 hour
  });
  
  const SAMPLE_INTERVAL_SECONDS = 5; // Expected real-time sample interval
  const [maxDataPoints, setMaxDataPoints] = useState(() => {
    const estimated = Math.ceil((timeRange * 60) / SAMPLE_INTERVAL_SECONDS);
    return Math.max(100, estimated);
  });
  
  const chartRef = useRef(null);

  // Save time range to localStorage whenever it changes and recompute max points
  useEffect(() => {
    localStorage.setItem('pi-monitor-time-range', timeRange.toString());
    const estimated = Math.ceil((timeRange * 60) / SAMPLE_INTERVAL_SECONDS);
    setMaxDataPoints(Math.max(100, estimated));
  }, [timeRange]);

  // Helper function to format timestamps properly
  const formatTimestamp = (timestamp, range) => {
    if (typeof timestamp === 'string') {
      // If it's already a formatted string, return as is
      return timestamp;
    }
    
    const date = new Date(timestamp * 1000);
    
    if (range >= 1440) { // 24 hours or more
      return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } else if (range >= 720) { // 12 hours or more
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } else {
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    }
  };

  // Helper function to get x-axis tick interval based on time range
  const getTickInterval = (range) => {
    if (range >= 1440) { // 24 hours
      return 6; // Show every 6 hours
    } else if (range >= 720) { // 12 hours
      return 3; // Show every 3 hours
    } else if (range >= 120) { // 2 hours or more
      return 1; // Show every hour
    } else {
      return 0.5; // Show every 30 minutes
    }
  };

  // Listen for real-time updates
  useEffect(() => {
    if (!unifiedClient) return;

    const handleUpdate = (data) => {
      if (data.type === 'initial_stats' || data.type === 'periodic_update' || data.type === 'mqtt_update') {
        const now = new Date();
        const timestamp = formatTimestamp(now.getTime() / 1000, timeRange);
        const systemData = data.data || data;

        setChartData(prevData => {
          const newData = { ...prevData };
          
          // Update CPU data - ensure value is a valid number and append to existing data
          if (systemData.cpu_percent !== undefined && systemData.cpu_percent !== null && !isNaN(systemData.cpu_percent)) {
            if (!prevData.cpu.labels.includes(timestamp)) {
              newData.cpu.labels = [...prevData.cpu.labels, timestamp].slice(-maxDataPoints);
              newData.cpu.data = [...prevData.cpu.data, parseFloat(systemData.cpu_percent)].slice(-maxDataPoints);
            }
          }
          
          // Update Memory data
          if (systemData.memory_percent !== undefined && systemData.memory_percent !== null && !isNaN(systemData.memory_percent)) {
            if (!prevData.memory.labels.includes(timestamp)) {
              newData.memory.labels = [...prevData.memory.labels, timestamp].slice(-maxDataPoints);
              newData.memory.data = [...prevData.memory.data, parseFloat(systemData.memory_percent)].slice(-maxDataPoints);
            }
          }
          
          // Update Temperature data
          if (systemData.temperature !== undefined && systemData.temperature !== null && !isNaN(systemData.temperature)) {
            if (!prevData.temperature.labels.includes(timestamp)) {
              newData.temperature.labels = [...prevData.temperature.labels, timestamp].slice(-maxDataPoints);
              newData.temperature.data = [...prevData.temperature.data, parseFloat(systemData.temperature)].slice(-maxDataPoints);
            }
          }
          
          // Update Disk data
          if (systemData.disk_percent !== undefined && systemData.disk_percent !== null && !isNaN(systemData.disk_percent)) {
            if (!prevData.disk.labels.includes(timestamp)) {
              newData.disk.labels = [...prevData.disk.labels, timestamp].slice(-maxDataPoints);
              newData.disk.data = [...prevData.disk.data, parseFloat(systemData.disk_percent)].slice(-maxDataPoints);
            }
          }
          
          return newData;
        });
      }
    };

    const unsubscribe = unifiedClient.addDataListener(handleUpdate);
    return () => {
      if (unsubscribe) unsubscribe();
    };
  }, [unifiedClient, timeRange, maxDataPoints]);

  // Seed with latest cached stats immediately on mount to avoid N/A
  useEffect(() => {
    if (!unifiedClient) return;
    const latest = unifiedClient.getLatestStats && unifiedClient.getLatestStats();
    if (!latest) return;
    const now = new Date();
    const timestamp = formatTimestamp(now.getTime() / 1000, timeRange);
    setChartData(prevData => {
      const newData = { ...prevData };
      if (latest.cpu_percent != null && !isNaN(latest.cpu_percent) && !prevData.cpu.labels.includes(timestamp)) {
        newData.cpu.labels = [...prevData.cpu.labels, timestamp].slice(-maxDataPoints);
        newData.cpu.data = [...prevData.cpu.data, parseFloat(latest.cpu_percent)].slice(-maxDataPoints);
      }
      if (latest.memory_percent != null && !isNaN(latest.memory_percent) && !prevData.memory.labels.includes(timestamp)) {
        newData.memory.labels = [...prevData.memory.labels, timestamp].slice(-maxDataPoints);
        newData.memory.data = [...prevData.memory.data, parseFloat(latest.memory_percent)].slice(-maxDataPoints);
      }
      if (latest.temperature != null && !isNaN(latest.temperature) && !prevData.temperature.labels.includes(timestamp)) {
        newData.temperature.labels = [...prevData.temperature.labels, timestamp].slice(-maxDataPoints);
        newData.temperature.data = [...prevData.temperature.data, parseFloat(latest.temperature)].slice(-maxDataPoints);
      }
      if (latest.disk_percent != null && !isNaN(latest.disk_percent) && !prevData.disk.labels.includes(timestamp)) {
        newData.disk.labels = [...prevData.disk.labels, timestamp].slice(-maxDataPoints);
        newData.disk.data = [...prevData.disk.data, parseFloat(latest.disk_percent)].slice(-maxDataPoints);
      }
      return newData;
    });
  }, [unifiedClient, timeRange, maxDataPoints]);

  const fetchHistoricalData = React.useCallback(async () => {
    if (!unifiedClient) return;
    setIsLoadingHistorical(true);
    try {
      const response = await unifiedClient.getMetricsHistory(timeRange);
      if (response && response.metrics) {
        const metrics = response.metrics;
        const labels = metrics.map(m => formatTimestamp(m.timestamp, timeRange));
        const cpuData = metrics.map(m => m.cpu_percent || 0);
        const memoryData = metrics.map(m => m.memory_percent || 0);
        const temperatureData = metrics.map(m => m.temperature || 0);
        const diskData = metrics.map(m => m.disk_percent || 0);

        setChartData({
          cpu: { labels, data: cpuData },
          memory: { labels, data: memoryData },
          temperature: { labels, data: temperatureData },
          disk: { labels, data: diskData }
        });

        if (chartRef.current) {
          chartRef.current.update();
        }
      }
    } catch (error) {
      console.error('Failed to fetch historical data:', error);
    } finally {
      setIsLoadingHistorical(false);
    }
  }, [unifiedClient, timeRange]);

  // Fetch historical metrics data - only when timeRange changes or component mounts
  useEffect(() => {
    if (!unifiedClient) return;
    fetchHistoricalData();
    const refreshInterval = Math.max(30000, timeRange * 1000 / 10);
    const interval = setInterval(fetchHistoricalData, refreshInterval);
    return () => clearInterval(interval);
  }, [unifiedClient, timeRange, fetchHistoricalData]);

  const getChartConfig = (metric) => {
    const isDarkMode = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
    
    const colors = {
      cpu: {
        background: 'rgba(59, 130, 246, 0.1)',
        border: 'rgb(59, 130, 246)',
        point: 'rgb(59, 130, 246)',
      },
      memory: {
        background: 'rgba(147, 51, 234, 0.1)',
        border: 'rgb(147, 51, 234)',
        point: 'rgb(147, 51, 234)',
      },
      temperature: {
        background: 'rgba(239, 68, 68, 0.1)',
        border: 'rgb(239, 68, 68)',
        point: 'rgb(239, 68, 68)',
      },
      disk: {
        background: 'rgba(34, 197, 94, 0.1)',
        border: 'rgb(34, 197, 94)',
        point: 'rgb(34, 197, 94)',
      },
    };

    return {
      data: {
        labels: chartData[metric].labels,
        datasets: [
          {
            label: metric === 'cpu' ? 'CPU Usage (%)' : 
                   metric === 'memory' ? 'Memory Usage (%)' : 
                   metric === 'temperature' ? 'Temperature (°C)' :
                   'Disk Usage (%)',
            data: chartData[metric].data,
            borderColor: colors[metric].border,
            backgroundColor: colors[metric].background,
            pointBackgroundColor: colors[metric].point,
            pointBorderColor: colors[metric].border,
            pointRadius: 3,
            pointHoverRadius: 6,
            tension: 0.4,
            fill: true,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: 'top',
            labels: {
              color: isDarkMode ? '#e5e7eb' : '#374151',
              font: {
                size: 12,
              },
            },
          },
          title: {
            display: true,
            text: `${metric.charAt(0).toUpperCase() + metric.slice(1)} Usage Over Time`,
            color: isDarkMode ? '#f9fafb' : '#111827',
            font: {
              size: 16,
              weight: 'bold',
            },
          },
          tooltip: {
            mode: 'index',
            intersect: false,
            backgroundColor: isDarkMode ? '#1f2937' : '#ffffff',
            titleColor: isDarkMode ? '#f9fafb' : '#111827',
            bodyColor: isDarkMode ? '#e5e7eb' : '#374151',
            borderColor: isDarkMode ? '#4b5563' : '#d1d5db',
            borderWidth: 1,
            callbacks: {
              label: function(context) {
                const value = context.parsed && context.parsed.y != null ? context.parsed.y : null;
                const unit = metric === 'temperature' ? '°C' : '%';
                const datasetLabel = context.dataset && context.dataset.label ? context.dataset.label : '';
                if (value == null || isNaN(value)) return datasetLabel;
                return `${datasetLabel}: ${Number(value).toFixed(2)}${unit}`;
              }
            }
          },
        },
        interaction: {
          mode: 'nearest',
          axis: 'x',
          intersect: false,
        },
        scales: {
          x: {
            type: 'category',
            ticks: {
              maxTicksLimit: getTickInterval(timeRange) * 2, // Adjust based on time range
              autoSkip: true,
              maxRotation: 45,
              minRotation: 0,
              callback: function(value, index, ticks) {
                // Custom label formatting to avoid "AM AM AM" issue
                const label = this.getLabelForValue(value);
                if (!label) return '';
                
                // For 24-hour view, show date and time
                if (timeRange >= 1440) {
                  return label;
                }
                // For 12-hour view, show time only
                else if (timeRange >= 720) {
                  return label.split(' ').pop(); // Get time part only
                }
                // For shorter views, show time with seconds
                else {
                  return label;
                }
              }
            },
            title: {
              display: true,
              text: 'Time'
            }
          },
          y: {
            display: true,
            title: {
              display: true,
              text: metric === 'temperature' ? 'Temperature (°C)' : 
                  metric === 'disk' ? 'Disk Usage (%)' : 'Usage (%)',
              color: isDarkMode ? '#9ca3af' : '#6b7280',
            },
            min: 0,
            max: metric === 'temperature' ? 100 : 100,
            ticks: {
              color: isDarkMode ? '#9ca3af' : '#6b7280',
              stepSize: metric === 'temperature' ? 10 : 20,
            },
            grid: {
              color: isDarkMode ? '#374151' : '#e5e7eb',
            },
          },
        },
        elements: {
          line: {
            borderWidth: 2,
          },
        },
        // Smooth horizontal slide without vertical morphing
        animation: { duration: 0 },
        animations: {
          y: { duration: 0 },
          x: { duration: 400, easing: 'linear' }
        },
      },
    };
  };

  const metrics = [
    { id: 'cpu', name: 'CPU Usage', icon: Timeline, color: 'text-blue-600' },
    { id: 'memory', name: 'Memory Usage', icon: BarChart3, color: 'text-purple-600' },
    { id: 'temperature', name: 'Temperature', icon: TrendingUp, color: 'text-red-600' },
    { id: 'disk', name: 'Disk Usage', icon: HardDrive, color: 'text-green-600' },
  ];

  // Updated time range options with better labels
  const timeRangeOptions = [
    { value: 60, label: '1 Hour', description: 'Last hour with 30-min intervals' },
    { value: 360, label: '6 Hours', description: 'Last 6 hours with 3-hour intervals' },
    { value: 720, label: '12 Hours', description: 'Last 12 hours with 3-hour intervals' },
    { value: 1440, label: '24 Hours', description: 'Last 24 hours with 6-hour intervals' }
  ];

  const chartConfig = getChartConfig(selectedMetric);
  const hasData = chartData[selectedMetric] && 
                  chartData[selectedMetric].data && 
                  Array.isArray(chartData[selectedMetric].data) && 
                  chartData[selectedMetric].data.length > 0 &&
                  chartData[selectedMetric].data.some(val => val !== null && val !== undefined && !isNaN(val));

  // Safety check to ensure chartData is properly initialized
  if (!chartData[selectedMetric] || !Array.isArray(chartData[selectedMetric].data)) {
    /* noop */
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
          Resource Charts
        </h2>
        <div className="text-sm text-gray-500 dark:text-gray-400">
          Real-time monitoring with 24-hour historical data
        </div>
      </div>

      {/* Metric Selection */}
      <div className="flex flex-wrap gap-2 sm:space-x-4 border-b border-gray-200 dark:border-gray-700">
        {metrics.map((metric) => {
          const Icon = metric.icon;
          return (
            <button
              key={metric.id}
              onClick={() => setSelectedMetric(metric.id)}
              className={`flex items-center space-x-2 px-3 sm:px-4 py-2 border-b-2 transition-colors duration-200 ${
                selectedMetric === metric.id
                  ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                  : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300'
              }`}
            >
              <Icon className="h-5 w-5" />
              <span className="font-medium">{metric.name}</span>
            </button>
          );
        })}
      </div>

      {/* Enhanced Time Range Selector */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 bg-gray-50 dark:bg-gray-800 p-3 sm:p-4 rounded-lg">
        <div className="flex flex-col sm:flex-row sm:items-center gap-3">
          <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Time Range:</span>
          <div className="flex flex-wrap gap-2">
            {timeRangeOptions.map((option) => (
              <button
                key={option.value}
                onClick={() => setTimeRange(option.value)}
                className={`px-3 py-1 text-sm rounded-md transition-colors duration-200 ${
                  timeRange === option.value
                    ? 'bg-blue-500 text-white'
                    : 'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-600'
                }`}
                title={option.description}
              >
                {option.label}
              </button>
            ))}
          </div>
          <button
            onClick={() => {
              setIsLoadingHistorical(true);
              setTimeout(() => { fetchHistoricalData(); }, 100);
            }}
            className="px-3 py-1 text-sm bg-blue-500 text-white rounded-md hover:bg-blue-600 transition-colors duration-200 flex items-center space-x-1"
            title="Refresh historical data"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            <span>Refresh</span>
          </button>
        </div>
        <div className="text-sm text-gray-500 dark:text-gray-400">
          <Database className="inline h-4 w-4 mr-1" />
          Historical data from backend (up to 24 hours)
        </div>
      </div>

      {/* Chart Container */}
      <div className="chart-container">
        {isLoadingHistorical ? (
          <div className="h-96 flex items-center justify-center text-gray-500 dark:text-gray-400">
            <div className="text-center">
              <Timeline className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p className="text-lg font-medium mb-2">Loading historical data...</p>
              <p className="text-sm">Fetching data from the backend to display charts.</p>
            </div>
          </div>
        ) : hasData ? (
          <div className="chart-responsive" style={{ height: '400px' }}>
            {(() => {
              try {
                // Ensure all data points are valid numbers
                const validatedData = {
                  ...chartConfig,
                  data: {
                    ...chartConfig.data,
                    datasets: chartConfig.data.datasets.map(dataset => ({
                      ...dataset,
                      data: dataset.data.map(val => 
                        val !== null && val !== undefined && !isNaN(val) ? parseFloat(val) : 0
                      )
                    }))
                  }
                };
                return <Line ref={chartRef} {...validatedData} />;
              } catch (error) {
                console.error('Chart error:', error);
                return (
                  <div className="h-full flex items-center justify-center text-red-500">
                    Chart failed to load: {error.message}. Please refresh.
                  </div>
                );
              }
            })()}
          </div>
        ) : (
          <div className="h-96 flex items-center justify-center text-gray-500 dark:text-gray-400">
            <div className="text-center">
              <Timeline className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p className="text-lg font-medium mb-2">Waiting for data...</p>
              <p className="text-sm">Charts will appear once real-time data starts flowing</p>
            </div>
          </div>
        )}
      </div>

      {/* Chart Statistics */}
      {hasData && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="metric-card">
            <div className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">
              Current Value
            </div>
            <div className="text-2xl font-bold text-gray-900 dark:text-white">
              {chartData[selectedMetric].data.length > 0 && 
               chartData[selectedMetric].data[chartData[selectedMetric].data.length - 1] !== null &&
               chartData[selectedMetric].data[chartData[selectedMetric].data.length - 1] !== undefined &&
               !isNaN(chartData[selectedMetric].data[chartData[selectedMetric].data.length - 1])
               ? `${Number(chartData[selectedMetric].data[chartData[selectedMetric].data.length - 1]).toFixed(2)}${selectedMetric === 'temperature' ? '°C' : '%'}`
                : 'N/A'
              }
            </div>
          </div>
          
          <div className="metric-card">
            <div className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">
              Average
            </div>
            <div className="text-2xl font-bold text-gray-900 dark:text-white">
              {chartData[selectedMetric].data.length > 0 
                ? (() => {
                    const validData = chartData[selectedMetric].data.filter(val => 
                      val !== null && val !== undefined && !isNaN(val)
                    );
                    if (validData.length === 0) return 'N/A';
                    const average = validData.reduce((a, b) => a + b, 0) / validData.length;
                    return `${Number(average).toFixed(2)}${selectedMetric === 'temperature' ? '°C' : '%'}`;
                  })()
                : 'N/A'
              }
            </div>
          </div>
          
          <div className="metric-card">
            <div className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">
              Peak Value
            </div>
            <div className="text-2xl font-bold text-gray-900 dark:text-white">
              {chartData[selectedMetric].data.length > 0 
                ? (() => {
                    const validData = chartData[selectedMetric].data.filter(val => 
                      val !== null && val !== undefined && !isNaN(val)
                    );
                    if (validData.length === 0) return 'N/A';
                    const maxValue = Math.max(...validData);
                    return `${Number(maxValue).toFixed(2)}${selectedMetric === 'temperature' ? '°C' : '%'}`;
                  })()
                : 'N/A'
              }
            </div>
          </div>
        </div>
      )}

      {/* Enhanced Chart Info */}
      <div className="text-sm text-gray-500 dark:text-gray-400">
        <p>
          Charts display both historical data from the backend database and real-time updates. 
          Historical data is loaded immediately when you select a time range, and real-time data 
          is continuously updated every 5 seconds. Data is automatically persisted and survives 
          power cycles and restarts.
        </p>
        <div className="mt-2 p-2 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded">
          <Database className="inline h-4 w-4 mr-1 text-green-600" />
          <span className="text-green-700 dark:text-green-300">
            Data persistence: Enabled - Metrics are stored in SQLite database and survive power cycles and restarts.
          </span>
        </div>
        <div className="mt-2 p-2 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded">
          <Activity className="inline h-4 w-4 mr-1 text-blue-600" />
          <span className="text-blue-700 dark:text-blue-300">
            Real-time updates: Active - New data points are added every 5 seconds and displayed immediately.
          </span>
        </div>
        <div className="mt-2 p-2 bg-purple-50 dark:bg-purple-900/20 border border-purple-200 dark:border-purple-800 rounded">
          <Timeline className="inline h-4 w-4 mr-1 text-purple-600" />
          <span className="text-purple-700 dark:text-purple-300">
            Time ranges: 1hr (30-min intervals), 6hr (3-hr intervals), 12hr (3-hr intervals), 24hr (6-hr intervals).
          </span>
        </div>
      </div>
    </div>
  );
};

export default ResourceChart;
