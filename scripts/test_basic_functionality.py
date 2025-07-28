#!/usr/bin/env python3
"""
Test basic SAGE functionality without external dependencies
"""

import sys
import os
import asyncio
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_basic_imports():
    """Test if basic modules can be imported"""
    print("🧪 Testing basic imports...")
    
    try:
        from core.config_manager import ConfigManager
        from core.cache_manager import CacheManager
        from core.logger import Logger
        from core.event_bus import EventBus
        from modules import BaseModule, Event, EventType
        
        print("✅ All basic modules imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False

def test_config_manager():
    """Test configuration manager"""
    print("\n🧪 Testing configuration manager...")
    
    try:
        from core.config_manager import ConfigManager
        
        config = ConfigManager("config.yaml")
        if config.load_config():
            print("✅ Configuration loaded successfully")
            return True
        else:
            print("❌ Configuration loading failed")
            return False
    except Exception as e:
        print(f"❌ Configuration manager error: {e}")
        return False

def test_logger():
    """Test logger functionality"""
    print("\n🧪 Testing logger...")
    
    try:
        from core.logger import Logger
        import tempfile
        
        with tempfile.TemporaryDirectory() as temp_dir:
            logger = Logger("TEST", log_dir=temp_dir)
            logger.info("Test message")
            
            print("✅ Logger works correctly")
            return True
    except Exception as e:
        print(f"❌ Logger error: {e}")
        return False

async def test_event_bus():
    """Test event bus functionality"""
    print("\n🧪 Testing event bus...")
    
    try:
        from core.event_bus import EventBus
        from modules import Event, EventType
        
        bus = EventBus()
        await bus.start()
        
        # Create a test event
        event = Event(
            type=EventType.VOICE_COMMAND,
            data={"command": "test"},
            source_module="test"
        )
        
        bus.emit(event)
        
        # Give it a moment to process
        await asyncio.sleep(0.1)
        
        await bus.stop()
        
        print("✅ Event bus works correctly")
        return True
    except Exception as e:
        print(f"❌ Event bus error: {e}")
        return False

def test_base_module():
    """Test base module functionality"""
    print("\n🧪 Testing base module...")
    
    try:
        from modules import BaseModule, EventType
        
        class TestModule(BaseModule):
            async def initialize(self) -> bool:
                return True
            
            async def shutdown(self) -> None:
                pass
            
            async def handle_event(self, event) -> None:
                pass
        
        module = TestModule("test_module")
        assert module.name == "test_module"
        assert not module.is_loaded
        
        print("✅ Base module works correctly")
        return True
    except Exception as e:
        print(f"❌ Base module error: {e}")
        return False

async def test_main_application_structure():
    """Test main application can be imported"""
    print("\n🧪 Testing main application structure...")
    
    try:
        # Test if main.py has correct structure without running it
        with open("main.py", "r") as f:
            content = f.read()
        
        required_classes = ["SAGEApplication"]
        required_methods = ["initialize", "shutdown", "run"]
        
        missing = []
        for item in required_classes + required_methods:
            if item not in content:
                missing.append(item)
        
        if missing:
            print(f"❌ Missing in main.py: {missing}")
            return False
        else:
            print("✅ Main application structure is correct")
            return True
            
    except Exception as e:
        print(f"❌ Main application error: {e}")
        return False

def test_voice_module_structure():
    """Test voice module structure"""
    print("\n🧪 Testing voice module structure...")
    
    try:
        # Check if voice module can be imported
        from modules.voice import VoiceModule
        
        # Create instance
        voice_module = VoiceModule()
        assert voice_module.name == "voice"
        assert hasattr(voice_module, 'initialize')
        assert hasattr(voice_module, 'shutdown')
        assert hasattr(voice_module, 'handle_event')
        
        print("✅ Voice module structure is correct")
        return True
    except ImportError as e:
        print(f"❌ Voice module import failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Voice module error: {e}")
        return False

async def main():
    """Run all basic functionality tests"""
    print("🧪 Testing Basic SAGE Functionality")
    print("=" * 60)
    
    sync_tests = [
        test_basic_imports,
        test_config_manager,
        test_logger,
        test_base_module,
        test_voice_module_structure
    ]
    
    async_tests = [
        test_event_bus,
        test_main_application_structure
    ]
    
    passed = 0
    total = len(sync_tests) + len(async_tests)
    
    # Run synchronous tests
    for test in sync_tests:
        if test():
            passed += 1
    
    # Run asynchronous tests
    for test in async_tests:
        if await test():
            passed += 1
    
    print("\n" + "=" * 60)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 Basic SAGE functionality is working!")
        print("✅ Issues #1 and #5 can be marked as COMPLETE")
        return True
    else:
        print("⚠️  Some basic functionality needs attention")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)