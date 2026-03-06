import React, { useState, useEffect } from 'react';
import PropTypes from 'prop-types';
import './SearchScanningAnimation.css';

const SearchScanningAnimation = ({ isScanning, progress = 0 }) => {
  const [currentStepIndex, setCurrentStepIndex] = useState(0);

  const scanningSteps = [
    { 
      text: "Detecting face...", 
      icon: "🔍",
      progress: 0,
      color: "#00d4ff"
    },
    { 
      text: "Extracting embeddings...", 
      icon: "🧬",
      progress: 25,
      color: "#00ff88"
    },
    { 
      text: "Searching database...", 
      icon: "🗄️",
      progress: 50,
      color: "#a855f7"
    },
    { 
      text: "Re-ranking candidates...", 
      icon: "📊",
      progress: 75,
      color: "#ffd700"
    },
    { 
      text: "Finalizing results...", 
      icon: "✓",
      progress: 95,
      color: "#00ff88"
    }
  ];

  useEffect(() => {
    // Update current step based on progress
    const stepIndex = scanningSteps.findIndex((step, index) => {
      const nextStep = scanningSteps[index + 1];
      return progress >= step.progress && (!nextStep || progress < nextStep.progress);
    });
    
    if (stepIndex !== -1) {
      setCurrentStepIndex(stepIndex);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [progress]);

  const currentStep = scanningSteps[currentStepIndex];

  return (
    <div className="search-scanning-overlay">
      <div className="search-backdrop"></div>
      
      {/* Scanning Lines Background */}
      <div className="search-lines-container">
        <div className="search-line search-line-1"></div>
        <div className="search-line search-line-2"></div>
        <div className="search-line search-line-3"></div>
      </div>

      <div className="search-modal">
        {/* Header */}
        <div className="search-header">
          <div className="search-icon">
            <svg viewBox="0 0 24 24" fill="currentColor">
              <path d="M9.5,3A6.5,6.5 0 0,1 16,9.5C16,11.11 15.41,12.59 14.44,13.73L14.71,14H15.5L20.5,19L19,20.5L14,15.5V14.71L13.73,14.44C12.59,15.41 11.11,16 9.5,16A6.5,6.5 0 0,1 3,9.5A6.5,6.5 0 0,1 9.5,3M9.5,5C7,5 5,7 5,9.5C5,12 7,14 9.5,14C12,14 14,12 14,9.5C14,7 12,5 9.5,5Z"/>
            </svg>
          </div>
          <h2 className="search-title">Criminal Database Search</h2>
          <p className="search-subtitle">AI-Powered Facial Recognition</p>
        </div>

        {/* Main Scanning Visualization */}
        <div className="search-visualization">
          {/* Circular Scanner */}
          <div className="search-scanner-container">
            {/* Outer rings */}
            <div className="search-ring search-ring-1"></div>
            <div className="search-ring search-ring-2"></div>
            <div className="search-ring search-ring-3"></div>
            
            {/* Center icon */}
            <div className="search-center" style={{ color: currentStep.color }}>
              <span className="search-icon-large">{currentStep.icon}</span>
            </div>
            
            {/* Scanning beam */}
            <div className="search-beam"></div>
          </div>
        </div>

        {/* Current Step Display */}
        <div className="search-current-step">
          <div className="search-step-icon" style={{ color: currentStep.color }}>
            {currentStep.icon}
          </div>
          <div className="search-step-text" style={{ color: currentStep.color }}>
            {currentStep.text}
          </div>
        </div>

        {/* Steps List */}
        <div className="search-steps-list">
          {scanningSteps.map((step, index) => (
            <div 
              key={index}
              className={`search-step-item ${index < currentStepIndex ? 'completed' : ''} ${index === currentStepIndex ? 'active' : ''}`}
            >
              <div className="search-step-indicator">
                {index < currentStepIndex ? (
                  <svg viewBox="0 0 24 24" fill="currentColor">
                    <path d="M9,20.42L2.79,14.21L5.62,11.38L9,14.77L18.88,4.88L21.71,7.71L9,20.42Z"/>
                  </svg>
                ) : (
                  <span className="search-step-number">{index + 1}</span>
                )}
              </div>
              <div className="search-step-label">{step.text}</div>
            </div>
          ))}
        </div>

        {/* Progress Bar */}
        <div className="search-progress-section">
          <div className="search-progress-header">
            <span className="search-progress-label">Search Progress</span>
            <span className="search-progress-percentage">{Math.round(progress)}%</span>
          </div>
          <div className="search-progress-bar-container">
            <div 
              className="search-progress-bar-fill"
              style={{ 
                width: `${progress}%`,
                background: `linear-gradient(90deg, ${currentStep.color}, ${currentStep.color}dd)`
              }}
            >
              <div className="search-progress-bar-shine"></div>
            </div>
          </div>
        </div>

        {/* Processing Indicator */}
        <div className="search-processing-indicator">
          <div className="search-processing-dots">
            <span className="search-dot"></span>
            <span className="search-dot"></span>
            <span className="search-dot"></span>
          </div>
          <span className="search-processing-text">Searching</span>
        </div>
      </div>
    </div>
  );
};

SearchScanningAnimation.propTypes = {
  isScanning: PropTypes.bool,
  progress: PropTypes.number
};

export default SearchScanningAnimation;
