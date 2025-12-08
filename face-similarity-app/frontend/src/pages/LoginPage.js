import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import './LoginPage.css';

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:5001';

function LoginPage() {
  const navigate = useNavigate();
  const [isLogin, setIsLogin] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // Login form state
  const [loginData, setLoginData] = useState({
    email: '',
    password: ''
  });

  // Register form state
  const [registerData, setRegisterData] = useState({
    full_name: '',
    department_name: '',
    email: '',
    officer_id: '',
    password: '',
    confirm_password: ''
  });

  const handleLoginChange = (e) => {
    setLoginData({
      ...loginData,
      [e.target.name]: e.target.value
    });
    setError('');
  };

  const handleRegisterChange = (e) => {
    setRegisterData({
      ...registerData,
      [e.target.name]: e.target.value
    });
    setError('');
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const response = await axios.post(`${API_BASE_URL}/api/auth/login`, {
        email: loginData.email,
        password: loginData.password
      });

      // Store token and user info
      localStorage.setItem('token', response.data.token);
      localStorage.setItem('user', JSON.stringify(response.data.user));

      setSuccess('Login successful! Redirecting...');
      
      // Redirect to main app
      setTimeout(() => {
        navigate('/');
      }, 1000);

    } catch (err) {
      setError(err.response?.data?.error || 'Login failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    // Validate passwords match
    if (registerData.password !== registerData.confirm_password) {
      setError('Passwords do not match');
      setLoading(false);
      return;
    }

    // Validate password strength
    if (registerData.password.length < 8) {
      setError('Password must be at least 8 characters long');
      setLoading(false);
      return;
    }

    try {
      const response = await axios.post(`${API_BASE_URL}/api/auth/register`, {
        full_name: registerData.full_name,
        department_name: registerData.department_name,
        email: registerData.email,
        officer_id: registerData.officer_id,
        password: registerData.password
      });

      // Store token and user info
      localStorage.setItem('token', response.data.token);
      localStorage.setItem('user', JSON.stringify(response.data.user));

      setSuccess('Registration successful! Redirecting...');
      
      // Redirect to main app
      setTimeout(() => {
        navigate('/');
      }, 1000);

    } catch (err) {
      setError(err.response?.data?.error || 'Registration failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const toggleMode = () => {
    setIsLogin(!isLogin);
    setError('');
    setSuccess('');
  };

  return (
    <div className="login-page">
      <div className="login-container">
        <div className="login-header">
          <div className="logo-section">
            <div className="logo-icon">🔐</div>
            <h1>Forensic Face Recognition System</h1>
            <p className="subtitle">Secure Access for Law Enforcement</p>
          </div>
        </div>

        <div className="login-form-container">
          <div className="form-tabs">
            <button 
              className={`tab ${isLogin ? 'active' : ''}`}
              onClick={() => setIsLogin(true)}
            >
              Login
            </button>
            <button 
              className={`tab ${!isLogin ? 'active' : ''}`}
              onClick={() => setIsLogin(false)}
            >
              Register
            </button>
          </div>

          {error && (
            <div className="alert alert-error">
              <span className="alert-icon">⚠️</span>
              {error}
            </div>
          )}

          {success && (
            <div className="alert alert-success">
              <span className="alert-icon">✓</span>
              {success}
            </div>
          )}

          {isLogin ? (
            <form onSubmit={handleLogin} className="login-form">
              <div className="form-group">
                <label htmlFor="login-email">Email Address</label>
                <input
                  type="email"
                  id="login-email"
                  name="email"
                  value={loginData.email}
                  onChange={handleLoginChange}
                  placeholder="officer@forensic.gov.in"
                  required
                  disabled={loading}
                />
              </div>

              <div className="form-group">
                <label htmlFor="login-password">Password</label>
                <input
                  type="password"
                  id="login-password"
                  name="password"
                  value={loginData.password}
                  onChange={handleLoginChange}
                  placeholder="Enter your password"
                  required
                  disabled={loading}
                />
              </div>

              <button 
                type="submit" 
                className="btn-primary"
                disabled={loading}
              >
                {loading ? 'Logging in...' : 'Login'}
              </button>

              <p className="form-footer">
                Don't have an account? 
                <button type="button" onClick={toggleMode} className="link-button">
                  Register here
                </button>
              </p>
            </form>
          ) : (
            <form onSubmit={handleRegister} className="login-form">
              <div className="form-group">
                <label htmlFor="register-name">Full Name</label>
                <input
                  type="text"
                  id="register-name"
                  name="full_name"
                  value={registerData.full_name}
                  onChange={handleRegisterChange}
                  placeholder="John Doe"
                  required
                  disabled={loading}
                />
              </div>

              <div className="form-group">
                <label htmlFor="register-department">Department Name</label>
                <input
                  type="text"
                  id="register-department"
                  name="department_name"
                  value={registerData.department_name}
                  onChange={handleRegisterChange}
                  placeholder="State Forensic Department"
                  required
                  disabled={loading}
                />
              </div>

              <div className="form-group">
                <label htmlFor="register-email">Official Email</label>
                <input
                  type="email"
                  id="register-email"
                  name="email"
                  value={registerData.email}
                  onChange={handleRegisterChange}
                  placeholder="officer@forensic.gov.in"
                  required
                  disabled={loading}
                />
                <small className="form-hint">
                  Only @forensic.gov.in, @police.gov.in, or @stateforensic.gov.in emails allowed
                </small>
              </div>

              <div className="form-group">
                <label htmlFor="register-officer-id">Officer ID</label>
                <input
                  type="text"
                  id="register-officer-id"
                  name="officer_id"
                  value={registerData.officer_id}
                  onChange={handleRegisterChange}
                  placeholder="F12345"
                  required
                  disabled={loading}
                />
                <small className="form-hint">
                  Contact your administrator if you don't have an Officer ID
                </small>
              </div>

              <div className="form-group">
                <label htmlFor="register-password">Password</label>
                <input
                  type="password"
                  id="register-password"
                  name="password"
                  value={registerData.password}
                  onChange={handleRegisterChange}
                  placeholder="Minimum 8 characters"
                  required
                  disabled={loading}
                />
              </div>

              <div className="form-group">
                <label htmlFor="register-confirm-password">Confirm Password</label>
                <input
                  type="password"
                  id="register-confirm-password"
                  name="confirm_password"
                  value={registerData.confirm_password}
                  onChange={handleRegisterChange}
                  placeholder="Re-enter your password"
                  required
                  disabled={loading}
                />
              </div>

              <button 
                type="submit" 
                className="btn-primary"
                disabled={loading}
              >
                {loading ? 'Registering...' : 'Register'}
              </button>

              <p className="form-footer">
                Already have an account? 
                <button type="button" onClick={toggleMode} className="link-button">
                  Login here
                </button>
              </p>
            </form>
          )}
        </div>

        <div className="login-footer">
          <p>🔒 Secure Authentication System</p>
          <p className="footer-note">
            This system is restricted to authorized law enforcement personnel only
          </p>
        </div>
      </div>
    </div>
  );
}

export default LoginPage;
