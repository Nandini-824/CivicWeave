import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { PriorityBadge, StatusBadge, LoadingSpinner } from '../../components/common/Badge';
import IncidentMap from '../../components/maps/IncidentMap';
import { incidentAPI } from '../../services/api';
import { formatDateTime } from '../../utils/helpers';
import toast from 'react-hot-toast';
import Navbar from '../../components/layout/Navbar';
import { useAuth } from '../../context/AuthContext';

export default function IncidentDetail() {
  const { id } = useParams();
  const { user } = useAuth();
  const [incident, setIncident] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = () => {
    incidentAPI.get(id).then((res) => setIncident(res.data)).finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, [id]);

  const toggleSupport = async () => {
    try {
      if (incident.user_supported) {
        await incidentAPI.withdrawSupport(id);
        toast.success('Support withdrawn');
      } else {
        await incidentAPI.support(id);
        toast.success('Support recorded');
      }
      load();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed');
    }
  };

  if (loading) return <><Navbar /><LoadingSpinner /></>;

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />
      <div className="max-w-7xl mx-auto px-4 py-8">
        <div className="flex justify-between items-start mb-6">
          <div>
            <h1 className="text-2xl font-bold text-[#1e3a5f]">{incident.incident_number}</h1>
            <h2 className="text-xl mt-1">{incident.title}</h2>
          </div>
          <div className="flex gap-2">
            <PriorityBadge priority={incident.approved_priority || incident.recommended_priority} />
            <StatusBadge status={incident.status} />
          </div>
        </div>

        <div className="grid md:grid-cols-2 gap-6 mb-6">
          <div className="bg-white rounded-lg shadow-sm border p-6 space-y-2 text-sm">
            <p><strong>Category:</strong> {incident.category}</p>
            <p><strong>Department:</strong> {incident.department_name}</p>
            <p><strong>Related Complaints:</strong> {incident.complaint_count}</p>
            <p><strong>Unique Reporters:</strong> {incident.unique_reporters}</p>
            <p><strong>Support Count:</strong> {incident.support_count}</p>
            <p><strong>First Reported:</strong> {formatDateTime(incident.first_reported_at)}</p>
            <p><strong>Last Reported:</strong> {formatDateTime(incident.last_reported_at)}</p>
            {user?.role === 'citizen' && (
              <button onClick={toggleSupport}
                className={`mt-4 px-4 py-2 rounded-md text-sm ${incident.user_supported ? 'bg-gray-200' : 'bg-teal-600 text-white'}`}>
                {incident.user_supported ? 'Withdraw Support' : 'I Am Also Affected'}
              </button>
            )}
          </div>
          {incident.priority_explanation && (
            <div className="bg-white rounded-lg shadow-sm border p-6">
              <h3 className="font-semibold mb-2">Priority Explanation</h3>
              <pre className="text-sm whitespace-pre-wrap text-gray-700">{incident.priority_explanation}</pre>
            </div>
          )}
        </div>

        <IncidentMap incidents={[incident]} center={[incident.center_latitude, incident.center_longitude]} zoom={15} />

        <div className="bg-white rounded-lg shadow-sm border mt-6">
          <div className="p-4 border-b font-semibold">Related Complaints</div>
          <div className="divide-y">
            {incident.complaints?.map((c) => (
              <div key={c.id} className="p-4 text-sm">
                <p className="font-medium">{c.complaint_number} — {c.title}</p>
                <p className="text-gray-600 mt-1">{c.description}</p>
                <p className="text-gray-400 mt-1">{formatDateTime(c.created_at)} • Link: {c.link_status}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
