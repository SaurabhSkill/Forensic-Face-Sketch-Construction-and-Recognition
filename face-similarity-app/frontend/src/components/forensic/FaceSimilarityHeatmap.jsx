import React, { useEffect, useRef, useState } from 'react';
import PropTypes from 'prop-types';
import './FaceSimilarityHeatmap.css';

const FaceSimilarityHeatmap = ({ imageUrl, regionScores, overallScore }) => {
  const canvasRef = useRef(null);
  const imageRef = useRef(null);
  const [imageLoaded, setImageLoaded] = useState(false);
  const [hoveredRegion, setHoveredRegion] = useState(null);

  // Get color based on similarity score (0-100)
  const getColorForScore = (score) => {
    if (score >= 80) {
      // High similarity: Red to Orange
      const intensity = (score - 80) / 20; // 0 to 1
      return {
        r: 255,
        g: Math.round(69 + (165 - 69) * (1 - intensity)), // 69 to 165
        b: 0,
        a: 0.6
      };
    } else if (score >= 50) {
      // Medium similarity: Yellow to Orange
      const intensity = (score - 50) / 30; // 0 to 1
      return {
        r: 255,
        g: Math.round(215 - (215 - 165) * intensity), // 215 to 165
        b: 0,
        a: 0.5
      };
    } else {
      // Low similarity: Blue to Cyan
      const intensity = score / 50; // 0 to 1
      return {
        r: Math.round(0 + 100 * intensity),
        g: Math.round(191 + (255 - 191) * intensity),
        b: 255,
        a: 0.4
      };
    }
  };

  // Define face regions as percentages of face dimensions
  const faceRegions = {
    eyes: {
      x: 0.15, // 15% from left
      y: 0.25, // 25% from top
      width: 0.7, // 70% of face width
      height: 0.2, // 20% of face height
      label: 'Eyes Region'
    },
    nose: {
      x: 0.35,
      y: 0.4,
      width: 0.3,
      height: 0.25,
      label: 'Nose Region'
    },
    mouth: {
      x: 0.25,
      y: 0.65,
      width: 0.5,
      height: 0.2,
      label: 'Mouth Region'
    },
    fullFace: {
      x: 0.1,
      y: 0.1,
      width: 0.8,
      height: 0.8,
      label: 'Full Face'
    }
  };

  const drawHeatmap = () => {
    const canvas = canvasRef.current;
    const image = imageRef.current;

    if (!canvas || !image || !imageLoaded) return;

    const ctx = canvas.getContext('2d');
    
    // Set canvas size to match image
    canvas.width = image.width;
    canvas.height = image.height;

    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Draw semi-transparent overlay for each region
    const regions = [
      { key: 'fullFace', score: overallScore || 0 },
      { key: 'eyes', score: regionScores?.eyes || 0 },
      { key: 'nose', score: regionScores?.nose || 0 },
      { key: 'mouth', score: regionScores?.mouth || 0 }
    ];

    // Draw full face first (as background)
    const fullFaceRegion = regions.find(r => r.key === 'fullFace');
    if (fullFaceRegion && fullFaceRegion.score > 0) {
      const region = faceRegions.fullFace;
      const color = getColorForScore(fullFaceRegion.score);
      
      ctx.fillStyle = `rgba(${color.r}, ${color.g}, ${color.b}, ${color.a * 0.3})`;
      ctx.fillRect(
        canvas.width * region.x,
        canvas.height * region.y,
        canvas.width * region.width,
        canvas.height * region.height
      );
    }

    // Draw specific regions on top
    regions.filter(r => r.key !== 'fullFace' && r.score > 0).forEach(({ key, score }) => {
      const region = faceRegions[key];
      const color = getColorForScore(score);

      // Create gradient for smoother appearance
      const x = canvas.width * region.x;
      const y = canvas.height * region.y;
      const width = canvas.width * region.width;
      const height = canvas.height * region.height;

      const gradient = ctx.createRadialGradient(
        x + width / 2,
        y + height / 2,
        0,
        x + width / 2,
        y + height / 2,
        Math.max(width, height) / 2
      );

      gradient.addColorStop(0, `rgba(${color.r}, ${color.g}, ${color.b}, ${color.a})`);
      gradient.addColorStop(0.7, `rgba(${color.r}, ${color.g}, ${color.b}, ${color.a * 0.5})`);
      gradient.addColorStop(1, `rgba(${color.r}, ${color.g}, ${color.b}, 0)`);

      ctx.fillStyle = gradient;
      ctx.fillRect(x, y, width, height);

      // Draw border if region is hovered
      if (hoveredRegion === key) {
        ctx.strokeStyle = `rgba(${color.r}, ${color.g}, ${color.b}, 1)`;
        ctx.lineWidth = 3;
        ctx.strokeRect(x, y, width, height);
      }
    });
  };

  useEffect(() => {
    if (imageLoaded) {
      drawHeatmap();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [imageLoaded, regionScores, overallScore, hoveredRegion]);

  const handleImageLoad = () => {
    setImageLoaded(true);
  };

  const handleCanvasHover = (e) => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    const x = (e.clientX - rect.left) / rect.width;
    const y = (e.clientY - rect.top) / rect.height;

    // Check which region is being hovered
    let foundRegion = null;
    for (const [key, region] of Object.entries(faceRegions)) {
      if (key === 'fullFace') continue; // Skip full face for hover
      
      if (
        x >= region.x &&
        x <= region.x + region.width &&
        y >= region.y &&
        y <= region.y + region.height
      ) {
        foundRegion = key;
        break;
      }
    }

    setHoveredRegion(foundRegion);
  };

  const handleCanvasLeave = () => {
    setHoveredRegion(null);
  };

  if (!imageUrl) {
    return (
      <div className="heatmap-placeholder">
        <div className="placeholder-icon">🔥</div>
        <p>Upload images to see similarity heatmap</p>
      </div>
    );
  }

  return (
    <div className="face-similarity-heatmap">
      <div className="heatmap-header">
        <h4 className="heatmap-title">
          <span className="heatmap-icon">🔥</span>
          Facial Similarity Heatmap
        </h4>
        <div className="heatmap-legend">
          <div className="legend-item">
            <div className="legend-color high"></div>
            <span>High (80-100%)</span>
          </div>
          <div className="legend-item">
            <div className="legend-color medium"></div>
            <span>Medium (50-79%)</span>
          </div>
          <div className="legend-item">
            <div className="legend-color low"></div>
            <span>Low (0-49%)</span>
          </div>
        </div>
      </div>

      <div className="heatmap-container">
        <div className="heatmap-image-wrapper">
          <img
            ref={imageRef}
            src={imageUrl}
            alt="Reference face"
            className="heatmap-base-image"
            onLoad={handleImageLoad}
            crossOrigin="anonymous"
          />
          <canvas
            ref={canvasRef}
            className="heatmap-overlay"
            onMouseMove={handleCanvasHover}
            onMouseLeave={handleCanvasLeave}
          />
        </div>

        {hoveredRegion && (
          <div className="heatmap-tooltip">
            <strong>{faceRegions[hoveredRegion].label}</strong>
            <span className="tooltip-score">
              {Math.round(regionScores?.[hoveredRegion] || 0)}% similarity
            </span>
          </div>
        )}
      </div>

      <div className="heatmap-scores">
        <div className="score-item">
          <span className="score-label">👁️ Eyes</span>
          <div className="score-bar-container">
            <div 
              className="score-bar eyes"
              style={{ width: `${regionScores?.eyes || 0}%` }}
            ></div>
          </div>
          <span className="score-value">{Math.round(regionScores?.eyes || 0)}%</span>
        </div>

        <div className="score-item">
          <span className="score-label">👃 Nose</span>
          <div className="score-bar-container">
            <div 
              className="score-bar nose"
              style={{ width: `${regionScores?.nose || 0}%` }}
            ></div>
          </div>
          <span className="score-value">{Math.round(regionScores?.nose || 0)}%</span>
        </div>

        <div className="score-item">
          <span className="score-label">👄 Mouth</span>
          <div className="score-bar-container">
            <div 
              className="score-bar mouth"
              style={{ width: `${regionScores?.mouth || 0}%` }}
            ></div>
          </div>
          <span className="score-value">{Math.round(regionScores?.mouth || 0)}%</span>
        </div>

        <div className="score-item overall">
          <span className="score-label">🎯 Overall</span>
          <div className="score-bar-container">
            <div 
              className="score-bar overall"
              style={{ width: `${overallScore || 0}%` }}
            ></div>
          </div>
          <span className="score-value">{Math.round(overallScore || 0)}%</span>
        </div>
      </div>
    </div>
  );
};

FaceSimilarityHeatmap.propTypes = {
  imageUrl: PropTypes.string,
  regionScores: PropTypes.shape({
    eyes: PropTypes.number,
    nose: PropTypes.number,
    mouth: PropTypes.number
  }),
  overallScore: PropTypes.number
};

export default FaceSimilarityHeatmap;
