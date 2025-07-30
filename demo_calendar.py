#!/usr/bin/env python3
"""
SAGE Calendar Demo - Interactive calendar demonstration
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

async def calendar_demo():
    """Interactive calendar demonstration"""
    print("🗓️  SAGE Calendar System Demo")
    print("=" * 40)
    print("Natural language scheduling and reminders")
    print()
    
    # Initialize Calendar
    from modules.calendar import CalendarModule
    
    calendar = CalendarModule()
    calendar.config = {
        'enabled': True,
        'natural_language_parsing': True,
        'reminder_lead_time': 15,
        'timezone': 'auto'
    }
    
    init_success = await calendar.initialize()
    if not init_success:
        print("❌ Failed to initialize calendar module")
        return
    
    print("✅ Calendar system ready!")
    print()
    
    # Demo scheduling commands
    demo_commands = [
        "schedule meeting with team tomorrow at 2pm",
        "remind me to call mom tomorrow at 10am", 
        "book dentist appointment next monday at 9am",
        "set up lunch with sarah today at noon",
        "remind me to take medication at 8pm"
    ]
    
    print("📅 Creating sample events...")
    for i, command in enumerate(demo_commands, 1):
        print(f"{i}. '{command}'")
        
        try:
            if 'remind' in command.lower():
                result = await calendar._create_reminder(command)
            else:
                result = await calendar._create_event(command)
            
            if result.get('success'):
                print(f"   ✅ {result['message']}")
            else:
                print(f"   ❌ {result.get('error', 'Unknown error')}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        print()
    
    # Show calendar status
    print("📊 Calendar Status:")
    status = calendar.get_status()
    stats = status.get('statistics', {})
    print(f"   Total events: {stats.get('total_events', 0)}")
    print(f"   Upcoming events: {stats.get('upcoming_events', 0)}")
    print(f"   Pending reminders: {stats.get('pending_reminders', 0)}")
    print()
    
    # List today's events
    print("📋 Today's Schedule:")
    try:
        today_events = await calendar._list_events("show me today's events")
        if today_events.get('success'):
            print(f"   {today_events['message']}")
        else:
            print(f"   ❌ {today_events.get('error')}")
    except Exception as e:
        print(f"   ❌ Error listing events: {e}")
    
    print()
    
    # Test natural language parsing
    print("🧠 Natural Language Examples:")
    test_phrases = [
        "tomorrow at 3pm",
        "next friday at 10am", 
        "today at noon",
        "in 2 hours"
    ]
    
    for phrase in test_phrases:
        try:
            parsed = calendar.parser.parse_datetime(phrase)
            if parsed:
                print(f"   '{phrase}' → {parsed.strftime('%A, %B %d at %I:%M %p')}")
            else:
                print(f"   '{phrase}' → Could not parse")
        except Exception as e:
            print(f"   '{phrase}' → Error: {e}")
    
    print()
    
    # Interactive mode
    print("💬 Interactive Mode (type 'quit' to exit)")
    print("Try: 'schedule lunch tomorrow at 1pm' or 'remind me to exercise at 6am'")
    print()
    
    try:
        while True:
            user_input = input("Calendar> ").strip()
            if user_input.lower() in ['quit', 'exit', 'bye']:
                break
                
            if not user_input:
                continue
            
            try:
                # Process the command
                if 'list' in user_input.lower() or 'show' in user_input.lower():
                    result = await calendar._list_events(user_input)
                elif 'remind' in user_input.lower():
                    result = await calendar._create_reminder(user_input)
                else:
                    result = await calendar._create_event(user_input)
                
                if result.get('success'):
                    print(f"✅ {result['message']}")
                else:
                    print(f"❌ {result.get('error', 'Unknown error')}")
                    
            except Exception as e:
                print(f"❌ Error: {e}")
            
            print()
            
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    
    # Cleanup
    await calendar.shutdown()
    print("\n✅ Calendar demo completed!")

if __name__ == "__main__":
    asyncio.run(calendar_demo())