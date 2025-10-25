import React from 'react';

function SearchScanningAnimation({ isScanning, progress = 0 }) {
  const searchSteps = [
    "Initializing criminal database search...",
    "Processing sketch features...",
    "Extracting facial landmarks...",
    "Comparing against criminal database...",
    "Analyzing similarity patterns...",
    "Ranking potential matches...",
    "Finalizing search results..."
  ];

  const currentStep = Math.floor((progress / 100) * searchSteps.length);
  const currentStepText = searchSteps[Math.min(currentStep, searchSteps.length - 1)];

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      background: 'rgba(0, 0, 0, 0.8)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 9999,
      backdropFilter: 'blur(4px)'
    }}>
      <div style={{
        background: 'linear-gradient(135deg, #1a2a3a 0%, #0f1b2e 100%)',
        borderRadius: '16px',
        padding: '2rem',
        maxWidth: '500px',
        width: '90%',
        textAlign: 'center',
        border: '2px solid #ff6b35',
        boxShadow: '0 20px 40px rgba(0, 0, 0, 0.3)'
      }}>
        {/* Search Icon */}
        <div style={{
          width: '80px',
          height: '80px',
          margin: '0 auto 1.5rem',
          position: 'relative',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center'
        }}>
          {/* Outer rotating ring */}
          <div style={{
            position: 'absolute',
            width: '80px',
            height: '80px',
            border: '3px solid transparent',
            borderTop: '3px solid #ff6b35',
            borderRadius: '50%',
            animation: 'spin 1s linear infinite'
          }}></div>
          
          {/* Inner pulsing circle */}
          <div style={{
            width: '40px',
            height: '40px',
            background: 'radial-gradient(circle, #ff6b35 0%, #f7931e 100%)',
            borderRadius: '50%',
            animation: 'pulse 1.5s ease-in-out infinite'
          }}></div>
          
          {/* Search magnifying glass */}
          <div style={{
            position: 'absolute',
            width: '20px',
            height: '20px',
            border: '2px solid #ff6b35',
            borderRadius: '50%',
            borderRight: 'none',
            borderBottom: 'none',
            transform: 'rotate(-45deg)',
            animation: 'searchPulse 2s ease-in-out infinite'
          }}></div>
          
          {/* Search handle */}
          <div style={{
            position: 'absolute',
            width: '2px',
            height: '15px',
            background: '#ff6b35',
            transform: 'rotate(45deg) translate(8px, 8px)',
            animation: 'searchPulse 2s ease-in-out infinite'
          }}></div>
        </div>

        {/* Title */}
        <h3 style={{
          color: '#ffffff',
          fontSize: '1.5rem',
          marginBottom: '1rem',
          fontWeight: '600'
        }}>
          Searching Criminal Database
        </h3>

        {/* Current Step */}
        <div style={{
          color: '#ff6b35',
          fontSize: '1rem',
          marginBottom: '1.5rem',
          minHeight: '1.2rem'
        }}>
          {currentStepText}
        </div>

        {/* Progress Bar */}
        <div style={{
          width: '100%',
          height: '8px',
          background: 'rgba(255, 255, 255, 0.1)',
          borderRadius: '4px',
          overflow: 'hidden',
          marginBottom: '1rem'
        }}>
          <div style={{
            width: `${progress}%`,
            height: '100%',
            background: 'linear-gradient(90deg, #ff6b35, #f7931e)',
            borderRadius: '4px',
            transition: 'width 0.3s ease',
            position: 'relative'
          }}>
            {/* Shimmer effect */}
            <div style={{
              position: 'absolute',
              top: 0,
              left: '-100%',
              width: '100%',
              height: '100%',
              background: 'linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.4), transparent)',
              animation: 'shimmer 2s infinite'
            }}></div>
          </div>
        </div>

        {/* Progress Percentage */}
        <div style={{
          color: '#a0aec0',
          fontSize: '0.9rem'
        }}>
          {Math.round(progress)}% Complete
        </div>

        {/* Search dots */}
        <div style={{
          display: 'flex',
          justifyContent: 'center',
          gap: '8px',
          marginTop: '1rem'
        }}>
          {[0, 1, 2].map((i) => (
            <div
              key={i}
              style={{
                width: '8px',
                height: '8px',
                background: '#ff6b35',
                borderRadius: '50%',
                animation: `bounce 1.4s ease-in-out infinite both`,
                animationDelay: `${i * 0.16}s`
              }}
            ></div>
          ))}
        </div>
      </div>

      {/* CSS Animations */}
      <style jsx>{`
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
        
        @keyframes pulse {
          0%, 100% { transform: scale(1); opacity: 1; }
          50% { transform: scale(1.1); opacity: 0.8; }
        }
        
        @keyframes searchPulse {
          0%, 100% { transform: rotate(-45deg) scale(1); opacity: 1; }
          50% { transform: rotate(-45deg) scale(1.1); opacity: 0.7; }
        }
        
        @keyframes shimmer {
          0% { left: -100%; }
          100% { left: 100%; }
        }
        
        @keyframes bounce {
          0%, 80%, 100% { transform: scale(0); }
          40% { transform: scale(1); }
        }
      `}</style>
    </div>
  );
}

export default SearchScanningAnimation;
