#!/usr/bin/env python3
"""
Test script for SAGE calendar functionality
"""

import asyncio
import sys
import os
sys.path.append('.')

from modules.nlp.nlp_module import NLPModule
from modules.calendar.calendar_module import CalendarModule

async def test_calendar_functionality():
    """Test calendar scheduling and querying functionality"""
    print("🧪 Testing SAGE Calendar Functionality")
    print("=" * 50)
    
    # Initialize modules
    nlp = NLPModule()
    calendar = CalendarModule()
    
    print("📋 Initializing modules...")
    
    # Initialize calendar module
    calendar_success = await calendar.initialize()
    print(f"Calendar module: {'✅ Success' if calendar_success else '❌ Failed'}")
    
    # Initialize NLP module
    nlp_success = await nlp.initialize()
    print(f"NLP module: {'✅ Success' if nlp_success else '❌ Failed'}")
    
    if not (calendar_success and nlp_success):
        print("❌ Module initialization failed")
        return
    
    # Connect NLP to calendar through event bus simulation
    nlp.event_bus = type('MockEventBus', (), {
        'subscribers': {
            'test': [calendar]
        }
    })()
    
    print("\n📅 Testing scheduling functionality...")
    
    # Test 1: Schedule a meeting
    schedule_text = "schedule team meeting tomorrow at 2pm"
    print(f"Test 1: '{schedule_text}'")
    
    result = await nlp.process_text(schedule_text)
    print(f"Response: {result['response']['text']}")
    print(f"Success: {'✅' if result['success'] else '❌'}")
    
    # Test 2: Check calendar
    check_text = "do i have any meetings tomorrow"
    print(f"\nTest 2: '{check_text}'")
    
    result = await nlp.process_text(check_text)
    print(f"Response: {result['response']['text']}")
    print(f"Success: {'✅' if result['success'] else '❌'}")
    
    # Test 3: Time query
    time_text = "what time is it"
    print(f"\nTest 3: '{time_text}'")
    
    result = await nlp.process_text(time_text)
    print(f"Response: {result['response']['text']}")
    print(f"Success: {'✅' if result['success'] else '❌'}")
    
    print("\n✅ Calendar functionality test completed!")
    
    # Cleanup
    await nlp.shutdown()
    await calendar.shutdown()

if __name__ == "__main__":
    asyncio.run(test_calendar_functionality())