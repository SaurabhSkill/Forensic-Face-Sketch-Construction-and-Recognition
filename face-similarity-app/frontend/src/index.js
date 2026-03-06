import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import './styles/layout.css';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import AppLayout from './layout/AppLayout';
import HomePage from './pages/HomePage';
import ComparePage from './pages/ComparePage';
import SearchPage from './pages/SearchPage';
import DatabasePage from './pages/DatabasePage';
import SketchPage from './pages/SketchPage.js';
import LoginPageV2 from './pages/LoginPageV2';
import AboutPage from './pages/AboutPage.js';
import ContactPage from './pages/ContactPage.js';
import AdminDashboard from './pages/AdminDashboard';
import ChangePassword from './pages/ChangePassword';
import ProtectedRouteV2 from './components/ProtectedRouteV2';

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <Routes>
        {/* Authentication Routes */}
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
        
        {/* Change Password Route */}
        <Route 
          path="/change-password" 
          element={
            <ProtectedRouteV2>
              <ChangePassword />
            </ProtectedRouteV2>
          } 
        />
        
        {/* Main Application Routes with Layout */}
        <Route 
          path="/" 
          element={
            <ProtectedRouteV2>
              <AppLayout />
            </ProtectedRouteV2>
          }
        >
          {/* Home Page */}
          <Route index element={<HomePage />} />
          
          {/* Tool Pages */}
          <Route path="sketch" element={<SketchPage />} />
          <Route path="compare" element={<ComparePage />} />
          <Route path="search" element={<SearchPage />} />
          <Route path="database" element={<DatabasePage />} />
          <Route path="about" element={<AboutPage />} />
          <Route path="contact" element={<ContactPage />} />
        </Route>
        
        {/* Fallback Route */}
        <Route path="*" element={<Navigate to="/compare" replace />} />
      </Routes>
    </BrowserRouter>
  </React.StrictMode>
);
