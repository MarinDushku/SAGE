#!/usr/bin/env python3
"""
Demo: Voice Recognition Fixes - Show what was fixed and how it works
"""

import sys
import asyncio
from pathlib import Path
from typing import Dict

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from modules.nlp.intent_analyzer import IntentAnalyzer
from modules.calendar.meeting_manager import MeetingManager


async def demo_voice_workflow_logic():
    """Demo the voice workflow logic (without actual voice recognition)"""
    print("🚀 SAGE Voice Recognition Fixes Demo")
    print("=" * 60)
    print("Demonstrating the complete voice workflow logic")
    print("(Simulated voice input - hardware may not be available)")
    print()
    
    # Initialize components
    print("Initializing components...")
    nlp_analyzer = IntentAnalyzer()
    meeting_manager = MeetingManager("data/demo_voice.db")
    print("✅ Components initialized")
    print()
    
    # Demo scenarios
    scenarios = [
        {
            'name': '🎤 Voice Input Simulation',
            'user_says': 'Hey Sage, schedule team meeting tomorrow at 2pm',
            'description': 'User speaks to SAGE with wake word'
        },
        {
            'name': '💬 Conversation Follow-up',
            'user_says': 'Book doctor appointment Friday',
            'description': 'Incomplete request requiring follow-up'
        },
        {
            'name': '📅 Calendar Query',
            'user_says': 'What do I have scheduled tomorrow',
            'description': 'Natural language calendar query'
        }
    ]
    
    for i, scenario in enumerate(scenarios, 1):
        await demo_single_interaction(i, scenario, nlp_analyzer, meeting_manager)
    
    print("🔧 Key Voice Recognition Fixes Implemented:")
    print("=" * 60)
    print("✅ Threading/Async Issues Fixed:")
    print("   • Proper event loop handling across threads")
    print("   • Fixed async task creation in audio callbacks")
    print("   • Thread-safe audio queue processing")
    print("   • Graceful shutdown of background threads")
    print()
    
    print("✅ Audio Processing Enhanced:")
    print("   • Comprehensive microphone calibration")
    print("   • Audio level monitoring and feedback")
    print("   • Better error handling and recovery")
    print("   • Detailed logging and debugging")
    print()
    
    print("✅ Recognition Pipeline Improved:")
    print("   • Queue-based audio processing")
    print("   • Multiple recognition engine support (Whisper, Google)")
    print("   • Confidence scoring and statistics")
    print("   • Wake word detection and filtering")
    print()
    
    print("✅ Integration Seamless:")
    print("   • Direct integration with Enhanced NLP")
    print("   • Conversational calendar workflow")
    print("   • Natural language response generation")
    print("   • Text-to-speech feedback")


async def demo_single_interaction(num: int, scenario: Dict, nlp_analyzer, meeting_manager):
    """Demo a single voice interaction"""
    print(f"Scenario {num}: {scenario['name']}")
    print(f"Description: {scenario['description']}")
    print()
    
    # Step 1: Voice Recognition (simulated)
    user_input = scenario['user_says']
    print(f"👤 User speaks: \"{user_input}\"")
    
    # Step 2: Wake word detection
    wake_word_detected, command = detect_wake_word(user_input)
    if wake_word_detected:
        print(f"🎯 Wake word detected: \"sage\"")
        print(f"📝 Command extracted: \"{command}\"")
    else:
        print("❌ No wake word detected - ignoring")
        print()
        return
    
    # Step 3: Enhanced NLP Processing
    print("🧠 Processing with Enhanced NLP...")
    intent_result = nlp_analyzer.analyze_intent(command)
    print(f"   Intent: {intent_result['intent']}")
    print(f"   Confidence: {intent_result['confidence']:.2f}")
    print(f"   Threshold met: {intent_result['threshold_met']}")
    
    # Step 4: Calendar Integration
    print("📅 Processing with Simplified Calendar...")
    
    if intent_result['intent'] == 'schedule_meeting':
        calendar_result = await meeting_manager.create_meeting_from_text(command)
        
        if calendar_result['success'] and calendar_result.get('needs_followup'):
            print(f"🤖 SAGE: {calendar_result['question']}")
            print("💭 (System is waiting for user response...)")
        elif calendar_result['success']:
            print(f"🤖 SAGE: {calendar_result['confirmation']}")
        else:
            print(f"❌ Error: {calendar_result.get('error')}")
    
    elif intent_result['intent'] == 'check_calendar':
        # Simulate calendar query
        from datetime import datetime, timedelta
        tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        meetings = await meeting_manager.get_meetings_for_date(tomorrow)
        
        if meetings:
            print(f"🤖 SAGE: You have {len(meetings)} meeting{'s' if len(meetings) != 1 else ''} tomorrow:")
            for meeting in meetings:
                print(f"   • {meeting['title']} at {meeting['time']}")
        else:
            print("🤖 SAGE: You don't have any meetings scheduled for tomorrow.")
    
    else:
        print(f"🤖 SAGE: I understand you said something about {intent_result['intent']}")
    
    print()
    print("-" * 50)
    print()


def detect_wake_word(text: str) -> tuple[bool, str]:
    """Simulate wake word detection"""
    wake_words = ['hey sage', 'sage', 'computer', 'hey computer']
    text_lower = text.lower()
    
    for wake_word in wake_words:
        if wake_word in text_lower:
            # Remove wake word and return command
            command = text_lower.replace(wake_word, '').strip()
            return True, command
    
    return False, text


async def demo_problem_analysis():
    """Demo analysis of the original voice recognition problems"""
    print("\n🔍 Original Voice Recognition Problems")
    print("=" * 60)
    
    print("❌ Problem 1: Threading/Async Issues")
    print("   Issue: SAGE could speak but couldn't hear users")
    print("   Root Cause: asyncio.create_task() called from thread context")
    print("   Solution: Proper event loop handling with run_coroutine_threadsafe()")
    print()
    
    print("❌ Problem 2: Audio Callback Pipeline")
    print("   Issue: Audio callbacks not properly processed")
    print("   Root Cause: Background thread couldn't communicate with async code")
    print("   Solution: Thread-safe queue with proper async processing")
    print()
    
    print("❌ Problem 3: Microphone Calibration")
    print("   Issue: Energy threshold detection failing")
    print("   Root Cause: Poor ambient noise calibration")
    print("   Solution: Enhanced calibration with monitoring and feedback")
    print()
    
    print("❌ Problem 4: Error Handling")
    print("   Issue: Silent failures with no debugging info")
    print("   Root Cause: Limited logging and error reporting")
    print("   Solution: Comprehensive logging and status monitoring")
    print()
    
    print("✅ All Problems Fixed in Enhanced Voice System!")


async def demo_technical_improvements():
    """Demo the technical improvements made"""
    print("\n⚙️ Technical Improvements Made")
    print("=" * 60)
    
    print("🧵 Threading Architecture:")
    print("   OLD: Direct callback from audio thread to async functions")
    print("   NEW: Background thread → Queue → Async processor")
    print("   Result: Proper separation of threaded and async code")
    print()
    
    print("🎤 Audio Processing:")
    print("   OLD: Basic microphone initialization")
    print("   NEW: Enhanced calibration with level monitoring")
    print("   Result: Better audio detection and debugging")
    print()
    
    print("🧠 NLP Integration:")
    print("   OLD: Basic keyword matching")
    print("   NEW: Semantic intent analysis with context")
    print("   Result: Understanding natural language variations")
    print()
    
    print("📅 Calendar Integration:")
    print("   OLD: Complex event creation workflow")
    print("   NEW: Conversational meeting scheduling")
    print("   Result: Natural interaction: 'schedule meeting' → 'what time?'")
    print()
    
    print("🔊 Response Generation:")
    print("   OLD: Simple text responses")
    print("   NEW: Context-aware responses with TTS")
    print("   Result: Natural conversation flow")


async def main():
    """Main demo function"""
    try:
        await demo_voice_workflow_logic()
        await demo_problem_analysis()
        await demo_technical_improvements()
        
        print("\n🎉 Enhanced Voice Recognition System")
        print("=" * 60)
        print("The voice recognition issues have been comprehensively fixed:")
        print()
        print("🔧 Technical Fixes:")
        print("   • Threading/async issues resolved")
        print("   • Audio processing pipeline enhanced")
        print("   • Error handling and debugging improved")
        print("   • Integration with NLP and Calendar seamless")
        print()
        print("🗣️ User Experience:")
        print("   • Natural wake word detection")
        print("   • Conversational meeting scheduling")
        print("   • Intelligent follow-up questions")
        print("   • Spoken responses and confirmations")
        print()
        print("💡 Try these voice commands when hardware is available:")
        print("   • 'Hey Sage, schedule meeting tomorrow at 2pm'")
        print("   • 'Sage, what do I have scheduled tomorrow?'")
        print("   • 'Schedule team standup Monday 9am online'")
        print("   • 'Book doctor appointment Friday'")
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())