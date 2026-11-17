import { NavLink } from 'react-router-dom';
import { FiHome, FiFileText, FiMapPin, FiHeart, FiUser, FiAlertTriangle, FiClock, FiMap, FiBarChart2, FiUsers, FiGrid } from 'react-icons/fi';

const linkClass = ({ isActive }) =>
  `flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm transition-colors ${
    isActive ? 'bg-teal-600 text-white' : 'text-gray-300 hover:bg-[#2a4a6f] hover:text-white'
  }`;

export function CitizenSidebar() {
  const links = [
    { to: '/dashboard', label: 'Dashboard', icon: FiHome },
    { to: '/report', label: 'Report Issue', icon: FiFileText },
    { to: '/my-complaints', label: 'My Complaints', icon: FiAlertTriangle },
    { to: '/nearby', label: 'Nearby Issues', icon: FiMapPin },
    { to: '/supported', label: 'My Supported Issues', icon: FiHeart },
    { to: '/profile', label: 'Profile', icon: FiUser },
  ];
  return <Sidebar links={links} title="CivicWeave" />;
}

export function OfficerSidebar() {
  const links = [
    { to: '/officer', label: 'Overview', icon: FiHome },
    { to: '/officer/incidents', label: 'Incident Queue', icon: FiAlertTriangle },
    { to: '/officer/complaints', label: 'Assigned Complaints', icon: FiFileText },
    { to: '/officer/map', label: 'Incident Map', icon: FiMap },
    { to: '/officer/priority', label: 'Priority Issues', icon: FiBarChart2 },
    { to: '/officer/overdue', label: 'Overdue Issues', icon: FiClock },
    { to: '/profile', label: 'Profile', icon: FiUser },
  ];
  return <Sidebar links={links} title="Officer Dashboard" />;
}

export function AdminSidebar() {
  const links = [
    { to: '/admin', label: 'Overview', icon: FiHome },
    { to: '/admin/departments', label: 'Departments', icon: FiGrid },
    { to: '/admin/officers', label: 'Officers', icon: FiUsers },
    { to: '/admin/complaints', label: 'Complaints', icon: FiFileText },
    { to: '/admin/incidents', label: 'Incidents', icon: FiAlertTriangle },
    { to: '/admin/jurisdictions', label: 'Jurisdictions', icon: FiMapPin },
    { to: '/admin/analytics', label: 'Analytics', icon: FiBarChart2 },
  ];
  return <Sidebar links={links} title="Super Admin" />;
}

function Sidebar({ links, title }) {
  return (
    <aside className="w-64 bg-[#1e3a5f] min-h-screen p-4 flex flex-col">
      <h2 className="text-white font-bold text-lg px-4 py-3 mb-4 border-b border-[#2a4a6f]">{title}</h2>
      <nav className="flex flex-col gap-1">
        {links.map(({ to, label, icon: Icon }) => (
          <NavLink key={to} to={to} className={linkClass} end={to === '/dashboard' || to === '/officer' || to === '/admin'}>
            <Icon size={18} />
            {label}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}

export function DashboardLayout({ sidebar, children }) {
  return (
    <div className="flex min-h-screen bg-gray-50">
      {sidebar}
      <main className="flex-1 p-6 overflow-auto">{children}</main>
    </div>
  );
}
