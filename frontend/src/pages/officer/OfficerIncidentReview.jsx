import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { OfficerSidebar, DashboardLayout } from '../../components/layout/Sidebar';
import { PriorityBadge, StatusBadge, LoadingSpinner } from '../../components/common/Badge';
import { incidentAPI, officerAPI } from '../../services/api';
import { formatDateTime } from '../../utils/helpers';
import toast from 'react-hot-toast';
import Navbar from '../../components/layout/Navbar';

export default function OfficerIncidentReview() {
  const { id } = useParams();
  const [incident, setIncident] = useState(null);
  const [candidates, setCandidates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [priority, setPriority] = useState('');
  const [status, setStatus] = useState('');
  const [remarks, setRemarks] = useState('');

  const load = () => {
    Promise.all([incidentAPI.get(id), officerAPI.candidates()])
      .then(([inc, cand]) => {
        setIncident(inc.data);
        setPriority(inc.data.approved_priority || inc.data.recommended_priority);
        setStatus(inc.data.status);
        setCandidates(cand.data.filter((c) => c.incident.id === parseInt(id)));
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, [id]);

  const confirmLink = async (linkId) => {
    await officerAPI.confirmLink(linkId);
    toast.success('Link confirmed');
    load();
  };

  const rejectLink = async (linkId) => {
    await officerAPI.rejectLink(linkId);
    toast.success('Link rejected');
    load();
  };

  const updatePriority = async () => {
    await incidentAPI.updatePriority(id, { approved_priority: priority });
    toast.success('Priority updated');
    load();
  };

  const updateStatus = async () => {
    await incidentAPI.updateStatus(id, { status, remarks, resolution_remarks: remarks });
    toast.success('Status updated');
    load();
  };

  if (loading) return <><Navbar /><LoadingSpinner /></>;

  return (
    <>
      <Navbar />
      <DashboardLayout sidebar={<OfficerSidebar />}>
        <h1 className="text-2xl font-bold text-[#1e3a5f] mb-2">{incident.incident_number}</h1>
        <h2 className="text-lg mb-6">{incident.title}</h2>

        <div className="grid md:grid-cols-2 gap-6 mb-6">
          <div className="bg-white rounded-lg border p-6 space-y-2 text-sm">
            <p><strong>Category:</strong> {incident.category}</p>
            <p><strong>Department:</strong> {incident.department_name}</p>
            <div className="flex gap-2"><PriorityBadge priority={incident.approved_priority || incident.recommended_priority} /><StatusBadge status={incident.status} /></div>
            <p><strong>Complaints:</strong> {incident.complaint_count} | <strong>Reporters:</strong> {incident.unique_reporters}</p>
          </div>
          {incident.priority_explanation && (
            <div className="bg-white rounded-lg border p-6">
              <h3 className="font-semibold mb-2">Priority Recommendation</h3>
              <pre className="text-sm whitespace-pre-wrap">{incident.priority_explanation}</pre>
            </div>
          )}
        </div>

        {candidates.length > 0 && (
          <div className="bg-white rounded-lg border p-6 mb-6">
            <h3 className="font-semibold mb-4">AI Linking Evidence — Pending Review</h3>
            {candidates.map((c) => (
              <div key={c.link_id} className="border rounded-lg p-4 mb-3 text-sm">
                <p className="font-medium">{c.complaint.complaint_number}: {c.complaint.title}</p>
                <p>Semantic: {(c.semantic_score * 100).toFixed(0)}% | Spatial: {(c.spatial_score * 100).toFixed(0)}% | Temporal: {(c.temporal_score * 100).toFixed(0)}% | Combined: {(c.combined_score * 100).toFixed(0)}%</p>
                <div className="flex gap-2 mt-2">
                  <button onClick={() => confirmLink(c.link_id)} className="bg-green-600 text-white px-3 py-1 rounded text-xs">Confirm Link</button>
                  <button onClick={() => rejectLink(c.link_id)} className="bg-red-600 text-white px-3 py-1 rounded text-xs">Reject Link</button>
                </div>
              </div>
            ))}
          </div>
        )}

        <div className="bg-white rounded-lg border p-6 mb-6">
          <h3 className="font-semibold mb-4">Related Complaints</h3>
          {incident.complaints?.map((c) => (
            <div key={c.id} className="border-b py-3 text-sm">
              <p className="font-medium">{c.complaint_number} — {c.title}</p>
              <p className="text-gray-600">{c.description}</p>
              <p className="text-gray-400">{formatDateTime(c.created_at)}</p>
            </div>
          ))}
        </div>

        <div className="bg-white rounded-lg border p-6 grid md:grid-cols-2 gap-6">
          <div>
            <h3 className="font-semibold mb-3">Modify Priority</h3>
            <select value={priority} onChange={(e) => setPriority(e.target.value)} className="border rounded-md px-3 py-2 w-full mb-2">
              {['Low', 'Medium', 'High', 'Critical'].map((p) => <option key={p} value={p}>{p}</option>)}
            </select>
            <button onClick={updatePriority} className="bg-[#1e3a5f] text-white px-4 py-2 rounded-md text-sm">Update Priority</button>
          </div>
          <div>
            <h3 className="font-semibold mb-3">Update Status</h3>
            <select value={status} onChange={(e) => setStatus(e.target.value)} className="border rounded-md px-3 py-2 w-full mb-2">
              {['Submitted', 'Under Review', 'Assigned', 'In Progress', 'Resolved', 'Closed', 'Reopened'].map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
            <textarea value={remarks} onChange={(e) => setRemarks(e.target.value)} className="border rounded-md px-3 py-2 w-full mb-2 text-sm" placeholder="Remarks" rows={2} />
            <button onClick={updateStatus} className="bg-teal-600 text-white px-4 py-2 rounded-md text-sm">Update Status</button>
          </div>
        </div>
      </DashboardLayout>
    </>
  );
}
