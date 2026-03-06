import { useState } from 'react';
import { apiService } from '../services/apiService';

export const useFaceComparison = () => {
  const [sketchFile, setSketchFile] = useState(null);
  const [photoFile, setPhotoFile] = useState(null);
  const [similarityScore, setSimilarityScore] = useState(null);
  const [loading, setLoading] = useState(false);
  const [scanningProgress, setScanningProgress] = useState(0);
  const [isScanning, setIsScanning] = useState(false);

  const handleSketchChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setSketchFile(e.target.files[0]);
    }
  };

  const handlePhotoChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setPhotoFile(e.target.files[0]);
    }
  };

  const handleCompare = async () => {
    let progressInterval = null;
    
    try {
      if (!sketchFile || !photoFile) {
        alert('Please select both a sketch and a photo.');
        return;
      }
      
      setLoading(true);
      setIsScanning(true);
      setScanningProgress(0);

      // Simulate scanning progress
      progressInterval = setInterval(() => {
        setScanningProgress(prev => {
          if (prev >= 90) {
            clearInterval(progressInterval);
            return 90;
          }
          return prev + Math.random() * 15;
        });
      }, 200);

      const response = await apiService.compareFaces(sketchFile, photoFile);

      // Complete the progress
      clearInterval(progressInterval);
      setScanningProgress(100);

      // Small delay to show 100% completion
      setTimeout(() => {
        if (response) {
          setSimilarityScore(response);
        } else {
          alert('Unexpected response from server.');
        }
        setIsScanning(false);
        setLoading(false);
      }, 500);

    } catch (error) {
      console.error('Compare error:', error);
      
      // Clear progress and show error
      if (progressInterval) {
        clearInterval(progressInterval);
      }
      setIsScanning(false);
      setLoading(false);
      
      // More detailed error message
      let errorMessage = 'Failed to compare faces. ';
      if (error.code === 'ECONNABORTED') {
        errorMessage += 'Request timed out. The server might be overloaded.';
      } else if (error.response) {
        errorMessage += `Server error: ${error.response.status}`;
        if (error.response.data && error.response.data.error) {
          errorMessage += ` - ${error.response.data.error}`;
        }
      } else if (error.request) {
        errorMessage += 'Cannot connect to server. Make sure the backend is running.';
      } else {
        errorMessage += error.message;
      }
      
      alert(errorMessage);
    }
  };

  return {
    sketchFile,
    photoFile,
    similarityScore,
    loading,
    scanningProgress,
    isScanning,
    handleSketchChange,
    handlePhotoChange,
    handleCompare
  };
};
