import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { CitizenSidebar, DashboardLayout } from '../../components/layout/Sidebar';
import { StatusBadge, LoadingSpinner } from '../../components/common/Badge';
import { complaintAPI } from '../../services/api';
import { formatDate } from '../../utils/helpers';
import Navbar from '../../components/layout/Navbar';

export default function MyComplaints() {
  const [complaints, setComplaints] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    complaintAPI.my().then((res) => setComplaints(res.data)).finally(() => setLoading(false));
  }, []);

  return (
    <>
      <Navbar />
      <DashboardLayout sidebar={<CitizenSidebar />}>
        <h1 className="text-2xl font-bold text-[#1e3a5f] mb-6">My Complaints</h1>
        {loading ? <LoadingSpinner /> : (
          <div className="bg-white rounded-lg shadow-sm border overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="text-left p-3">ID</th>
                  <th className="text-left p-3">Title</th>
                  <th className="text-left p-3">Category</th>
                  <th className="text-left p-3">Status</th>
                  <th className="text-left p-3">Incident</th>
                  <th className="text-left p-3">Submitted</th>
                </tr>
              </thead>
              <tbody>
                {complaints.map((c) => (
                  <tr key={c.id} className="border-t hover:bg-gray-50">
                    <td className="p-3"><Link to={`/complaints/${c.id}`} className="text-teal-600 hover:underline">{c.complaint_number}</Link></td>
                    <td className="p-3">{c.title}</td>
                    <td className="p-3">{c.category}</td>
                    <td className="p-3"><StatusBadge status={c.status} /></td>
                    <td className="p-3">{c.related_incident_number || '-'}</td>
                    <td className="p-3">{formatDate(c.created_at)}</td>
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
