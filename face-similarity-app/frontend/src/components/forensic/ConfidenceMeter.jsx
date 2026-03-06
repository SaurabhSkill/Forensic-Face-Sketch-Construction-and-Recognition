import React, { useState, useEffect } from 'react';
import PropTypes from 'prop-types';
import './ConfidenceMeter.css';

const ConfidenceMeter = ({ 
  confidence = 0,
  showLabel = true,
  showPercentage = true,
  size = 'medium',
  animated = true
}) => {
  const [animatedConfidence, setAnimatedConfidence] = useState(0);

  // Animate confidence value on mount or change
  useEffect(() => {
    if (!animated) {
      setAnimatedConfidence(confidence);
      return;
    }

    let startTime = null;
    const duration = 1000; // 1 second animation
    const startValue = animatedConfidence;
    const endValue = confidence;

    const animate = (timestamp) => {
      if (!startTime) startTime = timestamp;
      const progress = Math.min((timestamp - startTime) / duration, 1);
      
      // Easing function for smooth animation
      const easeOutCubic = 1 - Math.pow(1 - progress, 3);
      const currentValue = startValue + (endValue - startValue) * easeOutCubic;
      
      setAnimatedConfidence(currentValue);

      if (progress < 1) {
        requestAnimationFrame(animate);
      }
    };

    requestAnimationFrame(animate);
  }, [confidence, animated]);

  // Determine confidence level and color
  const getConfidenceLevel = (value) => {
    if (value >= 80) return { level: 'high', label: 'High Confidence', color: 'green' };
    if (value >= 50) return { level: 'medium', label: 'Medium Confidence', color: 'yellow' };
    return { level: 'low', label: 'Low Confidence', color: 'red' };
  };

  const confidenceInfo = getConfidenceLevel(animatedConfidence);
  const percentage = Math.round(animatedConfidence);

  return (
    <div className={`confidence-meter confidence-meter--${size}`}>
      {showLabel && (
        <div className="confidence-meter__header">
          <span className="confidence-meter__label">Confidence Level</span>
          <span className={`confidence-meter__badge confidence-meter__badge--${confidenceInfo.level}`}>
            {confidenceInfo.label}
          </span>
        </div>
      )}

      <div className="confidence-meter__container">
        <div className="confidence-meter__track">
          <div 
            className={`confidence-meter__fill confidence-meter__fill--${confidenceInfo.color}`}
            style={{ width: `${animatedConfidence}%` }}
          >
            <div className="confidence-meter__shine"></div>
            <div className="confidence-meter__glow"></div>
          </div>

          {/* Threshold markers */}
          <div className="confidence-meter__markers">
            <div className="confidence-meter__marker" style={{ left: '50%' }}>
              <div className="confidence-meter__marker-line"></div>
              <span className="confidence-meter__marker-label">50%</span>
            </div>
            <div className="confidence-meter__marker" style={{ left: '80%' }}>
              <div className="confidence-meter__marker-line"></div>
              <span className="confidence-meter__marker-label">80%</span>
            </div>
          </div>
        </div>

        {showPercentage && (
          <div className="confidence-meter__value">
            <span className={`confidence-meter__percentage confidence-meter__percentage--${confidenceInfo.color}`}>
              {percentage}%
            </span>
          </div>
        )}
      </div>

      {/* Confidence scale legend */}
      <div className="confidence-meter__legend">
        <div className="confidence-meter__legend-item">
          <div className="confidence-meter__legend-color confidence-meter__legend-color--red"></div>
          <span className="confidence-meter__legend-text">Low (0-49%)</span>
        </div>
        <div className="confidence-meter__legend-item">
          <div className="confidence-meter__legend-color confidence-meter__legend-color--yellow"></div>
          <span className="confidence-meter__legend-text">Medium (50-79%)</span>
        </div>
        <div className="confidence-meter__legend-item">
          <div className="confidence-meter__legend-color confidence-meter__legend-color--green"></div>
          <span className="confidence-meter__legend-text">High (80-100%)</span>
        </div>
      </div>

      {/* Technical note */}
      <div className="confidence-meter__note">
        <svg className="confidence-meter__note-icon" viewBox="0 0 24 24" fill="currentColor">
          <path d="M13,9H11V7H13M13,17H11V11H13M12,2A10,10 0 0,0 2,12A10,10 0 0,0 12,22A10,10 0 0,0 22,12A10,10 0 0,0 12,2Z"/>
        </svg>
        <p className="confidence-meter__note-text">
          Confidence score represents the model's certainty in the match prediction based on 
          embedding similarity and facial feature analysis.
        </p>
      </div>
    </div>
  );
};

ConfidenceMeter.propTypes = {
  confidence: PropTypes.number.isRequired,
  showLabel: PropTypes.bool,
  showPercentage: PropTypes.bool,
  size: PropTypes.oneOf(['small', 'medium', 'large']),
  animated: PropTypes.bool
};

export default ConfidenceMeter;
