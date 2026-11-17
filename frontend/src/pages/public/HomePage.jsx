import { Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { getDashboardPath } from '../../utils/helpers';
import Navbar from '../../components/layout/Navbar';
import { FiArrowRight, FiSearch, FiLink, FiTrendingUp, FiCheckCircle } from 'react-icons/fi';

export default function HomePage() {
  const { user } = useAuth();

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />
      <section className="bg-[#1e3a5f] text-white py-20">
        <div className="max-w-7xl mx-auto px-4 text-center">
          <h1 className="text-4xl md:text-5xl font-bold mb-4">From Complaints to Civic Intelligence.</h1>
          <p className="text-lg text-gray-300 max-w-3xl mx-auto mb-8">
            CivicWeave uses AI-assisted analysis to connect related civic complaints, identify potential real-world incidents, and help authorities prioritize action.
          </p>
          <div className="flex gap-4 justify-center flex-wrap">
            <Link to={user ? getDashboardPath(user.role) : '/register'}
              className="bg-teal-600 hover:bg-teal-700 px-6 py-3 rounded-lg font-medium flex items-center gap-2">
              Report an Issue <FiArrowRight />
            </Link>
            <Link to="/explore" className="border border-white/30 hover:bg-white/10 px-6 py-3 rounded-lg font-medium">
              Explore Civic Issues
            </Link>
          </div>
        </div>
      </section>

      <section className="py-16 max-w-7xl mx-auto px-4">
        <h2 className="text-2xl font-bold text-center text-[#1e3a5f] mb-10">How It Works</h2>
        <div className="flex flex-wrap justify-center gap-4 md:gap-8">
          {['Report', 'Analyze', 'Connect', 'Prioritize', 'Resolve'].map((step, i) => (
            <div key={step} className="flex items-center gap-2">
              <div className="w-10 h-10 rounded-full bg-teal-600 text-white flex items-center justify-center font-bold">{i + 1}</div>
              <span className="font-medium text-[#1e3a5f]">{step}</span>
              {i < 4 && <FiArrowRight className="text-gray-400 hidden md:block" />}
            </div>
          ))}
        </div>
      </section>

      <section className="py-16 bg-white">
        <div className="max-w-7xl mx-auto px-4 grid md:grid-cols-3 gap-8">
          <FeatureCard icon={FiSearch} title="Smart Complaint Analysis"
            description="Automatically categorizes complaints and identifies the responsible department." />
          <FeatureCard icon={FiLink} title="Incident Intelligence"
            description="Connects potentially related complaints using text similarity, location, and time." />
          <FeatureCard icon={FiTrendingUp} title="Explainable Prioritization"
            description="Provides priority recommendations with understandable supporting reasons." />
        </div>
      </section>

      <footer className="bg-[#1e3a5f] text-gray-300 py-8">
        <div className="max-w-7xl mx-auto px-4 text-center">
          <p className="font-bold text-white text-lg mb-2">CivicWeave</p>
          <p className="text-sm">AI-Based Civic Grievance Intelligence System</p>
          <p className="text-xs mt-4 text-gray-400">Development project — data shown is fictional for demonstration purposes.</p>
        </div>
      </footer>
    </div>
  );
}

function FeatureCard({ icon: Icon, title, description }) {
  return (
    <div className="p-6 rounded-lg border border-gray-100 shadow-sm">
      <div className="w-12 h-12 bg-teal-100 text-teal-700 rounded-lg flex items-center justify-center mb-4">
        <Icon size={24} />
      </div>
      <h3 className="text-lg font-semibold text-[#1e3a5f] mb-2">{title}</h3>
      <p className="text-gray-600 text-sm">{description}</p>
    </div>
  );
}
