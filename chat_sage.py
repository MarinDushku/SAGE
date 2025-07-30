#!/usr/bin/env python3
"""
SAGE Interactive Chat - Simple text-based interface to chat with SAGE
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from main import SAGEApplication


async def interactive_chat():
    """Interactive chat with SAGE"""
    print("🚀 Starting SAGE Interactive Chat...")
    print("=" * 60)
    
    # Initialize SAGE
    sage = SAGEApplication()
    if not await sage.initialize():
        print("❌ Failed to initialize SAGE")
        return
    
    # Get NLP module
    nlp_module = sage.plugin_manager.get_module('nlp')
    learning_module = sage.plugin_manager.get_module('learning')
    calendar_module = sage.plugin_manager.get_module('calendar')
    
    if not nlp_module:
        print("❌ NLP module not available")
        await sage.shutdown()
        return
    
    print("\n🤖 SAGE Interactive Chat Ready!")
    print("💬 Type your messages below (type 'quit' to exit)")
    print("📝 Available commands:")
    print("   • Ask questions: 'What is AI?'")
    print("   • Schedule events: 'Schedule meeting tomorrow at 3pm'")
    print("   • Check memory: 'What did we talk about?'")
    print("   • Get status: 'status'")
    print("-" * 60)
    
    conversation_count = 0
    
    while True:
        try:
            # Get user input
            user_input = input("\n👤 You: ").strip()
            
            if not user_input:
                continue
                
            if user_input.lower() in ['quit', 'exit', 'bye']:
                print("\n🤖 SAGE: Goodbye! Have a great day!")
                break
            
            if user_input.lower() == 'status':
                print("\n📊 SAGE Status:")
                if nlp_module:
                    nlp_status = nlp_module.get_status()
                    print(f"   NLP Module: ✅ {nlp_status.get('provider', 'Unknown')} - {nlp_status.get('model', 'Unknown')}")
                    stats = nlp_status.get('statistics', {})
                    print(f"   Total Requests: {stats.get('total_requests', 0)}")
                    print(f"   Successful: {stats.get('successful_requests', 0)}")
                    print(f"   Average Response Time: {stats.get('average_response_time', 0):.2f}s")
                
                if learning_module:
                    learning_status = learning_module.get_status()
                    cache_sizes = learning_status.get('cache_sizes', {})
                    print(f"   Learning: {cache_sizes.get('interactions', 0)} interactions learned")
                
                if calendar_module:
                    cal_status = calendar_module.get_status()
                    cal_stats = cal_status.get('statistics', {})
                    print(f"   Calendar: {cal_stats.get('total_events', 0)} events")
                continue
            
            print("🤖 SAGE: ", end="", flush=True)
            
            # Process with NLP
            response = await nlp_module.process_text(user_input)
            
            if response.get('success'):
                response_text = response['response'].get('text', 'No response generated')
                processing_time = response.get('processing_time', 0)
                cached = response.get('cached', False)
                
                print(response_text)
                
                # Show processing info
                cache_indicator = " (cached)" if cached else ""
                print(f"   💭 Processed in {processing_time:.2f}s{cache_indicator}")
                
                # Record interaction in learning module
                if learning_module:
                    try:
                        await learning_module.record_interaction(
                            user_input=user_input,
                            assistant_response=response_text,
                            source_module="chat",
                            response_time=processing_time
                        )
                    except Exception as e:
                        print(f"   ⚠️ Learning error: {e}")
                
                # Check for calendar commands
                if calendar_module and any(word in user_input.lower() for word in ['schedule', 'meeting', 'appointment', 'remind', 'calendar']):
                    try:
                        # Try to parse and add calendar event
                        cal_response = await calendar_module.handle_natural_language(user_input)
                        if cal_response.get('success') and cal_response.get('event_created'):
                            event = cal_response.get('event')
                            print(f"   📅 Added to calendar: {event.get('title')} on {event.get('start_time')}")
                    except Exception as e:
                        print(f"   ⚠️ Calendar error: {e}")
                
                conversation_count += 1
                
            else:
                error = response.get('error', 'Unknown error')
                print(f"Sorry, I encountered an error: {error}")
                print("   💡 This might be because Ollama isn't running or configured")
                print("   💡 Try starting Ollama: 'ollama serve'")
        
        except KeyboardInterrupt:
            print("\n\n🛑 Chat interrupted by user")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
    
    print(f"\n📊 Chat Summary:")
    print(f"   Total conversations: {conversation_count}")
    print(f"   Thanks for chatting with SAGE!")
    
    # Shutdown
    await sage.shutdown()
    print("✅ SAGE shutdown complete")


if __name__ == "__main__":
    try:
        asyncio.run(interactive_chat())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")