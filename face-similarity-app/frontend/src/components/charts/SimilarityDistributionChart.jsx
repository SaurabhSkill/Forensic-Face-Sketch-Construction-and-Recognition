import React from 'react';
import PropTypes from 'prop-types';
import { RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar, ResponsiveContainer, Legend, Tooltip } from 'recharts';
import './SimilarityDistributionChart.css';

const SimilarityDistributionChart = ({ similarityScore }) => {
  if (!similarityScore || typeof similarityScore !== 'object') return null;

  // Prepare data for radar chart
  const data = [];

  if (similarityScore.arcface_similarity !== undefined && similarityScore.arcface_similarity !== null) {
    data.push({
      metric: 'ArcFace',
      similarity: Math.round(similarityScore.arcface_similarity),
      fullMark: 100
    });
  }

  if (similarityScore.facenet_similarity !== undefined && similarityScore.facenet_similarity !== null) {
    data.push({
      metric: 'Facenet',
      similarity: Math.round(similarityScore.facenet_similarity),
      fullMark: 100
    });
  }

  if (similarityScore.geometric_similarity !== undefined && similarityScore.geometric_similarity !== null) {
    data.push({
      metric: 'Geometric',
      similarity: Math.round(similarityScore.geometric_similarity),
      fullMark: 100
    });
  }

  if (similarityScore.embedding_fusion !== undefined && similarityScore.embedding_fusion !== null) {
    data.push({
      metric: 'Fusion',
      similarity: Math.round(similarityScore.embedding_fusion),
      fullMark: 100
    });
  }

  // Add region analysis if available
  if (similarityScore.region_details) {
    const regions = similarityScore.region_details;
    if (regions.eyes !== undefined) {
      data.push({
        metric: 'Eyes',
        similarity: Math.round(regions.eyes),
        fullMark: 100
      });
    }
    if (regions.nose !== undefined) {
      data.push({
        metric: 'Nose',
        similarity: Math.round(regions.nose),
        fullMark: 100
      });
    }
    if (regions.mouth !== undefined) {
      data.push({
        metric: 'Mouth',
        similarity: Math.round(regions.mouth),
        fullMark: 100
      });
    }
  }

  if (data.length === 0) return null;

  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      return (
        <div className="custom-tooltip">
          <p className="tooltip-label">{payload[0].payload.metric}</p>
          <p className="tooltip-value">{payload[0].value}%</p>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="similarity-distribution-chart">
      <div className="chart-header">
        <h3 className="chart-title">
          <span className="chart-icon">📊</span>
          Similarity Distribution
        </h3>
        <p className="chart-subtitle">Multi-dimensional analysis across all metrics</p>
      </div>
      
      <div className="chart-container">
        <ResponsiveContainer width="100%" height={400}>
          <RadarChart data={data}>
            <PolarGrid 
              stroke="rgba(6, 182, 212, 0.2)" 
              strokeWidth={1}
            />
            <PolarAngleAxis 
              dataKey="metric" 
              tick={{ fill: 'rgba(255, 255, 255, 0.8)', fontSize: 13, fontWeight: 600 }}
              stroke="rgba(6, 182, 212, 0.3)"
            />
            <PolarRadiusAxis 
              angle={90} 
              domain={[0, 100]}
              tick={{ fill: 'rgba(255, 255, 255, 0.5)', fontSize: 11 }}
              stroke="rgba(6, 182, 212, 0.2)"
            />
            <Radar 
              name="Similarity" 
              dataKey="similarity" 
              stroke="#06b6d4" 
              fill="#06b6d4" 
              fillOpacity={0.3}
              strokeWidth={2}
              dot={{ fill: '#06b6d4', r: 4 }}
              activeDot={{ r: 6, fill: '#22d3ee' }}
            />
            <Tooltip content={<CustomTooltip />} />
            <Legend 
              wrapperStyle={{ 
                paddingTop: '20px',
                fontSize: '13px',
                fontWeight: 600
              }}
              iconType="circle"
            />
          </RadarChart>
        </ResponsiveContainer>
      </div>

      <div className="chart-footer">
        <div className="chart-stats">
          <div className="stat-item">
            <span className="stat-label">Metrics Analyzed</span>
            <span className="stat-value">{data.length}</span>
          </div>
          <div className="stat-item">
            <span className="stat-label">Average Score</span>
            <span className="stat-value">
              {Math.round(data.reduce((sum, item) => sum + item.similarity, 0) / data.length)}%
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SimilarityDistributionChart;


SimilarityDistributionChart.propTypes = {
  similarityScore: PropTypes.shape({
    arcface_similarity: PropTypes.number,
    facenet_similarity: PropTypes.number,
    geometric_similarity: PropTypes.number,
    embedding_fusion: PropTypes.number,
    region_details: PropTypes.shape({
      eyes: PropTypes.number,
      nose: PropTypes.number,
      mouth: PropTypes.number
    })
  })
};
