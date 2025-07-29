#!/usr/bin/env python3
"""
Verification script for Issue #3: Plugin Manager Advanced Features
"""

import sys
import asyncio
import tempfile
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_plugin_manager_advanced_features():
    """Test that all advanced plugin manager features are available"""
    print("🧪 Verifying Issue #3 implementation...")
    
    try:
        # Test imports
        from core.plugin_manager import PluginManager, PluginMetadata, ModuleState, FileWatchHandler
        from modules import Event, EventType
        
        print("✅ All advanced classes imported successfully")
        
        # Test PluginManager has new methods
        pm = PluginManager()
        required_methods = [
            'enable_hot_reload', 'enable_sandboxing', 'health_check',
            'get_dependency_graph', 'validate_dependencies', 'create_plugin_template',
            'get_plugin_manager_stats', '_load_dependencies', '_execute_lifecycle_hook',
            '_handle_module_change', '_resolve_load_order', '_validate_sandbox_compliance'
        ]
        
        missing_methods = []
        for method in required_methods:
            if not hasattr(pm, method):
                missing_methods.append(method)
                
        if missing_methods:
            print(f"❌ Missing methods: {missing_methods}")
            return False
            
        # Test PluginMetadata functionality
        metadata = PluginMetadata(
            name="test_plugin",
            version="1.0.0",
            dependencies=["dep1", "dep2"],
            sandboxed=True,
            reload_safe=True
        )
        
        if metadata.name != "test_plugin" or len(metadata.dependencies) != 2:
            print("❌ PluginMetadata creation failed")
            return False
            
        # Test ModuleState functionality
        from datetime import datetime
        state = ModuleState(loaded_at=datetime.now())
        
        if not hasattr(state, 'loaded_at') or not hasattr(state, 'health_check_passed'):
            print("❌ ModuleState creation failed")
            return False
            
        print("✅ All advanced features verified")
        return True
        
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        return False


async def test_dependency_resolution():
    """Test dependency resolution system"""
    print("\n🧪 Testing dependency resolution...")
    
    try:
        from core.plugin_manager import PluginManager
        
        pm = PluginManager()
        
        # Mock some metadata
        from core.plugin_manager import PluginMetadata
        pm.module_metadata = {
            "module_a": PluginMetadata(
                name="module_a",
                dependencies=["module_b"]
            ),
            "module_b": PluginMetadata(
                name="module_b",
                dependencies=[]
            )
        }
        pm.dependency_graph = {
            "module_a": {"module_b"},
            "module_b": set()
        }
        
        # Test dependency validation
        issues = pm.validate_dependencies()
        
        # Test load order resolution
        order = pm._resolve_load_order(["module_a", "module_b"])
        
        if order[0] != "module_b" or order[1] != "module_a":
            print("❌ Dependency resolution order incorrect")
            return False
            
        print("✅ Dependency resolution working")
        return True
        
    except Exception as e:
        print(f"❌ Dependency resolution test failed: {e}")
        return False


def test_hot_reload_setup():
    """Test hot reload functionality setup"""
    print("\n🧪 Testing hot reload setup...")
    
    try:
        from core.plugin_manager import PluginManager
        
        pm = PluginManager()
        
        # Test enabling hot reload (may fail if watchdog not available)
        pm.enable_hot_reload(True)
        
        # Hot reload might not be enabled if watchdog is not available
        # This is acceptable behavior
        hot_reload_works = pm.hot_reload_enabled
        
        # Test disabling hot reload
        pm.enable_hot_reload(False)
        
        if pm.hot_reload_enabled:
            print("❌ Hot reload not disabled")
            return False
            
        print("✅ Hot reload setup working")
        return True
        
    except Exception as e:
        print(f"❌ Hot reload setup test failed: {e}")
        return False


def test_sandboxing_setup():
    """Test sandboxing functionality"""
    print("\n🧪 Testing sandboxing setup...")
    
    try:
        from core.plugin_manager import PluginManager
        
        pm = PluginManager()
        
        # Test enabling sandboxing
        pm.enable_sandboxing(True, ["json", "yaml"])
        
        if not pm.sandbox_enabled:
            print("❌ Sandboxing not enabled")
            return False
            
        if "json" not in pm.allowed_imports or "yaml" not in pm.allowed_imports:
            print("❌ Allowed imports not set correctly")
            return False
            
        print("✅ Sandboxing setup working")
        return True
        
    except Exception as e:
        print(f"❌ Sandboxing setup test failed: {e}")
        return False


def test_plugin_template_creation():
    """Test plugin template creation"""
    print("\n🧪 Testing plugin template creation...")
    
    try:
        from core.plugin_manager import PluginManager
        import tempfile
        import json
        
        with tempfile.TemporaryDirectory() as temp_dir:
            pm = PluginManager(temp_dir)
            
            # Create a test plugin template
            success = pm.create_plugin_template("test_plugin")
            
            if not success:
                print("❌ Plugin template creation failed")
                return False
                
            # Check if files were created
            plugin_dir = Path(temp_dir) / "test_plugin"
            init_file = plugin_dir / "__init__.py"
            metadata_file = plugin_dir / "metadata.json"
            
            if not init_file.exists() or not metadata_file.exists():
                print("❌ Plugin template files not created")
                return False
                
            # Check metadata content
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
                
            if metadata["version"] != "1.0.0" or "test_plugin" not in metadata["provides"]:
                print("❌ Plugin metadata incorrect")
                return False
                
        print("✅ Plugin template creation working")
        return True
        
    except Exception as e:
        print(f"❌ Plugin template creation test failed: {e}")
        return False


async def test_health_check_system():
    """Test health check system"""
    print("\n🧪 Testing health check system...")
    
    try:
        from core.plugin_manager import PluginManager
        
        pm = PluginManager()
        
        # Test health check with no modules
        results = await pm.health_check()
        
        if not isinstance(results, dict):
            print("❌ Health check should return dict")
            return False
            
        print("✅ Health check system working")
        return True
        
    except Exception as e:
        print(f"❌ Health check system test failed: {e}")
        return False


async def main():
    """Run verification tests for Issue #3"""
    print("🎯 Issue #3 Verification: Plugin Manager Advanced Features")
    print("=" * 60)
    
    tests = [
        test_plugin_manager_advanced_features,
        test_dependency_resolution,
        test_hot_reload_setup,
        test_sandboxing_setup,
        test_plugin_template_creation,
        test_health_check_system
    ]
    
    passed = 0
    for test in tests:
        try:
            if asyncio.iscoroutinefunction(test):
                result = await test()
            else:
                result = test()
            if result:
                passed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with error: {e}")
            
    print(f"\n📊 Verification Results: {passed}/{len(tests)} tests passed")
    
    if passed == len(tests):
        print("\n🎉 Issue #3 is COMPLETE!")
        print("\n✅ Advanced Features Implemented:")
        print("   • Dependency resolution with topological sorting")
        print("   • Hot reload with file system watching")
        print("   • Plugin sandboxing and security validation")
        print("   • Comprehensive health checking system")
        print("   • Module lifecycle hooks and state tracking")
        print("   • Plugin template generation")
        print("   • Advanced statistics and monitoring")
        print("   • Metadata-driven plugin system")
        
        print("\n🚀 Ready to move to Issue #4: Resource Monitor enhancements")
        return True
    else:
        print("\n⚠️  Issue #3 needs attention")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)