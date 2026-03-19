/**
 * useLayerManager
 * Manages z-index / stacking order for canvas elements.
 *
 * Elements are stored in an array; their visual stacking order is determined
 * by their `zIndex` property.  This hook provides:
 *
 *   bringForward   – increase zIndex by 1 (swap with next higher)
 *   sendBackward   – decrease zIndex by 1 (swap with next lower)
 *   bringToFront   – set zIndex to max + 1
 *   sendToBack     – set zIndex to 0, shift all others up
 *
 * All operations return a new elements array (immutable).
 */
import { useCallback } from 'react';

export function useLayerManager(elements, setElements) {

  /** Re-assign sequential zIndex values based on array order */
  const reindex = (arr) =>
    arr.map((el, i) => ({ ...el, zIndex: i + 1 }));

  /** Sort elements array by zIndex ascending */
  const sorted = (arr) => [...arr].sort((a, b) => (a.zIndex || 0) - (b.zIndex || 0));

  const bringToFront = useCallback((id) => {
    const arr = sorted(elements);
    const idx = arr.findIndex(e => e.id === id);
    if (idx === -1 || idx === arr.length - 1) return;
    const [el] = arr.splice(idx, 1);
    arr.push(el);
    setElements(reindex(arr));
  }, [elements, setElements]);

  const sendToBack = useCallback((id) => {
    const arr = sorted(elements);
    const idx = arr.findIndex(e => e.id === id);
    if (idx === -1 || idx === 0) return;
    const [el] = arr.splice(idx, 1);
    arr.unshift(el);
    setElements(reindex(arr));
  }, [elements, setElements]);

  const bringForward = useCallback((id) => {
    const arr = sorted(elements);
    const idx = arr.findIndex(e => e.id === id);
    if (idx === -1 || idx === arr.length - 1) return;
    // Swap with next element
    [arr[idx], arr[idx + 1]] = [arr[idx + 1], arr[idx]];
    setElements(reindex(arr));
  }, [elements, setElements]);

  const sendBackward = useCallback((id) => {
    const arr = sorted(elements);
    const idx = arr.findIndex(e => e.id === id);
    if (idx === -1 || idx === 0) return;
    // Swap with previous element
    [arr[idx], arr[idx - 1]] = [arr[idx - 1], arr[idx]];
    setElements(reindex(arr));
  }, [elements, setElements]);

  return { bringToFront, sendToBack, bringForward, sendBackward };
}
