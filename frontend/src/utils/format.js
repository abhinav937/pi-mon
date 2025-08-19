// Utility functions for formatting values across the app

export const formatBytes = (bytes) => {
  if (bytes === 0) return '0 B';
  if (bytes == null || isNaN(bytes)) return 'N/A';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  const value = bytes / Math.pow(k, i);
  return `${parseFloat(value.toFixed(2))} ${sizes[i]}`;
};

export const formatSpeed = (bytesPerSecond) => {
  if (bytesPerSecond == null || isNaN(bytesPerSecond)) return 'N/A';
  return `${formatBytes(bytesPerSecond)}/s`;
};

// Professional time formatting utilities
export const formatTimestamp = (timestamp, timeRange, options = {}) => {
  if (typeof timestamp === 'string') {
    return timestamp;
  }
  
  const date = new Date(timestamp * 1000);
  const now = new Date();
  const isToday = date.toDateString() === now.toDateString();
  const isYesterday = new Date(now.getTime() - 24 * 60 * 60 * 1000).toDateString() === date.toDateString();
  const hm = { hour: '2-digit', minute: '2-digit', hour12: false };
  
  // Always exclude seconds; prefix Yesterday when applicable
  if (isYesterday) {
    return `Yesterday ${date.toLocaleTimeString([], hm)}`;
  }
  if (isToday) {
    return date.toLocaleTimeString([], hm);
  }
  return (
    date.toLocaleDateString([], { month: 'short', day: 'numeric' }) +
    ' ' +
    date.toLocaleTimeString([], hm)
  );
};

// Generate optimal tick intervals for different time ranges
export const getTickIntervals = (timeRange) => {
  if (timeRange >= 1440) { // 24+ hours
    return {
      major: 6 * 60 * 60 * 1000, // 6 hours
      minor: 2 * 60 * 60 * 1000, // 2 hours
      format: 'hour',
      maxTicks: 8
    };
  } else if (timeRange >= 720) { // 12+ hours
    return {
      major: 3 * 60 * 60 * 1000, // 3 hours
      minor: 1 * 60 * 60 * 1000, // 1 hour
      format: 'hour',
      maxTicks: 6
    };
  } else if (timeRange >= 120) { // 2+ hours
    return {
      major: 30 * 60 * 1000, // 30 minutes
      minor: 15 * 60 * 1000, // 15 minutes
      format: 'minute',
      maxTicks: 8
    };
  } else { // < 2 hours
    return {
      major: 10 * 60 * 1000, // 10 minutes
      minor: 5 * 60 * 1000, // 5 minutes
      format: 'minute',
      maxTicks: 12
    };
  }
};

// Generate time labels for x-axis
export const generateTimeLabels = (startTime, endTime, timeRange) => {
  const intervals = getTickIntervals(timeRange);
  const labels = [];
  const current = new Date(startTime);
  
  while (current <= endTime) {
    labels.push(formatTimestamp(current.getTime() / 1000, timeRange));
    current.setTime(current.getTime() + intervals.major);
  }
  
  return labels;
};

// Format relative time (e.g., "2 hours ago", "5 minutes ago")
export const formatRelativeTime = (timestamp) => {
  const now = new Date();
  const date = new Date(timestamp * 1000);
  const diffMs = now - date;
  const diffMins = Math.floor(diffMs / (1000 * 60));
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
  
  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins} minute${diffMins !== 1 ? 's' : ''} ago`;
  if (diffHours < 24) return `${diffHours} hour${diffHours !== 1 ? 's' : ''} ago`;
  if (diffDays < 7) return `${diffDays} day${diffDays !== 1 ? 's' : ''} ago`;
  
  return date.toLocaleDateString();
};


