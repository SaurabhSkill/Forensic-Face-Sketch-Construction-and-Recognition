import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { API_BASE_URL } from '../config';
import './AdminDashboard.css';

function AdminDashboard() {
  const navigate = useNavigate();
  const [user, setUser] = useState(null);
  const [officers, setOfficers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showAddForm, setShowAddForm] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');

  // Add officer form state
  const [formData, setFormData] = useState({
    full_name: '',
    department_name: '',
    email: '',
    officer_id: ''
  });

  useEffect(() => {
    const userStr = localStorage.getItem('user');
    if (userStr) {
      const userData = JSON.parse(userStr);
      setUser(userData);
      
      // Check if user is admin
      if (userData.role !== 'admin') {
        navigate('/');
        return;
      }
    } else {
      navigate('/login-v2');
      return;
    }

    loadOfficers();
  }, [navigate]);

  const loadOfficers = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get(`${API_BASE_URL}/api/admin/officers`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setOfficers(response.data.officers);
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to load officers');
    } finally {
      setLoading(false);
    }
  };

  const handleAddOfficer = async (e) => {
    e.preventDefault();
    setError('');
    setMessage('');

    try {
      const token = localStorage.getItem('token');
      const response = await axios.post(
        `${API_BASE_URL}/api/admin/officers`,
        formData,
        { headers: { Authorization: `Bearer ${token}` } }
      );

      setMessage('Officer added successfully!');
      if (response.data.temp_password_dev) {
        setMessage(`Officer added! Temp password: ${response.data.temp_password_dev}`);
      }
      
      setFormData({ full_name: '', department_name: '', email: '', officer_id: '' });
      setShowAddForm(false);
      loadOfficers();
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to add officer');
    }
  };

  const handleResetPassword = async (officerId) => {
    if (!window.confirm('Reset password for this officer?')) return;

    try {
      const token = localStorage.getItem('token');
      const response = await axios.post(
        `${API_BASE_URL}/api/admin/officers/${officerId}/reset-password`,
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      );

      if (response.data.temp_password_dev) {
        alert(`Password reset! New temp password: ${response.data.temp_password_dev}`);
      } else {
        alert('Password reset successfully! New password sent to officer email.');
      }
    } catch (err) {
      alert(err.response?.data?.error || 'Failed to reset password');
    }
  };

  const handleDeleteOfficer = async (officerId) => {
    if (!window.confirm('Are you sure you want to delete this officer?')) return;

    try {
      const token = localStorage.getItem('token');
      await axios.delete(`${API_BASE_URL}/api/admin/officers/${officerId}`, {
        headers: { Authorization: `Bearer ${token}` }
      });

      setMessage('Officer deleted successfully');
      loadOfficers();
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to delete officer');
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    navigate('/login-v2');
  };

  if (loading) {
    return (
      <div className="admin-dashboard">
        <div className="loading">Loading...</div>
      </div>
    );
  }

  return (
    <div className="admin-dashboard">
      {/* Header */}
      <header className="admin-header">
        <div className="header-content">
          <div className="logo">
            <div className="logo-icon">
              <svg viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
              </svg>
            </div>
            <div className="logo-text">
              <span className="logo-main">FaceFind</span>
              <span className="logo-sub">Admin Panel</span>
            </div>
          </div>

          <div className="header-right">
            <div className="user-info">
              <span className="user-name">{user?.full_name}</span>
              <span className="user-role">Administrator</span>
            </div>
            <button className="logout-btn" onClick={handleLogout}>
              Logout
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="admin-main">
        <div className="container">
          <div className="page-header">
            <h1>Officer Management</h1>
            <button className="add-btn" onClick={() => setShowAddForm(!showAddForm)}>
              {showAddForm ? 'Cancel' : '+ Add New Officer'}
            </button>
          </div>

          {error && <div className="alert alert-error">{error}</div>}
          {message && <div className="alert alert-success">{message}</div>}

          {/* Add Officer Form */}
          {showAddForm && (
            <div className="add-form-card">
              <h2>Add New Officer</h2>
              <form onSubmit={handleAddOfficer}>
                <div className="form-row">
                  <div className="form-group">
                    <label>Full Name *</label>
                    <input
                      type="text"
                      value={formData.full_name}
                      onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
                      placeholder="John Doe"
                      required
                    />
                  </div>
                  <div className="form-group">
                    <label>Department *</label>
                    <input
                      type="text"
                      value={formData.department_name}
                      onChange={(e) => setFormData({ ...formData, department_name: e.target.value })}
                      placeholder="Forensic Department"
                      required
                    />
                  </div>
                </div>

                <div className="form-row">
                  <div className="form-group">
                    <label>Email *</label>
                    <input
                      type="email"
                      value={formData.email}
                      onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                      placeholder="officer@forensic.gov.in"
                      required
                    />
                    <small>
                      Government emails required: @forensic.gov.in, @police.gov.in, @stateforensic.gov.in
                      <br />
                      <strong>Note:</strong> You can use your own email ({user?.email}) to test the officer portal
                    </small>
                  </div>
                  <div className="form-group">
                    <label>Officer ID *</label>
                    <input
                      type="text"
                      value={formData.officer_id}
                      onChange={(e) => setFormData({ ...formData, officer_id: e.target.value })}
                      placeholder="F12345"
                      required
                    />
                  </div>
                </div>

                <button type="submit" className="submit-btn">
                  Add Officer
                </button>
              </form>
            </div>
          )}

          {/* Officers List */}
          <div className="officers-list">
            <h2>All Officers ({officers.length})</h2>
            
            {officers.length === 0 ? (
              <div className="empty-state">
                <p>No officers found. Add your first officer to get started.</p>
              </div>
            ) : (
              <div className="officers-grid">
                {officers.map((officer) => (
                  <div key={officer.id} className="officer-card">
                    <div className="officer-header">
                      <div className="officer-avatar">
                        {officer.full_name.charAt(0).toUpperCase()}
                      </div>
                      <div className="officer-info">
                        <h3>{officer.full_name}</h3>
                        <p className="officer-id">{officer.officer_id}</p>
                      </div>
                    </div>

                    <div className="officer-details">
                      <div className="detail-row">
                        <span className="label">Department:</span>
                        <span className="value">{officer.department_name}</span>
                      </div>
                      <div className="detail-row">
                        <span className="label">Email:</span>
                        <span className="value">{officer.email}</span>
                      </div>
                      <div className="detail-row">
                        <span className="label">Status:</span>
                        <span className={`badge ${officer.is_temp_password ? 'badge-warning' : 'badge-success'}`}>
                          {officer.is_temp_password ? 'Temp Password' : 'Active'}
                        </span>
                      </div>
                      <div className="detail-row">
                        <span className="label">Last Login:</span>
                        <span className="value">
                          {officer.last_login ? new Date(officer.last_login).toLocaleDateString() : 'Never'}
                        </span>
                      </div>
                    </div>

                    <div className="officer-actions">
                      <button
                        className="action-btn reset-btn"
                        onClick={() => handleResetPassword(officer.id)}
                      >
                        Reset Password
                      </button>
                      <button
                        className="action-btn delete-btn"
                        onClick={() => handleDeleteOfficer(officer.id)}
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}

export default AdminDashboard;
