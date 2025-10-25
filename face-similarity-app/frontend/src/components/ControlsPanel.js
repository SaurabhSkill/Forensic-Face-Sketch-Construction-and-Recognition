import React from 'react';

function ControlsPanel({ selectedComponent, updateComponentProps, templateEnabled, setTemplateEnabled, templateOpacity, setTemplateOpacity }) {
  const panelStyle = {
    color: '#111827',
    marginBottom: '16px'
  };

  const sectionTitle = {
    margin: '12px 0 8px',
    fontWeight: 600,
    fontSize: '16px'
  };

  const rowStyle = {
    display: 'grid',
    gridTemplateColumns: '80px 1fr',
    alignItems: 'center',
    gap: '8px',
    marginBottom: '8px'
  };

  if (!selectedComponent) {
    return (
      <aside style={panelStyle}>
        <div style={sectionTitle}>Controls</div>
        <div style={{ color: '#64748b', fontSize: '14px' }}>Select a component to edit.</div>
        <div style={sectionTitle}>Template</div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr auto', alignItems: 'center', gap: '8px' }}>
          <label>Show Template</label>
          <input type="checkbox" checked={templateEnabled} onChange={(e) => setTemplateEnabled && setTemplateEnabled(e.target.checked)} />
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr auto', alignItems: 'center', gap: '8px', marginTop: '8px' }}>
          <label>Opacity</label>
          <input type="number" min={0} max={1} step={0.05} value={templateOpacity ?? 0.25} onChange={(e) => setTemplateOpacity && setTemplateOpacity(Number(e.target.value))} />
        </div>
      </aside>
    );
  }

  const handleNumber = (field) => (e) => {
    const value = Number(e.target.value);
    updateComponentProps && updateComponentProps(selectedComponent.id, { [field]: value });
  };

  return (
    <aside style={panelStyle}>
      <div style={sectionTitle}>Controls</div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
        <div style={{
          width: '40px', height: '40px', border: '1px solid #e5e7eb', borderRadius: '6px',
          display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#fff'
        }}>
          <img src={selectedComponent.imagePath} alt="preview" style={{ maxWidth: '100%', maxHeight: '100%' }} />
        </div>
        <div style={{ fontSize: '12px', color: '#475569' }}>{selectedComponent.id.slice(-6)}</div>
      </div>

      <div style={sectionTitle}>Transform</div>

      <div style={rowStyle}>
        <label>X</label>
        <input type="number" value={selectedComponent.x} onChange={handleNumber('x')} />
      </div>
      <div style={rowStyle}>
        <label>Y</label>
        <input type="number" value={selectedComponent.y} onChange={handleNumber('y')} />
      </div>
      <div style={rowStyle}>
        <label>Width</label>
        <input type="number" min={20} max={1000} value={selectedComponent.width} onChange={handleNumber('width')} />
      </div>
      <div style={rowStyle}>
        <label>Rotation</label>
        <input type="number" min={-180} max={180} value={selectedComponent.rotation} onChange={handleNumber('rotation')} />
      </div>

      <div style={sectionTitle}>Template</div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr auto', alignItems: 'center', gap: '8px' }}>
        <label>Show Template</label>
        <input type="checkbox" checked={templateEnabled} onChange={(e) => setTemplateEnabled && setTemplateEnabled(e.target.checked)} />
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr auto', alignItems: 'center', gap: '8px', marginTop: '8px' }}>
        <label>Opacity</label>
        <input type="number" min={0} max={1} step={0.05} value={templateOpacity ?? 0.25} onChange={(e) => setTemplateOpacity && setTemplateOpacity(Number(e.target.value))} />
      </div>
    </aside>
  );
}

export default ControlsPanel;


