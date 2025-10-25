import React from 'react';

function LayersPanel({ components, selectedId, onSelect, onToggleVisibility, onToggleLock, onDelete, onDuplicate, onReorder }) {
  const panelStyle = {
    color: '#111827',
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    minHeight: 0
  };

  const titleStyle = { margin: '12px 0 8px', fontWeight: 600, fontSize: '16px' };

  const itemStyle = (active) => ({
    display: 'grid',
    gridTemplateColumns: '1fr auto',
    alignItems: 'center',
    gap: '8px',
    padding: '6px 8px',
    border: '1px solid #e5e7eb',
    borderRadius: '6px',
    background: active ? '#eff6ff' : '#fff',
    cursor: 'pointer'
  });

  const actionsStyle = { display: 'flex', gap: '6px' };

  const btn = {
    padding: '2px 6px',
    border: '1px solid #e5e7eb',
    background: '#fff',
    borderRadius: '4px',
    cursor: 'pointer'
  };

  const move = (index, dir) => {
    const newIndex = index + dir;
    if (newIndex < 0 || newIndex >= components.length) return;
    onReorder(index, newIndex);
  };

  return (
    <aside style={panelStyle}>
      <div style={titleStyle}>Layers</div>
      <div style={{ 
        display: 'grid', 
        gap: '8px', 
        flex: 1, 
        overflowY: 'auto',
        paddingRight: '4px'
      }}>
        {components.map((c, index) => (
          <div key={c.id} style={itemStyle(selectedId === c.id)} onClick={() => onSelect && onSelect(c.id)}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <div style={{ width: '28px', height: '28px', border: '1px solid #e5e7eb', borderRadius: '4px', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#fff' }}>
                <img src={c.imagePath} alt="thumb" style={{ maxWidth: '100%', maxHeight: '100%' }} />
              </div>
              <div style={{ fontSize: '12px', color: '#475569' }}>{c.category || 'Layer'} {index + 1}</div>
            </div>
            <div style={actionsStyle} onClick={(e) => e.stopPropagation()}>
              <button style={btn} title="Move Up" onClick={() => move(index, -1)}>▲</button>
              <button style={btn} title="Move Down" onClick={() => move(index, 1)}>▼</button>
              <button style={btn} title="Toggle Visibility" onClick={() => onToggleVisibility && onToggleVisibility(c.id)}>{c.hidden ? '🙈' : '👁️'}</button>
              <button style={btn} title="Toggle Lock" onClick={() => onToggleLock && onToggleLock(c.id)}>{c.locked ? '🔒' : '🔓'}</button>
              <button style={btn} title="Duplicate" onClick={() => onDuplicate && onDuplicate(c.id)}>⧉</button>
              <button style={btn} title="Delete" onClick={() => onDelete && onDelete(c.id)}>✕</button>
            </div>
          </div>
        ))}
      </div>
    </aside>
  );
}

export default LayersPanel;


