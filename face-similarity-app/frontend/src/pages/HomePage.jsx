import React from 'react';
import { useNavigate } from 'react-router-dom';
import Face3DModel from '../components/Face3DModel';
import PageContainer from '../layout/PageContainer';
import './HomePage.css';

const HomePage = () => {
  const navigate = useNavigate();

  const features = [
    {
      id: 'compare',
      title: 'Face Comparison',
      description: 'Compare facial sketches with photographs using advanced AI algorithms',
      icon: (
        <svg viewBox="0 0 24 24" fill="currentColor">
          <path d="M12,2A10,10 0 0,0 2,12A10,10 0 0,0 12,22A10,10 0 0,0 22,12A10,10 0 0,0 12,2M12,4A8,8 0 0,1 20,12A8,8 0 0,1 12,20A8,8 0 0,1 4,12A8,8 0 0,1 12,4M12,6A6,6 0 0,0 6,12A6,6 0 0,0 12,18A6,6 0 0,0 18,12A6,6 0 0,0 12,6M12,8A4,4 0 0,1 16,12A4,4 0 0,1 12,16A4,4 0 0,1 8,12A4,4 0 0,1 12,8Z"/>
        </svg>
      ),
      route: '/compare'
    },
    {
      id: 'search',
      title: 'Sketch Search',
      description: 'Search criminal database using facial sketches with real-time matching',
      icon: (
        <svg viewBox="0 0 24 24" fill="currentColor">
          <path d="M9.5,3A6.5,6.5 0 0,1 16,9.5C16,11.11 15.41,12.59 14.44,13.73L14.71,14H15.5L20.5,19L19,20.5L14,15.5V14.71L13.73,14.44C12.59,15.41 11.11,16 9.5,16A6.5,6.5 0 0,1 3,9.5A6.5,6.5 0 0,1 9.5,3M9.5,5C7,5 5,7 5,9.5C5,12 7,14 9.5,14C12,14 14,12 14,9.5C14,7 12,5 9.5,5Z"/>
        </svg>
      ),
      route: '/search'
    },
    {
      id: 'database',
      title: 'Criminal Database',
      description: 'Manage and maintain comprehensive criminal profiles and records',
      icon: (
        <svg viewBox="0 0 24 24" fill="currentColor">
          <path d="M12,3C7.58,3 4,4.79 4,7C4,9.21 7.58,11 12,11C16.42,11 20,9.21 20,7C20,4.79 16.42,3 12,3M4,9V12C4,14.21 7.58,16 12,16C16.42,16 20,14.21 20,12V9C20,11.21 16.42,13 12,13C7.58,13 4,11.21 4,9M4,14V17C4,19.21 7.58,21 12,21C16.42,21 20,19.21 20,17V14C20,16.21 16.42,18 12,18C7.58,18 4,16.21 4,14Z"/>
        </svg>
      ),
      route: '/database'
    },
    {
      id: 'sketch',
      title: 'Create Sketch',
      description: 'Build a suspect sketch using facial components and AI-assisted tools',
      icon: (
        <svg viewBox="0 0 24 24" fill="currentColor">
          <path d="M12,2C6.47,2 2,6.47 2,12C2,17.53 6.47,22 12,22A10,10 0 0,0 22,12C22,6.47 17.5,2 12,2M12,20A8,8 0 0,1 4,12A8,8 0 0,1 12,4A8,8 0 0,1 20,12A8,8 0 0,1 12,20M16.18,7.76L15.12,8.82L14.06,7.76L13,8.82L14.06,9.88L13,10.94L14.06,12L15.12,10.94L16.18,12L17.24,10.94L16.18,9.88L17.24,8.82L16.18,7.76M7.82,12L8.88,10.94L9.94,12L11,10.94L9.94,9.88L11,8.82L9.94,7.76L8.88,8.82L7.82,7.76L6.76,8.82L7.82,9.88L6.76,10.94L7.82,12M12,14C9.67,14 7.69,15.46 6.89,17.5H17.11C16.31,15.46 14.33,14 12,14Z"/>
        </svg>
      ),
      route: '/sketch'
    }
  ];

  return (
    <PageContainer variant="wide" className="homepage">
      {/* Hero Section */}
      <section className="hero-section">
        <div className="hero-content-wrapper">
          <div className="hero-text">
            <h1 className="hero-title">
              AI Forensic Facial Recognition System
            </h1>
            <p className="hero-description">
              Advanced biometric analysis powered by deep learning algorithms. 
              Compare facial sketches with photographs, search criminal databases, 
              and manage forensic records with cutting-edge AI technology.
            </p>
            <div className="hero-stats">
              <div className="stat-item">
                <div className="stat-value">99.2%</div>
                <div className="stat-label">Accuracy</div>
              </div>
              <div className="stat-item">
                <div className="stat-value">&lt;2s</div>
                <div className="stat-label">Processing Time</div>
              </div>
              <div className="stat-item">
                <div className="stat-value">24/7</div>
                <div className="stat-label">Availability</div>
              </div>
            </div>
          </div>
          
          <div className="hero-visual">
            <Face3DModel />
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="features-section">
        <h2 className="section-heading">Core Features</h2>
        <div className="features-grid">
          {features.map((feature) => (
            <div 
              key={feature.id}
              className="feature-card"
            >
              <div className="feature-icon">
                {feature.icon}
              </div>
              <h3 className="feature-title">{feature.title}</h3>
              <p className="feature-description">{feature.description}</p>
              <button 
                className="feature-button"
                onClick={() => navigate(feature.route)}
              >
                Launch Tool
                <svg viewBox="0 0 24 24" fill="currentColor" className="arrow-icon">
                  <path d="M8.59,16.58L13.17,12L8.59,7.41L10,6L16,12L10,18L8.59,16.58Z"/>
                </svg>
              </button>
            </div>
          ))}
        </div>
      </section>

      {/* CTA Section */}
      <section className="cta-section">
        <div className="cta-content">
          <h2 className="cta-title">Ready to Get Started?</h2>
          <p className="cta-description">
            Choose a tool to begin your forensic analysis
          </p>
          <div className="cta-buttons">
            <button 
              className="cta-btn primary"
              onClick={() => navigate('/compare')}
            >
              Compare Faces
            </button>
            <button 
              className="cta-btn secondary"
              onClick={() => navigate('/sketch')}
            >
              Create Sketch
            </button>
            <button 
              className="cta-btn secondary"
              onClick={() => navigate('/search')}
            >
              Search Criminals
            </button>
          </div>
        </div>
      </section>
    </PageContainer>
  );
};

export default HomePage;
