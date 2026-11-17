import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { FiLogOut, FiUser } from 'react-icons/fi';

export default function Navbar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  return (
    <nav className="bg-[#1e3a5f] text-white shadow-md">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16 items-center">
          <Link to="/" className="flex items-center gap-2">
            <span className="text-xl font-bold">CivicWeave</span>
            <span className="text-xs text-teal-300 hidden sm:inline">From Complaints to Civic Intelligence</span>
          </Link>
          <div className="flex items-center gap-4">
            {user ? (
              <>
                <span className="text-sm flex items-center gap-1">
                  <FiUser size={14} /> {user.full_name}
                </span>
                <button onClick={handleLogout} className="text-sm flex items-center gap-1 hover:text-teal-300">
                  <FiLogOut size={14} /> Logout
                </button>
              </>
            ) : (
              <>
                <Link to="/login" className="text-sm hover:text-teal-300">Login</Link>
                <Link to="/register" className="bg-teal-600 hover:bg-teal-700 px-4 py-2 rounded-md text-sm font-medium">
                  Register
                </Link>
              </>
            )}
          </div>
        </div>
      </div>
    </nav>
  );
}
