#!/usr/bin/env python3
"""
SAGE Text-Only Test Interface
For testing functionality without voice recognition
"""

import asyncio
import sys
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from core.logger import Logger
from core.plugin_manager import PluginManager
from core.config_manager import ConfigManager
from core.event_bus import EventBus
from core.cache_manager import CacheManager
from modules.function_calling import FunctionRegistry, FunctionCallingProcessor
from modules.voice.conversation_state import ConversationManager


class TextTestInterface:
    """Simple text interface for testing SAGE functionality"""
    
    def __init__(self):
        self.logger = Logger("SAGE-TEST")
        self.main_log = self.logger.get_logger("test")
        
        # Initialize minimal core components (like main.py does)
        self.config_manager = ConfigManager("config.yaml")
        self.config_manager.load_config()
        
        self.cache_manager = CacheManager(max_memory_mb=50, default_ttl=3600)
        self.event_bus = EventBus(max_queue_size=100)
        
        # Initialize plugin manager (same as main.py)
        self.plugin_manager = PluginManager()
        self.plugin_manager.set_dependencies(
            event_bus=self.event_bus,
            config_manager=self.config_manager,
            cache_manager=self.cache_manager,
            logger=self.logger
        )
        
    async def initialize(self):
        """Initialize the plugin system like main.py does"""
        # Start event bus
        await self.event_bus.start()
        
        # Load calendar module (exactly like main.py)
        print("🔧 Loading calendar module...")
        calendar_result = await self.plugin_manager.load_module('calendar')
        if not calendar_result:
            self.main_log.warning("Failed to load calendar module, using direct DB access")
        else:
            print("✅ Calendar module loaded successfully")
        
        # Initialize conversation manager for memory
        self.conversation_manager = ConversationManager(
            self.logger.get_logger("conversation")
        )
        
        # Initialize function calling system (exactly like main.py)
        calendar_module = self.plugin_manager.get_module('calendar')
        self.function_registry = FunctionRegistry(
            self.logger.get_logger("functions"),
            calendar_module  # Pass calendar module like main.py does
        )
        self.function_processor = FunctionCallingProcessor(
            self.function_registry, 
            None,  # No NLP module for test
            self.logger.get_logger("function_calling")
        )
        
    async def run(self):
        """Run the text interface"""
        print("🤖 SAGE Text Test Interface")
        print("=" * 50)
        
        # Initialize the system first (like main.py)
        await self.initialize()
        
        print("Available commands:")
        print("• Ask for time: 'what time is it?'")
        print("• Schedule meeting: 'schedule a meeting for tomorrow at 9am'")
        print("• Check calendar: 'do I have anything scheduled for tomorrow?'")
        print("• Remove meeting: 'remove the meeting at 9am tomorrow'")
        print("• Move meeting: 'move my 9am meeting to 10am'")
        print("• Type 'quit' or 'exit' to stop")
        print("-" * 50)
        
        while True:
            try:
                # Get user input
                try:
                    user_input = input("\n🗣️  You: ").strip()
                except EOFError:
                    print("\n👋 Goodbye!")
                    break
                
                if not user_input:
                    continue
                    
                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("👋 Goodbye!")
                    break
                
                print(f"🧠 Processing: '{user_input}'")
                
                # Add user input to conversation history
                self.conversation_manager.add_to_history("User", user_input)
                
                # Check for contextual responses first (yes/no/sure to suggestions)
                suggestion = self.conversation_manager.get_pending_suggestion()
                if suggestion:
                    if self.conversation_manager.is_affirmative_response(user_input):
                        # User accepted the suggestion - execute it
                        response = await self._execute_suggestion(suggestion)
                        print(f"✅ {response}")
                        self.conversation_manager.add_to_history("SAGE", response)
                        # Don't clear suggestion here - let _execute_suggestion handle it
                        continue
                    elif self.conversation_manager.is_negative_response(user_input):
                        # User declined the suggestion
                        response = "Okay, no problem. What else can I help you with?"
                        print(f"🤖 SAGE: {response}")
                        self.conversation_manager.add_to_history("SAGE", response)
                        self.conversation_manager.clear_suggestion()
                        continue
                
                # Process through function calling system
                result = await self.function_processor.process_request(user_input)
                
                if result.get('success'):
                    response = result.get('response', 'Command processed.')
                    response_type = result.get('type', 'unknown')
                    
                    print(f"🤖 SAGE ({response_type}): {response}")
                    
                    # Add SAGE response to conversation history
                    self.conversation_manager.add_to_history("SAGE", response)
                    
                    # Check if this response contains a suggestion
                    await self._check_and_store_suggestion(response, result)
                    
                    # Show function details for debugging
                    if response_type == 'function_calls':
                        function_results = result.get('function_results', [])
                        for func_result in function_results:
                            func_name = func_result.get('function', 'unknown')
                            parameters = func_result.get('parameters', {})
                            success = func_result.get('result', {}).get('success', False)
                            print(f"   📋 Function: {func_name} | Params: {parameters} | Success: {success}")
                            
                else:
                    error_msg = result.get('error', 'Unknown error')
                    fallback_response = result.get('fallback_response', 'Sorry, I had trouble with that.')
                    print(f"❌ Error: {error_msg}")
                    print(f"🤖 SAGE: {fallback_response}")
                    self.conversation_manager.add_to_history("SAGE", fallback_response)
                    
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ Unexpected error: {e}")
    
    async def _execute_suggestion(self, suggestion: dict) -> str:
        """Execute a suggestion that the user accepted"""
        try:
            context = suggestion['context']
            suggestion_text = suggestion['suggestion_text']
            
            # Parse the suggestion to extract the action
            if 'How about' in suggestion_text and 'instead?' in suggestion_text:
                # This is a time conflict suggestion like "How about 10:00 AM instead?"
                import re
                time_match = re.search(r'How about (\d{1,2}:?\d{0,2}\s*(?:AM|PM|am|pm))', suggestion_text)
                if time_match:
                    suggested_time = time_match.group(1)
                    
                    # Extract original scheduling parameters from context
                    original_title = context.get('original_title', 'Meeting')
                    original_date = context.get('original_date', 'tomorrow')  # Default to tomorrow, not today
                    
                    # Schedule at the suggested time
                    result = await self.function_registry.execute_function("add_calendar_event", {
                        "title": original_title,
                        "date": original_date,
                        "time": suggested_time
                    })
                    
                    if result['success']:
                        response_text = result['result']
                        # Check if the result contains another conflict suggestion
                        if 'How about' in response_text and 'instead?' in response_text:
                            # There's another conflict - store this new suggestion
                            await self._check_and_store_suggestion_from_text(response_text, {
                                'original_title': original_title,
                                'original_date': original_date
                            })
                            # Don't clear the old suggestion since we have a new one
                            return f"Perfect! {response_text}"
                        else:
                            # No more conflicts - clear the suggestion
                            self.conversation_manager.clear_suggestion()
                            return f"Perfect! {response_text}"
                    else:
                        # Error occurred - clear suggestion
                        self.conversation_manager.clear_suggestion()
                        return f"Sorry, there was an error: {result.get('error', 'Unknown error')}"
            
            return "I executed your request!"
            
        except Exception as e:
            return f"Sorry, I had trouble executing that: {str(e)}"
    
    async def _check_and_store_suggestion(self, response: str, result: dict):
        """Check if a response contains a suggestion and store it for context"""
        try:
            # Check for time conflict suggestions
            if 'How about' in response and 'instead?' in response:
                # Extract the suggested time
                import re
                time_match = re.search(r'How about (\d{1,2}:?\d{0,2}\s*(?:AM|PM|am|pm))', response) 
                if time_match:
                    suggested_time = time_match.group(1)
                    
                    # Get the original function call context
                    function_results = result.get('function_results', [])
                    if function_results:
                        func_result = function_results[0]
                        parameters = func_result.get('parameters', {})
                        
                        # Store the suggestion with context
                        suggestion_context = {
                            'type': 'reschedule_conflict',
                            'suggested_time': suggested_time,
                            'original_title': parameters.get('title', 'Meeting'),
                            'original_date': parameters.get('date', 'today'),
                            'original_time': parameters.get('time')
                        }
                        
                        self.conversation_manager.store_suggestion(response, suggestion_context)
                        return
            
            # Check for other types of suggestions (can be extended)
            suggestion_indicators = [
                'would you like', 'do you want', 'should i', 'how about',
                'would you prefer', 'shall i', 'can i'
            ]
            
            if any(indicator in response.lower() for indicator in suggestion_indicators):
                # Generic suggestion
                suggestion_context = {
                    'type': 'generic_suggestion',
                    'response': response,
                    'result': result
                }
                self.conversation_manager.store_suggestion(response, suggestion_context)
                
        except Exception as e:
            # Don't fail if suggestion detection fails
            pass
    
    async def _check_and_store_suggestion_from_text(self, response_text: str, context: dict):
        """Store suggestion from text response (for chained conflicts)"""
        try:
            import re
            time_match = re.search(r'How about (\d{1,2}:?\d{0,2}\s*(?:AM|PM|am|pm))', response_text) 
            if time_match:
                suggested_time = time_match.group(1)
                
                suggestion_context = {
                    'type': 'reschedule_conflict',
                    'suggested_time': suggested_time,
                    'original_title': context.get('original_title', 'Meeting'),
                    'original_date': context.get('original_date', 'today'),
                    'original_time': None
                }
                
                self.conversation_manager.store_suggestion(response_text, suggestion_context)
                print(f"🧠 DEBUG: Stored new suggestion for {suggested_time}")
        except Exception as e:
            pass


async def main():
    """Main entry point"""
    try:
        interface = TextTestInterface()
        await interface.run()
        return 0
    except Exception as e:
        print(f"❌ Failed to start test interface: {e}")
        return 1


if __name__ == "__main__":
    # Ensure proper asyncio event loop on Windows
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        
    # Run the application
    exit_code = asyncio.run(main())
    sys.exit(exit_code)