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


const ProtectedRoute = ({ children }) => {
  const token = localStorage.getItem('satya_token');
  
  if (!token) {
    return <Navigate to="/login" replace />;
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
          <Route path="/admin" element={<ProtectedRoute><AdminDashboard /></ProtectedRoute>} />
          <Route path="/verify" element={<ProtectedRoute><DocumentVerification /></ProtectedRoute>} />
          <Route path="/verify-aadhaar" element={<ProtectedRoute><AadhaarVerification /></ProtectedRoute>} />

        </Routes>
      </div>
      <FloatingChatbot />
    </div>
  );
}

export default App;
