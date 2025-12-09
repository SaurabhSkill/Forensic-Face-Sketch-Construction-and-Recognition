import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import App from './App';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import SketchPage from './pages/SketchPage';
import LoginPageV2 from './pages/LoginPageV2';
import AboutPage from './pages/AboutPage';
import ContactPage from './pages/ContactPage';
import AdminDashboard from './pages/AdminDashboard';
import ChangePassword from './pages/ChangePassword';
import ProtectedRouteV2 from './components/ProtectedRouteV2';

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <Routes>
        {/* New V2 Authentication System */}
        <Route path="/login" element={<LoginPageV2 />} />
        <Route path="/login-v2" element={<LoginPageV2 />} />
        
        {/* Admin Routes */}
        <Route 
          path="/admin/dashboard" 
          element={
            <ProtectedRouteV2 requiredRole="admin">
              <AdminDashboard />
            </ProtectedRouteV2>
          } 
        />
        
        {/* Change Password (for officers with temp password) */}
        <Route 
          path="/change-password" 
          element={
            <ProtectedRouteV2>
              <ChangePassword />
            </ProtectedRouteV2>
          } 
        />
        
        {/* Officer/User Routes */}
        <Route 
          path="/" 
          element={
            <ProtectedRouteV2>
              <App />
            </ProtectedRouteV2>
          } 
        />
        <Route 
          path="/sketch" 
          element={
            <ProtectedRouteV2>
              <SketchPage />
            </ProtectedRouteV2>
          } 
        />
        <Route 
          path="/about" 
          element={
            <ProtectedRouteV2>
              <AboutPage />
            </ProtectedRouteV2>
          } 
        />
        <Route 
          path="/contact" 
          element={
            <ProtectedRouteV2>
              <ContactPage />
            </ProtectedRouteV2>
          } 
        />
        <Route 
          path="*" 
          element={
            <ProtectedRouteV2>
              <App />
            </ProtectedRouteV2>
          } 
        />
      </Routes>
    </BrowserRouter>
  </React.StrictMode>
);
