import React, { useState, useEffect } from 'react';
import PropTypes from 'prop-types';
import './AnalysisPipeline.css';

const AnalysisPipeline = ({ 
  pipelineData = null,
  isProcessing = false,
  currentStep = 0
}) => {
  const [animatedSteps, setAnimatedSteps] = useState([]);

  // Default pipeline steps
  const defaultSteps = [
    {
      id: 1,
      name: 'Face Detection',
      description: 'Detecting and localizing faces in images',
      icon: '🔍',
      status: 'pending',
      processingTime: null,
      details: null
    },
    {
      id: 2,
      name: 'Embedding Extraction',
      description: 'Extracting deep learning feature vectors',
      icon: '🧬',
      status: 'pending',
      processingTime: null,
      details: null
    },
    {
      id: 3,
      name: 'FAISS Candidate Retrieval',
      description: 'Searching vector database for similar faces',
      icon: '🔎',
      status: 'pending',
      processingTime: null,
      details: null
    },
    {
      id: 4,
      name: 'Re-ranking',
      description: 'Refining candidate matches with advanced metrics',
      icon: '📊',
      status: 'pending',
      processingTime: null,
      details: null
    },
    {
      id: 5,
      name: 'Hybrid Scoring',
      description: 'Computing final similarity scores',
      icon: '🎯',
      status: 'pending',
      processingTime: null,
      details: null
    }
  ];

  // Merge pipeline data with defaults
  const steps = pipelineData || defaultSteps;

  // Animate steps as they complete
  useEffect(() => {
    if (isProcessing) {
      const timer = setTimeout(() => {
        setAnimatedSteps(prev => {
          if (prev.length < currentStep) {
            return [...prev, currentStep];
          }
          return prev;
        });
      }, 300);
      return () => clearTimeout(timer);
    }
  }, [isProcessing, currentStep]);

  // Get status icon
  const getStatusIcon = (status) => {
    switch (status) {
      case 'completed':
        return '✓';
      case 'processing':
        return '⟳';
      case 'error':
        return '✗';
      case 'pending':
      default:
        return '○';
    }
  };

  // Get status class
  const getStatusClass = (status) => {
    switch (status) {
      case 'completed':
        return 'completed';
      case 'processing':
        return 'processing';
      case 'error':
        return 'error';
      case 'pending':
      default:
        return 'pending';
    }
  };

  // Calculate total processing time
  const totalTime = steps.reduce((sum, step) => {
    return sum + (step.processingTime || 0);
  }, 0);

  // Count completed steps
  const completedSteps = steps.filter(s => s.status === 'completed').length;
  const progressPercentage = (completedSteps / steps.length) * 100;

  return (
    <div className="analysis-pipeline">
      <div className="pipeline-header">
        <div className="pipeline-title-section">
          <h4 className="pipeline-title">
            <span className="pipeline-icon">⚙️</span>
            Analysis Pipeline
          </h4>
          <span className="pipeline-badge">
            {isProcessing ? 'Processing...' : 'Ready'}
          </span>
        </div>
        <div className="pipeline-stats">
          <div className="stat-item">
            <span className="stat-label">Progress</span>
            <span className="stat-value">{completedSteps}/{steps.length}</span>
          </div>
          <div className="stat-item">
            <span className="stat-label">Total Time</span>
            <span className="stat-value">{totalTime.toFixed(2)}s</span>
          </div>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="pipeline-progress-container">
        <div className="pipeline-progress-bar">
          <div 
            className="pipeline-progress-fill"
            style={{ width: `${progressPercentage}%` }}
          >
            <div className="progress-shine"></div>
          </div>
        </div>
        <span className="progress-percentage">{Math.round(progressPercentage)}%</span>
      </div>

      {/* Pipeline Steps */}
      <div className="pipeline-steps">
        {steps.map((step, index) => {
          const isActive = isProcessing && currentStep === step.id;
          const isAnimated = animatedSteps.includes(step.id);
          
          return (
            <div key={step.id} className="pipeline-step-wrapper">
              {/* Step Card */}
              <div 
                className={`pipeline-step ${getStatusClass(step.status)} ${isActive ? 'active' : ''} ${isAnimated ? 'animated' : ''}`}
              >
                {/* Step Number Badge */}
                <div className="step-number-badge">
                  <span className="step-number">{step.id}</span>
                </div>

                {/* Step Icon */}
                <div className="step-icon-container">
                  <div className="step-icon">{step.icon}</div>
                  <div className="step-status-icon">
                    {getStatusIcon(step.status)}
                  </div>
                </div>

                {/* Step Content */}
                <div className="step-content">
                  <h5 className="step-name">{step.name}</h5>
                  <p className="step-description">{step.description}</p>
                  
                  {/* Step Details */}
                  {step.details && (
                    <div className="step-details">
                      {Object.entries(step.details).map(([key, value]) => (
                        <div key={key} className="detail-item">
                          <span className="detail-key">{key}:</span>
                          <span className="detail-value">{value}</span>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Processing Time */}
                  {step.processingTime !== null && step.processingTime !== undefined && (
                    <div className="step-time">
                      <svg className="time-icon" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M12,20A8,8 0 0,0 20,12A8,8 0 0,0 12,4A8,8 0 0,0 4,12A8,8 0 0,0 12,20M12,2A10,10 0 0,1 22,12A10,10 0 0,1 12,22C6.47,22 2,17.5 2,12A10,10 0 0,1 12,2M12.5,7V12.25L17,14.92L16.25,16.15L11,13V7H12.5Z"/>
                      </svg>
                      <span>{step.processingTime.toFixed(3)}s</span>
                    </div>
                  )}
                </div>

                {/* Processing Spinner */}
                {step.status === 'processing' && (
                  <div className="step-spinner">
                    <div className="spinner-ring"></div>
                  </div>
                )}
              </div>

              {/* Connector Line */}
              {index < steps.length - 1 && (
                <div className={`pipeline-connector ${step.status === 'completed' ? 'completed' : ''}`}>
                  <div className="connector-line">
                    <div className="connector-pulse"></div>
                  </div>
                  <div className="connector-arrow">▼</div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Summary Section */}
      {completedSteps === steps.length && !isProcessing && (
        <div className="pipeline-summary">
          <div className="summary-icon">✓</div>
          <div className="summary-content">
            <h5 className="summary-title">Analysis Complete</h5>
            <p className="summary-text">
              All pipeline steps completed successfully in {totalTime.toFixed(2)} seconds.
              Results are ready for review.
            </p>
          </div>
        </div>
      )}

      {/* Error Summary */}
      {steps.some(s => s.status === 'error') && (
        <div className="pipeline-error">
          <div className="error-icon">⚠️</div>
          <div className="error-content">
            <h5 className="error-title">Pipeline Error</h5>
            <p className="error-text">
              One or more steps encountered an error. Please review the pipeline and try again.
            </p>
          </div>
        </div>
      )}

      {/* Technical Note */}
      <div className="pipeline-note">
        <svg className="note-icon" viewBox="0 0 24 24" fill="currentColor">
          <path d="M13,9H11V7H13M13,17H11V11H13M12,2A10,10 0 0,0 2,12A10,10 0 0,0 12,22A10,10 0 0,0 22,12A10,10 0 0,0 12,2Z"/>
        </svg>
        <p>
          The analysis pipeline processes faces through multiple stages using state-of-the-art 
          deep learning models and vector search algorithms for accurate identification.
        </p>
      </div>
    </div>
  );
};

AnalysisPipeline.propTypes = {
  pipelineData: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.number.isRequired,
      name: PropTypes.string.isRequired,
      description: PropTypes.string,
      icon: PropTypes.string,
      status: PropTypes.oneOf(['pending', 'processing', 'completed', 'error']),
      processingTime: PropTypes.number,
      details: PropTypes.object
    })
  ),
  isProcessing: PropTypes.bool,
  currentStep: PropTypes.number
};

export default AnalysisPipeline;
