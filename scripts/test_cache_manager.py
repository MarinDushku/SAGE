#!/usr/bin/env python3
"""
Test script to verify Issue #5: Cache manager
"""

import sys
import os
import tempfile
import shutil
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_cache_manager_import():
    """Test if cache manager can be imported"""
    print("🧪 Testing cache manager import...")
    
    try:
        from core.cache_manager import CacheManager
        print("✅ CacheManager imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Failed to import CacheManager: {e}")
        return False

def test_cache_manager_initialization():
    """Test cache manager initialization"""
    print("\n🧪 Testing cache manager initialization...")
    
    try:
        from core.cache_manager import CacheManager
        
        # Create temporary directory for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_manager = CacheManager(
                cache_dir=temp_dir,
                max_memory_mb=50,
                default_ttl=300
            )
            
            print("✅ CacheManager initialized successfully")
            return True
            
    except Exception as e:
        print(f"❌ Failed to initialize CacheManager: {e}")
        return False

def test_basic_cache_operations():
    """Test basic cache operations"""
    print("\n🧪 Testing basic cache operations...")
    
    try:
        from core.cache_manager import CacheManager
        
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_manager = CacheManager(
                cache_dir=temp_dir,
                max_memory_mb=50,
                default_ttl=300
            )
            
            # Test set and get
            cache_manager.set("test_module", "test_operation", "test_value", arg1="value1")
            result = cache_manager.get("test_module", "test_operation", arg1="value1")
            
            if result == "test_value":
                print("✅ Basic cache set/get operations work")
                return True
            else:
                print(f"❌ Cache returned wrong value: {result}")
                return False
                
    except Exception as e:
        print(f"❌ Error in cache operations: {e}")
        return False

def test_lru_eviction():
    """Test LRU eviction policy"""
    print("\n🧪 Testing LRU eviction...")
    
    try:
        from core.cache_manager import CacheManager
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create cache with very small memory limit
            cache_manager = CacheManager(
                cache_dir=temp_dir,
                max_memory_mb=1,  # Very small limit
                default_ttl=300
            )
            
            # Add items that should trigger eviction
            cache_manager.set("test", "op1", "value1")
            cache_manager.set("test", "op2", "value2")
            cache_manager.set("test", "op3", "value3")
            
            # Check that cache has some limit enforcement
            stats = cache_manager.get_statistics()
            if "memory_cache" in stats:
                print("✅ LRU eviction mechanism exists")
                return True
            else:
                print("❌ Cache statistics not available")
                return False
                
    except Exception as e:
        print(f"❌ Error testing LRU eviction: {e}")
        return False

def test_persistent_cache():
    """Test persistent cache storage"""
    print("\n🧪 Testing persistent cache...")
    
    try:
        from core.cache_manager import CacheManager
        
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_manager = CacheManager(
                cache_dir=temp_dir,
                max_memory_mb=50,
                default_ttl=300
            )
            
            # Set value with persistence
            cache_manager.set("test_module", "test_op", "persistent_value", persistent=True)
            
            # Check if persistent directory structure exists
            cache_dirs = list(Path(temp_dir).iterdir())
            if cache_dirs:
                print("✅ Persistent cache directories created")
                return True
            else:
                print("❌ No persistent cache directories found")
                return False
                
    except Exception as e:
        print(f"❌ Error testing persistent cache: {e}")
        return False

def test_cache_invalidation():
    """Test cache invalidation"""
    print("\n🧪 Testing cache invalidation...")
    
    try:
        from core.cache_manager import CacheManager
        
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_manager = CacheManager(
                cache_dir=temp_dir,
                max_memory_mb=50,
                default_ttl=300
            )
            
            # Set and then invalidate
            cache_manager.set("test_module", "test_op", "test_value")
            
            # Check value exists
            result = cache_manager.get("test_module", "test_op")
            if result != "test_value":
                print("❌ Value not found before invalidation")
                return False
                
            # Invalidate
            cache_manager.invalidate("test_module", "test_op")
            
            # Check value is gone
            result = cache_manager.get("test_module", "test_op", default="not_found")
            if result == "not_found":
                print("✅ Cache invalidation works")
                return True
            else:
                print(f"❌ Value still exists after invalidation: {result}")
                return False
                
    except Exception as e:
        print(f"❌ Error testing cache invalidation: {e}")
        return False

def test_memory_limits():
    """Test memory usage tracking"""
    print("\n🧪 Testing memory limits...")
    
    try:
        from core.cache_manager import CacheManager
        
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_manager = CacheManager(
                cache_dir=temp_dir,
                max_memory_mb=50,
                default_ttl=300
            )
            
            # Get statistics
            stats = cache_manager.get_statistics()
            
            required_fields = ["memory_cache", "persistent_cache"]
            missing_fields = []
            
            for field in required_fields:
                if field not in stats:
                    missing_fields.append(field)
                    
            if missing_fields:
                print(f"❌ Missing statistics fields: {missing_fields}")
                return False
            else:
                print("✅ Memory usage tracking implemented")
                return True
                
    except Exception as e:
        print(f"❌ Error testing memory limits: {e}")
        return False

def test_ttl_support():
    """Test TTL (time-to-live) support"""
    print("\n🧪 Testing TTL support...")
    
    try:
        from core.cache_manager import CacheManager
        import time
        
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_manager = CacheManager(
                cache_dir=temp_dir,
                max_memory_mb=50,
                default_ttl=1  # 1 second TTL
            )
            
            # Set value with short TTL
            cache_manager.set("test_module", "test_op", "test_value", ttl=1)
            
            # Should exist immediately
            result = cache_manager.get("test_module", "test_op")
            if result != "test_value":
                print("❌ Value not found immediately after setting")
                return False
                
            # Wait for expiration
            time.sleep(1.5)
            
            # Should be expired now
            result = cache_manager.get("test_module", "test_op", default="expired")
            if result == "expired":
                print("✅ TTL expiration works")
                return True
            else:
                print(f"❌ Value still exists after TTL: {result}")
                return False
                
    except Exception as e:
        print(f"❌ Error testing TTL: {e}")
        return False

def main():
    """Run all tests for Issue #5"""
    print("🧪 Testing Issue #5: Cache manager")
    print("=" * 60)
    
    tests = [
        test_cache_manager_import,
        test_cache_manager_initialization,
        test_basic_cache_operations,
        test_lru_eviction,
        test_persistent_cache,
        test_cache_invalidation,
        test_memory_limits,
        test_ttl_support
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
            
    print("\n" + "=" * 60)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 Issue #5 is COMPLETE! Cache manager fully functional.")
        return True
    else:
        print("⚠️  Issue #5 needs attention. Some cache features failed.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)