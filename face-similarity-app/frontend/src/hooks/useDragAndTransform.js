/**
 * useDragAndTransform
 * Handles pointer-based drag, resize, and rotate for a single canvas element.
 * Uses requestAnimationFrame for smooth updates.
 *
 * Returns event handlers to attach to the element wrapper and its handles.
 */
import { useRef, useCallback } from 'react';

export function useDragAndTransform({ element, onUpdate, snapPosition, canvasBounds }) {
  const dragState = useRef(null);
  const rafId = useRef(null);

  // ── DRAG ──────────────────────────────────────────────────────────────────
  const onDragPointerDown = useCallback((e) => {
    if (e.button !== 0) return;
    e.stopPropagation();
    e.currentTarget.setPointerCapture(e.pointerId);

    dragState.current = {
      type: 'drag',
      startPointerX: e.clientX,
      startPointerY: e.clientY,
      startElX: element.x,
      startElY: element.y,
    };
  }, [element]);

  const onDragPointerMove = useCallback((e) => {
    if (!dragState.current || dragState.current.type !== 'drag') return;
    e.preventDefault();

    const dx = e.clientX - dragState.current.startPointerX;
    const dy = e.clientY - dragState.current.startPointerY;

    let newX = dragState.current.startElX + dx;
    let newY = dragState.current.startElY + dy;

    // Clamp to canvas bounds
    if (canvasBounds) {
      newX = Math.max(0, Math.min(newX, canvasBounds.width - element.width));
      newY = Math.max(0, Math.min(newY, canvasBounds.height - element.height));
    }

    // Apply snap
    const snapped = snapPosition
      ? snapPosition(newX, newY, element.width, element.height)
      : { x: newX, y: newY };

    if (rafId.current) cancelAnimationFrame(rafId.current);
    rafId.current = requestAnimationFrame(() => {
      onUpdate({ x: snapped.x, y: snapped.y });
    });
  }, [element, onUpdate, snapPosition, canvasBounds]);

  const onDragPointerUp = useCallback(() => {
    dragState.current = null;
    if (rafId.current) cancelAnimationFrame(rafId.current);
  }, []);

  // ── RESIZE (corner handle) ────────────────────────────────────────────────
  const onResizePointerDown = useCallback((e) => {
    if (e.button !== 0) return;
    e.stopPropagation();
    e.currentTarget.setPointerCapture(e.pointerId);

    dragState.current = {
      type: 'resize',
      startPointerX: e.clientX,
      startPointerY: e.clientY,
      startWidth: element.width,
      startHeight: element.height,
    };
  }, [element]);

  const onResizePointerMove = useCallback((e) => {
    if (!dragState.current || dragState.current.type !== 'resize') return;
    e.preventDefault();

    const dx = e.clientX - dragState.current.startPointerX;
    const newWidth = Math.max(20, dragState.current.startWidth + dx);
    // Maintain aspect ratio: height scales proportionally
    const ratio = dragState.current.startHeight / dragState.current.startWidth;
    const newHeight = Math.round(newWidth * ratio);

    if (rafId.current) cancelAnimationFrame(rafId.current);
    rafId.current = requestAnimationFrame(() => {
      onUpdate({ width: newWidth, height: newHeight });
    });
  }, [element, onUpdate]);

  const onResizePointerUp = useCallback(() => {
    dragState.current = null;
  }, []);

  // ── ROTATE (top handle) ───────────────────────────────────────────────────
  const onRotatePointerDown = useCallback((e, elCenterX, elCenterY) => {
    if (e.button !== 0) return;
    e.stopPropagation();
    e.currentTarget.setPointerCapture(e.pointerId);

    dragState.current = {
      type: 'rotate',
      elCenterX,
      elCenterY,
      startRotation: element.rotation || 0,
    };
  }, [element]);

  const onRotatePointerMove = useCallback((e) => {
    if (!dragState.current || dragState.current.type !== 'rotate') return;
    e.preventDefault();

    const { elCenterX, elCenterY, startRotation } = dragState.current;
    const angle = Math.atan2(e.clientY - elCenterY, e.clientX - elCenterX) * (180 / Math.PI) + 90;

    if (rafId.current) cancelAnimationFrame(rafId.current);
    rafId.current = requestAnimationFrame(() => {
      onUpdate({ rotation: Math.round(angle) });
    });
  }, [onUpdate]);

  const onRotatePointerUp = useCallback(() => {
    dragState.current = null;
  }, []);

  return {
    drag: { onPointerDown: onDragPointerDown, onPointerMove: onDragPointerMove, onPointerUp: onDragPointerUp },
    resize: { onPointerDown: onResizePointerDown, onPointerMove: onResizePointerMove, onPointerUp: onResizePointerUp },
    rotate: { onPointerDown: onRotatePointerDown, onPointerMove: onRotatePointerMove, onPointerUp: onRotatePointerUp },
  };
}
