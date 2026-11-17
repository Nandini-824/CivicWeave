export const PRIORITY_COLORS = {
  Low: 'bg-green-100 text-green-800',
  Medium: 'bg-amber-100 text-amber-800',
  High: 'bg-orange-100 text-orange-800',
  Critical: 'bg-red-100 text-red-800',
};

export const STATUS_COLORS = {
  Submitted: 'bg-blue-100 text-blue-800',
  'Under Review': 'bg-purple-100 text-purple-800',
  Assigned: 'bg-indigo-100 text-indigo-800',
  'In Progress': 'bg-yellow-100 text-yellow-800',
  Resolved: 'bg-green-100 text-green-800',
  Closed: 'bg-gray-100 text-gray-800',
  Reopened: 'bg-red-100 text-red-800',
};

export function formatDate(dateStr) {
  if (!dateStr) return '-';
  return new Date(dateStr).toLocaleDateString('en-IN', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

export function formatDateTime(dateStr) {
  if (!dateStr) return '-';
  return new Date(dateStr).toLocaleString('en-IN', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export const CATEGORIES = [
  'Roads and Potholes',
  'Water Supply',
  'Drainage and Sewage',
  'Garbage and Sanitation',
  'Street Lighting',
  'Electricity',
  'Public Infrastructure',
  'Other',
];

export function getDashboardPath(role) {
  switch (role) {
    case 'admin': return '/admin';
    case 'officer': return '/officer';
    default: return '/dashboard';
  }
}
