import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import './UserHeader.css';

function UserHeader() {
  const navigate = useNavigate();
  const [user, setUser] = useState(null);
  const [showDropdown, setShowDropdown] = useState(false);

  useEffect(() => {
    const userStr = localStorage.getItem('user');
    if (userStr) {
      try {
        setUser(JSON.parse(userStr));
      } catch (e) {
        console.error('Error parsing user data:', e);
      }
    }
  }, []);

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    navigate('/login');
  };

  if (!user) {
    return null;
  }

  return (
    <div className="user-header">
      <div className="user-info-container">
        <div className="user-badge">
          <div className="user-avatar">
            {user.full_name.charAt(0).toUpperCase()}
          </div>
          <div className="user-details">
            <div className="user-name">{user.full_name}</div>
            <div className="user-role">{user.department_name}</div>
          </div>
        </div>
        
        <div className="user-actions">
          <button 
            className="user-menu-btn"
            onClick={() => setShowDropdown(!showDropdown)}
          >
            ⚙️
          </button>
          
          {showDropdown && (
            <div className="user-dropdown">
              <div className="dropdown-item user-info-item">
                <div className="info-label">Officer ID</div>
                <div className="info-value">{user.officer_id}</div>
              </div>
              <div className="dropdown-item user-info-item">
                <div className="info-label">Email</div>
                <div className="info-value">{user.email}</div>
              </div>
              <div className="dropdown-divider"></div>
              <button 
                className="dropdown-item logout-btn"
                onClick={handleLogout}
              >
                <span className="logout-icon">🚪</span>
                Logout
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default UserHeader;
