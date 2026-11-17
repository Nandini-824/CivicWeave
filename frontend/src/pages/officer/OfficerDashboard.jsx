import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { OfficerSidebar, DashboardLayout } from '../../components/layout/Sidebar';
import { MetricCard, PriorityBadge, StatusBadge, LoadingSpinner } from '../../components/common/Badge';
import { officerAPI } from '../../services/api';
import { FiFileText, FiAlertTriangle, FiTrendingUp, FiCheckCircle, FiClock } from 'react-icons/fi';
import Navbar from '../../components/layout/Navbar';

export default function OfficerDashboard() {
  const [stats, setStats] = useState(null);
  const [incidents, setIncidents] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([officerAPI.dashboard(), officerAPI.incidents()])
      .then(([d, i]) => { setStats(d.data); setIncidents(i.data.slice(0, 10)); })
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <><Navbar /><LoadingSpinner /></>;

  return (
    <>
      <Navbar />
      <DashboardLayout sidebar={<OfficerSidebar />}>
        <h1 className="text-2xl font-bold text-[#1e3a5f] mb-6">Officer Overview</h1>
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4 mb-8">
          <MetricCard title="Assigned Complaints" value={stats?.total_assigned_complaints || 0} icon={FiFileText} />
          <MetricCard title="Active Incidents" value={stats?.active_incidents || 0} icon={FiAlertTriangle} color="bg-amber-500" />
          <MetricCard title="High Priority" value={stats?.high_priority_incidents || 0} icon={FiTrendingUp} color="bg-orange-500" />
          <MetricCard title="Resolved" value={stats?.resolved_incidents || 0} icon={FiCheckCircle} color="bg-green-600" />
          <MetricCard title="Overdue" value={stats?.overdue_incidents || 0} icon={FiClock} color="bg-red-500" />
        </div>

        <div className="bg-white rounded-lg shadow-sm border">
          <div className="p-4 border-b font-semibold">Incident Queue</div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="text-left p-3">Incident</th>
                  <th className="text-left p-3">Category</th>
                  <th className="text-left p-3">Complaints</th>
                  <th className="text-left p-3">Priority</th>
                  <th className="text-left p-3">Status</th>
                  <th className="text-left p-3">Action</th>
                </tr>
              </thead>
              <tbody>
                {incidents.map((inc) => (
                  <tr key={inc.id} className="border-t">
                    <td className="p-3">{inc.incident_number}</td>
                    <td className="p-3">{inc.category}</td>
                    <td className="p-3">{inc.complaint_count}</td>
                    <td className="p-3"><PriorityBadge priority={inc.approved_priority || inc.recommended_priority} /></td>
                    <td className="p-3"><StatusBadge status={inc.status} /></td>
                    <td className="p-3"><Link to={`/officer/incidents/${inc.id}`} className="text-teal-600 hover:underline">View</Link></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </DashboardLayout>
    </>
  );
}
