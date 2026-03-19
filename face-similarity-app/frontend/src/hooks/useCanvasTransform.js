/**
 * useCanvasTransform
 * Manages zoom + pan state for the canvas viewport.
 *
 * Zoom: mouse-wheel, centered on cursor position.
 * Pan:  middle-mouse drag OR space+left-drag.
 *
 * Returns:
 *   transform   – { scale, offsetX, offsetY }  applied to the artboard wrapper
 *   handlers    – attach to the viewport container element
 *   zoomTo      – programmatic zoom (e.g. from slider)
 *   resetView   – snap back to 100 % centered
 *   toArtboard  – convert viewport (clientX/Y) → artboard (px) coordinates
 */
import { useRef, useState, useCallback } from 'react';

const MIN_SCALE = 0.15;
const MAX_SCALE = 4;
const ZOOM_SENSITIVITY = 0.001; // per wheel-delta unit

function clamp(v, lo, hi) { return Math.max(lo, Math.min(hi, v)); }

export function useCanvasTransform() {
  // offsetX/Y represent the translation of the artboard's top-left corner
  // within the viewport, with transform-origin: 0 0.
  // Initial value of null means "not yet initialised" — Canvas will call
  // resetView() with the container size on first render to center the board.
  const [transform, setTransform] = useState({ scale: 1, offsetX: 0, offsetY: 0 });

  // Refs for pan gesture (no re-render during drag)
  const panState = useRef(null);
  const spaceDown = useRef(false);

  // ── Zoom towards cursor ──────────────────────────────────────────────────
  // With transform-origin: 0 0, the artboard top-left is at (offsetX, offsetY).
  // To keep the point under the cursor fixed:
  //   cursorOnArtboard = (cursor - offset) / scale   [invariant]
  //   newOffset = cursor - cursorOnArtboard * newScale
  const zoomAt = useCallback((clientX, clientY, delta, containerRect) => {
    setTransform(prev => {
      const newScale = clamp(prev.scale * (1 - delta * ZOOM_SENSITIVITY), MIN_SCALE, MAX_SCALE);

      // Cursor position relative to the viewport container (origin = top-left)
      const cx = clientX - containerRect.left;
      const cy = clientY - containerRect.top;

      // Point on the artboard under the cursor (in artboard px)
      const artX = (cx - prev.offsetX) / prev.scale;
      const artY = (cy - prev.offsetY) / prev.scale;

      // New offset so that same artboard point stays under cursor
      const newOffsetX = cx - artX * newScale;
      const newOffsetY = cy - artY * newScale;

      return { scale: newScale, offsetX: newOffsetX, offsetY: newOffsetY };
    });
  }, []);

  // ── Programmatic zoom (slider) ───────────────────────────────────────────
  const zoomTo = useCallback((newScale, containerRect) => {
    setTransform(prev => {
      const s = clamp(newScale, MIN_SCALE, MAX_SCALE);
      // Zoom towards center of container
      const cx = containerRect ? containerRect.width  / 2 : 0;
      const cy = containerRect ? containerRect.height / 2 : 0;
      const artX = (cx - prev.offsetX) / prev.scale;
      const artY = (cy - prev.offsetY) / prev.scale;
      return {
        scale: s,
        offsetX: cx - artX * s,
        offsetY: cy - artY * s,
      };
    });
  }, []);

  // ── Reset view — center artboard in container ────────────────────────────
  const resetView = useCallback((containerRect) => {
    if (containerRect) {
      // Import CANVAS_W/H lazily to avoid circular deps — use the known values
      const CANVAS_W = 720, CANVAS_H = 540;
      setTransform({
        scale: 1,
        offsetX: (containerRect.width  - CANVAS_W) / 2,
        offsetY: (containerRect.height - CANVAS_H) / 2,
      });
    } else {
      setTransform({ scale: 1, offsetX: 0, offsetY: 0 });
    }
  }, []);

  // ── Convert viewport coords → artboard coords ────────────────────────────
  const toArtboard = useCallback((clientX, clientY, containerRect) => {
    return {
      x: (clientX - containerRect.left - transform.offsetX) / transform.scale,
      y: (clientY - containerRect.top  - transform.offsetY) / transform.scale,
    };
  }, [transform]);

  // ── Wheel handler ────────────────────────────────────────────────────────
  // ctrlKey is set by browsers for pinch gestures (trackpad pinch-to-zoom).
  // Normal scroll (two-finger swipe, mouse wheel) does NOT set ctrlKey.
  const onWheel = useCallback((e) => {
    if (!e.ctrlKey) return;          // ignore normal scroll — pinch only
    e.preventDefault();              // prevent browser page zoom on pinch
    const rect = e.currentTarget.getBoundingClientRect();
    zoomAt(e.clientX, e.clientY, e.deltaY, rect);
  }, [zoomAt]);

  // ── Space key tracking (for space+drag pan) ──────────────────────────────
  const onKeyDown = useCallback((e) => {
    if (e.code === 'Space') { spaceDown.current = true; e.preventDefault(); }
  }, []);
  const onKeyUp = useCallback((e) => {
    if (e.code === 'Space') spaceDown.current = false;
  }, []);

  // ── Pointer down: start pan on middle-mouse or space+left ────────────────
  const onPointerDown = useCallback((e) => {
    const isMiddle = e.button === 1;
    const isSpaceDrag = e.button === 0 && spaceDown.current;
    if (!isMiddle && !isSpaceDrag) return;

    e.preventDefault();
    e.currentTarget.setPointerCapture(e.pointerId);
    panState.current = {
      startX: e.clientX,
      startY: e.clientY,
      startOffsetX: 0,
      startOffsetY: 0,
    };
    // Capture current offset at drag start
    setTransform(prev => {
      panState.current.startOffsetX = prev.offsetX;
      panState.current.startOffsetY = prev.offsetY;
      return prev;
    });
  }, []);

  const onPointerMove = useCallback((e) => {
    if (!panState.current) return;
    const dx = e.clientX - panState.current.startX;
    const dy = e.clientY - panState.current.startY;
    setTransform(prev => ({
      ...prev,
      offsetX: panState.current.startOffsetX + dx,
      offsetY: panState.current.startOffsetY + dy,
    }));
  }, []);

  const onPointerUp = useCallback(() => {
    panState.current = null;
  }, []);

  const handlers = { onWheel, onPointerDown, onPointerMove, onPointerUp };

  return {
    transform,
    handlers,
    zoomTo,
    resetView,
    toArtboard,
    MIN_SCALE,
    MAX_SCALE,
    spaceDown,
    onKeyDown,
    onKeyUp,
  };
}
