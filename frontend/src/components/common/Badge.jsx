import { PRIORITY_COLORS, STATUS_COLORS } from '../../utils/helpers';

export function PriorityBadge({ priority }) {
  const cls = PRIORITY_COLORS[priority] || 'bg-gray-100 text-gray-800';
  return (
    <span className={`inline-flex px-2.5 py-0.5 rounded-full text-xs font-medium ${cls}`}>
      {priority || 'Unknown'}
    </span>
  );
}

export function StatusBadge({ status }) {
  const cls = STATUS_COLORS[status] || 'bg-gray-100 text-gray-800';
  return (
    <span className={`inline-flex px-2.5 py-0.5 rounded-full text-xs font-medium ${cls}`}>
      {status}
    </span>
  );
}

export function MetricCard({ title, value, icon: Icon, color = 'bg-[#1e3a5f]' }) {
  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-100 p-5">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-gray-500">{title}</p>
          <p className="text-2xl font-bold text-[#1e3a5f] mt-1">{value}</p>
        </div>
        {Icon && (
          <div className={`${color} p-3 rounded-lg text-white`}>
            <Icon size={24} />
          </div>
        )}
      </div>
    </div>
  );
}

export function LoadingSpinner() {
  return (
    <div className="flex items-center justify-center p-8">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#1e3a5f]" />
    </div>
  );
}

export function EmptyState({ message }) {
  return (
    <div className="text-center py-12 text-gray-500">
      <p>{message}</p>
    </div>
  );
}
