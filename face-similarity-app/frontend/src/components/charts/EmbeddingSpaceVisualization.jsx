import React, { useMemo, useState } from 'react';
import PropTypes from 'prop-types';
import { ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ZAxis } from 'recharts';
import './EmbeddingSpaceVisualization.css';

const EmbeddingSpaceVisualization = ({ 
  queryEmbedding, 
  matchedEmbeddings = [],
  queryLabel = 'Query Face',
  reductionMethod = 'PCA'
}) => {
  const [hoveredPoint, setHoveredPoint] = useState(null);

  // Simple PCA implementation for 2D reduction
  const performPCA = (embeddings) => {
    if (!embeddings || embeddings.length === 0) return [];

    // Convert to matrix
    const matrix = embeddings.map(e => e.vector);
    const n = matrix.length;
    const d = matrix[0].length;

    // Calculate mean
    const mean = new Array(d).fill(0);
    for (let i = 0; i < n; i++) {
      for (let j = 0; j < d; j++) {
        mean[j] += matrix[i][j];
      }
    }
    for (let j = 0; j < d; j++) {
      mean[j] /= n;
    }

    // Center the data
    const centered = matrix.map(row => 
      row.map((val, j) => val - mean[j])
    );

    // Calculate covariance matrix (simplified - using first 2 principal components)
    // For production, use a proper PCA library like ml-pca
    const covariance = [];
    for (let i = 0; i < Math.min(d, 50); i++) {
      covariance[i] = [];
      for (let j = 0; j < Math.min(d, 50); j++) {
        let sum = 0;
        for (let k = 0; k < n; k++) {
          sum += centered[k][i] * centered[k][j];
        }
        covariance[i][j] = sum / (n - 1);
      }
    }

    // Simplified projection (using first two dimensions with highest variance)
    const variances = covariance.map((row, i) => ({ index: i, variance: row[i] }));
    variances.sort((a, b) => b.variance - a.variance);
    
    const pc1 = variances[0].index;
    const pc2 = variances[1].index;

    // Project data onto first 2 principal components
    return centered.map((row, idx) => ({
      x: row[pc1] * 10, // Scale for better visualization
      y: row[pc2] * 10,
      ...embeddings[idx]
    }));
  };

  // Simple t-SNE approximation (for demo - use real t-SNE library in production)
  const performTSNE = (embeddings) => {
    if (!embeddings || embeddings.length === 0) return [];

    // Simplified t-SNE using distance-based positioning
    // For production, use a proper t-SNE library like tsne-js
    const matrix = embeddings.map(e => e.vector);
    const n = matrix.length;

    // Calculate pairwise distances
    const distances = [];
    for (let i = 0; i < n; i++) {
      distances[i] = [];
      for (let j = 0; j < n; j++) {
        if (i === j) {
          distances[i][j] = 0;
        } else {
          let sum = 0;
          for (let k = 0; k < matrix[i].length; k++) {
            sum += Math.pow(matrix[i][k] - matrix[j][k], 2);
          }
          distances[i][j] = Math.sqrt(sum);
        }
      }
    }

    // Simple 2D projection based on distances (MDS-like)
    const positions = [];
    for (let i = 0; i < n; i++) {
      // Use first point as reference
      const angle = (i / n) * 2 * Math.PI;
      const avgDist = distances[i].reduce((a, b) => a + b, 0) / n;
      const radius = avgDist * 5; // Scale for visualization
      
      positions.push({
        x: Math.cos(angle) * radius,
        y: Math.sin(angle) * radius,
        ...embeddings[i]
      });
    }

    return positions;
  };

  // Prepare data for visualization
  const visualizationData = useMemo(() => {
    if (!queryEmbedding) return { query: null, matches: [] };

    // Combine all embeddings
    const allEmbeddings = [
      { vector: queryEmbedding, label: queryLabel, type: 'query', id: 'query' },
      ...matchedEmbeddings.map((emb, idx) => ({
        vector: emb.embedding || emb.vector || emb,
        label: emb.name || emb.label || `Match ${idx + 1}`,
        similarity: emb.similarity || 0,
        type: emb.isTopMatch ? 'topMatch' : 'other',
        id: emb.id || `match-${idx}`
      }))
    ];

    // Apply dimensionality reduction
    const reduced = reductionMethod === 'PCA' 
      ? performPCA(allEmbeddings)
      : performTSNE(allEmbeddings);

    // Separate query and matches
    const query = reduced[0];
    const matches = reduced.slice(1);

    return { query, matches };
  }, [queryEmbedding, matchedEmbeddings, queryLabel, reductionMethod]);

  // Custom tooltip
  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div className="embedding-tooltip">
          <div className="tooltip-header">
            <span className={`tooltip-badge ${data.type}`}>
              {data.type === 'query' ? '🔍 Query' : 
               data.type === 'topMatch' ? '⭐ Top Match' : '👤 Criminal'}
            </span>
          </div>
          <div className="tooltip-content">
            <strong>{data.label}</strong>
            {data.similarity !== undefined && (
              <div className="tooltip-similarity">
                Similarity: <span>{(data.similarity * 100).toFixed(1)}%</span>
              </div>
            )}
            <div className="tooltip-coords">
              Position: ({data.x.toFixed(2)}, {data.y.toFixed(2)})
            </div>
          </div>
        </div>
      );
    }
    return null;
  };

  // Custom dot renderer
  const CustomDot = (props) => {
    const { cx, cy, payload } = props;
    
    let fill, stroke, radius;
    
    if (payload.type === 'query') {
      fill = '#06b6d4'; // Forensic accent (cyan)
      stroke = '#22d3ee';
      radius = 8;
    } else if (payload.type === 'topMatch') {
      fill = '#22c55e'; // Success green
      stroke = '#4ade80';
      radius = 7;
    } else {
      fill = '#64748b'; // Gray
      stroke = '#94a3b8';
      radius = 5;
    }

    const isHovered = hoveredPoint === payload.id;
    
    return (
      <g>
        {/* Glow effect */}
        <circle
          cx={cx}
          cy={cy}
          r={radius + 4}
          fill={fill}
          opacity={isHovered ? 0.3 : 0.1}
          className="dot-glow"
        />
        {/* Main dot */}
        <circle
          cx={cx}
          cy={cy}
          r={isHovered ? radius + 2 : radius}
          fill={fill}
          stroke={stroke}
          strokeWidth={2}
          className="dot-main"
          style={{ 
            cursor: 'pointer',
            transition: 'all 0.2s ease'
          }}
        />
        {/* Center highlight */}
        <circle
          cx={cx}
          cy={cy}
          r={radius / 2}
          fill="white"
          opacity={0.5}
        />
      </g>
    );
  };

  if (!queryEmbedding) {
    return (
      <div className="embedding-space-placeholder">
        <div className="placeholder-icon">🌌</div>
        <p>No embedding data available</p>
        <span className="placeholder-hint">Upload and compare faces to see embedding space</span>
      </div>
    );
  }

  const allPoints = visualizationData.query 
    ? [visualizationData.query, ...visualizationData.matches]
    : visualizationData.matches;

  return (
    <div className="embedding-space-visualization">
      <div className="embedding-header">
        <div className="embedding-title-section">
          <h4 className="embedding-title">
            <span className="embedding-icon">🌌</span>
            Embedding Space Visualization
          </h4>
          <span className="embedding-method-badge">{reductionMethod}</span>
        </div>
        <div className="embedding-legend">
          <div className="legend-item query">
            <div className="legend-dot"></div>
            <span>Query Face</span>
          </div>
          <div className="legend-item top-match">
            <div className="legend-dot"></div>
            <span>Top Match</span>
          </div>
          <div className="legend-item other">
            <div className="legend-dot"></div>
            <span>Other Criminals</span>
          </div>
        </div>
      </div>

      <div className="embedding-description">
        <p>
          Face embeddings projected into 2D space using {reductionMethod}. 
          Closer points indicate higher facial similarity.
        </p>
      </div>

      <div className="embedding-chart-container">
        <ResponsiveContainer width="100%" height={400}>
          <ScatterChart
            margin={{ top: 20, right: 30, bottom: 20, left: 30 }}
          >
            <CartesianGrid 
              strokeDasharray="3 3" 
              stroke="rgba(255, 255, 255, 0.1)"
            />
            <XAxis 
              type="number" 
              dataKey="x" 
              name="Component 1"
              stroke="var(--forensic-gray-400)"
              tick={{ fill: 'var(--forensic-gray-400)', fontSize: 12 }}
              label={{ 
                value: 'Principal Component 1', 
                position: 'insideBottom', 
                offset: -10,
                fill: 'var(--forensic-gray-300)'
              }}
            />
            <YAxis 
              type="number" 
              dataKey="y" 
              name="Component 2"
              stroke="var(--forensic-gray-400)"
              tick={{ fill: 'var(--forensic-gray-400)', fontSize: 12 }}
              label={{ 
                value: 'Principal Component 2', 
                angle: -90, 
                position: 'insideLeft',
                fill: 'var(--forensic-gray-300)'
              }}
            />
            <ZAxis range={[100, 400]} />
            <Tooltip 
              content={<CustomTooltip />}
              cursor={{ strokeDasharray: '3 3' }}
            />
            <Scatter
              data={allPoints}
              shape={<CustomDot />}
              onMouseEnter={(data) => setHoveredPoint(data.id)}
              onMouseLeave={() => setHoveredPoint(null)}
            />
          </ScatterChart>
        </ResponsiveContainer>
      </div>

      <div className="embedding-stats">
        <div className="stat-item">
          <span className="stat-label">Total Points</span>
          <span className="stat-value">{allPoints.length}</span>
        </div>
        <div className="stat-item">
          <span className="stat-label">Dimensions</span>
          <span className="stat-value">
            {queryEmbedding.length} → 2
          </span>
        </div>
        <div className="stat-item">
          <span className="stat-label">Method</span>
          <span className="stat-value">{reductionMethod}</span>
        </div>
      </div>

      <div className="embedding-note">
        <svg className="note-icon" viewBox="0 0 24 24" fill="currentColor">
          <path d="M13,9H11V7H13M13,17H11V11H13M12,2A10,10 0 0,0 2,12A10,10 0 0,0 12,22A10,10 0 0,0 22,12A10,10 0 0,0 12,2Z"/>
        </svg>
        <p>
          Embeddings are high-dimensional vectors (typically 128-512 dimensions) 
          reduced to 2D for visualization. Distance between points represents similarity.
        </p>
      </div>
    </div>
  );
};

EmbeddingSpaceVisualization.propTypes = {
  queryEmbedding: PropTypes.arrayOf(PropTypes.number),
  matchedEmbeddings: PropTypes.arrayOf(
    PropTypes.shape({
      embedding: PropTypes.arrayOf(PropTypes.number),
      vector: PropTypes.arrayOf(PropTypes.number),
      name: PropTypes.string,
      label: PropTypes.string,
      similarity: PropTypes.number,
      isTopMatch: PropTypes.bool,
      id: PropTypes.string
    })
  ),
  queryLabel: PropTypes.string,
  reductionMethod: PropTypes.oneOf(['PCA', 't-SNE'])
};

export default EmbeddingSpaceVisualization;
