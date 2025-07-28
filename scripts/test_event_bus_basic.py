#!/usr/bin/env python3
"""
Basic test for enhanced event bus system
"""

import sys
import asyncio
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.event_bus import EventBus, EventFilter
from modules import BaseModule, Event, EventType


class SimpleTestModule(BaseModule):
    def __init__(self, name: str):
        super().__init__(name)
        self.received_events = []
        
    async def initialize(self) -> bool:
        self.is_loaded = True
        return True
        
    async def shutdown(self) -> None:
        self.is_loaded = False
        
    async def handle_event(self, event: Event) -> None:
        self.received_events.append(event)


async def test_basic_functionality():
    """Test basic enhanced functionality"""
    print("🧪 Testing basic enhanced event bus...")
    
    try:
        # Create bus with enhanced features
        bus = EventBus(max_queue_size=10)
        await bus.start()
        
        # Create test module
        module = SimpleTestModule("test")
        await module.initialize()
        bus.subscribe(EventType.VOICE_COMMAND, module)
        
        # Test priority handling
        high_event = Event(
            type=EventType.VOICE_COMMAND,
            data={"test": "high"},
            source_module="test",
            priority=9
        )
        
        low_event = Event(
            type=EventType.VOICE_COMMAND,
            data={"test": "low"},
            source_module="test",
            priority=1
        )
        
        # Emit low priority first
        bus.emit(low_event)
        bus.emit(high_event)
        
        # Wait for processing
        await asyncio.sleep(0.1)
        
        # Get statistics
        stats = bus.get_statistics()
        queue_status = bus.get_queue_status()
        
        print(f"Events processed: {stats['events_processed']}")
        print(f"Queue size: {stats['queue_size']}")
        print(f"High priority events: {stats['high_priority_events']}")
        
        await bus.stop()
        
        # Check if high priority was processed first
        if (len(module.received_events) >= 2 and
            module.received_events[0].data["test"] == "high"):
            print("✅ Priority handling works!")
            return True
        else:
            print(f"❌ Priority order wrong: {[e.data['test'] for e in module.received_events]}")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False


async def test_filtering():
    """Test event filtering"""
    print("\n🧪 Testing event filtering...")
    
    try:
        bus = EventBus()
        await bus.start()
        
        module1 = SimpleTestModule("module1")
        module2 = SimpleTestModule("module2")
        await module1.initialize()
        await module2.initialize()
        
        # Create filter for high priority events
        high_priority_filter = EventFilter(min_priority=8)
        bus.add_filter("high_priority", high_priority_filter)
        
        # Subscribe module1 to all voice commands
        bus.subscribe(EventType.VOICE_COMMAND, module1)
        
        # Subscribe module2 only to high priority via filter
        bus.subscribe_with_filter("high_priority", module2)
        
        # Emit events
        low_event = Event(EventType.VOICE_COMMAND, {"test": "low"}, "test", priority=3)
        high_event = Event(EventType.VOICE_COMMAND, {"test": "high"}, "test", priority=9)
        
        bus.emit(low_event)
        bus.emit(high_event)
        
        await asyncio.sleep(0.1)
        await bus.stop()
        
        # module1 should get both, module2 should get only high priority
        if (len(module1.received_events) == 2 and 
            len(module2.received_events) == 1 and
            module2.received_events[0].data["test"] == "high"):
            print("✅ Filtering works!")
            return True
        else:
            print(f"❌ Filtering failed: m1={len(module1.received_events)}, m2={len(module2.received_events)}")
            return False
            
    except Exception as e:
        print(f"❌ Filtering test failed: {e}")
        return False


async def main():
    """Run basic tests"""
    print("🧪 Basic Enhanced Event Bus Tests")
    print("=" * 40)
    
    tests = [test_basic_functionality, test_filtering]
    
    passed = 0
    for test in tests:
        if await test():
            passed += 1
            
    print(f"\n📊 Results: {passed}/{len(tests)} tests passed")
    
    if passed == len(tests):
        print("🎉 Enhanced event bus is working!")
        return True
    else:
        print("⚠️  Some issues found")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)