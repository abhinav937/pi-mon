// Utility helpers for color/status mapping

export const getStatusColor = (percentage) => {
  if (percentage === null || percentage === undefined || isNaN(percentage)) return 'text-gray-500';
  if (percentage >= 90) return 'text-red-600';
  if (percentage >= 70) return 'text-yellow-600';
  return 'text-green-600';
};

export const getProgressBarColor = (percentage) => {
  if (percentage === null || percentage === undefined || isNaN(percentage)) return 'bg-gray-400';
  if (percentage >= 90) return 'bg-red-500';
  if (percentage >= 70) return 'bg-yellow-500';
  return 'bg-green-500';
};

export const getStatusBadgeClass = (status) => {
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


