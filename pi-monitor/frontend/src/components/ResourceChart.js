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
} from 'chart.js';
import { TrendingUp, BarChart3, Activity } from 'lucide-react';

// Register Chart.js components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

const ResourceChart = ({ unifiedClient }) => {
  const [selectedMetric, setSelectedMetric] = useState('cpu');
  const [chartData, setChartData] = useState({
    cpu: { labels: [], data: [] },
    memory: { labels: [], data: [] },
    temperature: { labels: [], data: [] },
  });
  const maxDataPoints = 50;

  // Listen for real-time updates
  useEffect(() => {
    if (!unifiedClient) return;

    const originalOnDataUpdate = unifiedClient.onDataUpdate;
    unifiedClient.onDataUpdate = (data) => {
      if (data.type === 'initial_stats' || data.type === 'periodic_update' || data.type === 'mqtt_update') {
        const timestamp = new Date().toLocaleTimeString();
        const systemData = data.data || data;

        setChartData(prevData => {
          const newData = { ...prevData };
          
          // Update CPU data
          if (systemData.cpu_percent !== undefined) {
            newData.cpu.labels = [...prevData.cpu.labels, timestamp].slice(-maxDataPoints);
            newData.cpu.data = [...prevData.cpu.data, systemData.cpu_percent].slice(-maxDataPoints);
          }
          
          // Update Memory data
          if (systemData.memory_percent !== undefined) {
            newData.memory.labels = [...prevData.memory.labels, timestamp].slice(-maxDataPoints);
            newData.memory.data = [...prevData.memory.data, systemData.memory_percent].slice(-maxDataPoints);
          }
          
          // Update Temperature data
          if (systemData.temperature !== undefined) {
            newData.temperature.labels = [...prevData.temperature.labels, timestamp].slice(-maxDataPoints);
            newData.temperature.data = [...prevData.temperature.data, systemData.temperature].slice(-maxDataPoints);
          }
          
          return newData;
        });
      }
      originalOnDataUpdate(data);
    };

    return () => {
      unifiedClient.onDataUpdate = originalOnDataUpdate;
    };
  }, [unifiedClient]);

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
    };

    return {
      data: {
        labels: chartData[metric].labels,
        datasets: [
          {
            label: metric === 'cpu' ? 'CPU Usage (%)' : 
                   metric === 'memory' ? 'Memory Usage (%)' : 
                   'Temperature (°C)',
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
          },
        },
        interaction: {
          mode: 'nearest',
          axis: 'x',
          intersect: false,
        },
        scales: {
          x: {
            display: true,
            title: {
              display: true,
              text: 'Time',
              color: isDarkMode ? '#9ca3af' : '#6b7280',
            },
            ticks: {
              color: isDarkMode ? '#9ca3af' : '#6b7280',
              maxTicksLimit: 10,
            },
            grid: {
              color: isDarkMode ? '#374151' : '#e5e7eb',
            },
          },
          y: {
            display: true,
            title: {
              display: true,
              text: metric === 'temperature' ? 'Temperature (°C)' : 'Usage (%)',
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
        animation: {
          duration: 300,
        },
      },
    };
  };

  const metrics = [
    { id: 'cpu', name: 'CPU Usage', icon: Activity, color: 'text-blue-600' },
    { id: 'memory', name: 'Memory Usage', icon: BarChart3, color: 'text-purple-600' },
    { id: 'temperature', name: 'Temperature', icon: TrendingUp, color: 'text-red-600' },
  ];

  const chartConfig = getChartConfig(selectedMetric);
  const hasData = chartData[selectedMetric].data.length > 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
          Resource Charts
        </h2>
        <div className="text-sm text-gray-500 dark:text-gray-400">
          Real-time monitoring
        </div>
      </div>

      {/* Metric Selection */}
      <div className="flex space-x-4 border-b border-gray-200 dark:border-gray-700">
        {metrics.map((metric) => {
          const Icon = metric.icon;
          return (
            <button
              key={metric.id}
              onClick={() => setSelectedMetric(metric.id)}
              className={`flex items-center space-x-2 px-4 py-2 border-b-2 transition-colors duration-200 ${
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

      {/* Chart Container */}
      <div className="chart-container">
        {hasData ? (
          <div className="chart-responsive" style={{ height: '400px' }}>
            <Line {...chartConfig} />
          </div>
        ) : (
          <div className="h-96 flex items-center justify-center text-gray-500 dark:text-gray-400">
            <div className="text-center">
              <Activity className="h-12 w-12 mx-auto mb-4 opacity-50" />
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
              {chartData[selectedMetric].data.length > 0 
                ? `${chartData[selectedMetric].data[chartData[selectedMetric].data.length - 1].toFixed(1)}${selectedMetric === 'temperature' ? '°C' : '%'}`
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
                ? `${(chartData[selectedMetric].data.reduce((a, b) => a + b, 0) / chartData[selectedMetric].data.length).toFixed(1)}${selectedMetric === 'temperature' ? '°C' : '%'}`
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
                ? `${Math.max(...chartData[selectedMetric].data).toFixed(1)}${selectedMetric === 'temperature' ? '°C' : '%'}`
                : 'N/A'
              }
            </div>
          </div>
        </div>
      )}

      {/* Chart Info */}
      <div className="text-sm text-gray-500 dark:text-gray-400">
        <p>
          Charts show real-time system metrics over the last {maxDataPoints} data points. 
          Data is automatically updated as new system information becomes available.
        </p>
      </div>
    </div>
  );
};

export default ResourceChart;