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