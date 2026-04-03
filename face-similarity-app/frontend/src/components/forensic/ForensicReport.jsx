import React, { useState, useEffect } from 'react';
import PropTypes from 'prop-types';
import MatchScoreGauge from './MatchScoreGauge';
import SimilarityBars from './SimilarityBars';
import RegionAnalysis from './RegionAnalysis';
import ProcessingInfo from './ProcessingInfo';
import ForensicVisualizationPanel from './ForensicVisualizationPanel';
import FaceSimilarityHeatmap from './FaceSimilarityHeatmap';
import './ForensicReport.css';

const ForensicReport = ({ similarityScore, photoFile }) => {
  const [photoUrl, setPhotoUrl] = useState(null);

  useEffect(() => {
    if (photoFile) {
      const url = URL.createObjectURL(photoFile);
      setPhotoUrl(url);
      
      // Cleanup URL when component unmounts or photoFile changes
      return () => URL.revokeObjectURL(url);
    }
  }, [photoFile]);

  if (!similarityScore) return null;

  // Check if similarityScore is an object
  const isObject = typeof similarityScore === 'object';

  const getSimilarityPercentage = (scoreData) => {
    if (typeof scoreData === 'object' && scoreData.display_similarity !== undefined) {
      return Math.round(scoreData.display_similarity);
    } else if (typeof scoreData === 'object' && scoreData.similarity !== undefined) {
      return Math.round(scoreData.similarity);
    } else if (typeof scoreData === 'number') {
      // If it's already a percentage (0-100), use it directly
      if (scoreData > 1) {
        return Math.round(scoreData);
      }
      // If it's a decimal (0-1), convert to percentage
      return Math.round(scoreData * 100);
    }
    return 0;
  };

  const score = getSimilarityPercentage(similarityScore);

  // Helper function to safely get numeric value
  const getNumericValue = (value) => {
    if (value === undefined || value === null) return null;
    const num = typeof value === 'string' ? parseFloat(value) : value;
    if (isNaN(num)) return null;
    // Backend sends display values already as percentages (0-100)
    return num;
  };

  // Prepare embedding metrics
  const embeddingMetrics = [];
  if (isObject) {
    // Try display values first, then fall back to raw values
    const arcface = getNumericValue(similarityScore.insightface_similarity);
    const facenet = getNumericValue(similarityScore.facenet_similarity);
    const fusion = getNumericValue(similarityScore.embedding_fusion);
    
    if (arcface !== null && arcface !== undefined) {
      embeddingMetrics.push({ 
        name: 'InsightFace Model', 
        value: arcface, 
        className: 'insightface',
        description: 'Deep learning face recognition model'
      });
    }
    if (facenet !== null && facenet !== undefined) {
      embeddingMetrics.push({ 
        name: 'Facenet Model', 
        value: facenet, 
        className: 'facenet',
        description: 'Deep learning face recognition model'
      });
    }
    if (fusion !== null && fusion !== undefined) {
      embeddingMetrics.push({ 
        name: 'Fusion Score (Combined)', 
        value: fusion, 
        className: 'fusion',
        description: 'Combined score from both models'
      });
    }
  }

  // Prepare geometric metrics
  const geometricMetrics = [];
  if (isObject) {
    const geometric = getNumericValue(similarityScore.geometric_similarity);
    
    if (geometric !== null && geometric !== undefined) {
      geometricMetrics.push({ 
        name: 'Facial Structure Similarity', 
        value: geometric, 
        className: 'geometric',
        description: 'Facial landmark and structure comparison'
      });
    }
  }

  // Prepare region details from direct fields
  const regionDetailsFromFields = {};
  if (isObject) {
    const eyes = getNumericValue(similarityScore.eyes_similarity);
    const nose = getNumericValue(similarityScore.nose_similarity);
    const mouth = getNumericValue(similarityScore.mouth_similarity);
    
    if (eyes !== null && eyes !== undefined) {
      regionDetailsFromFields.eyes = eyes;
    }
    if (nose !== null && nose !== undefined) {
      regionDetailsFromFields.nose = nose;
    }
    if (mouth !== null && mouth !== undefined) {
      regionDetailsFromFields.mouth = mouth;
    }
  }

  // Check if region_details exists in the response
  let finalRegionDetails = null;
  if (isObject && similarityScore.region_details) {
    finalRegionDetails = similarityScore.region_details;
  } else if (Object.keys(regionDetailsFromFields).length > 0) {
    finalRegionDetails = regionDetailsFromFields;
  }

  return (
    <div className="forensic-report-container">
      <div className="forensic-report-dashboard">
        
        {/* Report Header */}
        <div className="report-header">
          <div className="report-header-content">
            <div className="report-icon">
              <svg viewBox="0 0 24 24" fill="currentColor">
                <path d="M9,11.75A1.25,1.25 0 0,0 7.75,13A1.25,1.25 0 0,0 9,14.25A1.25,1.25 0 0,0 10.25,13A1.25,1.25 0 0,0 9,11.75M15,11.75A1.25,1.25 0 0,0 13.75,13A1.25,1.25 0 0,0 15,14.25A1.25,1.25 0 0,0 16.25,13A1.25,1.25 0 0,0 15,11.75M12,2A10,10 0 0,0 2,12A10,10 0 0,0 12,22A10,10 0 0,0 22,12A10,10 0 0,0 12,2M12,20C7.59,20 4,16.41 4,12C4,11.71 4,11.42 4.05,11.14C6.41,10.09 8.28,8.16 9.26,5.77C11.07,8.33 14.05,10 17.42,10C18.2,10 18.95,9.91 19.67,9.74C19.88,10.45 20,11.21 20,12C20,16.41 16.41,20 12,20Z"/>
              </svg>
            </div>
            <div className="report-header-text">
              <h2 className="report-title">Forensic Analysis Report</h2>
              <p className="report-subtitle">Facial Recognition Similarity Assessment</p>
            </div>
          </div>
          <div className="report-timestamp">
            {new Date().toLocaleString('en-US', { 
              dateStyle: 'medium', 
              timeStyle: 'short' 
            })}
          </div>
        </div>

        {/* Main Dashboard Grid */}
        <div className="dashboard-grid">
          
          {/* Left Column - Overall Score */}
          <div className="dashboard-section overall-score-section">
            <div className="forensic-section-header">
              <h3 className="forensic-section-title">
                <span className="forensic-section-icon">📊</span>
                Overall Match Score
              </h3>
            </div>
            <MatchScoreGauge 
              score={score}
              matchQuality={isObject ? similarityScore.match_quality : null}
              confidenceLevel={isObject ? similarityScore.confidence_level : null}
            />
          </div>

          {/* Right Column - Detailed Analysis */}
          <div className="dashboard-section detailed-analysis-section">
            
            {/* Embedding Similarity */}
            <div className="analysis-block">
              <div className="forensic-section-header">
                <h3 className="forensic-section-title">
                  <span className="forensic-section-icon">🧬</span>
                  Embedding Similarity
                </h3>
                <span className="forensic-section-badge">Deep Learning Models</span>
              </div>
              {embeddingMetrics.length > 0 ? (
                <SimilarityBars title="" metrics={embeddingMetrics} />
              ) : (
                <div className="forensic-no-data">
                  <p>No embedding similarity data available</p>
                </div>
              )}
            </div>

            {/* Geometric Similarity */}
            <div className="analysis-block">
              <div className="forensic-section-header">
                <h3 className="forensic-section-title">
                  <span className="forensic-section-icon">📐</span>
                  Geometric Similarity
                </h3>
                <span className="forensic-section-badge">Landmark Analysis</span>
              </div>
              {geometricMetrics.length > 0 ? (
                <SimilarityBars title="" metrics={geometricMetrics} />
              ) : (
                <div className="forensic-no-data">
                  <p>No geometric similarity data available</p>
                </div>
              )}
            </div>

            {/* Region Analysis */}
            <div className="analysis-block">
              <div className="forensic-section-header">
                <h3 className="forensic-section-title">
                  <span className="forensic-section-icon">🔍</span>
                  Region Analysis
                </h3>
                <span className="forensic-section-badge">Facial Features</span>
              </div>
              {isObject && (finalRegionDetails || similarityScore.region_similarity) ? (
                <RegionAnalysis 
                  regionDetails={finalRegionDetails}
                  regionSimilarity={similarityScore.region_similarity}
                />
              ) : (
                <div className="forensic-no-data">
                  <p>No region analysis data available</p>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Heatmap Visualization */}
        {photoUrl && isObject && finalRegionDetails && (
          <div className="dashboard-section heatmap-section">
            <FaceSimilarityHeatmap 
              imageUrl={photoUrl}
              regionScores={finalRegionDetails}
              overallScore={score}
            />
          </div>
        )}

        {/* Bottom Section - Processing Info & Technical Notes */}
        <div className="dashboard-footer">
          {isObject && (
            <ProcessingInfo 
              processingTime={similarityScore.processing_time}
              modelUsed={similarityScore.model_used}
              forensicNote={similarityScore.forensic_note}
            />
          )}
        </div>

      </div>

      {/* Data Visualizations Panel */}
      <ForensicVisualizationPanel similarityScore={similarityScore} />
    </div>
  );
};

ForensicReport.propTypes = {
  similarityScore: PropTypes.object,
  photoFile: PropTypes.object
};

export default ForensicReport;
