import React from 'react';
import { Navigate } from 'react-router-dom';

function ProtectedRouteV2({ children, requiredRole }) {
  const token = localStorage.getItem('token');
  const userStr = localStorage.getItem('user');

  // Check if user is authenticated
  if (!token || !userStr) {
    return <Navigate to="/login-v2" replace />;
  }

  // Check role if required
  if (requiredRole) {
    try {
      const user = JSON.parse(userStr);
      
      if (user.role !== requiredRole) {
        // Redirect based on actual role
        if (user.role === 'admin') {
          return <Navigate to="/admin/dashboard" replace />;
        } else {
          return <Navigate to="/" replace />;
        }
      }
    } catch (e) {
      console.error('Error parsing user data:', e);
      return <Navigate to="/login-v2" replace />;
    }
  }

  return children;
}

export default ProtectedRouteV2;
