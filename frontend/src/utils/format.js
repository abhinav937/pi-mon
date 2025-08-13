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


