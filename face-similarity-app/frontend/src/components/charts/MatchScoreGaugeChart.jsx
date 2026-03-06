import React from 'react';
import PropTypes from 'prop-types';
import { PieChart, Pie, Cell, ResponsiveContainer } from 'recharts';
import './MatchScoreGaugeChart.css';

const MatchScoreGaugeChart = ({ similarityScore }) => {
  if (!similarityScore) return null;

  // Calculate overall score
  const getSimilarityPercentage = (scoreData) => {
    if (typeof scoreData === 'object' && scoreData.display_similarity !== undefined) {
      return Math.round(scoreData.display_similarity);
    } else if (typeof scoreData === 'object' && scoreData.similarity !== undefined) {
      return Math.round(scoreData.similarity);
    } else if (typeof scoreData === 'number') {
      const maxDistance = 1.0;
      const percentage = Math.max(0, Math.min(100, (1 - Math.min(scoreData, maxDistance) / maxDistance) * 100));
      return Math.round(percentage);
    }
    return 0;
  };

  const score = getSimilarityPercentage(similarityScore);
  const remaining = 100 - score;

  // Prepare data for gauge
  const data = [
    { name: 'Match Score', value: score },
    { name: 'Remaining', value: remaining }
  ];

  // Color based on score
  const getScoreColor = (score) => {
    if (score >= 85) return '#22c55e'; // Success green
    if (score >= 70) return '#06b6d4'; // Accent cyan
    if (score >= 50) return '#f59e0b'; // Warning amber
    return '#ef4444'; // Error red
  };

  const scoreColor = getScoreColor(score);
  const COLORS = [scoreColor, 'rgba(255, 255, 255, 0.05)'];

  // Get match category
  const getMatchCategory = () => {
    if (typeof similarityScore === 'object' && similarityScore.match_quality) {
      return similarityScore.match_quality;
    }
    if (score >= 85) return 'Very Strong Match';
    if (score >= 70) return 'Strong Match';
    if (score >= 50) return 'Possible Match';
    return 'Low Similarity';
  };

  const matchCategory = getMatchCategory();

  // Get confidence level
  const getConfidenceLevel = () => {
    if (typeof similarityScore === 'object' && similarityScore.confidence_level) {
      return similarityScore.confidence_level;
    }
    if (score >= 85) return 'High';
    if (score >= 70) return 'Medium';
    return 'Low';
  };

  const confidenceLevel = getConfidenceLevel();

  return (
    <div className="match-score-gauge-chart">
      <div className="chart-header">
        <h3 className="chart-title">
          <span className="chart-icon">🎯</span>
          Match Score Gauge
        </h3>
        <p className="chart-subtitle">Overall similarity assessment</p>
      </div>

      <div className="gauge-container">
        <ResponsiveContainer width="100%" height={300}>
          <PieChart>
            <Pie
              data={data}
              cx="50%"
              cy="50%"
              startAngle={180}
              endAngle={0}
              innerRadius={80}
              outerRadius={120}
              paddingAngle={0}
              dataKey="value"
            >
              {data.map((entry, index) => (
                <Cell 
                  key={`cell-${index}`} 
                  fill={COLORS[index]}
                  stroke="none"
                />
              ))}
            </Pie>
          </PieChart>
        </ResponsiveContainer>

        {/* Center Score Display */}
        <div className="gauge-center">
          <div className="gauge-score" style={{ color: scoreColor }}>
            {score}
            <span className="gauge-percent">%</span>
          </div>
          <div className="gauge-label">Similarity</div>
        </div>
      </div>

      {/* Match Details */}
      <div className="gauge-details">
        <div className="detail-row">
          <span className="detail-label">Match Category</span>
          <span className="detail-badge" style={{ 
            background: `${scoreColor}20`,
            color: scoreColor,
            borderColor: `${scoreColor}40`
          }}>
            {matchCategory}
          </span>
        </div>
        
        <div className="detail-row">
          <span className="detail-label">Confidence Level</span>
          <span className="detail-badge confidence" style={{ 
            background: `${scoreColor}20`,
            color: scoreColor,
            borderColor: `${scoreColor}40`
          }}>
            {confidenceLevel}
          </span>
        </div>
      </div>

      {/* Score Interpretation */}
      <div className="score-interpretation">
        <div className="interpretation-bar">
          <div className="bar-segment low">
            <span className="bar-label">0-49</span>
            <span className="bar-text">Low</span>
          </div>
          <div className="bar-segment medium">
            <span className="bar-label">50-69</span>
            <span className="bar-text">Possible</span>
          </div>
          <div className="bar-segment high">
            <span className="bar-label">70-84</span>
            <span className="bar-text">Strong</span>
          </div>
          <div className="bar-segment very-high">
            <span className="bar-label">85-100</span>
            <span className="bar-text">Very Strong</span>
          </div>
        </div>
        <div className="score-indicator" style={{ left: `${score}%` }}>
          <div className="indicator-arrow" style={{ borderTopColor: scoreColor }}></div>
        </div>
      </div>
    </div>
  );
};

export default MatchScoreGaugeChart;


MatchScoreGaugeChart.propTypes = {
  similarityScore: PropTypes.oneOfType([
    PropTypes.number,
    PropTypes.shape({
      display_similarity: PropTypes.number,
      similarity: PropTypes.number,
      match_quality: PropTypes.string,
      confidence_level: PropTypes.string
    })
  ])
};
