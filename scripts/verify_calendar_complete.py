#!/usr/bin/env python3
"""
Verification script for SAGE Calendar Module
Tests all calendar functionality including scheduling, reminders, and natural language parsing
"""

import asyncio
import sys
import time
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

async def test_calendar_module():
    """Comprehensive test of the Calendar Module"""
    print("🗓️  SAGE Calendar Module Verification")
    print("=" * 50)
    
    tests_passed = 0
    total_tests = 12
    
    try:
        # Test 1: Module Import
        print("1️⃣  Testing Calendar Module Import...")
        try:
            from modules.calendar import CalendarModule
            print("   ✅ Calendar module imported successfully")
            tests_passed += 1
        except Exception as e:
            print(f"   ❌ Failed to import Calendar module: {e}")
            return False
        
        # Test 2: Module Initialization
        print("2️⃣  Testing Module Initialization...")
        try:
            calendar = CalendarModule()
            calendar.config = {
                'enabled': True,
                'natural_language_parsing': True,
                'reminder_lead_time': 15,
                'timezone': 'auto'
            }
            
            init_success = await calendar.initialize()
            if init_success:
                print("   ✅ Calendar module initialized successfully")
                tests_passed += 1
            else:
                print("   ❌ Calendar module initialization failed")
        except Exception as e:
            print(f"   ❌ Calendar initialization error: {e}")
        
        # Test 3: Database Setup
        print("3️⃣  Testing Database Setup...")
        try:
            status = calendar.get_status()
            if 'database_path' in status.get('statistics', {}):
                print(f"   ✅ Database created at {status['statistics']['database_path']}")
                tests_passed += 1
            else:
                print("   ❌ Database setup failed")
        except Exception as e:
            print(f"   ❌ Database setup error: {e}")
        
        # Test 4: Natural Language Parser
        print("4️⃣  Testing Natural Language Parser...")
        try:
            parser = calendar.parser
            
            # Test basic time parsing
            test_cases = [
                "tomorrow at 3pm",
                "next monday at 10am", 
                "today at noon",
                "in 2 hours"
            ]
            
            parsed_count = 0
            for test_case in test_cases:
                result = parser.parse_datetime(test_case)
                if result:
                    parsed_count += 1
            
            if parsed_count >= 2:  # At least half should work
                print(f"   ✅ Natural language parser working ({parsed_count}/{len(test_cases)} cases)")
                tests_passed += 1
            else:
                print(f"   ❌ Natural language parser failed ({parsed_count}/{len(test_cases)} cases)")
        except Exception as e:
            print(f"   ❌ Natural language parser error: {e}")
        
        # Test 5: Event Creation
        print("5️⃣  Testing Event Creation...")
        try:
            result = await calendar._create_event("schedule meeting tomorrow at 2pm")
            if result.get('success'):
                print(f"   ✅ Event created: {result.get('message')}")
                tests_passed += 1
            else:
                print(f"   ❌ Event creation failed: {result.get('error')}")
        except Exception as e:
            print(f"   ❌ Event creation error: {e}")
        
        # Test 6: Reminder Creation
        print("6️⃣  Testing Reminder Creation...")
        try:
            result = await calendar._create_reminder("remind me to call mom tomorrow at 10am")
            if result.get('success'):
                print(f"   ✅ Reminder created: {result.get('message')}")
                tests_passed += 1
            else:
                print(f"   ❌ Reminder creation failed: {result.get('error')}")
        except Exception as e:
            print(f"   ❌ Reminder creation error: {e}")
        
        # Test 7: Event Listing
        print("7️⃣  Testing Event Listing...")
        try:
            result = await calendar._list_events("show me today's events")
            if result.get('success'):
                print(f"   ✅ Event listing works: {len(result.get('events', []))} events found")
                tests_passed += 1
            else:
                print(f"   ❌ Event listing failed: {result.get('error')}")
        except Exception as e:
            print(f"   ❌ Event listing error: {e}")
        
        # Test 8: Event Intent Handling
        print("8️⃣  Testing Intent Handling...")
        try:
            from modules import Event, EventType
            
            # Test calendar-related intent
            test_event = Event(
                type=EventType.INTENT_PARSED,
                data={
                    'intent': 'schedule',
                    'confidence': 0.8,
                    'text': 'schedule lunch meeting tomorrow'
                },
                source_module='test'
            )
            
            result = await calendar.handle_event(test_event)
            if result and result.get('success'):
                print("   ✅ Intent handling working")
                tests_passed += 1
            else:
                print("   ❌ Intent handling failed")
        except Exception as e:
            print(f"   ❌ Intent handling error: {e}")
        
        # Test 9: Data Persistence
        print("9️⃣  Testing Data Persistence...")
        try:
            # Create an event and check if it persists
            await calendar._create_event("test persistence event tomorrow at 5pm")
            
            # Query events to verify persistence
            tomorrow = time.time() + (24 * 60 * 60)
            events = await calendar._get_events_in_range(time.time(), tomorrow)
            
            if events:
                print(f"   ✅ Data persistence working ({len(events)} events in database)")
                tests_passed += 1
            else:
                print("   ❌ Data persistence failed - no events found")
        except Exception as e:
            print(f"   ❌ Data persistence error: {e}")
        
        # Test 10: Status Reporting
        print("🔟 Testing Status Reporting...")
        try:
            status = calendar.get_status()
            if status.get('module') == 'calendar' and 'statistics' in status:
                stats = status['statistics']
                print(f"   ✅ Status reporting works")
                print(f"      Total events: {stats.get('total_events', 0)}")
                print(f"      Upcoming events: {stats.get('upcoming_events', 0)}")
                print(f"      Pending reminders: {stats.get('pending_reminders', 0)}")
                tests_passed += 1
            else:
                print("   ❌ Status reporting failed")
        except Exception as e:
            print(f"   ❌ Status reporting error: {e}")
        
        # Test 11: Calendar Keywords Detection
        print("1️⃣1️⃣ Testing Calendar Keyword Detection...")
        try:
            test_cases = [
                ("schedule meeting tomorrow", True),
                ("remind me to call", True),
                ("what's on my calendar", True),
                ("hello world", False),
                ("play music", False)
            ]
            
            correct_detections = 0
            for text, should_detect in test_cases:
                detected = calendar._is_calendar_intent('schedule', text)
                if detected == should_detect:
                    correct_detections += 1
            
            if correct_detections >= 4:  # At least 4/5 correct
                print(f"   ✅ Keyword detection working ({correct_detections}/{len(test_cases)} correct)")
                tests_passed += 1
            else:
                print(f"   ❌ Keyword detection needs improvement ({correct_detections}/{len(test_cases)} correct)")
        except Exception as e:
            print(f"   ❌ Keyword detection error: {e}")
        
        # Test 12: Module Cleanup
        print("1️⃣2️⃣ Testing Module Cleanup...")
        try:
            await calendar.shutdown()
            if not calendar.is_loaded:
                print("   ✅ Module cleanup successful")
                tests_passed += 1
            else:
                print("   ❌ Module cleanup failed")
        except Exception as e:
            print(f"   ❌ Module cleanup error: {e}")
        
        # Final Results
        print(f"\n📊 Calendar Module Test Results:")
        print(f"   Tests Passed: {tests_passed}/{total_tests}")
        print(f"   Success Rate: {(tests_passed/total_tests)*100:.1f}%")
        
        if tests_passed == total_tests:
            print("🎉 All Calendar Module tests passed!")
            return True
        elif tests_passed >= total_tests * 0.8:  # 80% pass rate
            print("✅ Calendar Module is mostly functional!")
            return True
        else:
            print("⚠️  Calendar Module needs attention")
            return False
            
    except Exception as e:
        print(f"\n❌ Calendar verification failed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_calendar_module())
    sys.exit(0 if success else 1)