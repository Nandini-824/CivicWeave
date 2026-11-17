import { useEffect, useState } from 'react';
import { AdminSidebar, DashboardLayout } from '../../components/layout/Sidebar';
import { adminAPI } from '../../services/api';
import toast from 'react-hot-toast';
import Navbar from '../../components/layout/Navbar';

export default function AdminDepartments() {
  const [departments, setDepartments] = useState([]);
  const [form, setForm] = useState({ name: '', description: '' });

  const load = () => adminAPI.departments().then((res) => setDepartments(res.data));
  useEffect(() => { load(); }, []);

  const create = async (e) => {
    e.preventDefault();
    await adminAPI.createDepartment(form);
    toast.success('Department created');
    setForm({ name: '', description: '' });
    load();
  };

  return (
    <>
      <Navbar />
      <DashboardLayout sidebar={<AdminSidebar />}>
        <h1 className="text-2xl font-bold text-[#1e3a5f] mb-6">Departments</h1>
        <form onSubmit={create} className="bg-white rounded-lg border p-4 mb-6 flex gap-3 flex-wrap">
          <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Department name" required className="border rounded-md px-3 py-2 text-sm" />
          <input value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} placeholder="Description" className="border rounded-md px-3 py-2 text-sm flex-1" />
          <button type="submit" className="bg-teal-600 text-white px-4 py-2 rounded-md text-sm">Create</button>
        </form>
        <div className="bg-white rounded-lg border">
          {departments.map((d) => (
            <div key={d.id} className="p-4 border-b flex justify-between">
              <div><p className="font-medium">{d.name}</p><p className="text-sm text-gray-500">{d.description}</p></div>
              <span className={`text-xs px-2 py-1 rounded ${d.is_active ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>{d.is_active ? 'Active' : 'Inactive'}</span>
            </div>
          ))}
        </div>
      </DashboardLayout>
    </>
  );
}
