/**
 * SketchCanvas.js — Main orchestrator for the forensic sketch tool.
 *
 * Phase 2 additions:
 *  - useLayerManager  → z-index operations (bringForward, sendBackward, bringToFront, sendToBack)
 *  - lockAspect state → passed to Canvas + ControlsPanel
 *  - TAB key          → cycle selection through all visible, unlocked elements
 *  - Element dropdown → allElements + onSelectElement wired to ControlsPanel
 *  - Layer z-index ops wired to both ControlsPanel and LayersPanel
 *
 * Keyboard shortcuts:
 *  Ctrl+Z        → Undo
 *  Ctrl+Y        → Redo
 *  Delete        → Remove selected element
 *  Arrow keys    → Move selected element 1px
 *  Shift+Arrow   → Move 10px
 *  TAB           → Cycle selection through elements
 */
import React, { useCallback, useEffect, useRef, useState } from 'react';
import html2canvas from 'html2canvas';
import ComponentLibrary from './ComponentLibrary';
import Canvas from './Canvas';
import ControlsPanel from './ControlsPanel';
import LayersPanel from './LayersPanel';
import { useCanvasHistory } from '../hooks/useCanvasHistory';
import { useSnapGuides, CANVAS_W, CANVAS_H } from '../hooks/useSnapGuides';
import { useLayerManager } from '../hooks/useLayerManager';

// ── Auto-placement defaults per category ─────────────────────────────────────
const AUTO_PLACE = {
  eyes:     { xRatio: 0.5, yRatio: 0.30, wRatio: 0.40 },
  eyebrows: { xRatio: 0.5, yRatio: 0.22, wRatio: 0.40 },
  nose:     { xRatio: 0.5, yRatio: 0.50, wRatio: 0.22 },
  lips:     { xRatio: 0.5, yRatio: 0.68, wRatio: 0.28 },
  mustach:  { xRatio: 0.5, yRatio: 0.62, wRatio: 0.24 },
  hair:     { xRatio: 0.5, yRatio: 0.05, wRatio: 0.60 },
  head:     { xRatio: 0.5, yRatio: 0.40, wRatio: 0.55 },
  more:     { xRatio: 0.5, yRatio: 0.50, wRatio: 0.20 },
};

function getCategory(imagePath) {
  const lower = imagePath.toLowerCase();
  for (const key of Object.keys(AUTO_PLACE)) {
    if (lower.includes(`/${key}/`)) return key;
  }
  return null;
}

function autoPosition(imagePath) {
  const cat = getCategory(imagePath);
  const d = AUTO_PLACE[cat] || { xRatio: 0.5, yRatio: 0.5, wRatio: 0.25 };
  const w = Math.round(CANVAS_W * d.wRatio);
  const h = w;
  const x = Math.round(CANVAS_W * d.xRatio - w / 2);
  const y = Math.round(CANVAS_H * d.yRatio - h / 2);
  return { x, y, width: w, height: h };
}

// ── Export resolution presets ─────────────────────────────────────────────────
const EXPORT_SCALES = { low: 1, medium: 1.5, high: 2 };

// ── Toolbar button style ──────────────────────────────────────────────────────
const tbBtn = (color = '#111827', disabled = false) => ({
  padding: '6px 12px',
  background: disabled ? '#e5e7eb' : color,
  color: disabled ? '#9ca3af' : '#fff',
  border: 'none', borderRadius: 6,
  cursor: disabled ? 'not-allowed' : 'pointer',
  fontSize: 13, fontWeight: 500, whiteSpace: 'nowrap',
});

// ─────────────────────────────────────────────────────────────────────────────
function SketchCanvas() {
  const { elements, canUndo, canRedo, checkpoint, patch, set, undo, redo } = useCanvasHistory([]);
  const [selectedId, setSelectedId]         = useState(null);
  const [templateEnabled, setTemplateEnabled] = useState(true);
  const [templateOpacity, setTemplateOpacity] = useState(0.25);
  const [showGuides, setShowGuides]           = useState(true);
  const [snapEnabled, setSnapEnabled]         = useState(true);
  const [exportScale, setExportScale]         = useState('medium');
  const [exportedImage, setExportedImage]     = useState(null);
  const [lockAspect, setLockAspect]           = useState(false);

  const canvasRef = useRef(null);
  const arrowCommitTimer = useRef(null);
  const arrowActive = useRef(false); // tracks whether a checkpoint was taken for this key sequence
  const { activeGuides, snapPosition, clearActiveGuides } = useSnapGuides(snapEnabled);

  // ── Layer manager — wraps set() so operations push to history ─────────────
  const setElementsAndCommit = useCallback((newEls) => set(newEls), [set]);
  const { bringToFront, sendToBack, bringForward, sendBackward } =
    useLayerManager(elements, setElementsAndCommit);

  // ── Helpers ────────────────────────────────────────────────────────────────
  const selectedEl = elements.find(e => e.id === selectedId) || null;

  const commit = useCallback((newEls) => set(newEls), [set]);

  /** Called at gesture start — saves "before" snapshot into history */
  const checkpointEl = useCallback(() => checkpoint(), [checkpoint]);

  /** Live update during drag — no history entry */
  const patchEl = useCallback((id, updates) => {
    patch(elements.map(e => e.id === id ? { ...e, ...updates } : e));
  }, [elements, patch]);

  /** Discrete commit — for panel inputs, flip, opacity, etc. */
  const updateEl = useCallback((id, updates) => {
    set(elements.map(e => e.id === id ? { ...e, ...updates } : e));
  }, [elements, set]);

  // ── Add element from library ───────────────────────────────────────────────
  const handleSelectComponent = useCallback((imagePath) => {
    const pos = autoPosition(imagePath);
    const cat = getCategory(imagePath);
    const newEl = {
      id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
      imagePath,
      category: cat || 'element',
      x: pos.x, y: pos.y,
      width: pos.width, height: pos.height,
      rotation: 0, opacity: 1,
      flipH: false, flipV: false,
      hidden: false, locked: false,
      zIndex: elements.length + 1,
    };
    commit([...elements, newEl]);
    setSelectedId(newEl.id);
  }, [elements, commit]);

  // ── Element operations ─────────────────────────────────────────────────────
  const deleteEl = useCallback((id) => {
    commit(elements.filter(e => e.id !== id));
    if (selectedId === id) setSelectedId(null);
  }, [elements, commit, selectedId]);

  const toggleVisibility = useCallback((id) => {
    commit(elements.map(e => e.id === id ? { ...e, hidden: !e.hidden } : e));
  }, [elements, commit]);

  const toggleLock = useCallback((id) => {
    commit(elements.map(e => e.id === id ? { ...e, locked: !e.locked } : e));
  }, [elements, commit]);

  const duplicateEl = useCallback((id) => {
    const target = elements.find(e => e.id === id);
    if (!target) return;
    const clone = {
      ...target,
      id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
      x: target.x + 12, y: target.y + 12,
      zIndex: elements.length + 1,
    };
    commit([...elements, clone]);
    setSelectedId(clone.id);
  }, [elements, commit]);

  // ── Keyboard shortcuts ─────────────────────────────────────────────────────
  useEffect(() => {
    const onKey = (e) => {
      const tag = document.activeElement?.tagName;
      const isInput = tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT';

      // Undo / Redo (always intercept)
      if ((e.ctrlKey || e.metaKey) && e.key === 'z') { e.preventDefault(); undo(); return; }
      if ((e.ctrlKey || e.metaKey) && (e.key === 'y' || (e.shiftKey && e.key === 'z'))) {
        e.preventDefault(); redo(); return;
      }

      if (isInput) return;

      // TAB — cycle selection through visible, unlocked elements
      if (e.key === 'Tab') {
        e.preventDefault();
        const selectable = elements.filter(el => !el.hidden);
        if (selectable.length === 0) return;
        const currentIdx = selectable.findIndex(el => el.id === selectedId);
        const nextIdx = e.shiftKey
          ? (currentIdx - 1 + selectable.length) % selectable.length
          : (currentIdx + 1) % selectable.length;
        setSelectedId(selectable[nextIdx].id);
        return;
      }

      // Delete selected
      if ((e.key === 'Delete' || e.key === 'Backspace') && selectedId) {
        e.preventDefault();
        deleteEl(selectedId);
        return;
      }

      // Arrow key nudge — checkpoint once, patch during repeat, set on idle
      if (selectedId && ['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(e.key)) {
        e.preventDefault();
        const step = e.shiftKey ? 10 : 1;
        const el = elements.find(x => x.id === selectedId);
        if (!el || el.locked) return;
        const dx = e.key === 'ArrowLeft' ? -step : e.key === 'ArrowRight' ? step : 0;
        const dy = e.key === 'ArrowUp'   ? -step : e.key === 'ArrowDown'  ? step : 0;
        const nx = Math.max(0, Math.min(el.x + dx, CANVAS_W - el.width));
        const ny = Math.max(0, Math.min(el.y + dy, CANVAS_H - el.height));

        // Take checkpoint only on the first keydown of a sequence
        if (!arrowActive.current) {
          checkpoint();
          arrowActive.current = true;
        }

        // Patch silently during key-repeat
        patch(elements.map(e2 => e2.id === selectedId ? { ...e2, x: nx, y: ny } : e2));

        // Debounce: commit final position 400ms after last keypress
        clearTimeout(arrowCommitTimer.current);
        arrowCommitTimer.current = setTimeout(() => {
          // Use set() to replace the patched present with a clean SET
          // (no extra history push — checkpoint already captured the before-state)
          // We just need to ensure future is cleared; patch already did that via CHECKPOINT.
          // Actually we just leave it — the PATCH is the final state, undo goes to CHECKPOINT.
          arrowActive.current = false;
        }, 400);
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [selectedId, elements, undo, redo, deleteEl, updateEl]);

  // ── Export ─────────────────────────────────────────────────────────────────
  const doExport = useCallback(async (download = false, format = 'png') => {
    if (!canvasRef.current) return;
    const scale = EXPORT_SCALES[exportScale] || 1.5;
    try {
      const canvas = await html2canvas(canvasRef.current, {
        backgroundColor: '#ffffff',
        scale,
        useCORS: true,
        logging: false,
        removeContainer: true,
        ignoreElements: (el) => el.dataset?.exportIgnore === 'true',
      });
      const mime = format === 'jpg' ? 'image/jpeg' : 'image/png';
      const dataUrl = canvas.toDataURL(mime, format === 'jpg' ? 0.92 : undefined);
      canvas.width = 0; canvas.height = 0;

      if (download) {
        const link = document.createElement('a');
        link.href = dataUrl;
        link.download = `forensic-sketch.${format}`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
      } else {
        setExportedImage(dataUrl);
      }
    } catch (err) {
      console.error('Export failed:', err);
      alert('Export failed. Please try again.');
    }
  }, [exportScale]);

  // ── Layout styles ──────────────────────────────────────────────────────────
  const containerStyle = {
    display: 'grid',
    gridTemplateColumns: '260px 1fr 300px',
    gap: 16,
    width: '100%',
    height: 'calc(100vh - 140px)',
    border: '1px solid #e5e7eb',
    borderRadius: 12,
    padding: 16,
    background: '#fafafa',
    color: '#111827',
    boxSizing: 'border-box',
    overflow: 'hidden',
  };

  const colStyle = (border) => ({
    display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden',
    ...(border === 'right' ? { borderRight: '1px solid #e5e7eb', paddingRight: 12 } : {}),
    ...(border === 'left'  ? { borderLeft:  '1px solid #e5e7eb', paddingLeft:  12 } : {}),
  });

  const sectionTitle = { fontWeight: 600, fontSize: 14, color: '#111827', marginBottom: 8 };

  return (
    <div style={{ color: '#111827', padding: 16, height: '100vh', background: '#f8fafc', overflow: 'hidden' }}>

      {/* ── Top toolbar ── */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12, flexWrap: 'wrap' }}>
        <span style={{ fontWeight: 700, fontSize: 20, color: '#111827', marginRight: 8 }}>
          Forensic Sketch Tool
        </span>

        <button style={tbBtn('#374151', !canUndo)} onClick={undo} disabled={!canUndo} title="Undo (Ctrl+Z)">
          ↩ Undo
        </button>
        <button style={tbBtn('#374151', !canRedo)} onClick={redo} disabled={!canRedo} title="Redo (Ctrl+Y)">
          ↪ Redo
        </button>

        <div style={{ width: 1, height: 24, background: '#e5e7eb', margin: '0 4px' }} />

        <select
          value={exportScale}
          onChange={e => setExportScale(e.target.value)}
          style={{
            padding: '5px 8px', border: '1px solid #cbd5e1', borderRadius: 6,
            fontSize: 13, color: '#111827', background: '#fff',
          }}
        >
          <option value="low">Low res (1×)</option>
          <option value="medium">Medium res (1.5×)</option>
          <option value="high">High res (2×)</option>
        </select>

        <button style={tbBtn('#111827')} onClick={() => doExport(false)}>Preview</button>
        <button style={tbBtn('#16a34a')} onClick={() => doExport(true, 'jpg')}>⬇ JPEG</button>
        <button style={tbBtn('#2563eb')} onClick={() => doExport(true, 'png')}>⬇ PNG</button>

        <span style={{ fontSize: 11, color: '#94a3b8', marginLeft: 'auto' }}>
          Del · Arrows · Ctrl+Z/Y · TAB=cycle
        </span>
      </div>

      {/* ── Main 3-column layout ── */}
      <div style={containerStyle}>

        {/* LEFT — Component Library (unchanged) */}
        <aside style={colStyle('right')}>
          <div style={sectionTitle}>Component Library</div>
          <ComponentLibrary onSelectComponent={handleSelectComponent} />
        </aside>

        {/* CENTER — Canvas */}
        <main style={colStyle()}>
          <div style={sectionTitle}>Canvas</div>
          <Canvas
            placedComponents={elements}
            selectedComponentId={selectedId}
            handleSelectForEditing={setSelectedId}
            updateComponentProps={updateEl}
            liveUpdateComponentProps={patchEl}
            onCheckpoint={checkpointEl}
            canvasRef={canvasRef}
            templateEnabled={templateEnabled}
            templateOpacity={templateOpacity}
            showGuides={showGuides}
            activeGuides={activeGuides}
            snapPosition={snapEnabled ? snapPosition : null}
            onDeselect={() => { setSelectedId(null); clearActiveGuides(); }}
            lockAspect={lockAspect}
          />

          {exportedImage && (
            <div style={{ marginTop: 10 }}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 6 }}>Export Preview</div>
              <img src={exportedImage} alt="Export preview"
                style={{ maxWidth: '100%', border: '1px solid #e5e7eb', borderRadius: 6 }} />
            </div>
          )}
        </main>

        {/* RIGHT — Controls + Layers */}
        <aside style={{ ...colStyle('left'), overflowY: 'auto' }}>
          <ControlsPanel
            selectedComponent={selectedEl}
            updateComponentProps={updateEl}
            onDelete={deleteEl}
            templateEnabled={templateEnabled}
            setTemplateEnabled={setTemplateEnabled}
            templateOpacity={templateOpacity}
            setTemplateOpacity={setTemplateOpacity}
            showGuides={showGuides}
            setShowGuides={setShowGuides}
            snapEnabled={snapEnabled}
            setSnapEnabled={setSnapEnabled}
            lockAspect={lockAspect}
            setLockAspect={setLockAspect}
            onBringForward={bringForward}
            onSendBackward={sendBackward}
            onBringToFront={bringToFront}
            onSendToBack={sendToBack}
            allElements={elements}
            onSelectElement={setSelectedId}
          />
          <LayersPanel
            components={elements}
            selectedId={selectedId}
            onSelect={setSelectedId}
            onToggleVisibility={toggleVisibility}
            onToggleLock={toggleLock}
            onDelete={deleteEl}
            onDuplicate={duplicateEl}
            onBringForward={bringForward}
            onSendBackward={sendBackward}
          />
        </aside>

      </div>
    </div>
  );
}

export default SketchCanvas;
