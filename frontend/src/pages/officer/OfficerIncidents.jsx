import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { OfficerSidebar, DashboardLayout } from '../../components/layout/Sidebar';
import { PriorityBadge, StatusBadge, LoadingSpinner } from '../../components/common/Badge';
import { officerAPI } from '../../services/api';
import Navbar from '../../components/layout/Navbar';

export default function OfficerIncidents() {
  const [incidents, setIncidents] = useState([]);
  const [filters, setFilters] = useState({ category: '', priority: '', status: '' });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    const params = { ...filters };
    Object.keys(params).forEach((k) => { if (!params[k]) delete params[k]; });
    officerAPI.incidents(params).then((res) => setIncidents(res.data)).finally(() => setLoading(false));
  }, [filters]);

  return (
    <>
      <Navbar />
      <DashboardLayout sidebar={<OfficerSidebar />}>
        <h1 className="text-2xl font-bold text-[#1e3a5f] mb-6">Incident Queue</h1>
        <div className="flex gap-3 mb-4">
          {['category', 'priority', 'status'].map((f) => (
            <input key={f} placeholder={`Filter ${f}`} value={filters[f]}
              onChange={(e) => setFilters({ ...filters, [f]: e.target.value })}
              className="border rounded-md px-3 py-2 text-sm capitalize" />
          ))}
        </div>
        {loading ? <LoadingSpinner /> : (
          <div className="bg-white rounded-lg border overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="text-left p-3">Incident</th><th className="text-left p-3">Category</th>
                  <th className="text-left p-3">Complaints</th><th className="text-left p-3">Priority</th>
                  <th className="text-left p-3">Status</th><th className="text-left p-3">Action</th>
                </tr>
              </thead>
              <tbody>
                {incidents.map((inc) => (
                  <tr key={inc.id} className="border-t">
                    <td className="p-3">{inc.incident_number} — {inc.title}</td>
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
        )}
      </DashboardLayout>
    </>
  );
}
