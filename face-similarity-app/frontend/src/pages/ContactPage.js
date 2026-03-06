import React, { useState } from 'react';
import './ContactPage.css';
import PageContainer from '../layout/PageContainer';

function ContactPage() {
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
      <div className="contact-hero">
        <PageContainer variant="default">
          <h1 className="contact-title">Contact Us</h1>
          <p className="contact-subtitle">
            Get in touch with our forensic support team
          </p>
        </PageContainer>
      </div>

      <div className="contact-content">
        <PageContainer variant="default">
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
        </PageContainer>
      </div>
    </div>
  );
}

export default ContactPage;
