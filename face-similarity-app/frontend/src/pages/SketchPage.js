import React from 'react';
import { Link } from 'react-router-dom';
import SketchCanvas from '../components/SketchCanvas';

function SketchPage() {
  return (
    <div className="sketch-page" style={{ padding: '16px' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
        <Link to="/" style={{
          textDecoration: 'none',
          color: '#111827',
          border: '1px solid #e5e7eb',
          padding: '6px 10px',
          borderRadius: '6px',
          background: '#fff'
        }}>← Back to Home</Link>
        <div style={{ fontWeight: 600 }}>Forensic Sketch Tool</div>
        <div />
      </div>
      <SketchCanvas />
    </div>
  );
}

export default SketchPage;


