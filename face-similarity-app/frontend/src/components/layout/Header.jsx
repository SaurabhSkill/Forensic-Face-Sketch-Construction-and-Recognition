import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import PropTypes from 'prop-types';

const Header = ({ activeTab }) => {
  const navigate = useNavigate();
  const [user, setUser] = useState(null);
  const [showUserDropdown, setShowUserDropdown] = useState(false);

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

  return (
    <header className="header">
      <div className="layout-container">
        <button 
          className="logo" 
          onClick={() => navigate('/')}
          aria-label="Go to home page"
        >
          <div className="logo-icon">
            <svg viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
            </svg>
          </div>
          <div className="logo-text">
            <span className="logo-main">FaceFind</span>
            <span className="logo-sub">Forensics</span>
          </div>
        </button>
        <nav className="nav">
          <button 
            className={`nav-link ${activeTab === 'home' ? 'active' : ''}`}
            onClick={() => navigate('/')}
          >
            Home
          </button>
          <button 
            className={`nav-link ${activeTab === 'sketch' ? 'active' : ''}`}
            onClick={() => navigate('/sketch')}
          >
            Create Sketch
          </button>
          <button 
            className={`nav-link ${activeTab === 'compare' ? 'active' : ''}`}
            onClick={() => navigate('/compare')}
          >
            Face Comparison
          </button>
          <button 
            className={`nav-link ${activeTab === 'search' ? 'active' : ''}`}
            onClick={() => navigate('/search')}
          >
            Sketch Search
          </button>
          <button 
            className={`nav-link ${activeTab === 'criminals' ? 'active' : ''}`}
            onClick={() => navigate('/database')}
          >
            Criminal Database
          </button>
          <button 
            className={`nav-link ${activeTab === 'about' ? 'active' : ''}`}
            onClick={() => navigate('/about')}
          >
            About
          </button>
          <button 
            className={`nav-link ${activeTab === 'contact' ? 'active' : ''}`}
            onClick={() => navigate('/contact')}
          >
            Contact
          </button>
          
          {/* User Menu */}
          {user && (
            <div className="user-menu">
              <button 
                className="user-menu-btn"
                onClick={() => setShowUserDropdown(!showUserDropdown)}
              >
                ⚙️
              </button>
              
              {showUserDropdown && (
                <div className="user-dropdown">
                  <div className="dropdown-item user-info-item">
                    <div className="info-label">Name</div>
                    <div className="info-value">{user.full_name}</div>
                  </div>
                  <div className="dropdown-item user-info-item">
                    <div className="info-label">Department</div>
                    <div className="info-value">{user.department_name}</div>
                  </div>
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
          )}
        </nav>
      </div>
    </header>
  );
};

Header.propTypes = {
  activeTab: PropTypes.string
};

export default Header;
