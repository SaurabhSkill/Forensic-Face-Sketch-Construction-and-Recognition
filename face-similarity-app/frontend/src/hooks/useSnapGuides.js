/**
 * useSnapGuides
 * Provides snap-to-guide logic for the canvas.
 * Returns active snap lines and a function to compute snapped position.
 *
 * Canvas dimensions: 720 × 540
 * Guide lines (x = vertical, y = horizontal):
 *   - Center vertical:   x = 360
 *   - Eye line:          y = 162  (~30% from top)
 *   - Nose line:         y = 270  (50% — center)
 *   - Mouth line:        y = 378  (~70% from top)
 */
import { useState, useCallback } from 'react';

export const CANVAS_W = 720;
export const CANVAS_H = 540;

export const GUIDE_LINES = {
  centerX:  { axis: 'x', value: CANVAS_W / 2,       label: 'Center' },
  eyeY:     { axis: 'y', value: Math.round(CANVAS_H * 0.30), label: 'Eye Line' },
  noseY:    { axis: 'y', value: Math.round(CANVAS_H * 0.50), label: 'Nose Line' },
  mouthY:   { axis: 'y', value: Math.round(CANVAS_H * 0.70), label: 'Mouth Line' },
};

const SNAP_THRESHOLD = 10; // px

export function useSnapGuides(snapEnabled = true) {
  const [activeGuides, setActiveGuides] = useState([]); // keys of currently snapping guides

  /**
   * Given a dragging element's proposed (x, y) and its dimensions,
   * return the snapped (x, y) and set active guide highlights.
   */
  const snapPosition = useCallback((x, y, width, height) => {
    if (!snapEnabled) {
      setActiveGuides([]);
      return { x, y };
    }

    let snappedX = x;
    let snappedY = y;
    const triggered = [];

    const elCenterX = x + width / 2;
    const elCenterY = y + height / 2;

    // Snap element center to vertical center guide
    const dCenterX = Math.abs(elCenterX - GUIDE_LINES.centerX.value);
    if (dCenterX < SNAP_THRESHOLD) {
      snappedX = GUIDE_LINES.centerX.value - width / 2;
      triggered.push('centerX');
    }

    // Snap element center-y to each horizontal guide
    Object.entries(GUIDE_LINES).forEach(([key, guide]) => {
      if (guide.axis !== 'y') return;
      const d = Math.abs(elCenterY - guide.value);
      if (d < SNAP_THRESHOLD) {
        snappedY = guide.value - height / 2;
        triggered.push(key);
      }
    });

    setActiveGuides(triggered);
    return { x: snappedX, y: snappedY };
  }, [snapEnabled]);

  const clearActiveGuides = useCallback(() => setActiveGuides([]), []);

  return { activeGuides, snapPosition, clearActiveGuides, GUIDE_LINES };
}
