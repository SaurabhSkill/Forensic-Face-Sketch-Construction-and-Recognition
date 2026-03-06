import React from 'react';
import './AboutPage.css';
import PageContainer from '../layout/PageContainer';

function AboutPage() {
  return (
    <div className="about-page">
      <div className="about-hero">
        <PageContainer variant="default">
          <h1 className="about-title">About FaceFind Forensics</h1>
          <p className="about-subtitle">
            Advanced AI-Powered Facial Recognition for Law Enforcement
          </p>
        </PageContainer>
      </div>

      <div className="about-content">
        <PageContainer variant="default">
          {/* Mission Section */}
          <section className="about-section">
            <div className="section-icon">🎯</div>
            <h2>Our Mission</h2>
            <p>
              FaceFind Forensics is dedicated to bridging the gap between witness testimony 
              and positive identification through cutting-edge facial reconstruction and 
              recognition technology. We empower law enforcement agencies with AI-powered 
              tools to solve cases faster and more accurately.
            </p>
          </section>

          {/* Technology Section */}
          <section className="about-section">
            <div className="section-icon">🤖</div>
            <h2>Our Technology</h2>
            <div className="tech-grid">
              <div className="tech-card">
                <h3>DeepFace AI</h3>
                <p>State-of-the-art facial recognition using Facenet512 model</p>
              </div>
              <div className="tech-card">
                <h3>Sketch Matching</h3>
                <p>Advanced algorithms optimized for sketch-to-photo comparison</p>
              </div>
              <div className="tech-card">
                <h3>Real-time Processing</h3>
                <p>Fast and accurate results with intelligent caching</p>
              </div>
              <div className="tech-card">
                <h3>Secure Database</h3>
                <p>Encrypted storage for sensitive criminal records</p>
              </div>
            </div>
          </section>

          {/* Features Section */}
          <section className="about-section">
            <div className="section-icon">✨</div>
            <h2>Key Features</h2>
            <div className="features-list">
              <div className="feature-item">
                <span className="feature-icon">👤</span>
                <div>
                  <h3>Face Comparison</h3>
                  <p>Compare sketches with photographs using AI-powered similarity scoring</p>
                </div>
              </div>
              <div className="feature-item">
                <span className="feature-icon">🗄️</span>
                <div>
                  <h3>Criminal Database</h3>
                  <p>Comprehensive database management with detailed forensic profiles</p>
                </div>
              </div>
              <div className="feature-item">
                <span className="feature-icon">🔍</span>
                <div>
                  <h3>Sketch Search</h3>
                  <p>Search entire database using sketch images with ranked results</p>
                </div>
              </div>
              <div className="feature-item">
                <span className="feature-icon">🎨</span>
                <div>
                  <h3>Sketch Creation</h3>
                  <p>Built-in tools for creating facial sketches from witness descriptions</p>
                </div>
              </div>
              <div className="feature-item">
                <span className="feature-icon">🔒</span>
                <div>
                  <h3>Secure Access</h3>
                  <p>JWT authentication restricted to verified law enforcement personnel</p>
                </div>
              </div>
              <div className="feature-item">
                <span className="feature-icon">⚡</span>
                <div>
                  <h3>Performance Optimized</h3>
                  <p>Intelligent caching and pre-loading for lightning-fast results</p>
                </div>
              </div>
            </div>
          </section>

          {/* Team Section */}
          <section className="about-section">
            <div className="section-icon">👥</div>
            <h2>Built for Law Enforcement</h2>
            <p>
              FaceFind Forensics is designed specifically for forensic departments, 
              police agencies, and state investigation bureaus. Our system is trusted 
              by law enforcement professionals across multiple jurisdictions to aid 
              in criminal investigations and positive identifications.
            </p>
            <div className="stats-grid">
              <div className="stat-card">
                <div className="stat-number">95%+</div>
                <div className="stat-label">Accuracy Rate</div>
              </div>
              <div className="stat-card">
                <div className="stat-number">&lt;3s</div>
                <div className="stat-label">Average Processing Time</div>
              </div>
              <div className="stat-card">
                <div className="stat-number">24/7</div>
                <div className="stat-label">System Availability</div>
              </div>
              <div className="stat-card">
                <div className="stat-number">100%</div>
                <div className="stat-label">Secure & Encrypted</div>
              </div>
            </div>
          </section>

          {/* Security Section */}
          <section className="about-section">
            <div className="section-icon">🛡️</div>
            <h2>Security & Privacy</h2>
            <p>
              We take security seriously. All data is encrypted, access is restricted 
              to verified officers, and our system complies with law enforcement data 
              protection standards. Your investigations remain confidential and secure.
            </p>
            <ul className="security-list">
              <li>✅ End-to-end encryption</li>
              <li>✅ JWT token-based authentication</li>
              <li>✅ Officer ID verification</li>
              <li>✅ Government email domain validation</li>
              <li>✅ Secure password hashing (bcrypt)</li>
              <li>✅ Audit logging for all actions</li>
            </ul>
          </section>
        </PageContainer>
      </div>
    </div>
  );
}

export default AboutPage;
