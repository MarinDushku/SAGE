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
from modules.function_calling import FunctionRegistry, FunctionCallingProcessor


class TextTestInterface:
    """Simple text interface for testing SAGE functionality"""
    
    def __init__(self):
        self.logger = Logger("SAGE-TEST")
        self.main_log = self.logger.get_logger("test")
        
        # Initialize function calling system
        self.function_registry = FunctionRegistry(
            self.logger.get_logger("functions"),
            None  # No calendar module for now - uses direct DB
        )
        self.function_processor = FunctionCallingProcessor(
            self.function_registry, 
            None,  # No NLP module
            self.logger.get_logger("function_calling")
        )
        
    async def run(self):
        """Run the text interface"""
        print("🤖 SAGE Text Test Interface")
        print("=" * 50)
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
                
                # Process through function calling system
                result = await self.function_processor.process_request(user_input)
                
                if result.get('success'):
                    response = result.get('response', 'Command processed.')
                    response_type = result.get('type', 'unknown')
                    
                    print(f"🤖 SAGE ({response_type}): {response}")
                    
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
                    
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ Unexpected error: {e}")


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