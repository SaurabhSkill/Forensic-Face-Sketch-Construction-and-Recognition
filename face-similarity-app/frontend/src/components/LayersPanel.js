/**
 * LayersPanel.js — Layer management panel.
 *
 * Phase 2 upgrades:
 *  - Z-index badge on each row
 *  - "↑ Fwd" / "↓ Back" buttons use useLayerManager (z-index swap) instead of array reorder
 *  - Keeps visibility, lock, duplicate, delete
 */
import React from 'react';

const S = {
  panel: { color: '#111827', flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0 },
  title: {
    margin: '12px 0 8px', fontWeight: 600, fontSize: 15,
    color: '#111827', borderBottom: '1px solid #e5e7eb', paddingBottom: 6,
  },
  list: { display: 'flex', flexDirection: 'column', gap: 4, flex: 1, overflowY: 'auto', paddingRight: 2 },
  item: (active, locked) => ({
    display: 'flex', alignItems: 'center', gap: 5,
    padding: '5px 6px', border: `1px solid ${active ? '#3b82f6' : '#e5e7eb'}`,
    borderRadius: 6, background: active ? '#eff6ff' : '#fff',
    cursor: 'pointer', opacity: locked ? 0.65 : 1,
  }),
  thumb: {
    width: 26, height: 26, border: '1px solid #e5e7eb', borderRadius: 4,
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    background: '#fff', flexShrink: 0,
  },
  name: {
    fontSize: 11, color: '#475569', flex: 1,
    overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
  },
  zBadge: {
    fontSize: 9, color: '#94a3b8', background: '#f1f5f9',
    border: '1px solid #e2e8f0', borderRadius: 3,
    padding: '1px 4px', flexShrink: 0, fontFamily: 'monospace',
  },
  iconBtn: {
    padding: '2px 4px', border: '1px solid #e5e7eb', background: '#fff',
    borderRadius: 4, cursor: 'pointer', fontSize: 11, lineHeight: 1,
    color: '#475569', whiteSpace: 'nowrap',
  },
};

function LayersPanel({
  components,
  selectedId,
  onSelect,
  onToggleVisibility,
  onToggleLock,
  onDelete,
  onDuplicate,
  // Phase 2: z-index operations
  onBringForward,
  onSendBackward,
}) {
  // Display sorted by zIndex descending (top layer first)
  const sorted = [...components].sort((a, b) => (b.zIndex || 0) - (a.zIndex || 0));

  return (
    <aside style={S.panel}>
      <div style={S.title}>
        Layers{' '}
        <span style={{ fontSize: 11, color: '#94a3b8', fontWeight: 400 }}>
          ({components.length})
        </span>
      </div>

      <div style={S.list}>
        {components.length === 0 && (
          <p style={{ fontSize: 12, color: '#94a3b8', margin: 0 }}>No elements yet.</p>
        )}

        {sorted.map((c) => {
          const isActive = selectedId === c.id;
          return (
            <div
              key={c.id}
              style={S.item(isActive, c.locked)}
              onClick={() => onSelect && onSelect(c.id)}
            >
              {/* Thumbnail */}
              <div style={S.thumb}>
                <img
                  src={c.imagePath}
                  alt=""
                  style={{ maxWidth: '100%', maxHeight: '100%', objectFit: 'contain' }}
                />
              </div>

              {/* Name */}
              <span style={S.name} title={c.category}>
                {c.category || 'Layer'}
              </span>

              {/* Z-index badge */}
              <span style={S.zBadge} title="z-index">z{c.zIndex || 1}</span>

              {/* Actions */}
              <div style={{ display: 'flex', gap: 2 }} onClick={e => e.stopPropagation()}>
                <button
                  style={S.iconBtn}
                  title="Bring Forward"
                  onClick={() => onBringForward && onBringForward(c.id)}
                >↑</button>
                <button
                  style={S.iconBtn}
                  title="Send Backward"
                  onClick={() => onSendBackward && onSendBackward(c.id)}
                >↓</button>
                <button
                  style={S.iconBtn}
                  title={c.hidden ? 'Show' : 'Hide'}
                  onClick={() => onToggleVisibility && onToggleVisibility(c.id)}
                >
                  {c.hidden ? '🙈' : '👁'}
                </button>
                <button
                  style={S.iconBtn}
                  title={c.locked ? 'Unlock' : 'Lock'}
                  onClick={() => onToggleLock && onToggleLock(c.id)}
                >
                  {c.locked ? '🔒' : '🔓'}
                </button>
                <button
                  style={S.iconBtn}
                  title="Duplicate"
                  onClick={() => onDuplicate && onDuplicate(c.id)}
                >⧉</button>
                <button
                  style={{ ...S.iconBtn, color: '#ef4444', borderColor: '#fca5a5' }}
                  title="Delete"
                  onClick={() => onDelete && onDelete(c.id)}
                >✕</button>
              </div>
            </div>
          );
        })}
      </div>
    </aside>
  );
}

export default LayersPanel;
