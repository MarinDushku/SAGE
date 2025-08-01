#!/usr/bin/env python3
"""
Test Simplified Calendar System - Interactive meeting scheduling
"""

import sys
import asyncio
from pathlib import Path
from datetime import datetime, timedelta

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from modules.calendar.meeting_manager import MeetingManager
from modules.calendar.conversation_state import ConversationStateManager
from modules.calendar.simplified_calendar import SimplifiedCalendarModule


async def test_basic_meeting_creation():
    """Test basic meeting creation without follow-up"""
    print("🗓️  Testing Basic Meeting Creation")
    print("=" * 40)
    
    manager = MeetingManager("data/test_calendar.db")
    
    # Test cases that should work without follow-up
    complete_requests = [
        "schedule team meeting tomorrow at 2pm",
        "book doctor appointment friday at 10am",
        "add standup monday at 9am online",
        "create interview thursday 3pm",
    ]
    
    for i, request in enumerate(complete_requests, 1):
        print(f"Test {i}: '{request}'")
        result = await manager.create_meeting_from_text(request)
        
        if result['success'] and not result.get('needs_followup'):
            meeting = result['meeting']
            print(f"  ✅ Created: {meeting.title} on {meeting.date} at {meeting.time}")
            print(f"  📋 Type: {meeting.meeting_type}, Location: {meeting.location or 'Not specified'}")
        elif result['success'] and result.get('needs_followup'):
            print(f"  ⚠️  Needs follow-up: {result['question']}")
        else:
            print(f"  ❌ Failed: {result.get('error', 'Unknown error')}")
        
        print()
    
    return True


async def test_interactive_conversation():
    """Test interactive conversation flow"""
    print("💬 Testing Interactive Conversation Flow")
    print("=" * 40)
    
    manager = MeetingManager("data/test_calendar.db")
    
    # Test incomplete request that needs follow-up
    request = "schedule meeting tomorrow"  # Missing time
    print(f"Initial request: '{request}'")
    
    result = await manager.create_meeting_from_text(request)
    
    if result['success'] and result.get('needs_followup'):
        conversation_id = result['conversation_id']
        print(f"✅ Started conversation: {conversation_id}")
        print(f"🤖 SAGE: {result['question']}")
        
        # Simulate user responses
        responses = ["2pm", "online", "https://zoom.us/j/123456"]
        
        for i, response in enumerate(responses):
            print(f"👤 User: {response}")
            
            result = await manager.continue_conversation(conversation_id, response)
            
            if result['success'] and result.get('needs_followup'):
                print(f"🤖 SAGE: {result['question']}")
            elif result['success'] and not result.get('needs_followup'):
                print(f"🎉 Meeting created: {result['confirmation']}")
                break
            else:
                print(f"❌ Error: {result.get('error')}")
                break
    else:
        print("❌ Expected follow-up conversation but didn't get one")
    
    print()


async def test_calendar_queries():
    """Test calendar query functionality"""
    print("📅 Testing Calendar Queries")
    print("=" * 40)
    
    manager = MeetingManager("data/test_calendar.db")
    
    # First, add some test meetings
    tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
    
    # Get meetings for tomorrow
    meetings = await manager.get_meetings_for_date(tomorrow)
    
    print(f"Meetings for tomorrow ({tomorrow}):")
    if meetings:
        for meeting in meetings:
            time_obj = datetime.strptime(meeting['time'], '%H:%M')
            formatted_time = time_obj.strftime('%I:%M %p').lstrip('0')
            location_info = f" ({meeting['location']})" if meeting['location'] else ""
            print(f"  • {meeting['title']} at {formatted_time}{location_info}")
    else:
        print("  No meetings scheduled")
    
    print()


async def test_natural_language_parsing():
    """Test natural language parsing accuracy"""
    print("🧠 Testing Natural Language Parsing")
    print("=" * 40)
    
    manager = MeetingManager("data/test_calendar.db")
    
    test_cases = [
        {
            'input': 'schedule team standup tomorrow at 9am',
            'expected': {'title': 'Team Standup', 'time': '09:00', 'meeting_type': 'in_person'}
        },
        {
            'input': 'book zoom call friday 2:30pm',
            'expected': {'title': 'Zoom Call', 'time': '14:30', 'meeting_type': 'online'}
        },
        {
            'input': 'add doctor appointment next monday 10am',
            'expected': {'title': 'Doctor Appointment', 'time': '10:00', 'meeting_type': 'in_person'}
        },
        {
            'input': 'create online interview wednesday 3pm with zoom',
            'expected': {'title': 'Online Interview', 'time': '15:00', 'meeting_type': 'online'}
        }
    ]
    
    correct_parses = 0
    
    for i, test_case in enumerate(test_cases, 1):
        input_text = test_case['input']
        expected = test_case['expected']
        
        print(f"Test {i}: '{input_text}'")
        
        # Parse the meeting info
        parsed_info = manager._parse_meeting_info(input_text)
        
        # Check key fields
        title_match = expected['title'].lower() in parsed_info.get('title', '').lower()
        time_match = parsed_info.get('time') == expected['time']
        type_match = parsed_info.get('meeting_type') == expected['meeting_type']
        
        if title_match and time_match and type_match:
            print(f"  ✅ Correctly parsed")
            correct_parses += 1
        else:
            print(f"  ❌ Parsing issues:")
            if not title_match:
                print(f"    Title: expected '{expected['title']}', got '{parsed_info.get('title')}'")
            if not time_match:
                print(f"    Time: expected '{expected['time']}', got '{parsed_info.get('time')}'")
            if not type_match:
                print(f"    Type: expected '{expected['meeting_type']}', got '{parsed_info.get('meeting_type')}'")
        
        print()
    
    accuracy = correct_parses / len(test_cases)
    print(f"📊 Parsing accuracy: {correct_parses}/{len(test_cases)} ({accuracy:.1%})")
    
    return accuracy


async def test_full_module_integration():
    """Test full module integration"""
    print("🔗 Testing Full Module Integration")
    print("=" * 40)
    
    # Initialize the simplified calendar module
    module = SimplifiedCalendarModule()
    await module.initialize()
    
    # Simulate events
    from modules import Event, EventType
    
    test_events = [
        {
            'type': EventType.INTENT_PARSED,
            'data': {
                'intent': 'schedule_meeting',
                'confidence': 0.8,
                'text': 'schedule team meeting tomorrow at 2pm',
                'user_id': 'test_user'
            }
        },
        {
            'type': EventType.INTENT_PARSED,
            'data': {
                'intent': 'check_calendar',
                'confidence': 0.9,
                'text': 'what do I have tomorrow',
                'user_id': 'test_user'
            }
        }
    ]
    
    for i, event_data in enumerate(test_events, 1):
        event = Event(
            type=event_data['type'],
            data=event_data['data'],
            source_module='test'
        )
        
        print(f"Event {i}: {event_data['data']['text']}")
        result = await module.handle_event(event)
        
        if result and result.get('success'):
            print(f"  ✅ {result.get('type', 'success')}: {result.get('message', 'No message')}")
        else:
            print(f"  ❌ Failed: {result.get('error') if result else 'No result'}")
        
        print()
    
    await module.shutdown()


async def main():
    """Main test function"""
    print("🚀 Simplified Calendar System Test Suite")
    print("=" * 60)
    
    try:
        # Run all tests
        await test_basic_meeting_creation()
        await test_interactive_conversation()
        await test_calendar_queries()
        
        parsing_accuracy = await test_natural_language_parsing()
        
        await test_full_module_integration()
        
        # Final assessment
        print("🎯 Final Assessment:")
        print("-" * 40)
        
        if parsing_accuracy >= 0.8:
            print("✅ EXCELLENT: Calendar system shows strong natural language understanding")
        elif parsing_accuracy >= 0.6:
            print("⚠️  GOOD: Calendar system working well, some parsing improvements possible")
        else:
            print("❌ NEEDS WORK: Calendar system requires parsing improvements")
        
        print(f"Natural language parsing accuracy: {parsing_accuracy:.1%}")
        print("\n✨ Simplified calendar system test completed!")
        print("\n💡 Key improvements over old system:")
        print("  • Single 'meetings' table instead of complex events/reminders")
        print("  • Interactive follow-up questions for missing details")
        print("  • Natural conversation flow: 'schedule meeting tomorrow' → 'what time?'")
        print("  • Better date/time parsing with relative dates")
        print("  • Simplified meeting types: online, in_person, phone")
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())