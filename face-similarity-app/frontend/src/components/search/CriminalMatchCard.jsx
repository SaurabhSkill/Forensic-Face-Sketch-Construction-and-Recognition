import React from 'react';
import { apiService } from '../../services/apiService';
import './CriminalMatchCard.css';

const CriminalMatchCard = ({ match, index, onViewDetails }) => {
  const rank = match.rank || index + 1;

  // Backend sends similarity_score already normalized (0-100 range via display normalization).
  // display_similarity is the same value — prefer it, fall back to similarity_score,
  // and as a last resort multiply raw decimal by 100.
  const score = match.display_similarity
    ?? match.similarity_score
    ?? (match.raw_similarity_score != null ? match.raw_similarity_score * 100 : 0);

  // confidence field is named confidence_level in the API response
  const confidence = match.confidence_level || match.confidence || null;

  // Debug: log the raw match object once per card to confirm field names
  console.log('[CriminalMatchCard] match fields:', {
    rank,
    display_similarity: match.display_similarity,
    similarity_score: match.similarity_score,
    raw_similarity_score: match.raw_similarity_score,
    confidence_level: match.confidence_level,
    score_used: score,
  });
  const getRankClass = () => {
    if (rank === 1) return 'rank-gold';
    if (rank === 2) return 'rank-silver';
    if (rank === 3) return 'rank-bronze';
    return 'rank-default';
  };

  const getRankLabel = () => {
    if (rank === 1) return '🥇 Best Match';
    if (rank === 2) return '🥈 2nd Match';
    if (rank === 3) return '🥉 3rd Match';
    return `#${rank} Match`;
  };

  const getConfidenceClass = () => {
    if (!confidence) return 'unknown';
    return confidence.toLowerCase().replace(/_/g, '-');
  };

  const getConfidenceLabel = () => {
    if (!confidence) return 'Unknown';
    return confidence.charAt(0).toUpperCase() + confidence.slice(1).replace(/_/g, ' ');
  };

  return (
    <div className={`criminal-match-card ${getRankClass()}`}>
      {/* Rank Badge */}
      <div className="rank-badge">
        <span className="rank-number">#{rank}</span>
        <span className="rank-label">{getRankLabel()}</span>
      </div>

      {/* Criminal Photo */}
      <div className="criminal-photo-container">
        <img 
          src={apiService.getCriminalPhotoUrl(match.criminal.id)}
          alt={match.criminal.full_name || match.criminal.name}
          className="criminal-photo"
          loading="lazy"
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
        {/* Match Score Overlay */}
        <div className="score-overlay">
          <div className="score-circle">
            <span className="score-number">{score.toFixed(0)}</span>
            <span className="score-percent">%</span>
          </div>
        </div>
      </div>

      {/* Criminal Info */}
      <div className="criminal-info">
        <h3 className="criminal-name">
          {match.criminal.full_name || match.criminal.name}
        </h3>
        
        {match.criminal.criminal_id && (
          <div className="info-row">
            <span className="info-label">ID:</span>
            <span className="info-value criminal-id">{match.criminal.criminal_id}</span>
          </div>
        )}

        {match.criminal.status && (
          <div className="status-badge">
            {match.criminal.status}
          </div>
        )}
      </div>

      {/* Similarity Progress Bar */}
      <div className="similarity-section">
        <div className="similarity-header">
          <span className="similarity-label">Match Score</span>
          <span className="similarity-value">{score.toFixed(1)}%</span>
        </div>
        <div className="similarity-bar-container">
          <div 
            className="similarity-bar-fill"
            style={{ width: `${Math.min(100, Math.max(0, score))}%` }}
          >
            <div className="similarity-bar-shine"></div>
          </div>
        </div>
      </div>

      {/* Confidence Level */}
      <div className="confidence-section">
        <span className="confidence-label">Confidence Level</span>
        <span className={`confidence-badge ${getConfidenceClass()}`}>
          {getConfidenceLabel()}
        </span>
      </div>

      {/* View Details Button */}
      <button 
        className="view-details-btn"
        onClick={() => onViewDetails(match.criminal)}
      >
        <svg viewBox="0 0 24 24" fill="currentColor">
          <path d="M12,9A3,3 0 0,0 9,12A3,3 0 0,0 12,15A3,3 0 0,0 15,12A3,3 0 0,0 12,9M12,17A5,5 0 0,1 7,12A5,5 0 0,1 12,7A5,5 0 0,1 17,12A5,5 0 0,1 12,17M12,4.5C7,4.5 2.73,7.61 1,12C2.73,16.39 7,19.5 12,19.5C17,19.5 21.27,16.39 23,12C21.27,7.61 17,4.5 12,4.5Z"/>
        </svg>
        View Full Profile
      </button>
    </div>
  );
};

export default CriminalMatchCard;
