import React, { useState } from 'react';
import './CriminalDetailModal.css';

const CriminalDetailModal = ({ criminal, onClose }) => {
  const [activeSection, setActiveSection] = useState('overview');

  // Helper function to format date
  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    try {
      return new Date(dateString).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
      });
    } catch {
      return dateString;
    }
  };

  // Helper function to calculate age from DOB
  const calculateAge = (dob) => {
    if (!dob) return null;
    try {
      const birthDate = new Date(dob);
      const today = new Date();
      let age = today.getFullYear() - birthDate.getFullYear();
      const monthDiff = today.getMonth() - birthDate.getMonth();
      if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < birthDate.getDate())) {
        age--;
      }
      return age;
    } catch {
      return null;
    }
  };

  const age = calculateAge(criminal.dob);

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-container" onClick={(e) => e.stopPropagation()}>
        {/* Modal Header */}
        <div className="modal-header">
          <div className="header-content">
            <h2>Criminal Profile Details</h2>
            <div className="header-meta">
              <span className="profile-id">{criminal.criminal_id || `ID: ${criminal.id}`}</span>
              <span className={`status-badge-large ${criminal.status ? criminal.status.toLowerCase().replace(/\s+/g, '-') : ''}`}>
                {criminal.status || 'Unknown'}
              </span>
            </div>
          </div>
          <button className="close-modal-button" onClick={onClose}>×</button>
        </div>

        {/* Modal Body */}
        <div className="modal-body">
          {/* Left Column - Photo and Basic Info */}
          <div className="modal-left-column">
            <div className="profile-photo-large">
              <img 
                src={`http://localhost:5001/api/criminals/${criminal.id}/photo`}
                alt={criminal.full_name || criminal.name}
                onError={(e) => {
                  e.target.style.display = 'none';
                  e.target.nextSibling.style.display = 'flex';
                }}
              />
              <div className="photo-placeholder-large" style={{display: 'none'}}>
                <svg viewBox="0 0 24 24" fill="currentColor">
                  <path d="M12,4A4,4 0 0,1 16,8A4,4 0 0,1 12,12A4,4 0 0,1 8,8A4,4 0 0,1 12,4M12,14C16.42,14 20,15.79 20,18V20H4V18C4,15.79 7.58,14 12,14Z"/>
                </svg>
              </div>
            </div>

            <div className="basic-info-card">
              <h3>Basic Information</h3>
              <div className="info-grid">
                <div className="info-row">
                  <span className="label">Full Name:</span>
                  <span className="value">{criminal.full_name || criminal.name || 'N/A'}</span>
                </div>
                
                {criminal.aliases && criminal.aliases.length > 0 && (
                  <div className="info-row">
                    <span className="label">Aliases:</span>
                    <span className="value">
                      {criminal.aliases.map((alias, index) => (
                        <span key={index} className="alias-tag">{alias}</span>
                      ))}
                    </span>
                  </div>
                )}

                <div className="info-row">
                  <span className="label">Date of Birth:</span>
                  <span className="value">
                    {formatDate(criminal.dob)}
                    {age && <span className="age-text"> ({age} years old)</span>}
                  </span>
                </div>

                <div className="info-row">
                  <span className="label">Sex:</span>
                  <span className="value">{criminal.sex || 'N/A'}</span>
                </div>

                <div className="info-row">
                  <span className="label">Nationality:</span>
                  <span className="value">{criminal.nationality || 'N/A'}</span>
                </div>

                <div className="info-row">
                  <span className="label">Ethnicity:</span>
                  <span className="value">{criminal.ethnicity || 'N/A'}</span>
                </div>

                <div className="info-row">
                  <span className="label">Profile Created:</span>
                  <span className="value">{formatDate(criminal.created_at)}</span>
                </div>

                {criminal.updated_at && (
                  <div className="info-row">
                    <span className="label">Last Updated:</span>
                    <span className="value">{formatDate(criminal.updated_at)}</span>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Right Column - Detailed Sections */}
          <div className="modal-right-column">
            {/* Section Navigation */}
            <div className="section-tabs">
              <button
                className={`section-tab ${activeSection === 'overview' ? 'active' : ''}`}
                onClick={() => setActiveSection('overview')}
              >
                Overview
              </button>
              <button
                className={`section-tab ${activeSection === 'appearance' ? 'active' : ''}`}
                onClick={() => setActiveSection('appearance')}
              >
                Appearance
              </button>
              <button
                className={`section-tab ${activeSection === 'location' ? 'active' : ''}`}
                onClick={() => setActiveSection('location')}
              >
                Location
              </button>
              <button
                className={`section-tab ${activeSection === 'forensics' ? 'active' : ''}`}
                onClick={() => setActiveSection('forensics')}
              >
                Forensics
              </button>
            </div>

            {/* Section Content */}
            <div className="section-content">
              {/* Overview Section */}
              {activeSection === 'overview' && (
                <div className="detail-section">
                  <h3>Criminal Summary</h3>
                  
                  {criminal.summary && (
                    <>
                      {criminal.summary.charges && (
                        <div className="detail-card">
                          <h4>Charges</h4>
                          <p>{criminal.summary.charges}</p>
                        </div>
                      )}

                      {criminal.summary.modus && (
                        <div className="detail-card">
                          <h4>Modus Operandi</h4>
                          <p>{criminal.summary.modus}</p>
                        </div>
                      )}

                      <div className="detail-card">
                        <h4>Risk Assessment</h4>
                        <div className="risk-display">
                          <span className={`risk-badge-large risk-${criminal.summary.risk ? criminal.summary.risk.toLowerCase() : 'unknown'}`}>
                            {criminal.summary.risk || 'Unknown'}
                          </span>
                          {criminal.summary.priorConvictions !== undefined && (
                            <span className="conviction-count">
                              Prior Convictions: {criminal.summary.priorConvictions}
                            </span>
                          )}
                        </div>
                      </div>
                    </>
                  )}

                  {criminal.evidence && criminal.evidence.length > 0 && (
                    <div className="detail-card">
                      <h4>Evidence Items</h4>
                      <ul className="evidence-list">
                        {criminal.evidence.map((item, index) => (
                          <li key={index}>{item}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {criminal.witness && (
                    <div className="detail-card">
                      <h4>Witness Information</h4>
                      {criminal.witness.statements && (
                        <p className="witness-statement">{criminal.witness.statements}</p>
                      )}
                      <div className="witness-meta">
                        {criminal.witness.credibility && (
                          <span className="credibility">
                            Credibility: <strong>{criminal.witness.credibility}</strong>
                          </span>
                        )}
                        {criminal.witness.contactInfo && (
                          <span className="contact">
                            Contact: {criminal.witness.contactInfo}
                          </span>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Appearance Section */}
              {activeSection === 'appearance' && (
                <div className="detail-section">
                  <h3>Physical Appearance</h3>
                  
                  {criminal.appearance && (
                    <>
                      <div className="detail-card">
                        <h4>Physical Characteristics</h4>
                        <div className="info-grid">
                          {criminal.appearance.height && (
                            <div className="info-row">
                              <span className="label">Height:</span>
                              <span className="value">{criminal.appearance.height}</span>
                            </div>
                          )}
                          {criminal.appearance.weight && (
                            <div className="info-row">
                              <span className="label">Weight:</span>
                              <span className="value">{criminal.appearance.weight}</span>
                            </div>
                          )}
                          {criminal.appearance.build && (
                            <div className="info-row">
                              <span className="label">Build:</span>
                              <span className="value">{criminal.appearance.build}</span>
                            </div>
                          )}
                          {criminal.appearance.hair && (
                            <div className="info-row">
                              <span className="label">Hair:</span>
                              <span className="value">{criminal.appearance.hair}</span>
                            </div>
                          )}
                          {criminal.appearance.eyes && (
                            <div className="info-row">
                              <span className="label">Eyes:</span>
                              <span className="value">{criminal.appearance.eyes}</span>
                            </div>
                          )}
                          {criminal.appearance.eyeColor && (
                            <div className="info-row">
                              <span className="label">Eye Color:</span>
                              <span className="value">{criminal.appearance.eyeColor}</span>
                            </div>
                          )}
                          {criminal.appearance.facialHair && (
                            <div className="info-row">
                              <span className="label">Facial Hair:</span>
                              <span className="value">{criminal.appearance.facialHair}</span>
                            </div>
                          )}
                        </div>
                      </div>

                      {criminal.appearance.marks && criminal.appearance.marks.length > 0 && (
                        <div className="detail-card">
                          <h4>Distinguishing Marks</h4>
                          <ul className="marks-list">
                            {criminal.appearance.marks.map((mark, index) => (
                              <li key={index}>{mark}</li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {criminal.appearance.tattoos && (
                        <div className="detail-card">
                          <h4>Tattoos</h4>
                          <p>{criminal.appearance.tattoos}</p>
                        </div>
                      )}

                      {criminal.appearance.scars && (
                        <div className="detail-card">
                          <h4>Scars</h4>
                          <p>{criminal.appearance.scars}</p>
                        </div>
                      )}

                      {criminal.appearance.clothing && (
                        <div className="detail-card">
                          <h4>Typical Clothing</h4>
                          <p>{criminal.appearance.clothing}</p>
                        </div>
                      )}
                    </>
                  )}
                </div>
              )}

              {/* Location Section */}
              {activeSection === 'location' && (
                <div className="detail-section">
                  <h3>Location & History</h3>
                  
                  {criminal.locations && (
                    <>
                      <div className="detail-card">
                        <h4>Current Location Information</h4>
                        <div className="info-grid">
                          {criminal.locations.city && (
                            <div className="info-row">
                              <span className="label">City:</span>
                              <span className="value">{criminal.locations.city}</span>
                            </div>
                          )}
                          {criminal.locations.area && (
                            <div className="info-row">
                              <span className="label">Area:</span>
                              <span className="value">{criminal.locations.area}</span>
                            </div>
                          )}
                          {criminal.locations.state && (
                            <div className="info-row">
                              <span className="label">State:</span>
                              <span className="value">{criminal.locations.state}</span>
                            </div>
                          )}
                          {criminal.locations.country && (
                            <div className="info-row">
                              <span className="label">Country:</span>
                              <span className="value">{criminal.locations.country}</span>
                            </div>
                          )}
                          {criminal.locations.lastSeen && (
                            <div className="info-row">
                              <span className="label">Last Seen:</span>
                              <span className="value">{formatDate(criminal.locations.lastSeen)}</span>
                            </div>
                          )}
                        </div>
                      </div>

                      {criminal.locations.knownAddresses && criminal.locations.knownAddresses.length > 0 && (
                        <div className="detail-card">
                          <h4>Known Addresses</h4>
                          <ul className="address-list">
                            {criminal.locations.knownAddresses.map((address, index) => (
                              <li key={index}>{address}</li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {criminal.locations.frequent && criminal.locations.frequent.length > 0 && (
                        <div className="detail-card">
                          <h4>Frequent Locations</h4>
                          <ul className="frequent-list">
                            {criminal.locations.frequent.map((location, index) => (
                              <li key={index}>{location}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </>
                  )}
                </div>
              )}

              {/* Forensics Section */}
              {activeSection === 'forensics' && (
                <div className="detail-section">
                  <h3>Forensic Data</h3>
                  
                  {criminal.forensics && (
                    <div className="detail-card">
                      <h4>Forensic Identifiers</h4>
                      <div className="info-grid">
                        {criminal.forensics.fingerprintId && (
                          <div className="info-row">
                            <span className="label">Fingerprint ID:</span>
                            <span className="value forensic-id">{criminal.forensics.fingerprintId}</span>
                          </div>
                        )}
                        {criminal.forensics.dnaProfile && (
                          <div className="info-row">
                            <span className="label">DNA Profile:</span>
                            <span className="value forensic-id">{criminal.forensics.dnaProfile}</span>
                          </div>
                        )}
                        {criminal.forensics.dnaSampleId && (
                          <div className="info-row">
                            <span className="label">DNA Sample ID:</span>
                            <span className="value forensic-id">{criminal.forensics.dnaSampleId}</span>
                          </div>
                        )}
                        {criminal.forensics.voiceprint && (
                          <div className="info-row">
                            <span className="label">Voiceprint ID:</span>
                            <span className="value forensic-id">{criminal.forensics.voiceprint}</span>
                          </div>
                        )}
                        {criminal.forensics.gait && (
                          <div className="info-row">
                            <span className="label">Gait Analysis:</span>
                            <span className="value">{criminal.forensics.gait}</span>
                          </div>
                        )}
                        {criminal.forensics.bootTread && (
                          <div className="info-row">
                            <span className="label">Boot Tread:</span>
                            <span className="value">{criminal.forensics.bootTread}</span>
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CriminalDetailModal;
