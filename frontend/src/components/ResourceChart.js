import React, { useState, useEffect, useRef, useCallback } from 'react';
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
import { TrendingUp, BarChart as BarChart3, Timeline, Bolt, DataObject as Database } from '@mui/icons-material';
import { formatTimestamp, getTickIntervals, formatRelativeTime } from '../utils/format';

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
    cpu: { labels: [], data: [], timestamps: [] },
    memory: { labels: [], data: [], timestamps: [] },
    temperature: { labels: [], data: [], timestamps: [] },
    voltage: { labels: [], data: [], timestamps: [] },
    core_current: { labels: [], data: [], timestamps: [] },
  });
  const [isLoadingHistorical, setIsLoadingHistorical] = useState(true);
  const [lastUpdateTime, setLastUpdateTime] = useState(null);
  
  // Updated time range options with professional intervals
  const [timeRange, setTimeRange] = useState(() => {
    const saved = localStorage.getItem('pi-monitor-time-range');
    return saved ? parseInt(saved) : 60; // Default to last 1 hour
  });
  
  // Get refresh interval from settings (default to 5 seconds if not set)
  const [refreshInterval, setRefreshInterval] = useState(() => {
    try {
      const saved = localStorage.getItem('pi-monitor-settings');
      if (saved) {
        const parsed = JSON.parse(saved);
        return parsed.refreshInterval || 5000; // Default to 5 seconds
      }
    } catch (_) {}
    return 5000; // Default to 5 seconds
  });
  
  const SAMPLE_INTERVAL_SECONDS = refreshInterval / 1000;
  const [maxDataPoints, setMaxDataPoints] = useState(() => {
    const estimated = Math.ceil((timeRange * 60) / SAMPLE_INTERVAL_SECONDS);
    return Math.max(100, estimated);
  });
  
  const chartRef = useRef(null);
  const chartInstanceRef = useRef(null);

  // Save time range to localStorage whenever it changes and recompute max points
  useEffect(() => {
    localStorage.setItem('pi-monitor-time-range', timeRange.toString());
    const estimated = Math.ceil((timeRange * 60) / SAMPLE_INTERVAL_SECONDS);
    setMaxDataPoints(Math.max(100, estimated));
  }, [timeRange, SAMPLE_INTERVAL_SECONDS]);

  // Listen for settings changes (refresh interval updates)
  useEffect(() => {
    const handleSettingsChange = () => {
      try {
        const saved = localStorage.getItem('pi-monitor-settings');
        if (saved) {
          const parsed = JSON.parse(saved);
          if (parsed.refreshInterval && parsed.refreshInterval !== refreshInterval) {
            setRefreshInterval(parsed.refreshInterval);
          }
        }
      } catch (_) {}
    };

    window.addEventListener('storage', handleSettingsChange);
    const interval = setInterval(handleSettingsChange, 1000);
    
    return () => {
      window.removeEventListener('storage', handleSettingsChange);
      clearInterval(interval);
    };
  }, [refreshInterval]);

  // Enhanced timestamp formatting with professional quality
  const formatChartTimestamp = useCallback((timestamp, range) => {
    if (typeof timestamp === 'string') {
      return timestamp;
    }
    
    const date = new Date(timestamp * 1000);
    const now = new Date();
    const isToday = date.toDateString() === now.toDateString();
    const isYesterday = new Date(now.getTime() - 24 * 60 * 60 * 1000).toDateString() === date.toDateString();
    
    // Professional formatting
    if (range >= 1440) { // 24+ hours
      if (isToday) {
        return date.toLocaleTimeString([], { 
          hour: '2-digit', 
          minute: '2-digit',
          hour12: false 
        });
      } else if (isYesterday) {
        return `Yesterday ${date.toLocaleTimeString([], { 
          hour: '2-digit', 
          minute: '2-digit',
          hour12: false 
        })}`;
      } else {
        return date.toLocaleDateString([], { 
          month: 'short', 
          day: 'numeric' 
        }) + ' ' + date.toLocaleTimeString([], { 
          hour: '2-digit', 
          minute: '2-digit',
          hour12: false 
        });
      }
    } else if (range >= 720) { // 12+ hours
      return date.toLocaleTimeString([], { 
        hour: '2-digit', 
        minute: '2-digit',
        hour12: false 
      });
    } else if (range >= 120) { // 2+ hours
      return date.toLocaleTimeString([], { 
        hour: '2-digit', 
        minute: '2-digit',
        hour12: false 
      });
    } else { // < 2 hours
      return date.toLocaleTimeString([], { 
        hour: '2-digit', 
        minute: '2-digit', 
        second: '2-digit',
        hour12: false 
      });
    }
  }, []);

  // Listen for real-time updates with enhanced data handling and performance optimization
  useEffect(() => {
    if (!unifiedClient) return;

    // Professional debounced update for smooth performance
    let updateTimeout;
    let pendingUpdates = [];

    const handleUpdate = (data) => {
      if (data.type === 'initial_stats' || data.type === 'periodic_update' || data.type === 'mqtt_update') {
        const now = new Date();
        const timestamp = now.getTime() / 1000;
        const formattedTimestamp = formatChartTimestamp(timestamp, timeRange);
        const systemData = data.data || data;

        // Collect updates for batch processing
        pendingUpdates.push({
          timestamp,
          formattedTimestamp,
          systemData
        });

        // Clear existing timeout and set new one for debounced update
        clearTimeout(updateTimeout);
        updateTimeout = setTimeout(() => {
          if (pendingUpdates.length > 0) {
            setChartData(prevData => {
              const newData = { ...prevData };
              
              // Process all pending updates in batch
              pendingUpdates.forEach(update => {
                const { timestamp, formattedTimestamp, systemData } = update;
                
                // Update CPU data with proper timestamp handling
                if (systemData.cpu_percent !== undefined && systemData.cpu_percent !== null && !isNaN(systemData.cpu_percent)) {
                  if (!newData.cpu.timestamps.includes(timestamp)) {
                    newData.cpu.timestamps = [...newData.cpu.timestamps, timestamp].slice(-maxDataPoints);
                    newData.cpu.labels = [...newData.cpu.labels, formattedTimestamp].slice(-maxDataPoints);
                    newData.cpu.data = [...newData.cpu.data, parseFloat(systemData.cpu_percent)].slice(-maxDataPoints);
                  }
                }
                
                // Update Memory data
                if (systemData.memory_percent !== undefined && systemData.memory_percent !== null && !isNaN(systemData.memory_percent)) {
                  if (!newData.memory.timestamps.includes(timestamp)) {
                    newData.memory.timestamps = [...newData.memory.timestamps, timestamp].slice(-maxDataPoints);
                    newData.memory.labels = [...newData.memory.labels, formattedTimestamp].slice(-maxDataPoints);
                    newData.memory.data = [...newData.memory.data, parseFloat(systemData.memory_percent)].slice(-maxDataPoints);
                  }
                }
                
                // Update Temperature data
                if (systemData.temperature !== undefined && systemData.temperature !== null && !isNaN(systemData.temperature)) {
                  if (!newData.temperature.timestamps.includes(timestamp)) {
                    newData.temperature.timestamps = [...newData.temperature.timestamps, timestamp].slice(-maxDataPoints);
                    newData.temperature.labels = [...newData.temperature.labels, formattedTimestamp].slice(-maxDataPoints);
                    newData.temperature.data = [...newData.temperature.data, parseFloat(systemData.temperature)].slice(-maxDataPoints);
                  }
                }
                
                // Update Core Voltage data
                if (systemData.voltage !== undefined && systemData.voltage !== null && !isNaN(systemData.voltage)) {
                  if (!newData.voltage.timestamps.includes(timestamp)) {
                    newData.voltage.timestamps = [...newData.voltage.timestamps, timestamp].slice(-maxDataPoints);
                    newData.voltage.labels = [...newData.voltage.labels, formattedTimestamp].slice(-maxDataPoints);
                    newData.voltage.data = [...newData.voltage.data, parseFloat(systemData.voltage)].slice(-maxDataPoints);
                  }
                }

                // Update Core Current data (for voltage overlay only)
                if (systemData.core_current !== undefined && systemData.core_current !== null && !isNaN(systemData.core_current)) {
                  if (!newData.core_current.timestamps.includes(timestamp)) {
                    newData.core_current.timestamps = [...newData.core_current.timestamps, timestamp].slice(-maxDataPoints);
                    newData.core_current.labels = [...newData.core_current.labels, formattedTimestamp].slice(-maxDataPoints);
                    newData.core_current.data = [...newData.core_current.data, parseFloat(systemData.core_current)].slice(-maxDataPoints);
                  }
                }
              });
              
              // Clear processed updates
              pendingUpdates = [];
              return newData;
            });
            
            setLastUpdateTime(now);
          }
        }, 100); // 100ms debounce for smooth performance
      }
    };

    const unsubscribe = unifiedClient.addDataListener(handleUpdate);
    return () => {
      if (unsubscribe) unsubscribe();
      clearTimeout(updateTimeout);
    };
  }, [unifiedClient, timeRange, maxDataPoints, formatChartTimestamp]);

  // Seed with latest cached stats immediately on mount
  useEffect(() => {
    if (!unifiedClient) return;
    const latest = unifiedClient.getLatestStats && unifiedClient.getLatestStats();
    if (!latest) return;
    
    const now = new Date();
    const timestamp = now.getTime() / 1000;
    const formattedTimestamp = formatChartTimestamp(timestamp, timeRange);
    
    setChartData(prevData => {
      const newData = { ...prevData };
      
      if (latest.cpu_percent != null && !isNaN(latest.cpu_percent) && !prevData.cpu.timestamps.includes(timestamp)) {
        newData.cpu.timestamps = [...prevData.cpu.timestamps, timestamp].slice(-maxDataPoints);
        newData.cpu.labels = [...prevData.cpu.labels, formattedTimestamp].slice(-maxDataPoints);
        newData.cpu.data = [...prevData.cpu.data, parseFloat(latest.cpu_percent)].slice(-maxDataPoints);
      }
      if (latest.memory_percent != null && !isNaN(latest.memory_percent) && !prevData.memory.timestamps.includes(timestamp)) {
        newData.memory.timestamps = [...prevData.memory.timestamps, timestamp].slice(-maxDataPoints);
        newData.memory.labels = [...prevData.memory.labels, formattedTimestamp].slice(-maxDataPoints);
        newData.memory.data = [...prevData.memory.data, parseFloat(latest.memory_percent)].slice(-maxDataPoints);
      }
      if (latest.temperature != null && !isNaN(latest.temperature) && !prevData.temperature.timestamps.includes(timestamp)) {
        newData.temperature.timestamps = [...prevData.temperature.timestamps, timestamp].slice(-maxDataPoints);
        newData.temperature.labels = [...prevData.temperature.labels, formattedTimestamp].slice(-maxDataPoints);
        newData.temperature.data = [...prevData.temperature.data, parseFloat(latest.temperature)].slice(-maxDataPoints);
      }
      
      if (latest.voltage != null && !isNaN(latest.voltage) && !prevData.voltage.timestamps.includes(timestamp)) {
        newData.voltage.timestamps = [...prevData.voltage.timestamps, timestamp].slice(-maxDataPoints);
        newData.voltage.labels = [...prevData.voltage.labels, formattedTimestamp].slice(-maxDataPoints);
        newData.voltage.data = [...prevData.voltage.data, parseFloat(latest.voltage)].slice(-maxDataPoints);
      }
      
      return newData;
    });
  }, [unifiedClient, timeRange, maxDataPoints, formatChartTimestamp]);

  const fetchHistoricalData = useCallback(async () => {
    if (!unifiedClient) return;
    setIsLoadingHistorical(true);
    
    try {
      const response = await unifiedClient.getMetricsHistory(timeRange);
      if (response && response.metrics) {
        const metrics = response.metrics;
        const timestamps = metrics.map(m => m.timestamp);
        const labels = metrics.map(m => formatChartTimestamp(m.timestamp, timeRange));
        const cpuData = metrics.map(m => m.cpu_percent || 0);
        const memoryData = metrics.map(m => m.memory_percent || 0);
        const temperatureData = metrics.map(m => m.temperature || 0);
        const voltageData = metrics.map(m => m.voltage || 0);

        setChartData({
          cpu: { labels, data: cpuData, timestamps },
          memory: { labels, data: memoryData, timestamps },
          temperature: { labels, data: temperatureData, timestamps },
          voltage: { labels, data: voltageData, timestamps },
          core_current: { labels, data: metrics.map(m => m.core_current || 0), timestamps },
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
  }, [unifiedClient, timeRange, formatChartTimestamp]);

  // Fetch historical metrics data
  useEffect(() => {
    if (!unifiedClient) return;
    fetchHistoricalData();
    const refreshInterval = Math.max(30000, timeRange * 1000 / 10);
    const interval = setInterval(fetchHistoricalData, refreshInterval);
    return () => clearInterval(interval);
  }, [unifiedClient, timeRange, fetchHistoricalData]);

  // Professional chart configuration
  const getChartConfig = useCallback((metric) => {
    const isDarkMode = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
    const intervals = getTickIntervals(timeRange);
    
    const colors = {
      cpu: {
        background: 'rgba(59, 130, 246, 0.08)',
        border: 'rgb(59, 130, 246)',
        point: 'rgb(59, 130, 246)',
        hover: 'rgba(59, 130, 246, 0.2)',
      },
      memory: {
        background: 'rgba(147, 51, 234, 0.08)',
        border: 'rgb(147, 51, 234)',
        point: 'rgb(147, 51, 234)',
        hover: 'rgba(147, 51, 234, 0.2)',
      },
      temperature: {
        background: 'rgba(239, 68, 68, 0.08)',
        border: 'rgb(239, 68, 68)',
        point: 'rgb(239, 68, 68)',
        hover: 'rgba(239, 68, 68, 0.2)',
      },
      voltage: {
        background: 'rgba(34, 197, 94, 0.08)',
        border: 'rgb(34, 197, 94)',
        point: 'rgb(34, 197, 94)',
        hover: 'rgba(34, 197, 94, 0.2)',
      },
      core_current: {
        background: 'rgba(107, 114, 128, 0.08)', // A neutral color for current
        border: 'rgb(107, 114, 128)',
        point: 'rgb(107, 114, 128)',
        hover: 'rgba(107, 114, 128, 0.2)',
      },
    };

    // Special configuration for voltage chart to overlay current
    if (metric === 'voltage') {
      return {
        data: {
          labels: chartData[metric].labels,
          datasets: [
            {
              label: 'Core Voltage (V)',
              data: chartData[metric].data,
              borderColor: colors[metric].border,
              backgroundColor: colors[metric].background,
              pointBackgroundColor: colors[metric].point,
              pointBorderColor: colors[metric].border,
              pointRadius: 0,
              pointHoverRadius: 6,
              pointHitRadius: 10,
              tension: 0.3,
              fill: true,
              borderWidth: 2,
              fillOpacity: 0.1,
              yAxisID: 'y',
            },
            {
              label: 'Core Current (A)',
              data: chartData.core_current.data,
              borderColor: colors.core_current.border,
              backgroundColor: colors.core_current.background,
              pointBackgroundColor: colors.core_current.point,
              pointBorderColor: colors.core_current.border,
              pointRadius: 0,
              pointHoverRadius: 6,
              pointHitRadius: 10,
              tension: 0.3,
              fill: false,
              borderWidth: 2,
              yAxisID: 'y1',
            }
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          interaction: {
            mode: 'nearest',
            axis: 'x',
            intersect: false,
          },
          plugins: {
            legend: {
              position: 'top',
              labels: {
                color: isDarkMode ? '#e5e7eb' : '#374151',
                font: {
                  size: 12,
                  weight: '500',
                },
                usePointStyle: true,
                pointStyle: 'circle',
                padding: 20,
              },
            },
            title: {
              display: false,
            },
            tooltip: {
              mode: 'index',
              intersect: false,
              backgroundColor: isDarkMode ? '#1f2937' : '#ffffff',
              titleColor: isDarkMode ? '#f9fafb' : '#111827',
              bodyColor: isDarkMode ? '#e5e7eb' : '#374151',
              borderColor: isDarkMode ? '#4b5563' : '#d1d5db',
              borderWidth: 1,
              borderRadius: 8,
              padding: 12,
              displayColors: true,
              callbacks: {
                title: function(context) {
                  const label = context[0].label;
                  if (lastUpdateTime && label.includes('Just now')) {
                    return `${label} (${formatRelativeTime(lastUpdateTime.getTime() / 1000)})`;
                  }
                  return label;
                },
                label: function(context) {
                  const value = context.parsed && context.parsed.y != null ? context.parsed.y : null;
                  const datasetLabel = context.dataset && context.dataset.label ? context.dataset.label : '';
                  if (value == null || isNaN(value)) return datasetLabel;
                  
                  if (datasetLabel.includes('Voltage')) {
                    return `${datasetLabel}: ${Number(value).toFixed(3)}V`;
                  } else if (datasetLabel.includes('Current')) {
                    return `${datasetLabel}: ${Number(value).toFixed(3)}A`;
                  }
                  return datasetLabel;
                }
              }
            },
          },
          scales: {
            x: {
              type: 'category',
              ticks: {
                maxTicksLimit: intervals.maxTicks,
                autoSkip: true,
                maxRotation: 0,
                minRotation: 0,
                color: isDarkMode ? '#9ca3af' : '#6b7280',
                font: {
                  size: 11,
                  weight: '500',
                },
                padding: 8,
                callback: function(value, index, ticks) {
                  const label = this.getLabelForValue(value);
                  if (!label) return '';
                  
                  if (timeRange >= 1440) {
                    return label;
                  } else if (timeRange >= 720) {
                    return label.split(' ').pop();
                  } else {
                    return label;
                  }
                }
              },
              grid: {
                color: isDarkMode ? '#374151' : '#e5e7eb',
                lineWidth: 0.5,
              },
              border: {
                color: isDarkMode ? '#4b5563' : '#d1d5db',
              },
              title: {
                display: false,
              }
            },
            y: {
              type: 'linear',
              display: true,
              position: 'left',
              min: 0,
              max: 1.0,
              ticks: {
                color: isDarkMode ? '#9ca3af' : '#6b7280',
                font: {
                  size: 11,
                  weight: '500',
                },
                stepSize: 0.1,
                padding: 8,
                callback: function(value) {
                  return `${value}V`;
                }
              },
              grid: {
                color: isDarkMode ? '#374151' : '#e5e7eb',
                lineWidth: 0.5,
              },
              border: {
                color: isDarkMode ? '#4b5563' : '#d1d5db',
              },
              title: {
                display: false,
              }
            },
            y1: {
              type: 'linear',
              display: true,
              position: 'right',
              min: 0,
              max: 10,
              ticks: {
                color: isDarkMode ? '#9ca3af' : '#6b7280',
                font: {
                  size: 11,
                  weight: '500',
                },
                stepSize: 2,
                padding: 8,
                callback: function(value) {
                  return `${value}A`;
                }
              },
              grid: {
                drawOnChartArea: false,
              },
              border: {
                color: isDarkMode ? '#4b5563' : '#d1d5db',
              },
              title: {
                display: false,
              }
            }
          },
          elements: {
            line: {
              borderWidth: 2,
            },
            point: {
              hoverRadius: 6,
              hitRadius: 10,
            },
          },
          animation: {
            duration: 0,
          },
          animations: {
            y: { 
              duration: 0 
            },
            x: { 
              duration: 300, 
              easing: 'easeOutQuart' 
            }
          },
          responsiveBreakpoints: {
            mobile: 768,
            tablet: 1024,
            desktop: 1200,
          },
        },
      };
    }

    // Standard configuration for other metrics
    return {
      data: {
        labels: chartData[metric].labels,
        datasets: [
          {
            label: metric === 'cpu' ? 'CPU Usage (%)' : 
                   metric === 'memory' ? 'Memory Usage (%)' : 
                   metric === 'temperature' ? 'Temperature (°C)' :
                   metric === 'voltage' ? 'Core Voltage (V)' :
                   'Core Current (A)',
            data: chartData[metric].data,
            borderColor: colors[metric].border,
            backgroundColor: colors[metric].background,
            pointBackgroundColor: colors[metric].point,
            pointBorderColor: colors[metric].border,
            pointRadius: 0, // Hide points by default for cleaner look
            pointHoverRadius: 6,
            pointHitRadius: 10,
            tension: 0.3, // Subtle curve
            fill: true,
            borderWidth: 2,
            fillOpacity: 0.1,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
          mode: 'nearest',
          axis: 'x',
          intersect: false,
        },
        plugins: {
          legend: {
            position: 'top',
            labels: {
              color: isDarkMode ? '#e5e7eb' : '#374151',
              font: {
                size: 12,
                weight: '500',
              },
              usePointStyle: true,
              pointStyle: 'circle',
              padding: 20,
            },
          },
          title: {
            display: false, // Cleaner without title
          },
          tooltip: {
            mode: 'index',
            intersect: false,
            backgroundColor: isDarkMode ? '#1f2937' : '#ffffff',
            titleColor: isDarkMode ? '#f9fafb' : '#111827',
            bodyColor: isDarkMode ? '#e5e7eb' : '#374151',
            borderColor: isDarkMode ? '#4b5563' : '#d1d5db',
            borderWidth: 1,
            borderRadius: 8,
            padding: 12,
            displayColors: true,
            callbacks: {
              title: function(context) {
                const label = context[0].label;
                if (lastUpdateTime && label.includes('Just now')) {
                  return `${label} (${formatRelativeTime(lastUpdateTime.getTime() / 1000)})`;
                }
                return label;
              },
              label: function(context) {
                const value = context.parsed && context.parsed.y != null ? context.parsed.y : null;
                let unit = '%';
                if (metric === 'temperature') unit = '°C';
                else if (metric === 'voltage') unit = 'V';
                const datasetLabel = context.dataset && context.dataset.label ? context.dataset.label : '';
                if (value == null || isNaN(value)) return datasetLabel;
                const precision = metric === 'voltage' ? 3 : 1;
                return `${datasetLabel}: ${Number(value).toFixed(precision)}${unit}`;
              }
            }
          },
        },
        scales: {
          x: {
            type: 'category',
            ticks: {
              maxTicksLimit: intervals.maxTicks,
              autoSkip: true,
              maxRotation: 0,
              minRotation: 0,
              color: isDarkMode ? '#9ca3af' : '#6b7280',
              font: {
                size: 11,
                weight: '500',
              },
              padding: 8,
              callback: function(value, index, ticks) {
                // Professional tick formatting
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
            grid: {
              color: isDarkMode ? '#374151' : '#e5e7eb',
              lineWidth: 0.5,
            },
            border: {
              color: isDarkMode ? '#4b5563' : '#d1d5db',
            },
            title: {
              display: false, // Cleaner without axis title
            }
          },
          y: {
            display: true,
            min: 0,
            max: metric === 'temperature' ? 100 : metric === 'voltage' ? 1.0 : 100,
            ticks: {
              color: isDarkMode ? '#9ca3af' : '#6b7280',
              font: {
                size: 11,
                weight: '500',
              },
              stepSize: metric === 'temperature' ? 20 : metric === 'voltage' ? 0.1 : 25,
              padding: 8,
              callback: function(value) {
                if (metric === 'temperature') return `${value}°C`;
                else if (metric === 'voltage') return `${value}V`;
                else return `${value}%`;
              }
            },
            grid: {
              color: isDarkMode ? '#374151' : '#e5e7eb',
              lineWidth: 0.5,
            },
            border: {
              color: isDarkMode ? '#4b5563' : '#d1d5db',
            },
            title: {
              display: false,
            },
          },
        },
        elements: {
          line: {
            borderWidth: 2,
          },
          point: {
            hoverRadius: 6,
            hitRadius: 10,
          },
        },
        // Professional animations
        animation: {
          duration: 0,
        },
        animations: {
          y: { 
            duration: 0 
          },
          x: { 
            duration: 300, 
            easing: 'easeOutQuart' 
          }
        },
        // Responsive breakpoints
        responsiveBreakpoints: {
          mobile: 768,
          tablet: 1024,
          desktop: 1200,
        },
      },
    };
  }, [chartData, timeRange, lastUpdateTime]);

  const metrics = [
    { id: 'cpu', name: 'CPU Usage', icon: TrendingUp, color: 'text-blue-600' },
    { id: 'memory', name: 'Memory Usage', icon: TrendingUp, color: 'text-purple-600' },
    { id: 'temperature', name: 'Temperature', icon: TrendingUp, color: 'text-red-600' },
    { id: 'voltage', name: 'Core Voltage', icon: Bolt, color: 'text-green-600' },
  ];

  // Professional time range options
  const timeRangeOptions = [
    { value: 60, label: '1 Hour', description: 'High-resolution view with 5-min intervals' },
    { value: 360, label: '6 Hours', description: 'Balanced view with 30-min intervals' },
    { value: 720, label: '12 Hours', description: 'Overview with 1-hour intervals' },
    { value: 1440, label: '24 Hours', description: 'Daily summary with 6-hour intervals' }
  ];

  const chartConfig = getChartConfig(selectedMetric);
  const hasData = chartData[selectedMetric] && 
                  chartData[selectedMetric].data && 
                  Array.isArray(chartData[selectedMetric].data) && 
                  chartData[selectedMetric].data.length > 0 &&
                  chartData[selectedMetric].data.some(val => val !== null && val !== undefined && !isNaN(val));

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
          Resource Charts
        </h2>
        <div className="text-sm text-gray-500 dark:text-gray-400">
          Resource monitoring with time scaling
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
              className={`flex items-center space-x-2 px-3 sm:px-4 py-2 border-b-2 transition-all duration-200 ${
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
                className={`px-3 py-1 text-sm rounded-md transition-all duration-200 ${
                  timeRange === option.value
                    ? 'bg-blue-500 text-white shadow-md'
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
            className="px-3 py-1 text-sm bg-blue-500 text-white rounded-md hover:bg-blue-600 transition-all duration-200 flex items-center space-x-1 shadow-md"
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
          Time scaling with {getTickIntervals(timeRange).maxTicks} ticks
        </div>
      </div>

      {/* Chart Container */}
      <div className="chart-container">
        {isLoadingHistorical ? (
          <div className="h-96 flex items-center justify-center text-gray-500 dark:text-gray-400">
            <div className="text-center">
              <Timeline className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p className="text-lg font-medium mb-2">Loading historical data...</p>
              <p className="text-sm">Fetching data with professional formatting</p>
            </div>
          </div>
        ) : hasData ? (
          <div className="chart-responsive" style={{ height: '450px', minHeight: '400px' }}>
            {(() => {
              try {
                // Ensure all data points are valid numbers and add professional data validation
                const validatedData = {
                  ...chartConfig,
                  data: {
                    ...chartConfig.data,
                    datasets: chartConfig.data.datasets.map(dataset => ({
                      ...dataset,
                      data: dataset.data.map(val => {
                        const numVal = val !== null && val !== undefined && !isNaN(val) ? parseFloat(val) : 0;
                        // Professional data validation: clamp values to reasonable ranges
                        if (dataset.label.includes('Temperature')) {
                          return Math.max(-20, Math.min(120, numVal)); // -20°C to 120°C
                        } else if (dataset.label.includes('Usage')) {
                          return Math.max(0, Math.min(100, numVal)); // 0% to 100%
                        } else if (dataset.label.includes('Voltage')) {
                          return Math.max(0, Math.min(1.0, numVal)); // 0V to 1.0V
                        }
                        return numVal;
                      })
                    }))
                  }
                };
                return <Line ref={chartRef} {...validatedData} />;
              } catch (error) {
                console.error('Chart error:', error);
                return (
                  <div className="h-full flex items-center justify-center text-red-500">
                    <div className="text-center">
                      <svg className="w-12 h-12 mx-auto mb-4 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z" />
                      </svg>
                      <p className="text-lg font-medium mb-2">Chart Error</p>
                      <p className="text-sm">{error.message}</p>
                      <button 
                        onClick={() => window.location.reload()} 
                        className="mt-3 px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 transition-colors"
                      >
                        Refresh Page
                      </button>
                    </div>
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
               ? (() => {
                   const value = Number(chartData[selectedMetric].data[chartData[selectedMetric].data.length - 1]);
                   if (selectedMetric === 'temperature') return `${value.toFixed(1)}°C`;
                   else if (selectedMetric === 'voltage') return `${value.toFixed(3)}V`;
                   else return `${value.toFixed(1)}%`;
                 })()
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
                    if (selectedMetric === 'temperature') return `${Number(average).toFixed(1)}°C`;
                    else if (selectedMetric === 'voltage') return `${Number(average).toFixed(3)}V`;
                    else return `${Number(average).toFixed(1)}%`;
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
                    if (selectedMetric === 'temperature') return `${Number(maxValue).toFixed(1)}°C`;
                    else if (selectedMetric === 'voltage') return `${Number(maxValue).toFixed(3)}V`;
                    else return `${Number(maxValue).toFixed(1)}%`;
                  })()
                : 'N/A'
              }
            </div>
          </div>
        </div>
      )}

      {/* Real-time Status Indicator */}
      {lastUpdateTime && (
        <div className="flex items-center justify-between p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
          <div className="flex items-center space-x-2">
            <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
            <span className="text-sm font-medium text-blue-700 dark:text-blue-300">
              Real-time monitoring active
            </span>
          </div>
          <div className="text-xs text-blue-600 dark:text-blue-400">
            Last update: {formatRelativeTime(lastUpdateTime.getTime() / 1000)}
          </div>
        </div>
      )}
    </div>
  );
};

export default ResourceChart;
