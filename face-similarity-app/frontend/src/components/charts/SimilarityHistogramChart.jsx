import React, { useMemo } from 'react';
import PropTypes from 'prop-types';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine, Legend } from 'recharts';
import './SimilarityHistogramChart.css';

const SimilarityHistogramChart = ({ 
  searchResults = [],
  topMatchId = null,
  binCount = 10
}) => {
  // Calculate statistics and histogram data
  const statistics = useMemo(() => {
    if (!searchResults || searchResults.length === 0) {
      return {
        mean: 0,
        stdDev: 0,
        min: 0,
        max: 0,
        topMatch: null,
        histogram: [],
        zScore: 0,
        confidenceLevel: 'Low'
      };
    }

    // Extract similarity scores
    const scores = searchResults.map(r => r.similarity || r.score || 0);
    
    // Calculate mean
    const mean = scores.reduce((a, b) => a + b, 0) / scores.length;
    
    // Calculate standard deviation
    const variance = scores.reduce((sum, score) => sum + Math.pow(score - mean, 2), 0) / scores.length;
    const stdDev = Math.sqrt(variance);
    
    // Find min and max
    const min = Math.min(...scores);
    const max = Math.max(...scores);
    
    // Find top match
    const topMatch = searchResults.find(r => r.id === topMatchId) || 
                     searchResults.reduce((prev, curr) => 
                       (curr.similarity || 0) > (prev.similarity || 0) ? curr : prev
                     );
    
    // Calculate z-score for top match
    const topScore = topMatch.similarity || topMatch.score || 0;
    const zScore = stdDev > 0 ? (topScore - mean) / stdDev : 0;
    
    // Determine confidence level based on z-score
    let confidenceLevel = 'Low';
    if (zScore >= 3) confidenceLevel = 'Very High';
    else if (zScore >= 2) confidenceLevel = 'High';
    else if (zScore >= 1) confidenceLevel = 'Medium';
    
    // Create histogram bins
    const binSize = (max - min) / binCount;
    const bins = Array(binCount).fill(0).map((_, i) => ({
      range: `${(min + i * binSize).toFixed(0)}-${(min + (i + 1) * binSize).toFixed(0)}`,
      rangeStart: min + i * binSize,
      rangeEnd: min + (i + 1) * binSize,
      count: 0,
      hasTopMatch: false
    }));
    
    // Fill bins
    scores.forEach((score, idx) => {
      const binIndex = Math.min(Math.floor((score - min) / binSize), binCount - 1);
      if (binIndex >= 0 && binIndex < binCount) {
        bins[binIndex].count++;
        if (searchResults[idx].id === topMatchId || searchResults[idx] === topMatch) {
          bins[binIndex].hasTopMatch = true;
        }
      }
    });
    
    return {
      mean,
      stdDev,
      min,
      max,
      topMatch,
      histogram: bins,
      zScore,
      confidenceLevel
    };
  }, [searchResults, topMatchId, binCount]);

  // Custom tooltip
  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div className="histogram-tooltip">
          <div className="tooltip-header">
            <strong>Similarity Range</strong>
          </div>
          <div className="tooltip-content">
            <div className="tooltip-row">
              <span className="tooltip-label">Range:</span>
              <span className="tooltip-value">{data.range}%</span>
            </div>
            <div className="tooltip-row">
              <span className="tooltip-label">Candidates:</span>
              <span className="tooltip-value">{data.count}</span>
            </div>
            {data.hasTopMatch && (
              <div className="tooltip-badge top-match">
                ⭐ Contains Top Match
              </div>
            )}
          </div>
        </div>
      );
    }
    return null;
  };

  if (!searchResults || searchResults.length === 0) {
    return (
      <div className="histogram-placeholder">
        <div className="placeholder-icon">📊</div>
        <p>No search results available</p>
        <span className="placeholder-hint">Perform a database search to see distribution</span>
      </div>
    );
  }

  const { mean, stdDev, topMatch, histogram, zScore, confidenceLevel } = statistics;

  return (
    <div className="similarity-histogram-chart">
      <div className="histogram-header">
        <div className="histogram-title-section">
          <h4 className="histogram-title">
            <span className="histogram-icon">📊</span>
            Similarity Distribution
          </h4>
          <span className="histogram-badge">Database Analysis</span>
        </div>
      </div>

      <div className="histogram-description">
        <p>
          Distribution of similarity scores across {searchResults.length} database candidates.
          The top match is highlighted in green.
        </p>
      </div>

      {/* Statistics Cards */}
      <div className="statistics-grid">
        <div className="stat-card">
          <div className="stat-icon">📈</div>
          <div className="stat-content">
            <span className="stat-label">Mean Similarity</span>
            <span className="stat-value">{mean.toFixed(2)}%</span>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon">📏</div>
          <div className="stat-content">
            <span className="stat-label">Std Deviation</span>
            <span className="stat-value">±{stdDev.toFixed(2)}%</span>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon">🎯</div>
          <div className="stat-content">
            <span className="stat-label">Z-Score</span>
            <span className="stat-value z-score">{zScore.toFixed(2)}σ</span>
          </div>
        </div>

        <div className={`stat-card confidence ${confidenceLevel.toLowerCase().replace(' ', '-')}`}>
          <div className="stat-icon">✓</div>
          <div className="stat-content">
            <span className="stat-label">Confidence</span>
            <span className="stat-value">{confidenceLevel}</span>
          </div>
        </div>
      </div>

      {/* Histogram Chart */}
      <div className="histogram-chart-container">
        <ResponsiveContainer width="100%" height={350}>
          <BarChart
            data={histogram}
            margin={{ top: 20, right: 30, left: 20, bottom: 60 }}
          >
            <CartesianGrid 
              strokeDasharray="3 3" 
              stroke="rgba(255, 255, 255, 0.1)"
              vertical={false}
            />
            <XAxis 
              dataKey="range" 
              stroke="var(--forensic-gray-400)"
              tick={{ fill: 'var(--forensic-gray-400)', fontSize: 11 }}
              angle={-45}
              textAnchor="end"
              height={80}
              label={{ 
                value: 'Similarity Score Range (%)', 
                position: 'insideBottom', 
                offset: -50,
                fill: 'var(--forensic-gray-300)',
                fontSize: 13
              }}
            />
            <YAxis 
              stroke="var(--forensic-gray-400)"
              tick={{ fill: 'var(--forensic-gray-400)', fontSize: 12 }}
              label={{ 
                value: 'Number of Candidates', 
                angle: -90, 
                position: 'insideLeft',
                fill: 'var(--forensic-gray-300)',
                fontSize: 13
              }}
            />
            <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(6, 182, 212, 0.1)' }} />
            <Legend 
              wrapperStyle={{ paddingTop: '20px' }}
              iconType="square"
            />
            
            {/* Mean line */}
            <ReferenceLine 
              y={0} 
              stroke="var(--forensic-warning)" 
              strokeDasharray="5 5"
              strokeWidth={2}
              label={{ 
                value: `Mean: ${mean.toFixed(1)}%`, 
                position: 'top',
                fill: 'var(--forensic-warning)',
                fontSize: 12,
                fontWeight: 600
              }}
            />
            
            {/* Standard deviation range */}
            <ReferenceLine 
              y={0}
              stroke="var(--forensic-gray-500)" 
              strokeDasharray="3 3"
              strokeWidth={1}
              label={{ 
                value: `+1σ: ${(mean + stdDev).toFixed(1)}%`, 
                position: 'top',
                fill: 'var(--forensic-gray-400)',
                fontSize: 10
              }}
            />
            <ReferenceLine 
              y={0}
              stroke="var(--forensic-gray-500)" 
              strokeDasharray="3 3"
              strokeWidth={1}
              label={{ 
                value: `-1σ: ${(mean - stdDev).toFixed(1)}%`, 
                position: 'top',
                fill: 'var(--forensic-gray-400)',
                fontSize: 10
              }}
            />
            
            <Bar 
              dataKey="count" 
              name="Candidates"
              radius={[8, 8, 0, 0]}
              shape={(props) => {
                const { x, y, width, height, payload } = props;
                const fill = payload.hasTopMatch ? 'var(--forensic-success)' : 'var(--forensic-accent)';
                const opacity = payload.hasTopMatch ? 1 : 0.7;
                return (
                  <rect
                    x={x}
                    y={y}
                    width={width}
                    height={height}
                    fill={fill}
                    opacity={opacity}
                    rx={8}
                    ry={8}
                  />
                );
              }}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Top Match Info */}
      {topMatch && (
        <div className="top-match-info">
          <div className="top-match-header">
            <span className="top-match-badge">⭐ Top Match</span>
          </div>
          <div className="top-match-details">
            <div className="detail-row">
              <span className="detail-label">Name:</span>
              <span className="detail-value">{topMatch.name || topMatch.label || 'Unknown'}</span>
            </div>
            <div className="detail-row">
              <span className="detail-label">Similarity:</span>
              <span className="detail-value highlight">
                {((topMatch.similarity || topMatch.score || 0) * 100).toFixed(2)}%
              </span>
            </div>
            <div className="detail-row">
              <span className="detail-label">Z-Score:</span>
              <span className="detail-value">
                {zScore.toFixed(2)}σ ({zScore >= 2 ? 'Statistically Significant' : 'Within Normal Range'})
              </span>
            </div>
            <div className="detail-row">
              <span className="detail-label">Confidence:</span>
              <span className={`detail-value confidence-badge ${confidenceLevel.toLowerCase().replace(' ', '-')}`}>
                {confidenceLevel}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Statistical Note */}
      <div className="histogram-note">
        <svg className="note-icon" viewBox="0 0 24 24" fill="currentColor">
          <path d="M13,9H11V7H13M13,17H11V11H13M12,2A10,10 0 0,0 2,12A10,10 0 0,0 12,22A10,10 0 0,0 22,12A10,10 0 0,0 12,2Z"/>
        </svg>
        <div className="note-content">
          <p>
            <strong>Z-Score Interpretation:</strong> Measures how many standard deviations the top match 
            is from the mean. A z-score ≥ 2 indicates the match is statistically significant (95% confidence).
          </p>
          <p>
            <strong>Confidence Levels:</strong> Very High (z ≥ 3), High (z ≥ 2), Medium (z ≥ 1), Low (z &lt; 1)
          </p>
        </div>
      </div>
    </div>
  );
};

SimilarityHistogramChart.propTypes = {
  searchResults: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.string,
      name: PropTypes.string,
      label: PropTypes.string,
      similarity: PropTypes.number,
      score: PropTypes.number
    })
  ),
  topMatchId: PropTypes.string,
  binCount: PropTypes.number
};

export default SimilarityHistogramChart;
