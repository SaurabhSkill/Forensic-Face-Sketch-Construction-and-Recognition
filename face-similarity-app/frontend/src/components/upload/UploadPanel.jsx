import React from 'react';
import PropTypes from 'prop-types';

const UploadPanel = ({ 
  sketchFile, 
  photoFile, 
  onSketchChange, 
  onPhotoChange, 
  onCompare, 
  loading,
  showPhotoUpload = true 
}) => {
  return (
    <div className="upload-section">
      <div className="upload-area">
        <h3>Upload Sketch</h3>
        <input 
          type="file" 
          accept="image/*" 
          onChange={onSketchChange}
          className="file-input"
          id="sketch-upload"
        />
        <label htmlFor="sketch-upload" className="file-label">
          {sketchFile ? sketchFile.name : 'Choose Sketch File'}
        </label>
      </div>
      
      {showPhotoUpload && (
        <div className="upload-area">
          <h3>Upload Photo</h3>
          <input 
            type="file" 
            accept="image/*" 
            onChange={onPhotoChange}
            className="file-input"
            id="photo-upload"
          />
          <label htmlFor="photo-upload" className="file-label">
            {photoFile ? photoFile.name : 'Choose Photo File'}
          </label>
        </div>
      )}
      
      {onCompare && (
        <button
          className="forensic-btn-primary compare-button"
          onClick={onCompare}
          disabled={!sketchFile || (showPhotoUpload && !photoFile) || loading}
        >
          {loading ? 'Analyzing...' : 'Compare Faces'}
        </button>
      )}
    </div>
  );
};

UploadPanel.propTypes = {
  sketchFile: PropTypes.object,
  photoFile: PropTypes.object,
  onSketchChange: PropTypes.func.isRequired,
  onPhotoChange: PropTypes.func,
  onCompare: PropTypes.func,
  loading: PropTypes.bool,
  showPhotoUpload: PropTypes.bool
};

export default UploadPanel;
