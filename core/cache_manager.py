"""
Cache Manager - Centralized caching system for SAGE
"""

import asyncio
import json
import pickle
import hashlib
import time
from typing import Any, Dict, Optional, Union, List
from pathlib import Path
from collections import OrderedDict
import threading
import logging
from dataclasses import dataclass, asdict


@dataclass
class CacheEntry:
    """Cache entry with metadata"""
    key: str
    value: Any
    timestamp: float
    ttl: Optional[float]
    access_count: int
    size_bytes: int
    
    @property
    def is_expired(self) -> bool:
        """Check if the cache entry has expired"""
        if self.ttl is None:
            return False
        return time.time() > (self.timestamp + self.ttl)
        
    @property
    def age_seconds(self) -> float:
        """Get the age of the cache entry in seconds"""
        return time.time() - self.timestamp


class CacheManager:
    """Centralized cache management with LRU eviction and persistence"""
    
    def __init__(self, 
                 cache_dir: str = "data/cache",
                 max_memory_mb: int = 200,
                 default_ttl: Optional[float] = 3600):  # 1 hour default TTL
        
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self.default_ttl = default_ttl
        
        # In-memory cache (LRU)
        self.memory_cache: OrderedDict[str, CacheEntry] = OrderedDict()
        
        # Persistent cache directories
        self.persistent_dirs = {
            "voice": self.cache_dir / "voice",
            "llm": self.cache_dir / "llm", 
            "web": self.cache_dir / "web",
            "vision": self.cache_dir / "vision",
            "general": self.cache_dir / "general"
        }
        
        # Create cache directories
        for cache_dir in self.persistent_dirs.values():
            cache_dir.mkdir(parents=True, exist_ok=True)
            
        self.current_memory_usage = 0
        self.lock = threading.RLock()
        self.logger = logging.getLogger(__name__)
        
        # Load existing cache metadata
        self._load_cache_metadata()
        
    def _load_cache_metadata(self) -> None:
        """Load cache metadata from disk"""
        try:
            metadata_file = self.cache_dir / "cache_metadata.json"
            if metadata_file.exists():
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
                    
                self.logger.info(f"Loaded cache metadata for {len(metadata)} entries")
        except Exception as e:
            self.logger.warning(f"Failed to load cache metadata: {e}")
            
    def _save_cache_metadata(self) -> None:
        """Save cache metadata to disk"""
        try:
            metadata = {}
            for key, entry in self.memory_cache.items():
                metadata[key] = {
                    "timestamp": entry.timestamp,
                    "ttl": entry.ttl,
                    "access_count": entry.access_count,
                    "size_bytes": entry.size_bytes
                }
                
            metadata_file = self.cache_dir / "cache_metadata.json"
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"Failed to save cache metadata: {e}")
            
    def _calculate_size(self, value: Any) -> int:
        """Calculate the approximate size of a value in bytes"""
        try:
            if isinstance(value, (str, bytes)):
                return len(value.encode('utf-8') if isinstance(value, str) else value)
            elif isinstance(value, dict):
                return len(json.dumps(value, ensure_ascii=False).encode('utf-8'))
            else:
                return len(pickle.dumps(value))
        except Exception:
            return 1024  # Default estimate
            
    def _generate_key(self, module: str, operation: str, **kwargs) -> str:
        """Generate a cache key from parameters"""
        key_data = f"{module}:{operation}:{kwargs}"
        return hashlib.md5(key_data.encode()).hexdigest()
        
    def _evict_lru(self, required_space: int) -> None:
        """Evict least recently used items to free up space"""
        while (self.current_memory_usage + required_space > self.max_memory_bytes and 
               self.memory_cache):
            
            # Remove oldest item
            key, entry = self.memory_cache.popitem(last=False)
            self.current_memory_usage -= entry.size_bytes
            self.logger.debug(f"Evicted cache entry: {key}")
            
    def _cleanup_expired(self) -> None:
        """Remove expired entries from memory cache"""
        expired_keys = []
        
        for key, entry in self.memory_cache.items():
            if entry.is_expired:
                expired_keys.append(key)
                
        for key in expired_keys:
            entry = self.memory_cache.pop(key)
            self.current_memory_usage -= entry.size_bytes
            self.logger.debug(f"Removed expired cache entry: {key}")
            
    def get(self, 
            module: str, 
            operation: str, 
            default: Any = None,
            **kwargs) -> Any:
        """Get a value from cache"""
        
        key = self._generate_key(module, operation, **kwargs)
        
        with self.lock:
            # Check memory cache first
            if key in self.memory_cache:
                entry = self.memory_cache[key]
                
                if entry.is_expired:
                    # Remove expired entry
                    self.memory_cache.pop(key)
                    self.current_memory_usage -= entry.size_bytes
                    return default
                    
                # Move to end (most recently used)
                self.memory_cache.move_to_end(key)
                entry.access_count += 1
                
                self.logger.debug(f"Cache hit: {module}.{operation}")
                return entry.value
                
            # Check persistent cache
            persistent_value = self._get_persistent(module, key)
            if persistent_value is not None:
                self.logger.debug(f"Persistent cache hit: {module}.{operation}")
                return persistent_value
                
        self.logger.debug(f"Cache miss: {module}.{operation}")
        return default
        
    def set(self, 
            module: str, 
            operation: str, 
            value: Any,
            ttl: Optional[float] = None,
            persistent: bool = False,
            **kwargs) -> None:
        """Set a value in cache"""
        
        key = self._generate_key(module, operation, **kwargs)
        ttl = ttl or self.default_ttl
        
        with self.lock:
            # Calculate size
            size_bytes = self._calculate_size(value)
            
            # Check if we need to evict items
            if size_bytes > self.max_memory_bytes:
                self.logger.warning(f"Cache value too large: {size_bytes} bytes")
                return
                
            self._evict_lru(size_bytes)
            
            # Create cache entry
            entry = CacheEntry(
                key=key,
                value=value,
                timestamp=time.time(),
                ttl=ttl,
                access_count=0,
                size_bytes=size_bytes
            )
            
            # Remove old entry if exists
            if key in self.memory_cache:
                old_entry = self.memory_cache.pop(key)
                self.current_memory_usage -= old_entry.size_bytes
                
            # Add new entry
            self.memory_cache[key] = entry
            self.current_memory_usage += size_bytes
            
            # Save to persistent cache if requested
            if persistent:
                self._set_persistent(module, key, value, ttl)
                
        self.logger.debug(f"Cache set: {module}.{operation}")
        
    def _get_persistent(self, module: str, key: str) -> Any:
        """Get value from persistent cache"""
        try:
            cache_dir = self.persistent_dirs.get(module, self.persistent_dirs["general"])
            cache_file = cache_dir / f"{key}.pkl"
            
            if not cache_file.exists():
                return None
                
            with open(cache_file, 'rb') as f:
                data = pickle.load(f)
                
            # Check if expired
            if 'ttl' in data and data['ttl']:
                if time.time() > (data['timestamp'] + data['ttl']):
                    cache_file.unlink()  # Remove expired file
                    return None
                    
            return data['value']
            
        except Exception as e:
            self.logger.error(f"Failed to get persistent cache {key}: {e}")
            return None
            
    def _set_persistent(self, module: str, key: str, value: Any, ttl: Optional[float]) -> None:
        """Set value in persistent cache"""
        try:
            cache_dir = self.persistent_dirs.get(module, self.persistent_dirs["general"])
            cache_file = cache_dir / f"{key}.pkl"
            
            data = {
                'value': value,
                'timestamp': time.time(),
                'ttl': ttl,
                'module': module
            }
            
            with open(cache_file, 'wb') as f:
                pickle.dump(data, f)
                
        except Exception as e:
            self.logger.error(f"Failed to set persistent cache {key}: {e}")
            
    def invalidate(self, module: str, operation: str = None, **kwargs) -> None:
        """Invalidate cache entries"""
        
        with self.lock:
            if operation:
                # Invalidate specific entry
                key = self._generate_key(module, operation, **kwargs)
                if key in self.memory_cache:
                    entry = self.memory_cache.pop(key)
                    self.current_memory_usage -= entry.size_bytes
                    
                # Remove from persistent cache
                self._remove_persistent(module, key)
                
            else:
                # Invalidate all entries for module
                keys_to_remove = []
                for key, entry in self.memory_cache.items():
                    if key.startswith(f"{module}:"):
                        keys_to_remove.append(key)
                        
                for key in keys_to_remove:
                    entry = self.memory_cache.pop(key)
                    self.current_memory_usage -= entry.size_bytes
                    
                # Clear persistent cache for module
                self._clear_persistent_module(module)
                
        self.logger.info(f"Invalidated cache for {module}" + (f".{operation}" if operation else ""))
        
    def _remove_persistent(self, module: str, key: str) -> None:
        """Remove persistent cache file"""
        try:
            cache_dir = self.persistent_dirs.get(module, self.persistent_dirs["general"])
            cache_file = cache_dir / f"{key}.pkl"
            if cache_file.exists():
                cache_file.unlink()
        except Exception as e:
            self.logger.error(f"Failed to remove persistent cache {key}: {e}")
            
    def _clear_persistent_module(self, module: str) -> None:
        """Clear all persistent cache files for a module"""
        try:
            cache_dir = self.persistent_dirs.get(module, self.persistent_dirs["general"])
            for cache_file in cache_dir.glob("*.pkl"):
                cache_file.unlink()
        except Exception as e:
            self.logger.error(f"Failed to clear persistent cache for {module}: {e}")
            
    def cleanup(self) -> None:
        """Clean up expired entries and optimize cache"""
        with self.lock:
            self._cleanup_expired()
            
            # Clean up persistent cache
            for module, cache_dir in self.persistent_dirs.items():
                try:
                    for cache_file in cache_dir.glob("*.pkl"):
                        try:
                            with open(cache_file, 'rb') as f:
                                data = pickle.load(f)
                                
                            # Check if expired
                            if 'ttl' in data and data['ttl']:
                                if time.time() > (data['timestamp'] + data['ttl']):
                                    cache_file.unlink()
                                    
                        except Exception:
                            # Remove corrupted files
                            cache_file.unlink()
                            
                except Exception as e:
                    self.logger.error(f"Failed to clean up {module} cache: {e}")
                    
            self._save_cache_metadata()
            
        self.logger.info("Cache cleanup completed")
        
    def get_statistics(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self.lock:
            persistent_stats = {}
            
            for module, cache_dir in self.persistent_dirs.items():
                file_count = len(list(cache_dir.glob("*.pkl")))
                total_size = sum(f.stat().st_size for f in cache_dir.glob("*.pkl"))
                persistent_stats[module] = {
                    "file_count": file_count,
                    "size_mb": total_size / 1024 / 1024
                }
                
            return {
                "memory_cache": {
                    "entries": len(self.memory_cache),
                    "size_mb": self.current_memory_usage / 1024 / 1024,
                    "max_size_mb": self.max_memory_bytes / 1024 / 1024,
                    "usage_percent": (self.current_memory_usage / self.max_memory_bytes) * 100
                },
                "persistent_cache": persistent_stats,
                "default_ttl": self.default_ttl
            }
            
    def clear_all(self) -> None:
        """Clear all cache data"""
        with self.lock:
            self.memory_cache.clear()
            self.current_memory_usage = 0
            
            # Clear persistent cache
            for cache_dir in self.persistent_dirs.values():
                for cache_file in cache_dir.glob("*.pkl"):
                    cache_file.unlink()
                    
        self.logger.info("Cleared all cache data")