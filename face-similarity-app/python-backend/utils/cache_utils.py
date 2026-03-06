"""
Caching utilities for result caching with LRU eviction policy
"""

from collections import OrderedDict
from typing import Optional

# Global LRU cache for comparison results using OrderedDict
# OrderedDict maintains insertion order and allows efficient reordering
RESULT_CACHE = OrderedDict()
CACHE_MAX_SIZE = 100


def get_cached_result(cache_key: str) -> Optional[dict]:
    """
    Get cached result by key and mark it as recently used (LRU)
    
    Args:
        cache_key: Cache key
    
    Returns:
        dict: Cached result or None if not found
    """
    if cache_key in RESULT_CACHE:
        # Move to end to mark as recently used (LRU policy)
        RESULT_CACHE.move_to_end(cache_key)
        return RESULT_CACHE[cache_key]
    return None


def set_cached_result(cache_key: str, result: dict):
    """
    Store result in cache with LRU eviction policy
    
    When cache exceeds max size, removes the least recently used item.
    
    Args:
        cache_key: Cache key
        result: Result to cache
    """
    global RESULT_CACHE
    
    # If key already exists, update it and move to end
    if cache_key in RESULT_CACHE:
        RESULT_CACHE[cache_key] = result
        RESULT_CACHE.move_to_end(cache_key)
    else:
        # Add new entry
        RESULT_CACHE[cache_key] = result
        
        # Remove least recently used entry if cache is full
        if len(RESULT_CACHE) > CACHE_MAX_SIZE:
            # popitem(last=False) removes the first (least recently used) item
            evicted_key, _ = RESULT_CACHE.popitem(last=False)
            print(f"[CACHE] Evicted LRU entry: {evicted_key[:50]}...")


def clear_cache():
    """Clear all cached results"""
    global RESULT_CACHE
    RESULT_CACHE = OrderedDict()


def get_cache_stats() -> dict:
    """
    Get cache statistics
    
    Returns:
        dict: Cache statistics including LRU order
    """
    return {
        'size': len(RESULT_CACHE),
        'max_size': CACHE_MAX_SIZE,
        'keys': list(RESULT_CACHE.keys()),
        'cache_type': 'LRU (Least Recently Used)',
        'oldest_key': list(RESULT_CACHE.keys())[0] if RESULT_CACHE else None,
        'newest_key': list(RESULT_CACHE.keys())[-1] if RESULT_CACHE else None
    }
