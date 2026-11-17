import { useEffect, useState } from 'react';
import { AdminSidebar, DashboardLayout } from '../../components/layout/Sidebar';
import { adminAPI } from '../../services/api';
import toast from 'react-hot-toast';
import Navbar from '../../components/layout/Navbar';

export default function AdminOfficers() {
  const [officers, setOfficers] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [form, setForm] = useState({ full_name: '', email: '', password: '', department_id: '' });

  useEffect(() => {
    adminAPI.officers().then((res) => setOfficers(res.data));
    adminAPI.departments().then((res) => setDepartments(res.data));
  }, []);

  const create = async (e) => {
    e.preventDefault();
    await adminAPI.createOfficer({ ...form, department_id: parseInt(form.department_id) });
    toast.success('Officer created');
    setForm({ full_name: '', email: '', password: '', department_id: '' });
    adminAPI.officers().then((res) => setOfficers(res.data));
  };

  return (
    <>
      <Navbar />
      <DashboardLayout sidebar={<AdminSidebar />}>
        <h1 className="text-2xl font-bold text-[#1e3a5f] mb-6">Officers</h1>
        <form onSubmit={create} className="bg-white rounded-lg border p-4 mb-6 grid md:grid-cols-2 gap-3">
          <input value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} placeholder="Full name" required className="border rounded-md px-3 py-2 text-sm" />
          <input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} placeholder="Email" required className="border rounded-md px-3 py-2 text-sm" />
          <input type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} placeholder="Password" required className="border rounded-md px-3 py-2 text-sm" />
          <select value={form.department_id} onChange={(e) => setForm({ ...form, department_id: e.target.value })} required className="border rounded-md px-3 py-2 text-sm">
            <option value="">Select Department</option>
            {departments.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
          </select>
          <button type="submit" className="bg-teal-600 text-white px-4 py-2 rounded-md text-sm md:col-span-2">Create Officer</button>
        </form>
        <div className="bg-white rounded-lg border">
          {officers.map((o) => (
            <div key={o.id} className="p-4 border-b">
              <p className="font-medium">{o.full_name}</p>
              <p className="text-sm text-gray-500">{o.email} — {o.department_name || 'Unassigned'}</p>
            </div>
          ))}
        </div>
      </DashboardLayout>
    </>
  );
}
