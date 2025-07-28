#!/usr/bin/env python3
"""
Comprehensive tests for the enhanced event bus system (Issue #2)
"""

import sys
import asyncio
import tempfile
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.event_bus import EventBus, EventFilter
from modules import BaseModule, Event, EventType


class TestModule(BaseModule):
    """Test module for event bus testing"""
    
    def __init__(self, name: str):
        super().__init__(name)
        self.received_events = []
        self.processing_time = 0.01  # Simulate processing time
        
    async def initialize(self) -> bool:
        self.is_loaded = True
        return True
        
    async def shutdown(self) -> None:
        self.is_loaded = False
        
    async def handle_event(self, event: Event) -> None:
        """Handle events and record them"""
        await asyncio.sleep(self.processing_time)  # Simulate work
        self.received_events.append(event)


async def test_priority_handling():
    """Test event priority handling"""
    print("🧪 Testing priority handling...")
    
    try:
        bus = EventBus(max_queue_size=100)
        await bus.start()
        
        module = TestModule("test_module")
        await module.initialize()
        
        bus.subscribe(EventType.VOICE_COMMAND, module)
        
        # Create events with different priorities
        low_priority = Event(
            type=EventType.VOICE_COMMAND,
            data={"command": "low"},
            source_module="test",
            priority=2
        )
        
        high_priority = Event(
            type=EventType.VOICE_COMMAND,
            data={"command": "high"},
            source_module="test",
            priority=9
        )
        
        medium_priority = Event(
            type=EventType.VOICE_COMMAND,
            data={"command": "medium"},
            source_module="test",
            priority=5
        )
        
        # Emit in reverse priority order
        bus.emit(low_priority)
        bus.emit(medium_priority)
        bus.emit(high_priority)
        
        # Give time to process
        await asyncio.sleep(0.2)
        
        await bus.stop()
        
        # Check that high priority was processed first
        if len(module.received_events) >= 3:
            first_event = module.received_events[0]
            if first_event.data["command"] == "high":
                print("✅ Priority handling works correctly")
                return True
            else:
                print(f"❌ Wrong priority order: {[e.data['command'] for e in module.received_events]}")
                return False
        else:
            print(f"❌ Not all events processed: {len(module.received_events)}/3")
            return False
            
    except Exception as e:
        print(f"❌ Priority handling test failed: {e}")
        return False


async def test_event_filtering():
    """Test event filtering and routing"""
    print("\n🧪 Testing event filtering...")
    
    try:
        bus = EventBus()
        await bus.start()
        
        # Create test modules
        voice_module = TestModule("voice_module")
        nlp_module = TestModule("nlp_module")
        await voice_module.initialize()
        await nlp_module.initialize()
        
        # Create a filter for high priority voice events
        voice_filter = EventFilter(
            event_types={EventType.VOICE_COMMAND},
            min_priority=7
        )
        
        # Add filter and subscribe module
        bus.add_filter("high_priority_voice", voice_filter)
        bus.subscribe_with_filter("high_priority_voice", voice_module)
        
        # Regular subscription
        bus.subscribe(EventType.VOICE_COMMAND, nlp_module)
        
        # Create events
        low_priority_voice = Event(
            type=EventType.VOICE_COMMAND,
            data={"command": "low priority"},
            source_module="test",
            priority=3
        )
        
        high_priority_voice = Event(
            type=EventType.VOICE_COMMAND,
            data={"command": "high priority"},
            source_module="test",
            priority=8
        )
        
        # Emit events
        bus.emit(low_priority_voice)
        bus.emit(high_priority_voice)
        
        # Give time to process
        await asyncio.sleep(0.1)
        
        await bus.stop()
        
        # Check results
        # NLP module should receive all voice commands (2)
        # Voice module should only receive high priority (1)
        if (len(nlp_module.received_events) == 2 and 
            len(voice_module.received_events) == 1 and
            voice_module.received_events[0].data["command"] == "high priority"):
            print("✅ Event filtering works correctly")
            return True
        else:
            print(f"❌ Filtering failed - nlp: {len(nlp_module.received_events)}, voice: {len(voice_module.received_events)}")
            return False
            
    except Exception as e:
        print(f"❌ Event filtering test failed: {e}")
        return False


async def test_event_persistence():
    """Test event persistence for critical events"""
    print("\n🧪 Testing event persistence...")
    
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create bus with persistence enabled
            bus = EventBus(enable_persistence=True, persistence_dir=temp_dir)
            await bus.start()
            
            # Create critical event (priority 9)
            critical_event = Event(
                type=EventType.SYSTEM_SHUTDOWN,
                data={"reason": "critical error"},
                source_module="test",
                priority=9
            )
            
            # Emit critical event
            bus.emit(critical_event)
            
            # Give time to persist
            await asyncio.sleep(0.1)
            await bus.stop()
            
            # Check if file was created
            persistence_files = list(Path(temp_dir).glob("critical_event_*.pkl"))
            
            if persistence_files:
                print("✅ Event persistence works correctly")
                return True
            else:
                print("❌ No persistence files found")
                return False
                
    except Exception as e:
        print(f"❌ Event persistence test failed: {e}")
        return False


async def test_performance_optimization():
    """Test performance optimizations"""
    print("\n🧪 Testing performance optimizations...")
    
    try:
        bus = EventBus(max_queue_size=1000)
        await bus.start()
        
        module = TestModule("perf_module")
        module.processing_time = 0.001  # Very fast processing
        await module.initialize()
        
        bus.subscribe(EventType.VOICE_COMMAND, module)
        
        # Generate many events quickly
        start_time = time.time()
        num_events = 100
        
        for i in range(num_events):
            event = Event(
                type=EventType.VOICE_COMMAND,
                data={"command": f"test_{i}"},
                source_module="perf_test",
                priority=5
            )
            bus.emit(event)
        
        # Wait for processing
        await asyncio.sleep(0.5)
        
        processing_time = time.time() - start_time
        await bus.stop()
        
        # Get performance metrics
        metrics = bus.get_performance_metrics()
        
        # Check results
        events_processed = len(module.received_events)
        throughput = events_processed / processing_time
        
        if (events_processed >= num_events * 0.95 and  # At least 95% processed
            throughput > 100):  # At least 100 events/second
            print(f"✅ Performance optimization works - {throughput:.1f} events/sec")
            return True
        else:
            print(f"❌ Performance too low - {throughput:.1f} events/sec, {events_processed}/{num_events} processed")
            return False
            
    except Exception as e:
        print(f"❌ Performance test failed: {e}")
        return False


async def test_queue_management():
    """Test queue size limits and priority-based dropping"""
    print("\n🧪 Testing queue management...")
    
    try:
        # Small queue size for testing
        bus = EventBus(max_queue_size=3)
        await bus.start()
        
        # Don't add any subscribers so events stay in queue
        
        # Fill queue with low priority events
        for i in range(3):
            event = Event(
                type=EventType.VOICE_COMMAND,
                data={"command": f"low_{i}"},
                source_module="test",
                priority=2
            )
            bus.emit(event)
            
        # Add high priority event (should replace a low priority one)
        high_priority_event = Event(
            type=EventType.VOICE_COMMAND,
            data={"command": "high"},
            source_module="test",
            priority=8
        )
        bus.emit(high_priority_event)
        
        # Check queue status
        queue_status = bus.get_queue_status()
        stats = bus.get_statistics()
        
        await bus.stop()
        
        # Should have high priority event in queue and some dropped events
        if (queue_status["total_events"] <= 3 and
            stats["events_dropped"] > 0):
            print("✅ Queue management works correctly")
            return True
        else:
            print(f"❌ Queue management failed - queue: {queue_status['total_events']}, dropped: {stats['events_dropped']}")
            return False
            
    except Exception as e:
        print(f"❌ Queue management test failed: {e}")
        return False


async def test_statistics_and_monitoring():
    """Test statistics and monitoring functionality"""
    print("\n🧪 Testing statistics and monitoring...")
    
    try:
        bus = EventBus()
        await bus.start()
        
        module = TestModule("stats_module")
        await module.initialize()
        
        bus.subscribe(EventType.VOICE_COMMAND, module)
        
        # Create filter
        test_filter = EventFilter(event_types={EventType.VOICE_COMMAND})
        bus.add_filter("test_filter", test_filter)
        
        # Emit some events
        for i in range(5):
            event = Event(
                type=EventType.VOICE_COMMAND,
                data={"command": f"test_{i}"},
                source_module="test",
                priority=5
            )
            bus.emit(event)
            
        # Wait for processing
        await asyncio.sleep(0.1)
        
        # Get statistics
        stats = bus.get_statistics()
        performance = bus.get_performance_metrics()
        queue_status = bus.get_queue_status()
        
        await bus.stop()
        
        # Check that we have comprehensive statistics
        required_stats = [
            "queue_size", "total_subscribers", "events_processed",
            "avg_processing_time_ms", "active_filters"
        ]
        
        missing_stats = []
        for stat in required_stats:
            if stat not in stats:
                missing_stats.append(stat)
                
        if not missing_stats and stats["events_processed"] > 0:
            print("✅ Statistics and monitoring work correctly")
            return True
        else:
            print(f"❌ Statistics incomplete - missing: {missing_stats}")
            return False
            
    except Exception as e:
        print(f"❌ Statistics test failed: {e}")
        return False


async def test_error_handling():
    """Test error handling and recovery"""
    print("\n🧪 Testing error handling...")
    
    try:
        bus = EventBus()
        await bus.start()
        
        # Create a module that will throw errors
        class ErrorModule(TestModule):
            async def handle_event(self, event: Event) -> None:
                if "error" in event.data.get("command", ""):
                    raise Exception("Test error")
                await super().handle_event(event)
        
        error_module = ErrorModule("error_module")
        normal_module = TestModule("normal_module")
        
        await error_module.initialize()
        await normal_module.initialize()
        
        bus.subscribe(EventType.VOICE_COMMAND, error_module)
        bus.subscribe(EventType.VOICE_COMMAND, normal_module)
        
        # Emit events that will cause errors and normal events
        error_event = Event(
            type=EventType.VOICE_COMMAND,
            data={"command": "error_command"},
            source_module="test",
            priority=5
        )
        
        normal_event = Event(
            type=EventType.VOICE_COMMAND,
            data={"command": "normal_command"},
            source_module="test",
            priority=5
        )
        
        bus.emit(error_event)
        bus.emit(normal_event)
        
        # Wait for processing
        await asyncio.sleep(0.1)
        
        await bus.stop()
        
        # Normal module should still receive events despite errors in error_module
        if len(normal_module.received_events) == 2:
            print("✅ Error handling works correctly")
            return True
        else:
            print(f"❌ Error handling failed - normal module received {len(normal_module.received_events)} events")
            return False
            
    except Exception as e:
        print(f"❌ Error handling test failed: {e}")
        return False


async def main():
    """Run all enhanced event bus tests"""
    print("🧪 Testing Enhanced Event Bus System (Issue #2)")
    print("=" * 60)
    
    tests = [
        test_priority_handling,
        test_event_filtering,
        test_event_persistence,
        test_performance_optimization,
        test_queue_management,
        test_statistics_and_monitoring,
        test_error_handling
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if await test():
            passed += 1
            
    print("\n" + "=" * 60)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 Issue #2 is COMPLETE! Enhanced event bus fully functional.")
        print("\n✅ New Features Working:")
        print("   - Priority-based event processing")
        print("   - Event filtering and routing")
        print("   - Critical event persistence")
        print("   - Performance optimizations")
        print("   - Queue management with limits")
        print("   - Comprehensive statistics")
        print("   - Robust error handling")
        return True
    else:
        print("⚠️  Issue #2 needs attention. Some features failed.")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)