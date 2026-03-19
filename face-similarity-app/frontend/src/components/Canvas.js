/**
 * Canvas.js — Professional forensic sketch canvas
 *
 * Features:
 *  • Zoom + pan  (mouse-wheel zoom towards cursor, middle-mouse / space+drag pan)
 *  • 8 resize handles (N, S, E, W, NE, NW, SE, SW) — each axis independent
 *  • Rotate handle (top-center, mouse-driven)
 *  • Aspect-ratio lock toggle per element
 *  • TAB cycles selection through overlapping elements
 *  • Snap-to-guide with visual highlight
 *  • White artboard preserved for clean export
 *  • Guide overlay excluded from export via data-export-ignore
 */
import React, { useRef, useCallback, useEffect, useState } from 'react';
import { CANVAS_W, CANVAS_H, GUIDE_LINES } from '../hooks/useSnapGuides';
import { useCanvasTransform } from '../hooks/useCanvasTransform';

// ─────────────────────────────────────────────────────────────────────────────
// Guide overlay (pointer-events:none, excluded from export)
// ─────────────────────────────────────────────────────────────────────────────
function GuideOverlay({ showGuides, activeGuides }) {
  if (!showGuides) return null;

  const base = { position: 'absolute', pointerEvents: 'none', zIndex: 9000 };

  const lines = [
    {
      key: 'centerX',
      el: <div key="centerX" style={{ ...base, left: GUIDE_LINES.centerX.value, top: 0, width: 1, height: '100%',
        borderLeft: `1px dashed ${activeGuides.includes('centerX') ? '#ef4444' : 'rgba(59,130,246,0.55)'}` }} />,
      lbl: <span key="centerX-lbl" style={{ ...base, left: GUIDE_LINES.centerX.value + 4, top: 4, fontSize: 9, color: '#3b82f6' }}>Center</span>,
    },
    {
      key: 'eyeY',
      el: <div key="eyeY" style={{ ...base, top: GUIDE_LINES.eyeY.value, left: 0, height: 1, width: '100%',
        borderTop: `1px dashed ${activeGuides.includes('eyeY') ? '#ef4444' : 'rgba(16,185,129,0.55)'}` }} />,
      lbl: <span key="eyeY-lbl" style={{ ...base, top: GUIDE_LINES.eyeY.value + 3, left: 4, fontSize: 9, color: '#10b981' }}>Eye Line</span>,
    },
    {
      key: 'noseY',
      el: <div key="noseY" style={{ ...base, top: GUIDE_LINES.noseY.value, left: 0, height: 1, width: '100%',
        borderTop: `1px dashed ${activeGuides.includes('noseY') ? '#ef4444' : 'rgba(245,158,11,0.55)'}` }} />,
      lbl: <span key="noseY-lbl" style={{ ...base, top: GUIDE_LINES.noseY.value + 3, left: 4, fontSize: 9, color: '#f59e0b' }}>Nose Line</span>,
    },
    {
      key: 'mouthY',
      el: <div key="mouthY" style={{ ...base, top: GUIDE_LINES.mouthY.value, left: 0, height: 1, width: '100%',
        borderTop: `1px dashed ${activeGuides.includes('mouthY') ? '#ef4444' : 'rgba(139,92,246,0.55)'}` }} />,
      lbl: <span key="mouthY-lbl" style={{ ...base, top: GUIDE_LINES.mouthY.value + 3, left: 4, fontSize: 9, color: '#8b5cf6' }}>Mouth Line</span>,
    },
  ];

  return (
    <div data-export-ignore="true" style={{ position: 'absolute', inset: 0, pointerEvents: 'none', zIndex: 9000 }}>
      {lines.map(l => <React.Fragment key={l.key}>{l.el}{l.lbl}</React.Fragment>)}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// 8-handle resize + rotate element
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Handle descriptors: each defines which deltas to apply to x/y/w/h.
 * cursor: CSS cursor string
 * dx/dy/dw/dh: multipliers applied to pointer delta
 */
const HANDLES = [
  { id: 'n',  cursor: 'n-resize',  top: -5,  left: '50%', ml: -5,  dx: 0,  dy: 1,  dw: 0,  dh: -1 },
  { id: 's',  cursor: 's-resize',  bottom: -5, left: '50%', ml: -5, dx: 0,  dy: 0,  dw: 0,  dh: 1  },
  { id: 'e',  cursor: 'e-resize',  top: '50%', mt: -5, right: -5,  dx: 0,  dy: 0,  dw: 1,  dh: 0  },
  { id: 'w',  cursor: 'w-resize',  top: '50%', mt: -5, left: -5,   dx: 1,  dy: 0,  dw: -1, dh: 0  },
  { id: 'ne', cursor: 'ne-resize', top: -5,  right: -5,              dx: 0,  dy: 1,  dw: 1,  dh: -1 },
  { id: 'nw', cursor: 'nw-resize', top: -5,  left: -5,               dx: 1,  dy: 1,  dw: -1, dh: -1 },
  { id: 'se', cursor: 'se-resize', bottom: -5, right: -5,            dx: 0,  dy: 0,  dw: 1,  dh: 1  },
  { id: 'sw', cursor: 'sw-resize', bottom: -5, left: -5,             dx: 1,  dy: 0,  dw: -1, dh: 1  },
];

function handleStyle(h) {
  const s = {
    position: 'absolute',
    width: 10, height: 10,
    background: '#fff',
    border: '2px solid #3b82f6',
    borderRadius: h.id.length === 2 ? 2 : '50%', // corners = square, edges = circle
    cursor: h.cursor,
    zIndex: 9999,
    touchAction: 'none',
  };
  if (h.top    !== undefined) s.top    = h.top;
  if (h.bottom !== undefined) s.bottom = h.bottom;
  if (h.left   !== undefined) s.left   = h.left;
  if (h.right  !== undefined) s.right  = h.right;
  if (h.ml     !== undefined) s.marginLeft = h.ml;
  if (h.mt     !== undefined) s.marginTop  = h.mt;
  return s;
}

function PlacedElement({ comp, isSelected, onSelect, onLiveUpdate, onCommit, onCheckpoint, snapPosition, viewportScale, lockAspect }) {
  const elRef = useRef(null);
  const ps    = useRef(null);
  const raf   = useRef(null);

  // ── Drag body ──────────────────────────────────────────────────────────────
  const onBodyDown = useCallback((e) => {
    if (e.button !== 0 || comp.locked) return;
    e.stopPropagation();
    e.currentTarget.setPointerCapture(e.pointerId);
    onSelect(comp.id);
    onCheckpoint?.();   // snapshot "before" state into history
    ps.current = { type: 'drag', px: e.clientX, py: e.clientY, ox: comp.x, oy: comp.y };
  }, [comp, onSelect, onCheckpoint]);

  // ── Resize handle ──────────────────────────────────────────────────────────
  const onHandleDown = useCallback((e, handle) => {
    if (e.button !== 0) return;
    e.stopPropagation();
    e.currentTarget.setPointerCapture(e.pointerId);
    onCheckpoint?.();   // snapshot "before" state into history
    ps.current = {
      type: 'resize', handle,
      px: e.clientX, py: e.clientY,
      ox: comp.x, oy: comp.y,
      ow: comp.width, oh: comp.height,
    };
  }, [comp, onCheckpoint]);

  // ── Rotate handle ──────────────────────────────────────────────────────────
  const onRotateDown = useCallback((e) => {
    if (e.button !== 0) return;
    e.stopPropagation();
    e.currentTarget.setPointerCapture(e.pointerId);
    onCheckpoint?.();   // snapshot "before" state into history
    const rect = elRef.current.getBoundingClientRect();
    ps.current = {
      type: 'rotate',
      cx: rect.left + rect.width  / 2,
      cy: rect.top  + rect.height / 2,
    };
  }, [onCheckpoint]);

  // ── Pointer move — patch only, no history ─────────────────────────────────
  const onMove = useCallback((e) => {
    if (!ps.current) return;
    e.preventDefault();
    if (raf.current) cancelAnimationFrame(raf.current);

    raf.current = requestAnimationFrame(() => {
      const state = ps.current;
      if (!state) return;

      if (state.type === 'drag') {
        const dx = (e.clientX - state.px) / viewportScale;
        const dy = (e.clientY - state.py) / viewportScale;
        let nx = Math.max(0, Math.min(state.ox + dx, CANVAS_W - comp.width));
        let ny = Math.max(0, Math.min(state.oy + dy, CANVAS_H - comp.height));
        const snapped = snapPosition ? snapPosition(nx, ny, comp.width, comp.height) : { x: nx, y: ny };
        onLiveUpdate(comp.id, { x: snapped.x, y: snapped.y });

      } else if (state.type === 'resize') {
        const h = state.handle;
        const rawDx = (e.clientX - state.px) / viewportScale;
        const rawDy = (e.clientY - state.py) / viewportScale;
        let nw = Math.max(20, state.ow + rawDx * h.dw);
        let nh = Math.max(20, state.oh + rawDy * h.dh);
        // Aspect-ratio lock only applies to handles that move BOTH axes (corners).
        // Pure horizontal (E/W) or vertical (N/S) handles always scale one axis only.
        const isTwoAxis = h.dw !== 0 && h.dh !== 0;
        if (lockAspect && isTwoAxis) {
          const ratio = state.oh / state.ow;
          nw = Math.abs(rawDx) >= Math.abs(rawDy) ? nw : Math.round(nh / ratio);
          nh = Math.abs(rawDx) >= Math.abs(rawDy) ? Math.round(nw * ratio) : nh;
        }
        let nx = state.ox + (h.dx ? rawDx * h.dx : 0);
        let ny = state.oy + (h.dy ? rawDy * h.dy : 0);
        nw = Math.min(nw, CANVAS_W - nx);
        nh = Math.min(nh, CANVAS_H - ny);
        nx = Math.max(0, nx);
        ny = Math.max(0, ny);
        onLiveUpdate(comp.id, { x: Math.round(nx), y: Math.round(ny), width: Math.round(nw), height: Math.round(nh) });

      } else if (state.type === 'rotate') {
        const angle = Math.atan2(e.clientY - state.cy, e.clientX - state.cx) * (180 / Math.PI) + 90;
        onLiveUpdate(comp.id, { rotation: Math.round(angle) });
      }
    });
  }, [comp, onLiveUpdate, snapPosition, viewportScale, lockAspect]);

  // ── Pointer up — gesture done; PATCH is already the final state.
  //    No extra history push needed — CHECKPOINT captured the before-state.
  const onUp = useCallback(() => {
    if (raf.current) cancelAnimationFrame(raf.current);
    ps.current = null;
  }, []);

  const opacity  = comp.opacity  !== undefined ? comp.opacity  : 1;
  const flipParts = [];
  if (comp.flipH) flipParts.push('scaleX(-1)');
  if (comp.flipV) flipParts.push('scaleY(-1)');

  return (
    <div
      ref={elRef}
      style={{
        position: 'absolute',
        left: comp.x, top: comp.y,
        width: comp.width, height: comp.height,
        transform: `rotate(${comp.rotation || 0}deg)`,
        transformOrigin: 'center center',
        opacity,
        cursor: comp.locked ? 'not-allowed' : 'move',
        userSelect: 'none',
        zIndex: comp.zIndex || 1,
        outline: isSelected ? '2px solid #3b82f6' : 'none',
        outlineOffset: 1,
        boxSizing: 'border-box',
        touchAction: 'none',
      }}
      onPointerDown={onBodyDown}
      onPointerMove={onMove}
      onPointerUp={onUp}
      onPointerCancel={onUp}
    >
      {/* Element image */}
      <img
        src={comp.imagePath}
        alt="element"
        draggable={false}
        style={{
          width: '100%', height: '100%',
          objectFit: 'fill', display: 'block',
          transform: flipParts.length ? flipParts.join(' ') : undefined,
          pointerEvents: 'none',
        }}
      />

      {/* Transform handles — only when selected + unlocked */}
      {isSelected && !comp.locked && (
        <>
          {/* Rotate handle */}
          <div
            title="Rotate"
            style={{
              position: 'absolute', top: -26, left: '50%', marginLeft: -7,
              width: 14, height: 14, borderRadius: '50%',
              background: '#3b82f6', border: '2px solid #fff',
              cursor: 'crosshair', zIndex: 9999, touchAction: 'none',
            }}
            onPointerDown={onRotateDown}
            onPointerMove={onMove}
            onPointerUp={onUp}
          />
          {/* Connector line to rotate handle */}
          <div style={{
            position: 'absolute', top: -16, left: '50%', marginLeft: -0.5,
            width: 1, height: 16, background: '#3b82f6', pointerEvents: 'none',
          }} />

          {/* 8 resize handles */}
          {HANDLES.map(h => (
            <div
              key={h.id}
              title={`Resize ${h.id.toUpperCase()}`}
              style={handleStyle(h)}
              onPointerDown={e => onHandleDown(e, h)}
              onPointerMove={onMove}
              onPointerUp={onUp}
            />
          ))}
        </>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Zoom controls bar
// ─────────────────────────────────────────────────────────────────────────────
function ZoomBar({ scale, onZoomTo, onReset, containerRef, MIN_SCALE, MAX_SCALE }) {
  const pct = Math.round(scale * 100);

  const getRect = () => containerRef.current?.getBoundingClientRect() || { width: 0, height: 0, left: 0, top: 0 };

  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 8,
      padding: '4px 10px', background: '#f1f5f9',
      borderTop: '1px solid #e2e8f0', flexShrink: 0,
      fontSize: 12, color: '#475569',
    }}>
      <button
        onClick={() => onZoomTo(scale - 0.1, getRect())}
        style={{ ...zBtn, fontSize: 16, lineHeight: 1 }} title="Zoom out">−</button>

      <input
        type="range" min={MIN_SCALE * 100} max={MAX_SCALE * 100} step={5}
        value={pct}
        onChange={e => onZoomTo(Number(e.target.value) / 100, getRect())}
        style={{ width: 100, accentColor: '#3b82f6' }}
      />

      <button
        onClick={() => onZoomTo(scale + 0.1, getRect())}
        style={{ ...zBtn, fontSize: 16, lineHeight: 1 }} title="Zoom in">+</button>

      <span style={{ minWidth: 40, textAlign: 'center', fontWeight: 600 }}>{pct}%</span>

      <button onClick={onReset} style={zBtn} title="Reset view (100%)">Reset</button>

      <span style={{ marginLeft: 'auto', color: '#94a3b8', fontSize: 11 }}>
        Wheel=zoom · Space+drag=pan · Middle-drag=pan
      </span>
    </div>
  );
}

const zBtn = {
  padding: '3px 8px', border: '1px solid #cbd5e1', borderRadius: 5,
  background: '#fff', cursor: 'pointer', fontSize: 12, color: '#374151',
};

// ─────────────────────────────────────────────────────────────────────────────
// Main Canvas component
// ─────────────────────────────────────────────────────────────────────────────
function Canvas({
  placedComponents,
  selectedComponentId,
  handleSelectForEditing,
  updateComponentProps,
  liveUpdateComponentProps,
  onCheckpoint,
  canvasRef,
  templateEnabled,
  templateOpacity,
  templateImage,
  showGuides,
  activeGuides,
  snapPosition,
  onDeselect,
  lockAspect,
  // TAB cycle — passed from parent
  onTabCycle,
}) {
  const containerRef = useRef(null);
  const artboardRef  = useRef(null);
  // Tracks whether the user has interacted (so ResizeObserver doesn't re-centre after pan/zoom)
  const [, setTransformInitialised] = useState(false);

  const {
    transform, handlers, zoomTo, resetView,
    MIN_SCALE, MAX_SCALE, onKeyDown, onKeyUp,
  } = useCanvasTransform();

  // Centre the artboard on first render (and whenever the container resizes)
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    resetView(el.getBoundingClientRect());
    // ResizeObserver keeps it centred if the panel resizes
    const ro = new ResizeObserver(() => {
      // Only re-centre if the user hasn't panned/zoomed yet
      setTransformInitialised(v => {
        if (!v) resetView(el.getBoundingClientRect());
        return true;
      });
    });
    ro.observe(el);
    return () => ro.disconnect();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Expose artboard DOM node to parent (for html2canvas export)
  useEffect(() => {
    if (canvasRef) canvasRef.current = artboardRef.current;
  });

  // Attach space-key listeners globally
  useEffect(() => {
    window.addEventListener('keydown', onKeyDown);
    window.addEventListener('keyup',   onKeyUp);
    return () => {
      window.removeEventListener('keydown', onKeyDown);
      window.removeEventListener('keyup',   onKeyUp);
    };
  }, [onKeyDown, onKeyUp]);

  // Prevent browser default scroll on wheel inside canvas
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    // Prevent browser default zoom on pinch (ctrlKey), but allow normal scroll
    const prevent = (e) => { if (e.ctrlKey) e.preventDefault(); };
    el.addEventListener('wheel', prevent, { passive: false });
    return () => el.removeEventListener('wheel', prevent);
  }, []);

  const handleContainerClick = useCallback((e) => {
    if (e.target === containerRef.current) onDeselect?.();
  }, [onDeselect]);

  // Cursor: show grab when space is held
  const [spaceCursor, setSpaceCursor] = useState(false);
  useEffect(() => {
    const kd = (e) => { if (e.code === 'Space') setSpaceCursor(true);  };
    const ku = (e) => { if (e.code === 'Space') setSpaceCursor(false); };
    window.addEventListener('keydown', kd);
    window.addEventListener('keyup',   ku);
    return () => { window.removeEventListener('keydown', kd); window.removeEventListener('keyup', ku); };
  }, []);

  const { scale, offsetX, offsetY } = transform;

  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0, overflow: 'hidden' }}>
      {/* ── Viewport ── */}
      <div
        ref={containerRef}
        style={{
          flex: 1,
          overflow: 'hidden',
          position: 'relative',
          background: 'repeating-conic-gradient(#e5e7eb 0% 25%, #f9fafb 0% 50%) 50% / 20px 20px',
          cursor: spaceCursor ? 'grab' : 'default',
          userSelect: 'none',
        }}
        onClick={handleContainerClick}
        {...handlers}
      >
        {/* Artboard — scaled + translated, origin at top-left */}
        <div
          style={{
            position: 'absolute',
            top: 0, left: 0,
            transform: `translate(${offsetX}px, ${offsetY}px) scale(${scale})`,
            transformOrigin: '0 0',
            width: CANVAS_W, height: CANVAS_H,
            willChange: 'transform',
          }}
        >
          {/* White artboard (exported) */}
          <div
            ref={artboardRef}
            style={{
              position: 'relative',
              width: CANVAS_W, height: CANVAS_H,
              backgroundColor: '#ffffff',
              boxShadow: '0 8px 32px rgba(0,0,0,0.18)',
              overflow: 'visible',
            }}
            onClick={(e) => { if (e.target === artboardRef.current) onDeselect?.(); }}
          >
            {/* Template */}
            {templateEnabled && (
              <img
                src={templateImage || 'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="720" height="540"><rect width="100%25" height="100%25" fill="white"/><g stroke="%23000" stroke-width="1" opacity="0.25"><ellipse cx="360" cy="240" rx="130" ry="160" fill="none"/></g></svg>'}
                alt="template"
                style={{
                  position: 'absolute', inset: 0, width: '100%', height: '100%',
                  objectFit: 'contain', opacity: templateOpacity ?? 0.25,
                  pointerEvents: 'none', zIndex: 0,
                }}
              />
            )}

            {/* Guide overlay */}
            <GuideOverlay showGuides={showGuides} activeGuides={activeGuides || []} />

            {/* Elements — sorted by zIndex so stacking is correct */}
            {placedComponents &&
              [...placedComponents]
                .filter(c => !c.hidden)
                .sort((a, b) => (a.zIndex || 0) - (b.zIndex || 0))
                .map(comp => (
                  <PlacedElement
                    key={comp.id}
                    comp={comp}
                    isSelected={selectedComponentId === comp.id}
                    onSelect={handleSelectForEditing}
                    onLiveUpdate={liveUpdateComponentProps || updateComponentProps}
                    onCommit={updateComponentProps}
                    onCheckpoint={onCheckpoint}
                    snapPosition={snapPosition}
                    viewportScale={scale}
                    lockAspect={lockAspect}
                  />
                ))
            }
          </div>
        </div>

        {/* Empty state hint */}
        {(!placedComponents || placedComponents.length === 0) && (
          <div style={{
            position: 'absolute', top: '50%', left: '50%',
            transform: 'translate(-50%,-50%)',
            color: '#94a3b8', fontSize: 13, pointerEvents: 'none', textAlign: 'center',
          }}>
            <div style={{ fontSize: 32, marginBottom: 8 }}>🎨</div>
            Click an element in the library to add it
          </div>
        )}
      </div>

      {/* ── Zoom bar ── */}
      <ZoomBar
        scale={scale}
        onZoomTo={zoomTo}
        onReset={() => resetView(containerRef.current?.getBoundingClientRect())}
        containerRef={containerRef}
        MIN_SCALE={MIN_SCALE}
        MAX_SCALE={MAX_SCALE}
      />
    </div>
  );
}

export default Canvas;
