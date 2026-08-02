import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import Navbar from './components/Navbar';
import LandingPage from './pages/LandingPage';
import EligibilityForm from './pages/EligibilityForm';
import SchemeList from './pages/SchemeList';
import FloatingChatbot from './components/FloatingChatbot';
import Login from './pages/Login';
import Register from './pages/Register';
import AdminDashboard from './pages/AdminDashboard';
import DocumentVerification from './pages/DocumentVerification';
import AadhaarVerification from './pages/AadhaarVerification';
import DocumentVault from './pages/DocumentVault';
import AdminDiagnostics from './pages/AdminDiagnostics';


const ProtectedRoute = ({ children }) => {
  const token = localStorage.getItem('satya_token');
  if (!token) return <Navigate to="/login" replace />;
  return children;
};

const AdminRoute = ({ children }) => {
  const token = localStorage.getItem('satya_token');
  const userJson = localStorage.getItem('satya_user');
  const user = userJson ? JSON.parse(userJson) : null;

  if (!token || !user || user.role !== 'admin') {
    return <Navigate to="/" replace />;
  }

  return children;
};

function App() {
  return (
    <div className="App">
      <Navbar />
      <div style={{ paddingTop: '70px', minHeight: '100vh', width: '100%' }}>
         <Routes>
          <Route path="/" element={<ProtectedRoute><LandingPage /></ProtectedRoute>} />
          <Route path="/check" element={<ProtectedRoute><EligibilityForm /></ProtectedRoute>} />
          <Route path="/schemes" element={<ProtectedRoute><SchemeList /></ProtectedRoute>} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/admin" element={<AdminRoute><AdminDashboard /></AdminRoute>} />
          <Route path="/verify" element={<ProtectedRoute><DocumentVerification /></ProtectedRoute>} />
          <Route path="/verify-aadhaar" element={<ProtectedRoute><AadhaarVerification /></ProtectedRoute>} />
          <Route path="/vault" element={<ProtectedRoute><DocumentVault /></ProtectedRoute>} />
          <Route path="/diagnostics" element={<AdminRoute><AdminDiagnostics /></AdminRoute>} />
        </Routes>
      </div>
      <FloatingChatbot />
    </div>
  );
}

export default App;
