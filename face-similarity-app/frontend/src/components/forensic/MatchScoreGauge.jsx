import React, { useEffect, useState } from 'react';
import PropTypes from 'prop-types';
import './MatchScoreGauge.css';

const MatchScoreGauge = ({ score, matchQuality, confidenceLevel }) => {
  const [animatedScore, setAnimatedScore] = useState(0);
  
  const getMatchCategory = () => {
    if (matchQuality) {
      return matchQuality;
    }
    if (score >= 80) return 'VERY STRONG MATCH';
    if (score >= 65) return 'STRONG MATCH';
    if (score >= 45) return 'POSSIBLE MATCH';
    return 'LOW SIMILARITY';
  };

  const getCategoryClass = () => {
    if (matchQuality) {
      if (matchQuality.toLowerCase().includes('excellent')) return 'very-strong';
      if (matchQuality.toLowerCase().includes('strong') || matchQuality.toLowerCase().includes('good')) return 'strong';
      if (matchQuality.toLowerCase().includes('average') || matchQuality.toLowerCase().includes('moderate')) return 'possible';
      return 'low';
    }
    if (score >= 80) return 'very-strong';
    if (score >= 65) return 'strong';
    if (score >= 45) return 'possible';
    return 'low';
  };

  const getConfidenceLevel = () => {
    if (confidenceLevel) {
      return confidenceLevel.replace(/_/g, ' ').split(' ').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
    }
    if (score >= 70) return 'High';
    if (score >= 50) return 'Medium';
    return 'Low';
  };

  const getConfidenceClass = () => {
    if (confidenceLevel) {
      return confidenceLevel.toLowerCase().replace(/ /g, '-');
    }
    if (score >= 70) return 'high';
    if (score >= 50) return 'medium';
    return 'low';
  };

  // Smooth animation with easing
  useEffect(() => {
    let startTime = null;
    const duration = 2000; // 2 seconds
    const startValue = 0;
    const endValue = score;

    const easeOutCubic = (t) => {
      return 1 - Math.pow(1 - t, 3);
    };

    const animate = (currentTime) => {
      if (!startTime) startTime = currentTime;
      const elapsed = currentTime - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const easedProgress = easeOutCubic(progress);
      const currentValue = startValue + (endValue - startValue) * easedProgress;

      setAnimatedScore(currentValue);

      if (progress < 1) {
        requestAnimationFrame(animate);
      }
    };

    requestAnimationFrame(animate);
  }, [score]);

  // Calculate circle progress
  const radius = 70;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (animatedScore / 100) * circumference;

  return (
    <div className="forensic-match-score-section">
      <div className="forensic-match-score-display">
        <div className="forensic-score-circle-container">
          <svg className="forensic-circular-gauge" viewBox="0 0 160 160">
            {/* Gradient definitions */}
            <defs>
              <linearGradient id="gaugeGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" className="gradient-start" />
                <stop offset="100%" className="gradient-end" />
              </linearGradient>
              <filter id="glow">
                <feGaussianBlur stdDeviation="3" result="coloredBlur"/>
                <feMerge>
                  <feMergeNode in="coloredBlur"/>
                  <feMergeNode in="SourceGraphic"/>
                </feMerge>
              </filter>
            </defs>
            
            {/* Background circle */}
            <circle
              className="forensic-gauge-background"
              cx="80"
              cy="80"
              r={radius}
              fill="none"
              strokeWidth="12"
            />
            
            {/* Progress circle */}
            <circle
              className="forensic-gauge-progress"
              cx="80"
              cy="80"
              r={radius}
              fill="none"
              stroke="url(#gaugeGradient)"
              strokeWidth="12"
              strokeLinecap="round"
              strokeDasharray={circumference}
              strokeDashoffset={strokeDashoffset}
              transform="rotate(-90 80 80)"
              filter="url(#glow)"
            />
            
            {/* Center dot indicator */}
            <circle
              cx="80"
              cy="80"
              r="3"
              className="forensic-gauge-center-dot"
            />
          </svg>
          
          <div className="forensic-score-circle">
            <div className="forensic-score-value">
              {Math.round(animatedScore)}
              <span className="forensic-score-percent">%</span>
            </div>
            <div className="forensic-score-label">MATCH SCORE</div>
          </div>
        </div>
        
        <div className="forensic-match-category">
          <div className="forensic-category-label">Match Category</div>
          <div className={`forensic-category-badge ${getCategoryClass()}`}>
            {getMatchCategory()}
          </div>
          <div className="forensic-confidence-indicator">
            <span className="forensic-confidence-label">Confidence Level</span>
            <span className={`forensic-confidence-badge ${getConfidenceClass()}`}>
              {getConfidenceLevel()}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};

MatchScoreGauge.propTypes = {
  score: PropTypes.number.isRequired,
  matchQuality: PropTypes.string,
  confidenceLevel: PropTypes.string
};

export default MatchScoreGauge;
