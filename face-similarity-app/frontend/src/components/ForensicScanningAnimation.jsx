import React, { useState, useEffect } from 'react';
import './ForensicScanningAnimation.css';

const ForensicScanningAnimation = ({ isScanning, progress = 0 }) => {
  const [currentStepIndex, setCurrentStepIndex] = useState(0);

  const scanningSteps = [
    { 
      text: "Detecting Face...", 
      icon: "🔍",
      progress: 0,
      color: "#00d4ff"
    },
    { 
      text: "Extracting InsightFace Embeddings...", 
      icon: "🧬",
      progress: 20,
      color: "#00d4ff"
    },
    { 
      text: "Extracting Facenet Embeddings...", 
      icon: "🧬",
      progress: 40,
      color: "#00ff88"
    },
    { 
      text: "Running Multi-Region Analysis...", 
      icon: "📐",
      progress: 60,
      color: "#a855f7"
    },
    { 
      text: "Computing Hybrid Score...", 
      icon: "⚡",
      progress: 80,
      color: "#ffd700"
    },
    { 
      text: "Finalizing Results...", 
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
    <div className="forensic-scanning-overlay">
      <div className="scanning-backdrop"></div>
      
      {/* Scanning Lines Background */}
      <div className="scanning-lines-container">
        <div className="scanning-line scanning-line-1"></div>
        <div className="scanning-line scanning-line-2"></div>
        <div className="scanning-line scanning-line-3"></div>
      </div>

      <div className="scanning-modal">
        {/* Header */}
        <div className="scanning-header">
          <div className="header-icon">
            <svg viewBox="0 0 24 24" fill="currentColor">
              <path d="M9,11.75A1.25,1.25 0 0,0 7.75,13A1.25,1.25 0 0,0 9,14.25A1.25,1.25 0 0,0 10.25,13A1.25,1.25 0 0,0 9,11.75M15,11.75A1.25,1.25 0 0,0 13.75,13A1.25,1.25 0 0,0 15,14.25A1.25,1.25 0 0,0 16.25,13A1.25,1.25 0 0,0 15,11.75M12,2A10,10 0 0,0 2,12A10,10 0 0,0 12,22A10,10 0 0,0 22,12A10,10 0 0,0 12,2M12,20C7.59,20 4,16.41 4,12C4,11.71 4,11.42 4.05,11.14C6.41,10.09 8.28,8.16 9.26,5.77C11.07,8.33 14.05,10 17.42,10C18.2,10 18.95,9.91 19.67,9.74C19.88,10.45 20,11.21 20,12C20,16.41 16.41,20 12,20Z"/>
            </svg>
          </div>
          <h2 className="scanning-title">Forensic Analysis</h2>
          <p className="scanning-subtitle">Deep Learning Facial Recognition</p>
        </div>

        {/* Main Scanning Visualization */}
        <div className="scanning-visualization">
          {/* Circular Scanner */}
          <div className="scanner-container">
            {/* Outer rings */}
            <div className="scanner-ring scanner-ring-1"></div>
            <div className="scanner-ring scanner-ring-2"></div>
            <div className="scanner-ring scanner-ring-3"></div>
            
            {/* Center icon */}
            <div className="scanner-center" style={{ color: currentStep.color }}>
              <span className="scanner-icon">{currentStep.icon}</span>
            </div>
            
            {/* Scanning beam */}
            <div className="scanning-beam"></div>
          </div>
        </div>

        {/* Current Step Display */}
        <div className="current-step">
          <div className="step-icon" style={{ color: currentStep.color }}>
            {currentStep.icon}
          </div>
          <div className="step-text" style={{ color: currentStep.color }}>
            {currentStep.text}
          </div>
        </div>

        {/* Steps List */}
        <div className="steps-list">
          {scanningSteps.map((step, index) => (
            <div 
              key={index}
              className={`step-item ${index < currentStepIndex ? 'completed' : ''} ${index === currentStepIndex ? 'active' : ''}`}
            >
              <div className="step-indicator">
                {index < currentStepIndex ? (
                  <svg viewBox="0 0 24 24" fill="currentColor">
                    <path d="M9,20.42L2.79,14.21L5.62,11.38L9,14.77L18.88,4.88L21.71,7.71L9,20.42Z"/>
                  </svg>
                ) : (
                  <span className="step-number">{index + 1}</span>
                )}
              </div>
              <div className="step-label">{step.text}</div>
            </div>
          ))}
        </div>

        {/* Progress Bar */}
        <div className="progress-section">
          <div className="progress-header">
            <span className="progress-label">Overall Progress</span>
            <span className="progress-percentage">{Math.round(progress)}%</span>
          </div>
          <div className="progress-bar-container">
            <div 
              className="progress-bar-fill"
              style={{ 
                width: `${progress}%`,
                background: `linear-gradient(90deg, ${currentStep.color}, ${currentStep.color}dd)`
              }}
            >
              <div className="progress-bar-shine"></div>
            </div>
          </div>
        </div>

        {/* Processing Indicator */}
        <div className="processing-indicator">
          <div className="processing-dots">
            <span className="dot"></span>
            <span className="dot"></span>
            <span className="dot"></span>
          </div>
          <span className="processing-text">Processing</span>
        </div>
      </div>
    </div>
  );
};

export default ForensicScanningAnimation;
