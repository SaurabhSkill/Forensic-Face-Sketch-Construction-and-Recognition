import React, { useEffect, useState } from 'react';
import './SimilarityBars.css';

const SimilarityBars = ({ title, metrics }) => {
  const [animatedMetrics, setAnimatedMetrics] = useState(
    metrics.map(() => 0)
  );

  useEffect(() => {
    // Animate each bar with staggered delay
    metrics.forEach((metric, index) => {
      setTimeout(() => {
        let start = 0;
        const end = metric.value || 0;
        const duration = 1500;
        const increment = end / (duration / 16);

        const timer = setInterval(() => {
          start += increment;
          if (start >= end) {
            setAnimatedMetrics(prev => {
              const newValues = [...prev];
              newValues[index] = end;
              return newValues;
            });
            clearInterval(timer);
          } else {
            setAnimatedMetrics(prev => {
              const newValues = [...prev];
              newValues[index] = start;
              return newValues;
            });
          }
        }, 16);
      }, index * 200); // Stagger by 200ms
    });
  }, [metrics]);

  return (
    <div className="forensic-embedding-section">
      {title && <h4 className="forensic-metrics-title">{title}</h4>}
      <div className="forensic-metrics-grid">
        {metrics.map((metric, index) => (
          metric.value !== undefined && metric.value !== null && (
            <div key={index} className="forensic-metric-item">
              <div className="forensic-metric-header">
                <span className="forensic-metric-name">
                  <span className="forensic-metric-icon">▊</span>
                  {metric.name}
                </span>
                <span className="forensic-metric-percentage">
                  {Number(animatedMetrics[index] || 0).toFixed(1)}%
                </span>
              </div>
              <div className="forensic-metric-bar-container">
                <div className="forensic-metric-bar">
                  <div 
                    className={`forensic-metric-fill ${metric.className}`}
                    style={{
                      width: `${Math.min(100, Math.max(0, animatedMetrics[index] || 0))}%`,
                      transition: 'width 0.3s ease-out'
                    }}
                  >
                    <div className="forensic-metric-fill-shine"></div>
                  </div>
                </div>
                <div className="forensic-metric-bar-background"></div>
              </div>
              {metric.description && (
                <div className="forensic-metric-description">{metric.description}</div>
              )}
            </div>
          )
        ))}
      </div>
    </div>
  );
};

export default SimilarityBars;
