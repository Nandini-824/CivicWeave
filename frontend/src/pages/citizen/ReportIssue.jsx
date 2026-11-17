import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { CitizenSidebar, DashboardLayout } from '../../components/layout/Sidebar';
import LocationPicker from '../../components/maps/LocationPicker';
import { complaintAPI, aiAPI } from '../../services/api';
import { CATEGORIES } from '../../utils/helpers';
import toast from 'react-hot-toast';
import Navbar from '../../components/layout/Navbar';

const STEPS = ['Describe', 'Location', 'Evidence', 'AI Analysis', 'Confirm'];

export default function ReportIssue() {
  const navigate = useNavigate();
  const [step, setStep] = useState(0);
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState({
    title: '', description: '', category: '',
    latitude: null, longitude: null, address: '', city: 'Sample City',
    image_url: null, imagePreview: null,
  });
  const [analysis, setAnalysis] = useState(null);
  const [linkChoice, setLinkChoice] = useState(null);
  const [result, setResult] = useState(null);

  const canProceed = () => {
    if (step === 0) return form.title.length >= 5 && form.description.length >= 10;
    if (step === 1) return form.latitude && form.longitude && form.address;
    return true;
  };

  const runAnalysis = async () => {
    setLoading(true);
    try {
      const res = await aiAPI.analyze({
        title: form.title, description: form.description,
        latitude: form.latitude, longitude: form.longitude,
        category: form.category || undefined,
      });
      setAnalysis(res.data);
      setStep(3);
    } catch {
      toast.error('Analysis failed');
    } finally {
      setLoading(false);
    }
  };

  const handleImage = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const allowed = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp'];
    if (!allowed.includes(file.type)) { toast.error('Invalid file type'); return; }
    if (file.size > 5 * 1024 * 1024) { toast.error('File too large (max 5MB)'); return; }
    setForm({ ...form, imagePreview: URL.createObjectURL(file) });
    try {
      const res = await complaintAPI.uploadImage(file);
      if (res.data.image_url) setForm((f) => ({ ...f, image_url: res.data.image_url }));
    } catch {
      toast.error('Image upload failed');
    }
  };

  const submit = async () => {
    setLoading(true);
    try {
      const payload = {
        title: form.title, description: form.description,
        category: form.category || analysis?.classification?.category,
        latitude: form.latitude, longitude: form.longitude,
        address: form.address, city: form.city,
        image_url: form.image_url,
        link_to_incident_id: linkChoice === 'link' ? analysis?.related_incidents?.[0]?.incident_id : null,
        submit_separately: linkChoice === 'separate',
      };
      const res = await complaintAPI.create(payload);
      setResult(res.data);
      setStep(4);
      toast.success('Complaint submitted!');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Submission failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <Navbar />
      <DashboardLayout sidebar={<CitizenSidebar />}>
        <h1 className="text-2xl font-bold text-[#1e3a5f] mb-6">Report an Issue</h1>
        <div className="flex gap-2 mb-8">
          {STEPS.map((s, i) => (
            <div key={s} className={`px-3 py-1 rounded-full text-xs font-medium ${i <= step ? 'bg-teal-600 text-white' : 'bg-gray-200 text-gray-600'}`}>
              {i + 1}. {s}
            </div>
          ))}
        </div>

        <div className="bg-white rounded-lg shadow-sm border p-6 max-w-3xl">
          {step === 0 && (
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">Complaint Title</label>
                <input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })}
                  className="w-full border rounded-md px-3 py-2" placeholder="Large pothole near ABC Chowk" />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Description</label>
                <textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })}
                  rows={4} className="w-full border rounded-md px-3 py-2"
                  placeholder="Describe the issue in detail..." />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Category (optional)</label>
                <select value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })}
                  className="w-full border rounded-md px-3 py-2">
                  <option value="">Let AI suggest</option>
                  {CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
                </select>
              </div>
            </div>
          )}

          {step === 1 && (
            <LocationPicker
              latitude={form.latitude} longitude={form.longitude}
              onChange={(lat, lng) => setForm({ ...form, latitude: lat, longitude: lng })}
              address={form.address} onAddressChange={(v) => setForm({ ...form, address: v })}
              city={form.city} onCityChange={(v) => setForm({ ...form, city: v })}
            />
          )}

          {step === 2 && (
            <div>
              <label className="block text-sm font-medium mb-2">Upload Evidence (Optional)</label>
              <input type="file" accept=".jpg,.jpeg,.png,.webp" onChange={handleImage} className="text-sm" />
              {form.imagePreview && <img src={form.imagePreview} alt="Preview" className="mt-4 max-h-48 rounded-lg" />}
            </div>
          )}

          {step === 3 && analysis && (
            <div className="space-y-4">
              <h3 className="font-semibold text-[#1e3a5f]">AI Analysis</h3>
              <div className="bg-gray-50 p-4 rounded-lg space-y-2 text-sm">
                <p><strong>Detected Category:</strong> {analysis.classification?.category}</p>
                <p><strong>Suggested Department:</strong> {analysis.suggested_department}</p>
                <p><strong>Potential Related Incidents:</strong> {analysis.potential_related_incidents}</p>
                <p><strong>Analysis Status:</strong> {analysis.analysis_status}</p>
              </div>
              {analysis.related_incidents?.length > 0 && (
                <div className="border border-teal-200 bg-teal-50 p-4 rounded-lg">
                  <h4 className="font-medium text-teal-800 mb-2">Potential Related Incident Found</h4>
                  {analysis.related_incidents.map((inc) => (
                    <div key={inc.incident_id} className="text-sm space-y-1 mb-3">
                      <p><strong>{inc.title}</strong> ({inc.incident_number})</p>
                      <p>Distance: ~{inc.distance_meters}m | Complaints: {inc.related_complaint_count} | Status: {inc.status}</p>
                      <p className="text-gray-600">{inc.similarity_explanation}</p>
                    </div>
                  ))}
                  <div className="flex gap-3 mt-4">
                    <button onClick={() => { setLinkChoice('link'); setStep(4); submit(); }}
                      className="bg-teal-600 text-white px-4 py-2 rounded-md text-sm">Link to This Incident</button>
                    <button onClick={() => { setLinkChoice('separate'); submit(); }}
                      className="border border-gray-300 px-4 py-2 rounded-md text-sm">Submit as Separate</button>
                  </div>
                </div>
              )}
              {analysis.related_incidents?.length === 0 && (
                <button onClick={submit} disabled={loading}
                  className="bg-[#1e3a5f] text-white px-6 py-2 rounded-md">Submit Complaint</button>
              )}
            </div>
          )}

          {step === 4 && result && (
            <div className="text-center space-y-4">
              <div className="text-green-600 text-5xl">✓</div>
              <h3 className="text-xl font-bold text-[#1e3a5f]">Complaint Submitted Successfully!</h3>
              <p>Complaint ID: <strong>{result.complaint_number}</strong></p>
              <p>Status: {result.status}</p>
              <p>Suggested Department: {result.suggested_department}</p>
              <div className="flex gap-3 justify-center mt-4">
                <button onClick={() => navigate(`/complaints/${result.id}`)}
                  className="bg-teal-600 text-white px-4 py-2 rounded-md">View Complaint</button>
                <button onClick={() => navigate('/dashboard')}
                  className="border px-4 py-2 rounded-md">Go to Dashboard</button>
              </div>
            </div>
          )}

          {step < 3 && (
            <div className="flex justify-between mt-6">
              <button onClick={() => setStep(Math.max(0, step - 1))} disabled={step === 0}
                className="px-4 py-2 border rounded-md text-sm disabled:opacity-50">Back</button>
              <button onClick={() => step === 2 ? runAnalysis() : setStep(step + 1)}
                disabled={!canProceed() || loading}
                className="px-4 py-2 bg-[#1e3a5f] text-white rounded-md text-sm disabled:opacity-50">
                {loading ? 'Processing...' : step === 2 ? 'Run AI Analysis' : 'Next'}
              </button>
            </div>
          )}
        </div>
      </DashboardLayout>
    </>
  );
}
