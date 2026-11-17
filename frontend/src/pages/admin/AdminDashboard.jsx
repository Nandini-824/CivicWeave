import { useEffect, useState } from 'react';
import { AdminSidebar, DashboardLayout } from '../../components/layout/Sidebar';
import { MetricCard, LoadingSpinner } from '../../components/common/Badge';
import { adminAPI } from '../../services/api';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import { FiFileText, FiAlertTriangle, FiCheckCircle, FiClock } from 'react-icons/fi';
import Navbar from '../../components/layout/Navbar';

const COLORS = ['#1e3a5f', '#0d9488', '#f59e0b', '#ef4444', '#8b5cf6'];

export default function AdminDashboard() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    adminAPI.dashboard().then((res) => setData(res.data)).finally(() => setLoading(false));
  }, []);

  if (loading) return <><Navbar /><LoadingSpinner /></>;

  return (
    <>
      <Navbar />
      <DashboardLayout sidebar={<AdminSidebar />}>
        <h1 className="text-2xl font-bold text-[#1e3a5f] mb-6">Admin Overview</h1>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          <MetricCard title="Total Complaints" value={data?.total_complaints || 0} icon={FiFileText} />
          <MetricCard title="Total Incidents" value={data?.total_incidents || 0} icon={FiAlertTriangle} color="bg-amber-500" />
          <MetricCard title="Resolved" value={data?.resolved_incidents || 0} icon={FiCheckCircle} color="bg-green-600" />
          <MetricCard title="Pending" value={data?.pending_incidents || 0} icon={FiClock} color="bg-orange-500" />
        </div>
        <div className="grid md:grid-cols-2 gap-6">
          <div className="bg-white rounded-lg border p-4">
            <h3 className="font-semibold mb-4">Complaints by Category</h3>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={data?.complaints_by_category || []}>
                <XAxis dataKey="category" tick={{ fontSize: 10 }} angle={-20} textAnchor="end" height={60} />
                <YAxis /><Tooltip /><Bar dataKey="count" fill="#1e3a5f" />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="bg-white rounded-lg border p-4">
            <h3 className="font-semibold mb-4">Incidents by Priority</h3>
            <ResponsiveContainer width="100%" height={250}>
              <PieChart>
                <Pie data={data?.incidents_by_priority || []} dataKey="count" nameKey="priority" cx="50%" cy="50%" outerRadius={80} label>
                  {(data?.incidents_by_priority || []).map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      </DashboardLayout>
    </>
  );
}
