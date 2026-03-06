import React from 'react';
import CriminalMatchCard from './CriminalMatchCard';
import './SearchResultsGrid.css';

const SearchResultsGrid = ({ matches, onViewDetails }) => {
  if (matches.length === 0) {
    return (
      <div className="no-matches-container">
        <div className="no-matches-content">
          <div className="no-matches-icon">
            <svg viewBox="0 0 24 24" fill="currentColor">
              <path d="M12,2A10,10 0 0,0 2,12A10,10 0 0,0 12,22A10,10 0 0,0 22,12A10,10 0 0,0 12,2M12,4A8,8 0 0,1 20,12A8,8 0 0,1 12,20A8,8 0 0,1 4,12A8,8 0 0,1 12,4M12,6A6,6 0 0,0 6,12A6,6 0 0,0 12,18A6,6 0 0,0 18,12A6,6 0 0,0 12,6M12,8A4,4 0 0,1 16,12A4,4 0 0,1 12,16A4,4 0 0,1 8,12A4,4 0 0,1 12,8Z"/>
            </svg>
          </div>
          <h3 className="no-matches-title">No Matches Found</h3>
          <p className="no-matches-text">
            No criminals matching this sketch were found in the database.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="search-results-container">
      <div className="results-header">
        <h3 className="results-title">
          <span className="results-icon">🎯</span>
          Top {Math.min(matches.length, 5)} Matching Results
        </h3>
        <p className="results-subtitle">
          Ranked by similarity score • Highest confidence first
        </p>
      </div>
      
      <div className="matches-grid">
        {matches.slice(0, 5).map((match, index) => (
          <CriminalMatchCard 
            key={match.criminal.id}
            match={match}
            index={index}
            onViewDetails={onViewDetails}
          />
        ))}
      </div>
    </div>
  );
};

export default SearchResultsGrid;
