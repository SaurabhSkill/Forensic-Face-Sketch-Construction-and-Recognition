import React from 'react';
import './ProcessingInfo.css';

const ProcessingInfo = ({ processingTime, modelUsed, forensicNote }) => {
  return (
    <div className="forensic-processing-container">
      {/* Processing Information */}
      {(processingTime !== undefined || modelUsed) && (
        <div className="forensic-processing-section forensic-info-section">
          <h4 className="forensic-section-title">
            <span className="forensic-section-icon">⚙️</span>
            Processing Information
          </h4>
          <div className="forensic-info-grid">
            {processingTime !== undefined && processingTime !== null && (
              <div className="forensic-info-item">
                <span className="forensic-info-label">Processing Time</span>
                <span className="forensic-info-value">
                  <span className="forensic-info-number">{Number(processingTime).toFixed(2)}</span>
                  <span className="forensic-info-unit">seconds</span>
                </span>
              </div>
            )}
            {modelUsed && (
              <div className="forensic-info-item">
                <span className="forensic-info-label">Analysis Method</span>
                <span className="forensic-info-value">{modelUsed}</span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Technical Notes */}
      {forensicNote && (
        <div className="forensic-processing-section forensic-note-section">
          <h4 className="forensic-section-title">
            <span className="forensic-section-icon">📋</span>
            Technical Notes
          </h4>
          <div className="forensic-note-content">
            <svg className="forensic-note-icon" viewBox="0 0 24 24" fill="currentColor">
              <path d="M13,9H11V7H13M13,17H11V11H13M12,2A10,10 0 0,0 2,12A10,10 0 0,0 12,22A10,10 0 0,0 22,12A10,10 0 0,0 12,2Z"/>
            </svg>
            <p className="forensic-note-text">{forensicNote}</p>
          </div>
        </div>
      )}
    </div>
  );
};

export default ProcessingInfo;
