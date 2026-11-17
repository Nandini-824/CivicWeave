import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import { AuthProvider } from './context/AuthContext';
import ProtectedRoute from './components/common/ProtectedRoute';

import HomePage from './pages/public/HomePage';
import ExplorePage from './pages/public/ExplorePage';
import LoginPage from './pages/auth/LoginPage';
import RegisterPage from './pages/auth/RegisterPage';

import CitizenDashboard from './pages/citizen/CitizenDashboard';
import ReportIssue from './pages/citizen/ReportIssue';
import MyComplaints from './pages/citizen/MyComplaints';
import ComplaintDetail from './pages/citizen/ComplaintDetail';
import NearbyIssues from './pages/citizen/NearbyIssues';
import IncidentDetail from './pages/citizen/IncidentDetail';
import ProfilePage from './pages/citizen/ProfilePage';

import OfficerDashboard from './pages/officer/OfficerDashboard';
import OfficerIncidents from './pages/officer/OfficerIncidents';
import OfficerIncidentReview from './pages/officer/OfficerIncidentReview';
import CivicMapPage from './pages/CivicMapPage';

import AdminDashboard from './pages/admin/AdminDashboard';
import AdminDepartments from './pages/admin/AdminDepartments';
import AdminOfficers from './pages/admin/AdminOfficers';

function OfficerComplaints() {
  return <OfficerDashboard />;
}

function OfficerMap() {
  return <CivicMapPage audience="officer" />;
}

function OfficerPriority() {
  return <OfficerIncidents />;
}

function OfficerOverdue() {
  return <OfficerIncidents />;
}

function AdminComplaints() {
  return <AdminDashboard />;
}

function AdminIncidents() {
  return <AdminDashboard />;
}

function AdminJurisdictions() {
  return <AdminDepartments />;
}

function AdminAnalytics() {
  return <AdminDashboard />;
}

function SupportedIssues() {
  return <NearbyIssues />;
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Toaster position="top-right" />
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/explore" element={<ExplorePage />} />
          <Route path="/explore/incidents/:id" element={<IncidentDetail />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />

          <Route path="/dashboard" element={<ProtectedRoute roles={['citizen']}><CitizenDashboard /></ProtectedRoute>} />
          <Route path="/report" element={<ProtectedRoute roles={['citizen']}><ReportIssue /></ProtectedRoute>} />
          <Route path="/my-complaints" element={<ProtectedRoute roles={['citizen']}><MyComplaints /></ProtectedRoute>} />
          <Route path="/complaints/:id" element={<ProtectedRoute roles={['citizen']}><ComplaintDetail /></ProtectedRoute>} />
          <Route path="/nearby" element={<ProtectedRoute roles={['citizen']}><NearbyIssues /></ProtectedRoute>} />
          <Route path="/supported" element={<ProtectedRoute roles={['citizen']}><SupportedIssues /></ProtectedRoute>} />
          <Route path="/incidents/:id" element={<ProtectedRoute><IncidentDetail /></ProtectedRoute>} />
          <Route path="/profile" element={<ProtectedRoute><ProfilePage /></ProtectedRoute>} />

          <Route path="/officer" element={<ProtectedRoute roles={['officer']}><OfficerDashboard /></ProtectedRoute>} />
          <Route path="/officer/incidents" element={<ProtectedRoute roles={['officer']}><OfficerIncidents /></ProtectedRoute>} />
          <Route path="/officer/incidents/:id" element={<ProtectedRoute roles={['officer']}><OfficerIncidentReview /></ProtectedRoute>} />
          <Route path="/officer/complaints" element={<ProtectedRoute roles={['officer']}><OfficerComplaints /></ProtectedRoute>} />
          <Route path="/officer/map" element={<ProtectedRoute roles={['officer']}><OfficerMap /></ProtectedRoute>} />
          <Route path="/officer/priority" element={<ProtectedRoute roles={['officer']}><OfficerPriority /></ProtectedRoute>} />
          <Route path="/officer/overdue" element={<ProtectedRoute roles={['officer']}><OfficerOverdue /></ProtectedRoute>} />

          <Route path="/admin" element={<ProtectedRoute roles={['admin']}><AdminDashboard /></ProtectedRoute>} />
          <Route path="/admin/departments" element={<ProtectedRoute roles={['admin']}><AdminDepartments /></ProtectedRoute>} />
          <Route path="/admin/officers" element={<ProtectedRoute roles={['admin']}><AdminOfficers /></ProtectedRoute>} />
          <Route path="/admin/complaints" element={<ProtectedRoute roles={['admin']}><AdminComplaints /></ProtectedRoute>} />
          <Route path="/admin/incidents" element={<ProtectedRoute roles={['admin']}><AdminIncidents /></ProtectedRoute>} />
          <Route path="/admin/jurisdictions" element={<ProtectedRoute roles={['admin']}><AdminJurisdictions /></ProtectedRoute>} />
          <Route path="/admin/analytics" element={<ProtectedRoute roles={['admin']}><AdminAnalytics /></ProtectedRoute>} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
