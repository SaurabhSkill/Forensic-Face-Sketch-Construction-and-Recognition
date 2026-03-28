import React, { useState } from 'react';
import SearchResultsGrid from '../components/search/SearchResultsGrid';
import CriminalDetailModal from '../components/CriminalDetailModal';
import SearchScanningAnimation from '../components/SearchScanningAnimation';
import { apiService } from '../services/apiService';
import PageContainer from '../layout/PageContainer';

const SearchPage = () => {
  const [sketchFile, setSketchFile] = useState(null);
  const [criminalMatches, setCriminalMatches] = useState([]);
  const [searchLoading, setSearchLoading] = useState(false);
  const [isSearching, setIsSearching] = useState(false);
  const [searchProgress, setSearchProgress] = useState(0);
  const [selectedSearchCriminal, setSelectedSearchCriminal] = useState(null);
  const [showSearchDetailModal, setShowSearchDetailModal] = useState(false);

  const handleSketchChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setSketchFile(e.target.files[0]);
    }
  };

  const searchCriminals = async () => {
    let progressInterval = null;
    
    try {
      if (!sketchFile) {
        alert('Please select a sketch to search.');
        return;
      }
      
      setSearchLoading(true);
      setIsSearching(true);
      setSearchProgress(0);

      // Simulate search progress
      progressInterval = setInterval(() => {
        setSearchProgress(prev => {
          if (prev >= 90) {
            clearInterval(progressInterval);
            return 90;
          }
          return prev + Math.random() * 15;
        });
      }, 200);

      const response = await apiService.searchCriminals(sketchFile);

      // Complete the progress
      clearInterval(progressInterval);
      setSearchProgress(100);

      // Small delay to show 100% completion
      setTimeout(() => {
        console.log('[SearchPage] API response:', response);
        console.log('[SearchPage] matches[0] sample:', response.matches?.[0]);
        setCriminalMatches(response.matches || []);
        setIsSearching(false);
        setSearchLoading(false);
      }, 500);

    } catch (error) {
      console.error('Error searching criminals:', error);
      
      // Clear progress and show error
      if (progressInterval) {
        clearInterval(progressInterval);
      }
      setIsSearching(false);
      setSearchLoading(false);
      
      alert('Failed to search criminals. Check console for details.');
    }
  };

  const handleViewDetails = (criminal) => {
    setSelectedSearchCriminal(criminal);
    setShowSearchDetailModal(true);
  };

  return (
    <>
      {/* Search Scanning Animation */}
      {isSearching && (
        <SearchScanningAnimation 
          isScanning={isSearching} 
          progress={searchProgress} 
        />
      )}
      
      <PageContainer variant="default">
        <div className="tab-content">
          <h2 className="section-title">Sketch Search</h2>
          <div className="search-container">
            <div className="upload-section">
              <div className="upload-area">
                <h3>Upload Sketch to Search</h3>
                <input 
                  type="file" 
                  accept="image/*" 
                  onChange={handleSketchChange}
                  className="file-input"
                  id="search-sketch-upload"
                />
                <label htmlFor="search-sketch-upload" className="file-label">
                  {sketchFile ? sketchFile.name : 'Choose Sketch File'}
                </label>
              </div>
            </div>
            
            <button
              className="forensic-btn-primary search-button"
              onClick={searchCriminals}
              disabled={!sketchFile || searchLoading}
            >
              {searchLoading ? 'Searching...' : 'Search Criminals'}
            </button>

            <SearchResultsGrid 
              matches={criminalMatches}
              onViewDetails={handleViewDetails}
            />
          </div>

          {showSearchDetailModal && selectedSearchCriminal && (
            <CriminalDetailModal
              criminal={selectedSearchCriminal}
              onClose={() => {
                setShowSearchDetailModal(false);
                setSelectedSearchCriminal(null);
              }}
            />
          )}
        </div>
      </PageContainer>
    </>
  );
};

export default SearchPage;
