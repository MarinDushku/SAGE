#!/usr/bin/env python3
"""
Test Enhanced NLP System - Verify improved intent recognition
"""

import sys
import asyncio
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from modules.nlp.intent_analyzer import IntentAnalyzer
from modules.nlp.semantic_matcher import SemanticMatcher


async def test_intent_recognition():
    """Test the enhanced intent recognition system"""
    print("🧠 Testing Enhanced NLP Intent Recognition")
    print("=" * 50)
    
    # Initialize analyzer
    analyzer = IntentAnalyzer()
    matcher = SemanticMatcher()
    
    # Test cases - various ways to express the same intents
    test_cases = [
        # Schedule meeting variations
        ("schedule meeting tomorrow at 9am", "schedule_meeting"),
        ("book appointment friday 2pm", "schedule_meeting"),
        ("set up call with john monday", "schedule_meeting"),
        ("need to meet with team tuesday", "schedule_meeting"),
        ("can you add meeting wednesday", "schedule_meeting"),
        ("plan standup for next week", "schedule_meeting"),
        ("arrange interview thursday", "schedule_meeting"),
        ("make appointment tomorrow", "schedule_meeting"),
        ("organize sync friday", "schedule_meeting"),
        
        # Calendar check variations
        ("what's on my schedule tomorrow", "check_calendar"),
        ("do i have meetings friday", "check_calendar"),
        ("am i free this afternoon", "check_calendar"),
        ("show me my agenda", "check_calendar"),
        ("check my calendar today", "check_calendar"),
        ("any appointments tomorrow", "check_calendar"),
        ("what meetings do i have", "check_calendar"),
        ("tell me about my schedule", "check_calendar"),
        ("am i busy monday", "check_calendar"),
        ("list my events", "check_calendar"),
        
        # Time queries
        ("what time is it", "time_query"),
        ("current time please", "time_query"),
        ("tell me the time", "time_query"),
        ("what's the time now", "time_query"),
        
        # Greetings
        ("hello sage", "greeting"),
        ("good morning", "greeting"),
        ("hey there", "greeting"),
        ("hi", "greeting"),
        
        # Context-dependent (should work after scheduling)
        ("make it 3pm instead", "modify_meeting"),
        ("change to online", "modify_meeting"),
        ("yes that's correct", "modify_meeting"),
        ("cancel that", "modify_meeting"),
    ]
    
    print("Testing individual intent recognition:")
    print("-" * 40)
    
    correct_predictions = 0
    total_tests = len(test_cases)
    
    for i, (text, expected_intent) in enumerate(test_cases, 1):
        # Analyze intent
        result = analyzer.analyze_intent(text)
        
        predicted_intent = result['intent']
        confidence = result['confidence']
        threshold_met = result['threshold_met']
        
        # Check if prediction is correct
        is_correct = predicted_intent == expected_intent
        if is_correct:
            correct_predictions += 1
        
        # Display result
        status = "✅" if is_correct else "❌"
        print(f"{status} Test {i:2d}: '{text}'")
        print(f"    Expected: {expected_intent}")
        print(f"    Got: {predicted_intent} (confidence: {confidence:.2f}, threshold_met: {threshold_met})")
        
        if not is_correct and result.get('suggestion'):
            print(f"    Suggestion: {result['suggestion']}")
        
        print()
    
    # Calculate accuracy
    accuracy = correct_predictions / total_tests
    print(f"📊 Results: {correct_predictions}/{total_tests} correct ({accuracy:.1%} accuracy)")
    print()
    
    # Test semantic matching
    print("Testing semantic matching:")
    print("-" * 40)
    
    semantic_tests = [
        ("schedule meeting", ["book appointment", "add event", "plan session"]),
        ("check calendar", ["show agenda", "list schedule", "view meetings"]),
        ("what time", ["current time", "tell time", "time now"]),
    ]
    
    for original, variations in semantic_tests:
        print(f"Original: '{original}'")
        for variation in variations:
            matches = matcher.find_matches(variation, [original])
            if matches:
                score = matches[0]['score']  
                match_type = matches[0]['match_type']
                print(f"  '{variation}' -> Score: {score:.2f} ({match_type})")
            else:
                print(f"  '{variation}' -> No match found")
        print()
    
    # Test conversation context
    print("Testing conversation context:")
    print("-" * 40)
    
    context_tests = [
        "schedule meeting tomorrow at 2pm",
        "make it 3pm instead",
        "change to online",
        "yes that works",
    ]
    
    for i, text in enumerate(context_tests, 1):
        result = analyzer.analyze_intent(text)
        print(f"Turn {i}: '{text}'")
        print(f"  Intent: {result['intent']} (confidence: {result['confidence']:.2f})")
        
        if i > 1:  # Show context summary
            context = analyzer.get_context_summary()
            print(f"  Context: {context['recent_intents'][-2:] if context['recent_intents'] else 'None'}")
        print()
    
    # Show statistics
    print("📈 Analyzer Statistics:")
    print("-" * 40)
    stats = analyzer.get_statistics()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    print("\n🔍 Semantic Matcher Statistics:")
    print("-" * 40)
    matcher_stats = matcher.get_statistics()
    for key, value in matcher_stats.items():
        print(f"  {key}: {value}")
    
    return accuracy


async def test_real_world_scenarios():
    """Test with real-world conversational scenarios"""
    print("\n🌍 Testing Real-World Scenarios")
    print("=" * 50)
    
    analyzer = IntentAnalyzer()
    
    scenarios = [
        # Casual scheduling
        "hey can you add a team meeting for tomorrow morning?",
        "i need to book a doctor's appointment next friday at 2",
        "set up interview with candidate monday 10am",
        
        # Natural calendar queries  
        "what do i have going on tomorrow?",
        "am i free for lunch on wednesday?",
        "do i have anything scheduled this afternoon?",
        
        # Follow-up conversations
        "actually make that 3pm instead",
        "can we do it online instead of in person?",
        "yes that time works for me",
        
        # Typos and variations
        "schedual meeting tommorow",
        "book apointment friday",
        "whats on my calender?",
    ]
    
    for i, text in enumerate(scenarios, 1):
        result = analyzer.analyze_intent(text)
        
        print(f"Scenario {i}: '{text}'")
        print(f"  Intent: {result['intent']}")
        print(f"  Confidence: {result['confidence']:.2f}")
        print(f"  Threshold Met: {result['threshold_met']}")
        
        if result.get('entities'):
            print(f"  Entities: {result['entities']}")
        
        if result.get('suggestion'):
            print(f"  Suggestion: {result['suggestion']}")
        
        print()


async def main():
    """Main test function"""
    print("🚀 Enhanced NLP System Test Suite")
    print("=" * 60)
    
    try:
        # Run intent recognition tests
        accuracy = await test_intent_recognition()
        
        # Run real-world scenario tests
        await test_real_world_scenarios()
        
        # Final assessment
        print("🎯 Final Assessment:")
        print("-" * 40)
        if accuracy >= 0.85:
            print("✅ EXCELLENT: NLP system shows strong intent recognition")
        elif accuracy >= 0.70:
            print("⚠️  GOOD: NLP system working well, some improvements possible")
        else:
            print("❌ NEEDS WORK: NLP system requires significant improvements")
        
        print(f"Overall accuracy: {accuracy:.1%}")
        print("\n✨ Enhanced NLP system test completed!")
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())