import React from 'react';
import UploadPanel from '../components/upload/UploadPanel';
import ForensicReport from '../components/forensic/ForensicReport';
import ForensicScanningAnimation from '../components/ForensicScanningAnimation';
import { useFaceComparison } from '../hooks/useFaceComparison';
import PageContainer from '../layout/PageContainer';

const ComparePage = () => {
  const {
    sketchFile,
    photoFile,
    similarityScore,
    loading,
    isScanning,
    scanningProgress,
    handleSketchChange,
    handlePhotoChange,
    handleCompare
  } = useFaceComparison();

  return (
    <>
      {/* Forensic Scanning Animation */}
      {isScanning && (
        <ForensicScanningAnimation 
          isScanning={isScanning} 
          progress={scanningProgress} 
        />
      )}
      
      <PageContainer variant="default">
        <div className="tab-content">
          <h2 className="section-title">Facial Recognition Tool</h2>
          <div className="comparison-container">
            <UploadPanel
              sketchFile={sketchFile}
              photoFile={photoFile}
              onSketchChange={handleSketchChange}
              onPhotoChange={handlePhotoChange}
              onCompare={handleCompare}
              loading={loading}
              showPhotoUpload={true}
            />
            
            <ForensicReport 
              similarityScore={similarityScore}
              photoFile={photoFile}
            />
          </div>
        </div>
      </PageContainer>
    </>
  );
};

export default ComparePage;
