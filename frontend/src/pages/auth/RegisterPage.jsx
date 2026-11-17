import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import toast from 'react-hot-toast';
import Navbar from '../../components/layout/Navbar';

export default function RegisterPage() {
  const [form, setForm] = useState({ full_name: '', email: '', password: '', phone: '' });
  const [loading, setLoading] = useState(false);
  const { register } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await register(form);
      toast.success('Registration successful');
      navigate('/dashboard');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Registration failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />
      <div className="max-w-md mx-auto mt-16 p-8 bg-white rounded-lg shadow-sm border">
        <h1 className="text-2xl font-bold text-[#1e3a5f] mb-6 text-center">Citizen Registration</h1>
        <form onSubmit={handleSubmit} className="space-y-4">
          {['full_name', 'email', 'password', 'phone'].map((field) => (
            <div key={field}>
              <label className="block text-sm font-medium mb-1 capitalize">{field.replace('_', ' ')}</label>
              <input
                type={field === 'password' ? 'password' : field === 'email' ? 'email' : 'text'}
                value={form[field]}
                onChange={(e) => setForm({ ...form, [field]: e.target.value })}
                required={field !== 'phone'}
                className="w-full border rounded-md px-3 py-2"
              />
            </div>
          ))}
          <button type="submit" disabled={loading}
            className="w-full bg-teal-600 text-white py-2 rounded-md hover:bg-teal-700 disabled:opacity-50">
            {loading ? 'Registering...' : 'Register'}
          </button>
        </form>
        <p className="text-center text-sm mt-4 text-gray-600">
          Already have an account? <Link to="/login" className="text-teal-600 hover:underline">Login</Link>
        </p>
      </div>
    </div>
  );
}
