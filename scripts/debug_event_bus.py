#!/usr/bin/env python3
"""
Debug the event bus issue
"""

import sys
import asyncio
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


async def test_import():
    """Test if we can import everything"""
    print("Testing imports...")
    
    try:
        from core.event_bus import EventBus, EventFilter
        print("✅ EventBus imported")
        
        from modules import Event, EventType, BaseModule
        print("✅ Modules imported")
        
        return True
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False


async def test_creation():
    """Test if we can create EventBus"""
    print("\nTesting EventBus creation...")
    
    try:
        from core.event_bus import EventBus
        bus = EventBus(max_queue_size=5)
        print("✅ EventBus created")
        return bus
    except Exception as e:
        print(f"❌ Creation failed: {e}")
        return None


async def test_start_stop():
    """Test start/stop without processing"""
    print("\nTesting start/stop...")
    
    try:
        from core.event_bus import EventBus
        bus = EventBus(max_queue_size=5)
        
        print("Starting bus...")
        await bus.start()
        print("✅ Bus started")
        
        print("Getting stats...")
        stats = bus.get_statistics()
        print(f"Stats: {stats}")
        
        print("Stopping bus...")
        await bus.stop()
        print("✅ Bus stopped")
        
        return True
    except Exception as e:
        print(f"❌ Start/stop failed: {e}")
        return False


async def main():
    """Run debug tests"""
    print("🐛 Debugging Event Bus")
    print("=" * 30)
    
    if not await test_import():
        return False
        
    if not await test_creation():
        return False
        
    if not await test_start_stop():
        return False
        
    print("\n🎉 All debug tests passed!")
    return True


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)