import React from 'react';
import { useQuery, useMutation, useQueryClient } from 'react-query';
import { PlayArrow as Play, Stop as Square, RestartAlt as RotateCcw, Refresh as RefreshCw, Settings, CheckCircle, ErrorOutline as AlertCircle, Cancel as XCircle } from '@mui/icons-material';
import toast from 'react-hot-toast';

function ServiceManagement({ unifiedClient }) {
  const queryClient = useQueryClient();

  // Query for services
  const { data: services, isLoading, error: queryError, refetch } = useQuery(
    'services',
    async () => {
      if (!unifiedClient) return [];
      return await unifiedClient.getServices();
    },
    {
      enabled: !!unifiedClient,
      refetchInterval: 10000, // Refetch every 10 seconds
      onError: (err) => {
        toast.error('Failed to fetch services');
        console.error('Services error:', err);
      },
    }
  );

  // Mutation for service actions
  const serviceMutation = useMutation(
    async ({ serviceName, action }) => {
      if (!unifiedClient) throw new Error('Client not available');
      return await unifiedClient.controlService(serviceName, action);
    },
    {
      onSuccess: (data, variables) => {
        toast.success(data.message || `Service ${variables.action} completed`);
        // Refetch services to get updated status
        queryClient.invalidateQueries('services');
      },
      onError: (error, variables) => {
        toast.error(error.message || `Failed to ${variables.action} service ${variables.serviceName}`);
      },
    }
  );

  const handleServiceAction = (serviceName, action) => {
    serviceMutation.mutate({ serviceName, action });
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'running':
        return <CheckCircle className="h-5 w-5 text-green-600 dark:text-green-400" />;
      case 'stopped':
        return <Square className="h-5 w-5 text-gray-600 dark:text-gray-400" />;
      case 'failed':
        return <XCircle className="h-5 w-5 text-red-600 dark:text-red-400" />;
      default:
        return <AlertCircle className="h-5 w-5 text-yellow-600 dark:text-yellow-400" />;
    }
  };

  const getStatusBadgeClass = (status) => {
    switch (status) {
      case 'running':
        return 'status-badge-success';
      case 'stopped':
        return 'status-badge-info';
      case 'failed':
        return 'status-badge-error';
      default:
        return 'status-badge-warning';
    }
  };

  const ServiceCard = ({ service }) => (
    <div className="metric-card transition-all duration-200 hover:shadow-md">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-3">
          {getStatusIcon(service.status)}
          <div>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
              {service.name}
            </h3>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              {service.description || 'System service'}
            </p>
          </div>
        </div>
        <span className={getStatusBadgeClass(service.status)}>
          {service.status}
        </span>
      </div>

      <div className="grid grid-cols-2 gap-2 mb-4 text-sm">
        <div>
          <span className="text-gray-500 dark:text-gray-400">Active:</span>
          <span className={`ml-2 font-medium ${service.active ? 'text-green-600' : 'text-red-600'}`}>
            {service.active ? 'Yes' : 'No'}
          </span>
        </div>
        <div>
          <span className="text-gray-500 dark:text-gray-400">Enabled:</span>
          <span className={`ml-2 font-medium ${service.enabled ? 'text-green-600' : 'text-yellow-600'}`}>
            {service.enabled ? 'Yes' : 'No'}
          </span>
        </div>
      </div>

      <div className="flex space-x-2">
        {service.status !== 'running' && (
          <button
            onClick={() => handleServiceAction(service.name, 'start')}
            disabled={serviceMutation.isLoading}
            className="flex-1 flex items-center justify-center px-3 py-2 bg-green-600 hover:bg-green-700 text-white text-sm font-medium rounded-md transition-colors duration-200 disabled:opacity-50"
          >
            <Play className="h-4 w-4 mr-1" />
            Start
          </button>
        )}
        
        {service.status === 'running' && (
          <button
            onClick={() => handleServiceAction(service.name, 'stop')}
            disabled={serviceMutation.isLoading}
            className="flex-1 flex items-center justify-center px-3 py-2 bg-red-600 hover:bg-red-700 text-white text-sm font-medium rounded-md transition-colors duration-200 disabled:opacity-50"
          >
            <Square className="h-4 w-4 mr-1" />
            Stop
          </button>
        )}
        
        <button
          onClick={() => handleServiceAction(service.name, 'restart')}
          disabled={serviceMutation.isLoading}
          className="flex-1 flex items-center justify-center px-3 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-md transition-colors duration-200 disabled:opacity-50"
        >
          <RotateCcw className="h-4 w-4 mr-1" />
          Restart
        </button>
      </div>
    </div>
  );

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

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
          Service Management
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

      {/* Services Overview */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="metric-card">
          <div className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">
            Total Services
          </div>
          <div className="text-2xl font-bold text-gray-900 dark:text-white">
            {services?.length || 0}
          </div>
        </div>
        
        <div className="metric-card">
          <div className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">
            Running
          </div>
          <div className="text-2xl font-bold text-green-600 dark:text-green-400">
            {services?.filter(s => s.status === 'running').length || 0}
          </div>
        </div>
        
        <div className="metric-card">
          <div className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">
            Stopped
          </div>
          <div className="text-2xl font-bold text-gray-600 dark:text-gray-400">
            {services?.filter(s => s.status === 'stopped').length || 0}
          </div>
        </div>
        
        <div className="metric-card">
          <div className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">
            Failed
          </div>
          <div className="text-2xl font-bold text-red-600 dark:text-red-400">
            {services?.filter(s => s.status === 'failed').length || 0}
          </div>
        </div>
      </div>

      {/* Services List */}
      {queryError ? (
        <div className="metric-card bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800">
          <div className="text-center">
            <AlertCircle className="h-8 w-8 text-red-600 dark:text-red-400 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-red-800 dark:text-red-200 mb-2">
              Failed to Load Services
            </h3>
            <p className="text-red-600 dark:text-red-400 mb-4">
              {queryError.message || 'Unable to fetch services from the server'}
            </p>
            <button
              onClick={() => refetch()}
              className="button-primary bg-red-600 hover:bg-red-700"
            >
              Try Again
            </button>
          </div>
        </div>
      ) : services && services.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {services.map((service) => (
            <ServiceCard key={service.name} service={service} />
          ))}
        </div>
      ) : (
        <div className="metric-card">
          <div className="text-center py-8">
            <Settings className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
              No Services Found
            </h3>
            <p className="text-gray-500 dark:text-gray-400">
              No system services are currently available for management.
            </p>
          </div>
        </div>
      )}

      {/* Service Actions Info */}
      <div className="metric-card">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          Service Actions
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
          <div className="flex items-start space-x-3">
            <Play className="h-5 w-5 text-green-600 dark:text-green-400 flex-shrink-0 mt-0.5" />
            <div>
              <div className="font-medium text-gray-900 dark:text-white">Start</div>
              <div className="text-gray-600 dark:text-gray-400">
                Start a stopped service
              </div>
            </div>
          </div>
          
          <div className="flex items-start space-x-3">
            <Square className="h-5 w-5 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
            <div>
              <div className="font-medium text-gray-900 dark:text-white">Stop</div>
              <div className="text-gray-600 dark:text-gray-400">
                Stop a running service
              </div>
            </div>
          </div>
          
          <div className="flex items-start space-x-3">
            <RotateCcw className="h-5 w-5 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5" />
            <div>
              <div className="font-medium text-gray-900 dark:text-white">Restart</div>
              <div className="text-gray-600 dark:text-gray-400">
                Restart a service (stop then start)
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ServiceManagement;
