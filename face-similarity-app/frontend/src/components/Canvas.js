import React from 'react';
import Draggable from 'react-draggable';

function Canvas({ placedComponents, updateComponentPosition, selectedComponentId, handleSelectForEditing, updateComponentProps, canvasRef, templateEnabled, templateOpacity, templateImage }) {
  const canvasStyle = {
    flex: 1,
    minHeight: '360px',
    background: 'repeating-conic-gradient(#f3f4f6 0% 25%, #ffffff 0% 50%) 50% / 16px 16px',
    border: '1px dashed #cbd5e1',
    borderRadius: '8px',
    position: 'relative',
    overflow: 'hidden',
    backgroundColor: '#f8fafc',
    color: '#111827'
  };

  const nodeRefs = React.useRef({});

  const artboardWrapperStyle = {
    width: '100%',
    height: '100%',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '12px'
  };

  const artboardStyle = {
    position: 'relative',
    width: '720px',
    height: '540px',
    backgroundImage:
      'linear-gradient(#ffffff, #ffffff), linear-gradient(90deg, rgba(148,163,184,0.15) 1px, transparent 1px), linear-gradient(rgba(148,163,184,0.15) 1px, transparent 1px)',
    backgroundSize: '100% 100%, 24px 24px, 24px 24px',
    backgroundPosition: '0 0, 0 0, 0 0',
    backgroundColor: '#ffffff',
    borderRadius: '8px',
    boxShadow: '0 10px 24px rgba(0,0,0,0.08)',
    overflow: 'hidden'
  };

  return (
    <div style={canvasStyle}>
      {(!placedComponents || placedComponents.length === 0) && (
        <div style={{
          position: 'absolute',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          color: '#64748b'
        }}>
          Placeholder Canvas Area
        </div>
      )}

      <div style={artboardWrapperStyle}>
        <div style={artboardStyle} ref={canvasRef}>
          {templateEnabled && (
            <img
              src={templateImage || 'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="720" height="540"><rect width="100%" height="100%" fill="white"/><g stroke="black" stroke-width="1" opacity="0.3"><circle cx="360" cy="220" r="120" fill="none"/></g></svg>'}
              alt="template"
              style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', objectFit: 'contain', opacity: templateOpacity ?? 0.25, pointerEvents: 'none' }}
            />
          )}

          {placedComponents && placedComponents.map((comp, index) => {
        if (comp.hidden) return null;
        if (!nodeRefs.current[comp.id]) {
          nodeRefs.current[comp.id] = React.createRef();
        }
        const ref = nodeRefs.current[comp.id];
        return (
          <Draggable
            key={comp.id}
            disabled={!!comp.locked}
            nodeRef={ref}
            defaultPosition={{ x: comp.x, y: comp.y }}
            onStop={(e, data) => updateComponentPosition && updateComponentPosition(comp.id, data.x, data.y)}
          >
            <div
              ref={ref}
              onClick={() => handleSelectForEditing && handleSelectForEditing(comp.id)}
              style={{
                position: 'absolute',
                transform: `rotate(${comp.rotation}deg)`,
                outline: selectedComponentId === comp.id ? '2px solid #3b82f6' : 'none',
                borderRadius: '4px',
                padding: selectedComponentId === comp.id ? '2px' : '0',
                zIndex: index + 1
              }}
            >
              <img src={comp.imagePath} alt="component" style={{ width: comp.width }} />

              {selectedComponentId === comp.id && (
                <div style={{
                  position: 'absolute',
                  top: '100%',
                  left: 0,
                  background: '#ffffff',
                  border: '1px solid #e5e7eb',
                  borderRadius: '6px',
                  padding: '8px',
                  marginTop: '6px',
                  boxShadow: '0 2px 6px rgba(0,0,0,0.08)',
                  display: 'flex',
                  gap: '8px',
                  alignItems: 'center'
                }} onClick={(e) => e.stopPropagation()}>
                  <label style={{ fontSize: '12px', color: '#334155' }}>W</label>
                  <input
                    type="number"
                    value={comp.width}
                    min={20}
                    max={600}
                    onChange={(e) => updateComponentProps && updateComponentProps(comp.id, { width: Number(e.target.value) })}
                    style={{ width: '70px' }}
                  />
                  <label style={{ fontSize: '12px', color: '#334155' }}>R</label>
                  <input
                    type="number"
                    value={comp.rotation}
                    min={-180}
                    max={180}
                    onChange={(e) => updateComponentProps && updateComponentProps(comp.id, { rotation: Number(e.target.value) })}
                    style={{ width: '70px' }}
                  />
                </div>
              )}
            </div>
          </Draggable>
        );
          })}
        </div>
      </div>
    </div>
  );
}

export default Canvas;


