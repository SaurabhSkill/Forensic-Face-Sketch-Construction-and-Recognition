import React from 'react';
import PropTypes from 'prop-types';
import { 
  SimilarityDistributionChart, 
  MatchScoreGaugeChart, 
  EmbeddingComparisonChart,
  EmbeddingSpaceVisualization
} from '../charts';
import './ForensicVisualizationPanel.css';

const ForensicVisualizationPanel = ({ similarityScore }) => {
  if (!similarityScore) return null;

  // Prepare embedding data if available
  const hasEmbeddingData = similarityScore.query_embedding || similarityScore.embeddings;
  const queryEmbedding = similarityScore.query_embedding;
  const matchedEmbeddings = similarityScore.matched_embeddings || [];

  return (
    <div className="forensic-visualization-panel">
      <div className="panel-header">
        <h2 className="panel-title">
          <span className="panel-icon">📈</span>
          Data Visualizations
        </h2>
        <p className="panel-subtitle">
          Interactive charts and graphs for comprehensive analysis
        </p>
      </div>

      <div className="visualizations-grid">
        {/* Row 1: Gauge Chart */}
        <div className="viz-item full-width">
          <MatchScoreGaugeChart similarityScore={similarityScore} />
        </div>

        {/* Row 2: Distribution and Comparison Charts */}
        <div className="viz-item">
          <SimilarityDistributionChart similarityScore={similarityScore} />
        </div>

        <div className="viz-item">
          <EmbeddingComparisonChart similarityScore={similarityScore} />
        </div>

        {/* Row 3: Embedding Space Visualization (if data available) */}
        {hasEmbeddingData && (
          <div className="viz-item full-width">
            <EmbeddingSpaceVisualization 
              queryEmbedding={queryEmbedding}
              matchedEmbeddings={matchedEmbeddings}
              queryLabel="Query Face"
              reductionMethod="PCA"
            />
          </div>
        )}
      </div>

      {/* Analysis Summary */}
      <div className="analysis-summary">
        <div className="summary-card">
          <div className="summary-icon">🎯</div>
          <div className="summary-content">
            <h4 className="summary-title">Key Insights</h4>
            <ul className="summary-list">
              <li>Multiple deep learning models analyzed for accuracy</li>
              <li>Geometric and embedding-based comparisons performed</li>
              <li>Regional facial feature analysis completed</li>
              <li>Confidence levels calculated across all metrics</li>
            </ul>
          </div>
        </div>

        <div className="summary-card">
          <div className="summary-icon">🔬</div>
          <div className="summary-content">
            <h4 className="summary-title">Analysis Methods</h4>
            <ul className="summary-list">
              <li><strong>InsightFace:</strong> State-of-the-art face recognition</li>
              <li><strong>Facenet:</strong> Neural network embeddings</li>
              <li><strong>Geometric:</strong> Facial landmark analysis</li>
              <li><strong>Fusion:</strong> Combined model consensus</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ForensicVisualizationPanel;


ForensicVisualizationPanel.propTypes = {
  similarityScore: PropTypes.object
};
