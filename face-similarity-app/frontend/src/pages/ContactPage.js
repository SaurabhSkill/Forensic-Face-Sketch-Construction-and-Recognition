import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import './ContactPage.css';

function ContactPage() {
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

  const [formData, setFormData] = useState({
    name: '',
    email: '',
    department: '',
    subject: '',
    message: ''
  });

  const [submitted, setSubmitted] = useState(false);

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    // In a real application, you would send this to a backend
    console.log('Form submitted:', formData);
    setSubmitted(true);
    
    // Reset form after 3 seconds
    setTimeout(() => {
      setSubmitted(false);
      setFormData({
        name: '',
        email: '',
        department: '',
        subject: '',
        message: ''
      });
    }, 3000);
  };

  return (
    <div className="contact-page">
      {/* Header */}
      <header className="header">
        <div className="container">
          <div className="logo" onClick={() => navigate('/')} style={{cursor: 'pointer'}}>
            <div className="logo-icon">
              <svg viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
              </svg>
            </div>
            <div className="logo-text">
              <span className="logo-main">FaceFind</span>
              <span className="logo-sub">Forensics</span>
            </div>
          </div>
          <nav className="nav">
            <button 
              className="nav-link"
              onClick={() => navigate('/')}
            >
              Dashboard
            </button>
            <button 
              className="nav-link"
              onClick={() => navigate('/about')}
            >
              About Us
            </button>
            <button 
              className="nav-link active"
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
      
      <div className="contact-hero">
        <div className="container">
          <h1 className="contact-title">Contact Us</h1>
          <p className="contact-subtitle">
            Get in touch with our forensic support team
          </p>
        </div>
      </div>

      <div className="contact-content">
        <div className="container">
          <div className="contact-grid">
            {/* Contact Information */}
            <div className="contact-info">
              <h2>Get In Touch</h2>
              <p className="info-description">
                Have questions about FaceFind Forensics? Need technical support? 
                Want to request access for your department? We're here to help.
              </p>

              <div className="info-cards">
                <div className="info-card">
                  <div className="info-icon">📧</div>
                  <h3>Email</h3>
                  <p>support@facefind.forensic.gov.in</p>
                  <p>info@facefind.forensic.gov.in</p>
                </div>

                <div className="info-card">
                  <div className="info-icon">📞</div>
                  <h3>Phone</h3>
                  <p>+91 (0) 5231 958</p>
                  <p>Mon-Fri: 9:00 AM - 6:00 PM IST</p>
                </div>

                <div className="info-card">
                  <div className="info-icon">📍</div>
                  <h3>Address</h3>
                  <p>Central Forensic Science Laboratory</p>
                  <p>New Delhi, India</p>
                </div>

                <div className="info-card">
                  <div className="info-icon">🚨</div>
                  <h3>Emergency Support</h3>
                  <p>24/7 Hotline: +91 (0) 1800-FORENSIC</p>
                  <p>For urgent case assistance</p>
                </div>
              </div>

              <div className="support-hours">
                <h3>Support Hours</h3>
                <ul>
                  <li><strong>Technical Support:</strong> 24/7</li>
                  <li><strong>General Inquiries:</strong> Mon-Fri, 9 AM - 6 PM</li>
                  <li><strong>Training & Onboarding:</strong> By Appointment</li>
                  <li><strong>Emergency Cases:</strong> 24/7 Priority Support</li>
                </ul>
              </div>
            </div>

            {/* Contact Form */}
            <div className="contact-form-container">
              <h2>Send Us a Message</h2>
              
              {submitted ? (
                <div className="success-message">
                  <div className="success-icon">✓</div>
                  <h3>Message Sent Successfully!</h3>
                  <p>We'll get back to you within 24 hours.</p>
                </div>
              ) : (
                <form className="contact-form" onSubmit={handleSubmit}>
                  <div className="form-group">
                    <label htmlFor="name">Full Name *</label>
                    <input
                      type="text"
                      id="name"
                      name="name"
                      value={formData.name}
                      onChange={handleChange}
                      placeholder="Officer John Doe"
                      required
                    />
                  </div>

                  <div className="form-group">
                    <label htmlFor="email">Official Email *</label>
                    <input
                      type="email"
                      id="email"
                      name="email"
                      value={formData.email}
                      onChange={handleChange}
                      placeholder="officer@forensic.gov.in"
                      required
                    />
                  </div>

                  <div className="form-group">
                    <label htmlFor="department">Department/Agency *</label>
                    <input
                      type="text"
                      id="department"
                      name="department"
                      value={formData.department}
                      onChange={handleChange}
                      placeholder="State Forensic Department"
                      required
                    />
                  </div>

                  <div className="form-group">
                    <label htmlFor="subject">Subject *</label>
                    <select
                      id="subject"
                      name="subject"
                      value={formData.subject}
                      onChange={handleChange}
                      required
                    >
                      <option value="">Select a subject</option>
                      <option value="technical">Technical Support</option>
                      <option value="access">Request Access</option>
                      <option value="training">Training & Onboarding</option>
                      <option value="feedback">Feedback</option>
                      <option value="bug">Report a Bug</option>
                      <option value="feature">Feature Request</option>
                      <option value="other">Other</option>
                    </select>
                  </div>

                  <div className="form-group">
                    <label htmlFor="message">Message *</label>
                    <textarea
                      id="message"
                      name="message"
                      value={formData.message}
                      onChange={handleChange}
                      placeholder="Please describe your inquiry in detail..."
                      rows="6"
                      required
                    ></textarea>
                  </div>

                  <button type="submit" className="submit-btn">
                    Send Message
                  </button>

                  <p className="form-note">
                    * All fields are required. We typically respond within 24 hours.
                  </p>
                </form>
              )}
            </div>
          </div>

          {/* FAQ Section */}
          <div className="faq-section">
            <h2>Frequently Asked Questions</h2>
            <div className="faq-grid">
              <div className="faq-item">
                <h3>How do I get access to FaceFind?</h3>
                <p>
                  Access is restricted to verified law enforcement personnel. Contact us 
                  with your official email and officer ID for verification.
                </p>
              </div>
              <div className="faq-item">
                <h3>What email domains are accepted?</h3>
                <p>
                  We accept @forensic.gov.in, @police.gov.in, and @stateforensic.gov.in 
                  email addresses for registration.
                </p>
              </div>
              <div className="faq-item">
                <h3>Is training provided?</h3>
                <p>
                  Yes! We offer comprehensive training sessions for new departments. 
                  Contact us to schedule a training session.
                </p>
              </div>
              <div className="faq-item">
                <h3>How accurate is the face matching?</h3>
                <p>
                  Our AI achieves 95%+ accuracy for photo-to-photo matching and optimized 
                  algorithms for sketch-to-photo comparison.
                </p>
              </div>
              <div className="faq-item">
                <h3>Is my data secure?</h3>
                <p>
                  Absolutely. All data is encrypted, access is restricted, and we comply 
                  with law enforcement data protection standards.
                </p>
              </div>
              <div className="faq-item">
                <h3>What if I forget my password?</h3>
                <p>
                  Contact our support team with your officer ID and official email for 
                  password reset assistance.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default ContactPage;
