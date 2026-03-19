/**
 * ControlsPanel.js — Precision transform controls for selected element.
 *
 * New in Phase 2:
 *  - Aspect ratio lock toggle
 *  - Z-index controls: Bring Forward / Send Backward / Bring to Front / Send to Back
 *  - Element selector dropdown (select any element by name even if hidden behind others)
 */
import React from 'react';

const S = {
  panel: { color: '#111827', marginBottom: 16 },
  title: {
    margin: '12px 0 8px', fontWeight: 600, fontSize: 15,
    color: '#111827', borderBottom: '1px solid #e5e7eb', paddingBottom: 6,
  },
  row: { display: 'grid', gridTemplateColumns: '72px 1fr', alignItems: 'center', gap: 8, marginBottom: 8 },
  label: { fontSize: 12, color: '#475569', fontWeight: 500 },
  input: {
    width: '100%', padding: '4px 8px', border: '1px solid #cbd5e1',
    borderRadius: 5, fontSize: 13, color: '#111827', background: '#fff',
    boxSizing: 'border-box',
  },
  slider: { width: '100%', accentColor: '#3b82f6' },
  btn: (color) => ({
    flex: 1, padding: '5px 0', border: `1px solid ${color}`,
    borderRadius: 5, background: '#fff', color, cursor: 'pointer',
    fontSize: 12, fontWeight: 500,
  }),
  deleteBtn: {
    width: '100%', padding: '6px 0', marginTop: 8,
    border: '1px solid #ef4444', borderRadius: 5,
    background: '#fef2f2', color: '#ef4444',
    cursor: 'pointer', fontSize: 13, fontWeight: 600,
  },
  emptyNote: { color: '#64748b', fontSize: 13, marginTop: 4 },
  zBtn: {
    flex: 1, padding: '4px 0', border: '1px solid #cbd5e1',
    borderRadius: 5, background: '#fff', color: '#374151',
    cursor: 'pointer', fontSize: 11, fontWeight: 500,
  },
  select: {
    width: '100%', padding: '5px 8px', border: '1px solid #cbd5e1',
    borderRadius: 5, fontSize: 13, color: '#111827', background: '#fff',
    marginBottom: 10, boxSizing: 'border-box',
  },
};

function Row({ label, children }) {
  return (
    <div style={S.row}>
      <span style={S.label}>{label}</span>
      {children}
    </div>
  );
}

function ControlsPanel({
  selectedComponent,
  updateComponentProps,
  onDelete,
  templateEnabled,
  setTemplateEnabled,
  templateOpacity,
  setTemplateOpacity,
  showGuides,
  setShowGuides,
  snapEnabled,
  setSnapEnabled,
  // Phase 2 props
  lockAspect,
  setLockAspect,
  onBringForward,
  onSendBackward,
  onBringToFront,
  onSendToBack,
  allElements,
  onSelectElement,
}) {
  const num = (field) => (e) => {
    if (!selectedComponent) return;
    updateComponentProps(selectedComponent.id, { [field]: Number(e.target.value) });
  };

  // ── Canvas options section (always visible) ────────────────────────────────
  const templateSection = (
    <>
      <div style={S.title}>Canvas Options</div>

      <Row label="Template">
        <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13 }}>
          <input type="checkbox" checked={!!templateEnabled}
            onChange={e => setTemplateEnabled && setTemplateEnabled(e.target.checked)} />
          Show face outline
        </label>
      </Row>

      {templateEnabled && (
        <Row label="Opacity">
          <input type="range" min={0} max={1} step={0.05}
            value={templateOpacity ?? 0.25} style={S.slider}
            onChange={e => setTemplateOpacity && setTemplateOpacity(Number(e.target.value))} />
        </Row>
      )}

      <Row label="Guides">
        <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13 }}>
          <input type="checkbox" checked={!!showGuides}
            onChange={e => setShowGuides && setShowGuides(e.target.checked)} />
          Show guide lines
        </label>
      </Row>

      <Row label="Snap">
        <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13 }}>
          <input type="checkbox" checked={!!snapEnabled}
            onChange={e => setSnapEnabled && setSnapEnabled(e.target.checked)} />
          Snap to guides
        </label>
      </Row>
    </>
  );

  // ── Element selector dropdown ──────────────────────────────────────────────
  const elementSelector = allElements && allElements.length > 0 && (
    <>
      <div style={S.title}>Select Element</div>
      <select
        style={S.select}
        value={selectedComponent?.id || ''}
        onChange={e => onSelectElement && onSelectElement(e.target.value)}
      >
        <option value="">— Select element —</option>
        {[...allElements]
          .sort((a, b) => (b.zIndex || 0) - (a.zIndex || 0))
          .map((el, i) => (
            <option key={el.id} value={el.id}>
              {el.category || 'element'} {i + 1}
              {el.hidden ? ' (hidden)' : ''}
              {el.locked ? ' 🔒' : ''}
            </option>
          ))}
      </select>
    </>
  );

  if (!selectedComponent) {
    return (
      <aside style={S.panel}>
        <div style={S.title}>Controls</div>
        <p style={S.emptyNote}>Select an element to edit its properties.</p>
        {elementSelector}
        {templateSection}
      </aside>
    );
  }

  const c = selectedComponent;

  return (
    <aside style={S.panel}>
      {/* Element selector */}
      {elementSelector}

      {/* Preview */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
        <div style={{
          width: 40, height: 40, border: '1px solid #e5e7eb', borderRadius: 6,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          background: '#fff', flexShrink: 0,
        }}>
          <img src={c.imagePath} alt="preview"
            style={{ maxWidth: '100%', maxHeight: '100%', objectFit: 'contain' }} />
        </div>
        <div>
          <div style={{ fontSize: 12, fontWeight: 600, color: '#111827', textTransform: 'capitalize' }}>
            {c.category || 'element'}
          </div>
          <span style={{ fontSize: 10, color: '#94a3b8', fontFamily: 'monospace' }}>#{c.id.slice(-6)}</span>
        </div>
        {c.locked && <span style={{ fontSize: 11, color: '#f59e0b', marginLeft: 'auto' }}>🔒 Locked</span>}
      </div>

      {/* Z-index controls */}
      <div style={S.title}>Layer Order</div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: 4, marginBottom: 8 }}>
        <button style={S.zBtn} title="Bring to Front" onClick={() => onBringToFront && onBringToFront(c.id)}>⤒ Front</button>
        <button style={S.zBtn} title="Bring Forward"  onClick={() => onBringForward  && onBringForward(c.id)}>↑ Fwd</button>
        <button style={S.zBtn} title="Send Backward"  onClick={() => onSendBackward  && onSendBackward(c.id)}>↓ Back</button>
        <button style={S.zBtn} title="Send to Back"   onClick={() => onSendToBack    && onSendToBack(c.id)}>⤓ Back</button>
      </div>
      <div style={{ fontSize: 11, color: '#94a3b8', marginBottom: 8 }}>
        z-index: {c.zIndex || 1}
      </div>

      {/* Position */}
      <div style={S.title}>Position</div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 8 }}>
        <div>
          <div style={{ ...S.label, marginBottom: 3 }}>X</div>
          <input type="number" value={Math.round(c.x)} style={S.input}
            onChange={num('x')} disabled={c.locked} />
        </div>
        <div>
          <div style={{ ...S.label, marginBottom: 3 }}>Y</div>
          <input type="number" value={Math.round(c.y)} style={S.input}
            onChange={num('y')} disabled={c.locked} />
        </div>
      </div>

      {/* Size + aspect ratio lock */}
      <div style={S.title}>Size</div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 6 }}>
        <div>
          <div style={{ ...S.label, marginBottom: 3 }}>Width</div>
          <input type="number" min={20} max={720} value={Math.round(c.width)} style={S.input}
            onChange={num('width')} disabled={c.locked} />
        </div>
        <div>
          <div style={{ ...S.label, marginBottom: 3 }}>Height</div>
          <input type="number" min={20} max={540} value={Math.round(c.height || c.width)} style={S.input}
            onChange={num('height')} disabled={c.locked} />
        </div>
      </div>
      <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, color: '#475569', marginBottom: 8 }}>
        <input
          type="checkbox"
          checked={!!lockAspect}
          onChange={e => setLockAspect && setLockAspect(e.target.checked)}
        />
        Lock aspect ratio
      </label>

      {/* Rotation */}
      <div style={S.title}>Rotation</div>
      <Row label={`${c.rotation || 0}°`}>
        <input type="range" min={-180} max={180} value={c.rotation || 0}
          style={S.slider} disabled={c.locked}
          onChange={e => updateComponentProps(c.id, { rotation: Number(e.target.value) })} />
      </Row>

      {/* Opacity */}
      <div style={S.title}>Opacity</div>
      <Row label={`${Math.round((c.opacity !== undefined ? c.opacity : 1) * 100)}%`}>
        <input type="range" min={0} max={1} step={0.01}
          value={c.opacity !== undefined ? c.opacity : 1}
          style={S.slider} disabled={c.locked}
          onChange={e => updateComponentProps(c.id, { opacity: Number(e.target.value) })} />
      </Row>

      {/* Flip */}
      <div style={S.title}>Flip</div>
      <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
        <button style={S.btn('#475569')} disabled={c.locked}
          onClick={() => updateComponentProps(c.id, { flipH: !c.flipH })}>
          ↔ Horizontal
        </button>
        <button style={S.btn('#475569')} disabled={c.locked}
          onClick={() => updateComponentProps(c.id, { flipV: !c.flipV })}>
          ↕ Vertical
        </button>
      </div>

      {/* Delete */}
      <button style={S.deleteBtn} onClick={() => onDelete && onDelete(c.id)}>
        🗑 Delete Element
      </button>

      {/* Canvas options */}
      {templateSection}
    </aside>
  );
}

export default ControlsPanel;
