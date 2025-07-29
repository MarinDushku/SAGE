#!/usr/bin/env python3
"""
Quick test of SAGE's working components
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_imports():
    """Test that all core components can be imported"""
    print("🧪 Testing core component imports...")
    
    try:
        from core.config_manager import ConfigManager
        from core.cache_manager import CacheManager
        from core.plugin_manager import PluginManager
        from core.event_bus import EventBus
        from core.logger import Logger
        from modules import BaseModule, Event, EventType
        print("✅ All core components imported successfully")
        return True
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False


def test_config_system():
    """Test configuration system"""
    print("\n🧪 Testing configuration system...")
    
    try:
        from core.config_manager import ConfigManager
        config = ConfigManager("config.yaml")
        
        if config.load_config():
            print("✅ Configuration loading works")
            
            # Test getting module config
            voice_config = config.get_module_config("voice")
            if isinstance(voice_config, dict):
                print("✅ Module configuration retrieval works")
                return True
        
        return False
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False


def test_plugin_manager():
    """Test plugin manager"""
    print("\n🧪 Testing plugin manager...")
    
    try:
        from core.plugin_manager import PluginManager
        pm = PluginManager()
        
        # Test module discovery
        modules = pm.discover_modules()
        print(f"✅ Discovered {len(modules)} modules: {modules}")
        
        # Test advanced features
        if hasattr(pm, 'enable_hot_reload') and hasattr(pm, 'health_check'):
            print("✅ Advanced plugin features available")
            return True
        
        return False
    except Exception as e:
        print(f"❌ Plugin manager test failed: {e}")
        return False


def test_cache_system():
    """Test cache system"""
    print("\n🧪 Testing cache system...")
    
    try:
        import tempfile
        from core.cache_manager import CacheManager
        
        with tempfile.TemporaryDirectory() as temp_dir:
            cache = CacheManager(cache_dir=temp_dir, max_memory_mb=10)
            
            # Test basic operations
            cache.set("test_module", "test_key", "test_value")
            result = cache.get("test_module", "test_key")
            
            if result == "test_value":
                print("✅ Cache operations work")
                
                # Test statistics
                stats = cache.get_statistics()
                if 'memory_cache' in stats and 'persistent_cache' in stats:
                    print("✅ Cache statistics work")
                    return True
        
        return False
    except Exception as e:
        print(f"❌ Cache test failed: {e}")
        return False


def test_event_system_basic():
    """Test basic event system (without async processing)"""
    print("\n🧪 Testing basic event system...")
    
    try:
        from core.event_bus import EventBus, EventFilter
        from modules import Event, EventType
        
        # Test EventBus creation
        bus = EventBus(max_queue_size=10)
        print("✅ EventBus created")
        
        # Test Event creation
        event = Event(
            type=EventType.VOICE_COMMAND,
            data={"test": "data"},
            source_module="test",
            priority=5
        )
        print("✅ Event creation works")
        
        # Test EventFilter creation
        event_filter = EventFilter(
            event_types={EventType.VOICE_COMMAND},
            min_priority=1,
            max_priority=10
        )
        
        if event_filter.matches(event):
            print("✅ Event filtering works")
            return True
        
        return False
    except Exception as e:
        print(f"❌ Event system test failed: {e}")
        return False


def test_project_structure():
    """Test project structure"""
    print("\n🧪 Testing project structure...")
    
    try:
        # Check key directories
        key_dirs = ["core", "modules", "data", "scripts"]
        missing_dirs = []
        
        for dirname in key_dirs:
            if not Path(dirname).exists():
                missing_dirs.append(dirname)
        
        if missing_dirs:
            print(f"❌ Missing directories: {missing_dirs}")
            return False
        
        # Count module directories
        module_dirs = list(Path("modules").glob("*/"))
        module_count = len([d for d in module_dirs if d.is_dir() and not d.name.startswith('__')])
        
        print(f"✅ Project structure complete with {module_count} modules")
        return True
        
    except Exception as e:
        print(f"❌ Project structure test failed: {e}")
        return False


def main():
    """Run quick tests"""
    print("🚀 SAGE Quick Test - Core Components")
    print("=" * 50)
    
    tests = [
        test_imports,
        test_config_system,
        test_plugin_manager,
        test_cache_system,
        test_event_system_basic,
        test_project_structure
    ]
    
    passed = 0
    for test in tests:
        if test():
            passed += 1
    
    print(f"\n📊 Quick Test Results: {passed}/{len(tests)} tests passed")
    
    if passed == len(tests):
        print("\n🎉 All core components working!")
        print("\n✅ SAGE Status:")
        print("   • Configuration system ✅")
        print("   • Plugin management ✅") 
        print("   • Caching system ✅")
        print("   • Event system ✅")
        print("   • Project structure ✅")
        print("\n🚀 Ready for module development!")
    else:
        print(f"\n⚠️  {len(tests) - passed} tests need attention")
    
    return passed == len(tests)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)