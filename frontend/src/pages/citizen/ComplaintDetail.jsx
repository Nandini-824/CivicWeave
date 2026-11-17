import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { CitizenSidebar, DashboardLayout } from '../../components/layout/Sidebar';
import { StatusBadge, LoadingSpinner } from '../../components/common/Badge';
import { complaintAPI } from '../../services/api';
import { formatDateTime } from '../../utils/helpers';
import toast from 'react-hot-toast';
import Navbar from '../../components/layout/Navbar';

export default function ComplaintDetail() {
  const { id } = useParams();
  const [complaint, setComplaint] = useState(null);
  const [timeline, setTimeline] = useState([]);
  const [loading, setLoading] = useState(true);
  const [feedback, setFeedback] = useState({ is_resolved: true, remarks: '' });

  useEffect(() => {
    Promise.all([complaintAPI.get(id), complaintAPI.timeline(id)])
      .then(([c, t]) => { setComplaint(c.data); setTimeline(t.data); })
      .finally(() => setLoading(false));
  }, [id]);

  const submitFeedback = async (isResolved) => {
    try {
      await complaintAPI.feedback(id, { is_resolved: isResolved, remarks: feedback.remarks });
      toast.success('Feedback submitted');
      const c = await complaintAPI.get(id);
      setComplaint(c.data);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed');
    }
  };

  if (loading) return <><Navbar /><LoadingSpinner /></>;

  return (
    <>
      <Navbar />
      <DashboardLayout sidebar={<CitizenSidebar />}>
        <h1 className="text-2xl font-bold text-[#1e3a5f] mb-6">{complaint.complaint_number}</h1>
        <div className="grid md:grid-cols-2 gap-6">
          <div className="bg-white rounded-lg shadow-sm border p-6 space-y-3">
            <h2 className="font-semibold">{complaint.title}</h2>
            <p className="text-sm text-gray-600">{complaint.description}</p>
            <div className="grid grid-cols-2 gap-2 text-sm">
              <p><strong>Category:</strong> {complaint.category}</p>
              <p><strong>Department:</strong> {complaint.assigned_department || complaint.suggested_department}</p>
              <p><strong>Status:</strong> <StatusBadge status={complaint.status} /></p>
              <p><strong>Submitted:</strong> {formatDateTime(complaint.created_at)}</p>
              {complaint.related_incident_number && (
                <p><strong>Incident:</strong> {complaint.related_incident_number}</p>
              )}
            </div>
            {complaint.image_url && (
              <img src={complaint.image_url} alt="Evidence" className="max-h-48 rounded-lg mt-2" />
            )}
          </div>
          <div className="bg-white rounded-lg shadow-sm border p-6">
            <h3 className="font-semibold mb-4">Progress Timeline</h3>
            <div className="space-y-4">
              {timeline.map((t, i) => (
                <div key={i} className="flex gap-3">
                  <div className="w-3 h-3 rounded-full bg-teal-600 mt-1.5 shrink-0" />
                  <div>
                    <p className="font-medium text-sm">{t.new_status}</p>
                    {t.remarks && <p className="text-xs text-gray-500">{t.remarks}</p>}
                    <p className="text-xs text-gray-400">{formatDateTime(t.created_at)}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {['Resolved', 'Closed'].includes(complaint.status) && (
          <div className="bg-white rounded-lg shadow-sm border p-6 mt-6">
            <h3 className="font-semibold mb-3">Resolution Feedback</h3>
            <p className="text-sm mb-4">Has the reported issue been resolved satisfactorily?</p>
            <textarea value={feedback.remarks} onChange={(e) => setFeedback({ ...feedback, remarks: e.target.value })}
              className="w-full border rounded-md px-3 py-2 text-sm mb-4" placeholder="Optional remarks" rows={2} />
            <div className="flex gap-3">
              <button onClick={() => submitFeedback(true)} className="bg-green-600 text-white px-4 py-2 rounded-md text-sm">Yes, Resolved</button>
              <button onClick={() => submitFeedback(false)} className="bg-red-600 text-white px-4 py-2 rounded-md text-sm">No, Still Unresolved</button>
            </div>
          </div>
        )}
      </DashboardLayout>
    </>
  );
}
