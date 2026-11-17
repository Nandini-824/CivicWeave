import { useAuth } from '../../context/AuthContext';
import { CitizenSidebar, DashboardLayout } from '../../components/layout/Sidebar';
import Navbar from '../../components/layout/Navbar';

export default function ProfilePage() {
  const { user } = useAuth();

  return (
    <>
      <Navbar />
      <DashboardLayout sidebar={<CitizenSidebar />}>
        <h1 className="text-2xl font-bold text-[#1e3a5f] mb-6">Profile</h1>
        <div className="bg-white rounded-lg shadow-sm border p-6 max-w-md space-y-3">
          <p><strong>Name:</strong> {user?.full_name}</p>
          <p><strong>Email:</strong> {user?.email}</p>
          <p><strong>Role:</strong> <span className="capitalize">{user?.role}</span></p>
          {user?.phone && <p><strong>Phone:</strong> {user.phone}</p>}
        </div>
      </DashboardLayout>
    </>
  );
}
