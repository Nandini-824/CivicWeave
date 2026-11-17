import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { CitizenSidebar, DashboardLayout } from '../../components/layout/Sidebar';
import { MetricCard, StatusBadge, PriorityBadge, LoadingSpinner } from '../../components/common/Badge';
import { complaintAPI, incidentAPI } from '../../services/api';
import { formatDate } from '../../utils/helpers';
import { FiFileText, FiClock, FiCheckCircle, FiHeart } from 'react-icons/fi';
import Navbar from '../../components/layout/Navbar';

export default function CitizenDashboard() {
  const [complaints, setComplaints] = useState([]);
  const [nearby, setNearby] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      complaintAPI.my(),
      incidentAPI.nearby({ latitude: 18.5204, longitude: 73.8567, radius_km: 5 }),
    ]).then(([c, n]) => {
      setComplaints(c.data);
      setNearby(n.data.slice(0, 4));
    }).finally(() => setLoading(false));
  }, []);

  const active = complaints.filter((c) => !['Resolved', 'Closed'].includes(c.status)).length;
  const resolved = complaints.filter((c) => ['Resolved', 'Closed'].includes(c.status)).length;

  if (loading) return <><Navbar /><LoadingSpinner /></>;

  return (
    <>
      <Navbar />
      <DashboardLayout sidebar={<CitizenSidebar />}>
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-2xl font-bold text-[#1e3a5f]">Dashboard</h1>
          <Link to="/report" className="bg-teal-600 text-white px-4 py-2 rounded-md hover:bg-teal-700 text-sm font-medium">
            + Report New Issue
          </Link>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          <MetricCard title="Total Complaints" value={complaints.length} icon={FiFileText} />
          <MetricCard title="Active" value={active} icon={FiClock} color="bg-amber-500" />
          <MetricCard title="Resolved" value={resolved} icon={FiCheckCircle} color="bg-green-600" />
          <MetricCard title="Supported Issues" value="-" icon={FiHeart} color="bg-teal-600" />
        </div>

        <div className="bg-white rounded-lg shadow-sm border mb-8">
          <div className="p-4 border-b"><h2 className="font-semibold text-[#1e3a5f]">Recent Complaints</h2></div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="text-left p-3">Complaint ID</th>
                  <th className="text-left p-3">Title</th>
                  <th className="text-left p-3">Category</th>
                  <th className="text-left p-3">Status</th>
                  <th className="text-left p-3">Submitted</th>
                </tr>
              </thead>
              <tbody>
                {complaints.slice(0, 5).map((c) => (
                  <tr key={c.id} className="border-t hover:bg-gray-50">
                    <td className="p-3"><Link to={`/complaints/${c.id}`} className="text-teal-600 hover:underline">{c.complaint_number}</Link></td>
                    <td className="p-3">{c.title}</td>
                    <td className="p-3">{c.category}</td>
                    <td className="p-3"><StatusBadge status={c.status} /></td>
                    <td className="p-3">{formatDate(c.created_at)}</td>
                  </tr>
                ))}
                {complaints.length === 0 && (
                  <tr><td colSpan={5} className="p-8 text-center text-gray-500">No complaints yet. Report your first issue!</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        <div>
          <h2 className="font-semibold text-[#1e3a5f] mb-4">Nearby Incidents</h2>
          <div className="grid md:grid-cols-2 gap-4">
            {nearby.map((inc) => (
              <div key={inc.id} className="bg-white rounded-lg shadow-sm border p-4">
                <h3 className="font-medium">{inc.title}</h3>
                <p className="text-sm text-gray-500">{inc.category}</p>
                <div className="flex gap-2 mt-2">
                  <PriorityBadge priority={inc.approved_priority || inc.recommended_priority} />
                  <StatusBadge status={inc.status} />
                </div>
                <p className="text-sm mt-2">{inc.complaint_count} related complaints</p>
                <Link to={`/incidents/${inc.id}`} className="text-teal-600 text-sm hover:underline mt-2 inline-block">View Details</Link>
              </div>
            ))}
          </div>
        </div>
      </DashboardLayout>
    </>
  );
}
