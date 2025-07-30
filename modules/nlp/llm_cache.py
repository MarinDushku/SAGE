"""
LLM Response Cache - Intelligent caching system for LLM responses
"""

import asyncio
import json
import time
import hashlib
import logging
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, asdict
from collections import OrderedDict
from pathlib import Path
import re

# Try to import sentence transformers for semantic similarity
try:
    from sentence_transformers import SentenceTransformer
    import numpy as np
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    SentenceTransformer = None
    np = None


@dataclass
class CacheConfig:
    """Configuration for LLM cache"""
    max_size: int = 1000
    ttl_seconds: int = 3600  # 1 hour default
    similarity_threshold: float = 0.85
    enable_similarity_matching: bool = True
    persistent: bool = True
    cache_file: str = "llm_cache.json"
    cleanup_interval: int = 300  # 5 minutes
    enable_compression: bool = False
    max_response_length: int = 10000
    enable_analytics: bool = True


@dataclass
class CacheEntry:
    """Single cache entry"""
    key: str
    prompt: str
    response: str
    metadata: Dict[str, Any]
    created_at: float
    accessed_at: float
    access_count: int
    ttl: int
    embedding: Optional[List[float]] = None
    
    def is_expired(self) -> bool:
        """Check if entry has expired"""
        return time.time() > (self.created_at + self.ttl)
    
    def update_access(self):
        """Update access information"""
        self.accessed_at = time.time()
        self.access_count += 1


class LLMCache:
    """Intelligent LLM response cache with semantic similarity"""
    
    def __init__(self, config: CacheConfig = None):
        self.config = config or CacheConfig()
        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.logger = logging.getLogger(__name__)
        
        # Statistics
        self.stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'evictions': 0,
            'total_entries': 0,
            'total_size_bytes': 0,
            'cleanup_runs': 0,
            'similarity_matches': 0
        }
        
        # Semantic similarity model
        self.similarity_model = None
        self.embeddings_cache: Dict[str, List[float]] = {}
        
        # Background tasks
        self.cleanup_task = None
        self.is_initialized = False
        
    async def initialize(self) -> bool:
        """Initialize the cache system"""
        try:
            self.logger.info("Initializing LLM Cache...")
            
            # Load similarity model if enabled and available
            if self.config.enable_similarity_matching and TRANSFORMERS_AVAILABLE:
                await self._load_similarity_model()
            
            # Load existing cache if persistent
            if self.config.persistent:
                await self.load_from_disk()
            
            # Start cleanup task
            self.cleanup_task = asyncio.create_task(self._cleanup_loop())
            
            self.is_initialized = True
            self.logger.info("LLM Cache initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize LLM Cache: {e}")
            return False
    
    async def shutdown(self):
        """Shutdown the cache system"""
        try:
            self.logger.info("Shutting down LLM Cache...")
            
            # Cancel cleanup task
            if self.cleanup_task:
                self.cleanup_task.cancel()
                try:
                    await self.cleanup_task
                except asyncio.CancelledError:
                    pass
            
            # Save cache to disk if persistent
            if self.config.persistent:
                await self.save_to_disk()
            
            self.is_initialized = False
            self.logger.info("LLM Cache shutdown complete")
            
        except Exception as e:
            self.logger.error(f"Error during LLM Cache shutdown: {e}")
    
    async def get(self, prompt: str, metadata: Dict[str, Any] = None) -> Optional[str]:
        """Get cached response for a prompt"""
        try:
            # Generate cache key
            key = self._generate_key(prompt, metadata or {})
            
            # Check exact match first
            if key in self.cache:
                entry = self.cache[key]
                
                # Check if expired
                if entry.is_expired():
                    del self.cache[key]
                    self.stats['evictions'] += 1
                    self.stats['total_entries'] -= 1
                else:
                    # Update access info and move to end (LRU)
                    entry.update_access()
                    self.cache.move_to_end(key)
                    self.stats['hits'] += 1
                    return entry.response
            
            # Try semantic similarity if enabled
            if self.config.enable_similarity_matching and self.similarity_model:
                similar_response = await self._find_similar_response(prompt, metadata or {})
                if similar_response:
                    self.stats['hits'] += 1
                    self.stats['similarity_matches'] += 1
                    return similar_response
            
            self.stats['misses'] += 1
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting cached response: {e}")
            self.stats['misses'] += 1
            return None
    
    async def set(self, prompt: str, response: str, metadata: Dict[str, Any] = None) -> bool:
        """Cache a response for a prompt"""
        try:
            # Validate inputs
            if not prompt or not response:
                return False
            
            if len(response) > self.config.max_response_length:
                self.logger.warning(f"Response too long for caching: {len(response)} chars")
                return False
            
            # Generate cache key
            key = self._generate_key(prompt, metadata or {})
            
            # Create entry
            entry = CacheEntry(
                key=key,
                prompt=prompt,
                response=response,
                metadata=metadata or {},
                created_at=time.time(),
                accessed_at=time.time(),
                access_count=1,
                ttl=self.config.ttl_seconds
            )
            
            # Generate embedding if similarity matching is enabled
            if self.config.enable_similarity_matching and self.similarity_model:
                entry.embedding = await self._generate_embedding(prompt)
            
            # Check if cache is full
            if len(self.cache) >= self.config.max_size:
                await self._evict_entries(1)
            
            # Add to cache
            self.cache[key] = entry
            self.stats['sets'] += 1
            self.stats['total_entries'] += 1
            self.stats['total_size_bytes'] += len(prompt) + len(response)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error setting cache entry: {e}")
            return False
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get cache statistics"""
        stats = self.stats.copy()
        
        # Calculate derived metrics
        total_requests = stats['hits'] + stats['misses']
        if total_requests > 0:
            stats['hit_rate'] = stats['hits'] / total_requests
            stats['miss_rate'] = stats['misses'] / total_requests
        else:
            stats['hit_rate'] = 0.0
            stats['miss_rate'] = 0.0
        
        # Cache health metrics
        stats['cache_size'] = len(self.cache)
        stats['cache_utilization'] = len(self.cache) / self.config.max_size
        stats['avg_entry_size'] = (
            stats['total_size_bytes'] / max(stats['total_entries'], 1)
        )
        
        # Add configuration info
        stats['config'] = {
            'max_size': self.config.max_size,
            'ttl_seconds': self.config.ttl_seconds,
            'similarity_enabled': self.config.enable_similarity_matching,
            'persistent': self.config.persistent
        }
        
        return stats
    
    async def clear(self):
        """Clear all cache entries"""
        self.cache.clear()
        self.embeddings_cache.clear()
        self.stats = {key: 0 for key in self.stats}
        self.logger.info("Cache cleared")
    
    async def optimize(self):
        """Optimize cache performance"""
        try:
            # Remove expired entries
            expired_keys = [
                key for key, entry in self.cache.items()
                if entry.is_expired()
            ]
            
            for key in expired_keys:
                del self.cache[key]
                self.stats['evictions'] += 1
                self.stats['total_entries'] -= 1
            
            # Clean up unused embeddings
            if self.embeddings_cache:
                active_prompts = {entry.prompt for entry in self.cache.values()}
                self.embeddings_cache = {
                    prompt: embedding
                    for prompt, embedding in self.embeddings_cache.items()
                    if prompt in active_prompts
                }
            
            self.logger.info(f"Cache optimized: removed {len(expired_keys)} expired entries")
            
        except Exception as e:
            self.logger.error(f"Error optimizing cache: {e}")
    
    async def save_to_disk(self):
        """Save cache to disk"""
        try:
            if not self.config.persistent:
                return
            
            cache_data = {
                'entries': [asdict(entry) for entry in self.cache.values()],
                'stats': self.stats,
                'config': asdict(self.config),
                'embeddings': self.embeddings_cache,
                'timestamp': time.time()
            }
            
            cache_file = Path(f"data/{self.config.cache_file}")
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2)
            
            self.logger.info(f"Cache saved to disk: {len(self.cache)} entries")
            
        except Exception as e:
            self.logger.error(f"Error saving cache to disk: {e}")
    
    async def load_from_disk(self):
        """Load cache from disk"""
        try:
            cache_file = Path(f"data/{self.config.cache_file}")
            if not cache_file.exists():
                return
            
            with open(cache_file, 'r') as f:
                cache_data = json.load(f)
            
            # Load entries
            self.cache.clear()
            for entry_data in cache_data.get('entries', []):
                entry = CacheEntry(**entry_data)
                # Skip expired entries
                if not entry.is_expired():
                    self.cache[entry.key] = entry
            
            # Load stats
            self.stats.update(cache_data.get('stats', {}))
            
            # Load embeddings
            self.embeddings_cache = cache_data.get('embeddings', {})
            
            self.logger.info(f"Cache loaded from disk: {len(self.cache)} entries")
            
        except Exception as e:
            self.logger.error(f"Error loading cache from disk: {e}")
    
    # Private helper methods
    def _generate_key(self, prompt: str, metadata: Dict[str, Any]) -> str:
        """Generate cache key from prompt and metadata"""
        # Normalize prompt
        normalized_prompt = re.sub(r'\s+', ' ', prompt.strip().lower())
        
        # Include relevant metadata in key
        key_metadata = {
            'model': metadata.get('model', ''),
            'temperature': metadata.get('temperature', ''),
            'max_tokens': metadata.get('max_tokens', '')
        }
        
        # Generate hash
        key_string = f"{normalized_prompt}|{json.dumps(key_metadata, sort_keys=True)}"
        return hashlib.sha256(key_string.encode()).hexdigest()[:16]
    
    async def _load_similarity_model(self):
        """Load sentence transformer model for similarity matching"""
        try:
            if not TRANSFORMERS_AVAILABLE:
                self.logger.warning("Sentence transformers not available for similarity matching")
                return
            
            # Use a lightweight model for efficiency
            model_name = 'all-MiniLM-L6-v2'
            self.similarity_model = SentenceTransformer(model_name)
            self.logger.info(f"Loaded similarity model: {model_name}")
            
        except Exception as e:
            self.logger.warning(f"Failed to load similarity model: {e}")
            self.similarity_model = None
    
    async def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text"""
        try:
            if not self.similarity_model:
                return []
            
            # Check cache first
            if text in self.embeddings_cache:
                return self.embeddings_cache[text]
            
            # Generate embedding
            embedding = self.similarity_model.encode(text).tolist()
            
            # Cache embedding
            self.embeddings_cache[text] = embedding
            
            return embedding
            
        except Exception as e:
            self.logger.error(f"Error generating embedding: {e}")
            return []
    
    async def _find_similar_response(self, prompt: str, metadata: Dict[str, Any]) -> Optional[str]:
        """Find similar cached response using semantic similarity"""
        try:
            if not self.similarity_model or not self.cache:
                return None
            
            # Generate embedding for query prompt
            query_embedding = await self._generate_embedding(prompt)
            if not query_embedding:
                return None
            
            best_similarity = 0.0
            best_response = None
            best_entry = None
            
            # Compare with cached entries
            for entry in self.cache.values():
                # Skip expired entries
                if entry.is_expired():
                    continue
                
                # Check metadata compatibility
                if not self._metadata_compatible(metadata, entry.metadata):
                    continue
                
                # Get or generate embedding for cached prompt
                if entry.embedding:
                    cached_embedding = entry.embedding
                else:
                    cached_embedding = await self._generate_embedding(entry.prompt)
                    entry.embedding = cached_embedding
                
                if not cached_embedding:
                    continue
                
                # Calculate cosine similarity
                similarity = self._calculate_similarity(query_embedding, cached_embedding)
                
                if similarity > best_similarity and similarity >= self.config.similarity_threshold:
                    best_similarity = similarity
                    best_response = entry.response
                    best_entry = entry
            
            # Update access info for best match
            if best_entry:
                best_entry.update_access()
                self.cache.move_to_end(best_entry.key)
                
                self.logger.debug(f"Found similar response with similarity {best_similarity:.3f}")
            
            return best_response
            
        except Exception as e:
            self.logger.error(f"Error finding similar response: {e}")
            return None
    
    def _calculate_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """Calculate cosine similarity between embeddings"""
        try:
            if not embedding1 or not embedding2:
                return 0.0
            
            # Convert to numpy arrays
            vec1 = np.array(embedding1)
            vec2 = np.array(embedding2)
            
            # Calculate cosine similarity
            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            similarity = dot_product / (norm1 * norm2)
            return float(similarity)
            
        except Exception as e:
            self.logger.error(f"Error calculating similarity: {e}")
            return 0.0
    
    def _metadata_compatible(self, metadata1: Dict[str, Any], metadata2: Dict[str, Any]) -> bool:
        """Check if metadata is compatible for cache matching"""
        # Key fields that must match
        key_fields = ['model', 'temperature', 'max_tokens']
        
        for field in key_fields:
            val1 = metadata1.get(field)
            val2 = metadata2.get(field)
            
            # Allow None/empty to match anything
            if val1 and val2 and val1 != val2:
                return False
        
        return True
    
    async def _evict_entries(self, count: int = 1):
        """Evict entries using LRU policy"""
        try:
            evicted = 0
            while len(self.cache) > 0 and evicted < count:
                # Remove least recently used (first in OrderedDict)
                key, entry = self.cache.popitem(last=False)
                self.stats['evictions'] += 1
                self.stats['total_entries'] -= 1
                self.stats['total_size_bytes'] -= len(entry.prompt) + len(entry.response)
                evicted += 1
                
                self.logger.debug(f"Evicted cache entry: {key}")
            
        except Exception as e:
            self.logger.error(f"Error evicting entries: {e}")
    
    async def _cleanup_loop(self):
        """Background cleanup loop"""
        while True:
            try:
                await asyncio.sleep(self.config.cleanup_interval)
                await self.optimize()
                self.stats['cleanup_runs'] += 1
                
                # Save to disk periodically if persistent
                if self.config.persistent:
                    await self.save_to_disk()
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in cleanup loop: {e}")


__all__ = ['LLMCache', 'CacheEntry', 'CacheConfig']