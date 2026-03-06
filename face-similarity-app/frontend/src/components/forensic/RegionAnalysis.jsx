import React from 'react';
import './RegionAnalysis.css';

const RegionAnalysis = ({ regionDetails, regionSimilarity }) => {
  const hasIndividualRegions = regionDetails && (
    regionDetails.eyes !== undefined || 
    regionDetails.nose !== undefined || 
    regionDetails.mouth !== undefined
  );

  const hasRegionData = hasIndividualRegions || (regionSimilarity !== undefined && regionSimilarity !== null);

  if (!hasRegionData) return null;

  const metrics = [];

  if (hasIndividualRegions) {
    if (regionDetails.eyes !== undefined && regionDetails.eyes !== null) {
      metrics.push({ 
        name: '👁️ Eyes Similarity', 
        value: regionDetails.eyes, 
        className: 'region-eyes',
        description: 'Periocular region and eye shape analysis'
      });
    }
    if (regionDetails.nose !== undefined && regionDetails.nose !== null) {
      metrics.push({ 
        name: '👃 Nose Similarity', 
        value: regionDetails.nose, 
        className: 'region-nose',
        description: 'Nasal structure and bridge comparison'
      });
    }
    if (regionDetails.mouth !== undefined && regionDetails.mouth !== null) {
      metrics.push({ 
        name: '👄 Mouth Similarity', 
        value: regionDetails.mouth, 
        className: 'region-mouth',
        description: 'Lip shape and oral region analysis'
      });
    }
  } else if (regionSimilarity !== undefined && regionSimilarity !== null) {
    metrics.push({ 
      name: 'Combined Region Similarity', 
      value: regionSimilarity, 
      className: 'region-combined',
      description: 'Aggregate facial region analysis'
    });
  }

  return (
    <div className="region-analysis-wrapper">
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
                  {Number(metric.value).toFixed(1)}%
                </span>
              </div>
              <div className="forensic-metric-bar-container">
                <div className="forensic-metric-bar">
                  <div 
                    className={`forensic-metric-fill ${metric.className}`}
                    style={{
                      width: `${Math.min(100, Math.max(0, metric.value))}%`,
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

export default RegionAnalysis;
