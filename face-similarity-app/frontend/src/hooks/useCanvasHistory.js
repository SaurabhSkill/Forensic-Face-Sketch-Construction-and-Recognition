/**
 * useCanvasHistory
 * Action-based undo/redo — like Figma/Canva.
 *
 * Three dispatch types:
 *
 *  CHECKPOINT  – called on gesture START (drag/resize/rotate pointerdown).
 *                Pushes current present → past. Does NOT change present.
 *                This is the "before" snapshot.
 *
 *  PATCH       – called on every pointermove frame.
 *                Silently replaces present. No history entry.
 *                Visual-only update during live interaction.
 *
 *  SET         – called for discrete actions: add, delete, duplicate,
 *                toggle visibility/lock, z-index ops, panel input changes.
 *                Pushes current present → past, replaces present.
 *
 * Result: one undo step = one complete user gesture or action.
 */
import { useReducer, useCallback } from 'react';

const MAX_HISTORY = 50;

const initialState = {
  past:    [],   // snapshots before each action
  present: [],   // current live elements
  future:  [],   // snapshots for redo
};

function historyReducer(state, action) {
  switch (action.type) {

    case 'CHECKPOINT': {
      // Save current present as the "before" state — called at gesture start.
      // Don't change present, don't clear future (user hasn't done anything yet).
      const newPast = [...state.past, state.present].slice(-MAX_HISTORY);
      return { ...state, past: newPast, future: [] };
    }

    case 'PATCH': {
      // Live update during drag — only replace present, touch nothing else.
      return { ...state, present: action.payload };
    }

    case 'SET': {
      // Discrete action — push present to past, replace present, clear future.
      const newPast = [...state.past, state.present].slice(-MAX_HISTORY);
      return { past: newPast, present: action.payload, future: [] };
    }

    case 'UNDO': {
      if (state.past.length === 0) return state;
      const previous = state.past[state.past.length - 1];
      const newPast  = state.past.slice(0, -1);
      return { past: newPast, present: previous, future: [state.present, ...state.future] };
    }

    case 'REDO': {
      if (state.future.length === 0) return state;
      const next      = state.future[0];
      const newFuture = state.future.slice(1);
      return { past: [...state.past, state.present], present: next, future: newFuture };
    }

    case 'RESET':
      return { ...initialState, present: action.payload || [] };

    default:
      return state;
  }
}

export function useCanvasHistory(initialElements = []) {
  const [state, dispatch] = useReducer(historyReducer, {
    ...initialState,
    present: initialElements,
  });

  /**
   * checkpoint() — call at the START of any gesture (pointerdown).
   * Saves the current state as the "before" snapshot so undo can return to it.
   */
  const checkpoint = useCallback(() => {
    dispatch({ type: 'CHECKPOINT' });
  }, []);

  /**
   * patch() — call on every pointermove frame.
   * Updates the visual state without touching history.
   */
  const patch = useCallback((newElements) => {
    dispatch({ type: 'PATCH', payload: newElements });
  }, []);

  /**
   * set() — call for discrete actions (add, delete, property change, etc.).
   * Pushes one history entry.
   */
  const set = useCallback((newElements) => {
    dispatch({ type: 'SET', payload: newElements });
  }, []);

  const undo  = useCallback(() => dispatch({ type: 'UNDO'  }), []);
  const redo  = useCallback(() => dispatch({ type: 'REDO'  }), []);
  const reset = useCallback((els) => dispatch({ type: 'RESET', payload: els }), []);

  return {
    elements: state.present,
    canUndo:  state.past.length  > 0,
    canRedo:  state.future.length > 0,
    checkpoint,
    patch,
    set,
    undo,
    redo,
    reset,
  };
}
