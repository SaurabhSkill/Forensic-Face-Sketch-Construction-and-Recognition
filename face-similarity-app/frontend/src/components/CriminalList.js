import React, { useState } from 'react';
import CriminalDetailModal from './CriminalDetailModal';
import './CriminalList.css';

const CriminalList = ({ criminals, onDelete, onRefresh }) => {
  const [selectedCriminal, setSelectedCriminal] = useState(null);
  const [showDetailModal, setShowDetailModal] = useState(false);

  const handleViewDetails = (criminal) => {
    setSelectedCriminal(criminal);
    setShowDetailModal(true);
  };

  const handleCloseModal = () => {
    setShowDetailModal(false);
    setSelectedCriminal(null);
  };

  const handleDelete = async (criminalId) => {
    if (window.confirm('Are you sure you want to delete this criminal profile?')) {
      await onDelete(criminalId);
      if (onRefresh) {
        onRefresh();
      }
    }
  };

  return (
    <div className="criminals-list-container">
      <div className="list-header">
        <h3>Criminal Database ({criminals.length} profiles)</h3>
      </div>

      <div className="criminals-grid">
        {criminals.map((criminal) => (
          <div key={criminal.id} className="criminal-card-modern">
            {/* Photo Section */}
            <div className="criminal-photo-section">
              <img 
                src={`http://localhost:5001/api/criminals/${criminal.id}/photo`}
                alt={criminal.full_name || criminal.name}
                onError={(e) => {
                  e.target.style.display = 'none';
                  e.target.nextSibling.style.display = 'flex';
                }}
              />
              <div className="photo-placeholder" style={{display: 'none'}}>
                <svg viewBox="0 0 24 24" fill="currentColor">
                  <path d="M12,4A4,4 0 0,1 16,8A4,4 0 0,1 12,12A4,4 0 0,1 8,8A4,4 0 0,1 12,4M12,14C16.42,14 20,15.79 20,18V20H4V18C4,15.79 7.58,14 12,14Z"/>
                </svg>
              </div>
              
              {/* Status Badge */}
              <div className={`status-badge ${criminal.status ? criminal.status.toLowerCase().replace(/\s+/g, '-') : 'unknown'}`}>
                {criminal.status || 'Unknown'}
              </div>
            </div>

            {/* Info Section */}
            <div className="criminal-info-section">
              <div className="criminal-header">
                <h4 className="criminal-name">{criminal.full_name || criminal.name}</h4>
                <span className="criminal-id">{criminal.criminal_id || `ID: ${criminal.id}`}</span>
              </div>

              {/* Quick Info */}
              <div className="quick-info">
                {criminal.aliases && criminal.aliases.length > 0 && (
                  <div className="info-item">
                    <span className="info-label">Aliases:</span>
                    <span className="info-value">{criminal.aliases.slice(0, 2).join(', ')}</span>
                  </div>
                )}
                
                {criminal.summary && criminal.summary.charges && (
                  <div className="info-item">
                    <span className="info-label">Charges:</span>
                    <span className="info-value">{criminal.summary.charges}</span>
                  </div>
                )}

                {criminal.summary && criminal.summary.risk && (
                  <div className="info-item">
                    <span className="info-label">Risk:</span>
                    <span className={`risk-badge risk-${criminal.summary.risk.toLowerCase()}`}>
                      {criminal.summary.risk}
                    </span>
                  </div>
                )}

                {criminal.locations && criminal.locations.city && (
                  <div className="info-item">
                    <span className="info-label">Location:</span>
                    <span className="info-value">
                      {criminal.locations.city}{criminal.locations.state ? `, ${criminal.locations.state}` : ''}
                    </span>
                  </div>
                )}
              </div>

              {/* Action Buttons */}
              <div className="card-actions">
                <button 
                  className="view-details-button"
                  onClick={() => handleViewDetails(criminal)}
                >
                  <svg viewBox="0 0 24 24" fill="currentColor">
                    <path d="M12,9A3,3 0 0,0 9,12A3,3 0 0,0 12,15A3,3 0 0,0 15,12A3,3 0 0,0 12,9M12,17A5,5 0 0,1 7,12A5,5 0 0,1 12,7A5,5 0 0,1 17,12A5,5 0 0,1 12,17M12,4.5C7,4.5 2.73,7.61 1,12C2.73,16.39 7,19.5 12,19.5C17,19.5 21.27,16.39 23,12C21.27,7.61 17,4.5 12,4.5Z"/>
                  </svg>
                  View Details
                </button>
                <button 
                  className="delete-button-icon"
                  onClick={() => handleDelete(criminal.id)}
                  title="Delete Profile"
                >
                  <svg viewBox="0 0 24 24" fill="currentColor">
                    <path d="M19,4H15.5L14.5,3H9.5L8.5,4H5V6H19M6,19A2,2 0 0,0 8,21H16A2,2 0 0,0 18,19V7H6V19Z"/>
                  </svg>
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>

      {criminals.length === 0 && (
        <div className="empty-state">
          <svg viewBox="0 0 24 24" fill="currentColor">
            <path d="M12,2A10,10 0 0,0 2,12A10,10 0 0,0 12,22A10,10 0 0,0 22,12A10,10 0 0,0 12,2M12,4A8,8 0 0,1 20,12A8,8 0 0,1 12,20A8,8 0 0,1 4,12A8,8 0 0,1 12,4M11,7V13H13V7H11M11,15V17H13V15H11Z"/>
          </svg>
          <h3>No Criminal Profiles Found</h3>
          <p>Add a new criminal profile to get started.</p>
        </div>
      )}

      {/* Detail Modal */}
      {showDetailModal && selectedCriminal && (
        <CriminalDetailModal
          criminal={selectedCriminal}
          onClose={handleCloseModal}
        />
      )}
    </div>
  );
};

export default CriminalList;
