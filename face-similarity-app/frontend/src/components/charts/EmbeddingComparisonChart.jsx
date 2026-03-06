import React from 'react';
import PropTypes from 'prop-types';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import './EmbeddingComparisonChart.css';

const EmbeddingComparisonChart = ({ similarityScore }) => {
  if (!similarityScore || typeof similarityScore !== 'object') return null;

  // Prepare data for bar chart
  const data = [];

  if (similarityScore.arcface_similarity !== undefined && similarityScore.arcface_similarity !== null) {
    data.push({
      name: 'ArcFace',
      score: Math.round(similarityScore.arcface_similarity),
      color: '#06b6d4',
      description: 'Deep learning face recognition model'
    });
  }

  if (similarityScore.facenet_similarity !== undefined && similarityScore.facenet_similarity !== null) {
    data.push({
      name: 'Facenet',
      score: Math.round(similarityScore.facenet_similarity),
      color: '#22c55e',
      description: 'Neural network embedding model'
    });
  }

  if (similarityScore.embedding_fusion !== undefined && similarityScore.embedding_fusion !== null) {
    data.push({
      name: 'Fusion',
      score: Math.round(similarityScore.embedding_fusion),
      color: '#a855f7',
      description: 'Combined embedding score'
    });
  }

  if (similarityScore.geometric_similarity !== undefined && similarityScore.geometric_similarity !== null) {
    data.push({
      name: 'Geometric',
      score: Math.round(similarityScore.geometric_similarity),
      color: '#f59e0b',
      description: 'Facial landmark analysis'
    });
  }

  if (data.length === 0) return null;

  // Custom Tooltip
  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div className="custom-tooltip">
          <p className="tooltip-title">{data.name}</p>
          <p className="tooltip-score">{data.score}%</p>
          <p className="tooltip-description">{data.description}</p>
        </div>
      );
    }
    return null;
  };

  // Custom Label
  const CustomLabel = (props) => {
    const { x, y, width, value } = props;
    return (
      <text 
        x={x + width / 2} 
        y={y - 10} 
        fill="rgba(255, 255, 255, 0.9)" 
        textAnchor="middle"
        fontSize={14}
        fontWeight={700}
        fontFamily="'Courier New', monospace"
      >
        {value}%
      </text>
    );
  };

  // Calculate statistics
  const avgScore = Math.round(data.reduce((sum, item) => sum + item.score, 0) / data.length);
  const maxScore = Math.max(...data.map(item => item.score));
  const minScore = Math.min(...data.map(item => item.score));
  const variance = Math.round(maxScore - minScore);

  return (
    <div className="embedding-comparison-chart">
      <div className="chart-header">
        <h3 className="chart-title">
          <span className="chart-icon">🧬</span>
          Embedding Model Comparison
        </h3>
        <p className="chart-subtitle">Deep learning model performance analysis</p>
      </div>

      <div className="chart-container">
        <ResponsiveContainer width="100%" height={350}>
          <BarChart 
            data={data}
            margin={{ top: 30, right: 30, left: 20, bottom: 20 }}
          >
            <CartesianGrid 
              strokeDasharray="3 3" 
              stroke="rgba(6, 182, 212, 0.1)"
              vertical={false}
            />
            <XAxis 
              dataKey="name" 
              tick={{ fill: 'rgba(255, 255, 255, 0.8)', fontSize: 13, fontWeight: 600 }}
              stroke="rgba(6, 182, 212, 0.3)"
              axisLine={{ stroke: 'rgba(6, 182, 212, 0.3)' }}
            />
            <YAxis 
              domain={[0, 100]}
              tick={{ fill: 'rgba(255, 255, 255, 0.6)', fontSize: 12 }}
              stroke="rgba(6, 182, 212, 0.3)"
              axisLine={{ stroke: 'rgba(6, 182, 212, 0.3)' }}
              label={{ 
                value: 'Similarity (%)', 
                angle: -90, 
                position: 'insideLeft',
                fill: 'rgba(255, 255, 255, 0.6)',
                fontSize: 12,
                fontWeight: 600
              }}
            />
            <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(6, 182, 212, 0.1)' }} />
            <Bar 
              dataKey="score" 
              radius={[8, 8, 0, 0]}
              label={<CustomLabel />}
              animationDuration={1000}
              animationBegin={200}
            >
              {data.map((entry, index) => (
                <rect 
                  key={`bar-${entry.name}`}
                  fill={entry.color}
                  style={{
                    filter: `drop-shadow(0 4px 8px ${entry.color}40)`
                  }}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Statistics Panel */}
      <div className="chart-statistics">
        <div className="stat-card">
          <div className="stat-icon">📊</div>
          <div className="stat-content">
            <span className="stat-label">Average</span>
            <span className="stat-value">{avgScore}%</span>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon">⬆️</div>
          <div className="stat-content">
            <span className="stat-label">Highest</span>
            <span className="stat-value">{maxScore}%</span>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon">⬇️</div>
          <div className="stat-content">
            <span className="stat-label">Lowest</span>
            <span className="stat-value">{minScore}%</span>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon">📈</div>
          <div className="stat-content">
            <span className="stat-label">Variance</span>
            <span className="stat-value">{variance}%</span>
          </div>
        </div>
      </div>

      {/* Model Legend */}
      <div className="model-legend">
        {data.map((item, index) => (
          <div key={index} className="legend-item">
            <div 
              className="legend-color" 
              style={{ 
                background: item.color,
                boxShadow: `0 0 12px ${item.color}60`
              }}
            ></div>
            <div className="legend-text">
              <span className="legend-name">{item.name}</span>
              <span className="legend-desc">{item.description}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default EmbeddingComparisonChart;


EmbeddingComparisonChart.propTypes = {
  similarityScore: PropTypes.shape({
    arcface_similarity: PropTypes.number,
    facenet_similarity: PropTypes.number,
    embedding_fusion: PropTypes.number,
    geometric_similarity: PropTypes.number
  })
};
