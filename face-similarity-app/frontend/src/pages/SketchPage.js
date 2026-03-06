import React from 'react';
import SketchCanvas from '../components/SketchCanvas';

function SketchPage() {
  return (
    <div className="sketch-page" style={{ padding: '16px' }}>
      <div style={{ marginBottom: '12px', textAlign: 'center' }}>
        <div style={{ fontWeight: 600, fontSize: '1.5rem', color: 'var(--forensic-accent)' }}>Forensic Sketch Tool</div>
      </div>
      <SketchCanvas />
    </div>
  );
}

export default SketchPage;


