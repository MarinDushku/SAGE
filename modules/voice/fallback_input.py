"""
Fallback Input Methods - Text input and push-to-talk when voice recognition unavailable
"""

import asyncio
import logging
from typing import Dict, Any, Optional, Callable
from pathlib import Path


class FallbackInputManager:
    """Manage fallback input methods when voice recognition is unavailable"""
    
    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger(__name__)
        
        # Input modes
        self.text_input_enabled = True
        self.push_to_talk_enabled = False
        
        # Callbacks
        self.on_text_input: Optional[Callable] = None
        self.on_command_received: Optional[Callable] = None
        
        # State
        self.is_active = False
        self.input_task = None
        
        # Statistics
        self.stats = {
            'text_commands_processed': 0,
            'push_to_talk_activations': 0,
            'fallback_activations': 0
        }
    
    def log(self, message: str, level: str = "info"):
        """Log with fallback input prefix"""
        if self.logger:
            getattr(self.logger, level)(f"[FALLBACK] {message}")
        else:
            print(f"[FALLBACK-{level.upper()}] {message}")
    
    async def initialize(self) -> bool:
        """Initialize fallback input systems"""
        try:
            self.log("Initializing fallback input systems...")
            
            # Check if we can do text input
            if self.text_input_enabled:
                self.log("✅ Text input mode available")
            
            # Check for push-to-talk support (would need additional hardware support)
            # For now, we'll keep it simple with text input
            
            self.log("Fallback input systems initialized")
            return True
            
        except Exception as e:
            self.log(f"Failed to initialize fallback input: {e}", "error")
            return False
    
    async def start_text_input_mode(self) -> bool:
        """Start interactive text input mode"""
        if self.is_active:
            self.log("Fallback input already active", "warning")
            return True
        
        try:
            self.log("Starting text input mode...")
            self.is_active = True
            
            # Start the input loop
            self.input_task = asyncio.create_task(self._text_input_loop())
            
            self.stats['fallback_activations'] += 1
            self.log("📝 Text input mode started - type commands or 'quit' to exit")
            
            return True
            
        except Exception as e:
            self.log(f"Failed to start text input mode: {e}", "error")
            return False
    
    async def _text_input_loop(self):
        """Main text input loop"""
        try:
            self.log("Text input loop started")
            
            # Display instructions
            print("\n" + "="*60)
            print("🎤 SAGE Voice Recognition Fallback Mode")
            print("="*60)
            print("Voice recognition is not available (likely due to hardware/environment)")
            print("You can still interact with SAGE using text input!")
            print()
            print("💡 Try these commands:")
            print("  • schedule meeting tomorrow at 2pm")
            print("  • what do I have scheduled tomorrow")
            print("  • book doctor appointment friday")
            print("  • quit (to exit)")
            print()
            print("Type your command:")
            
            while self.is_active:
                try:
                    # Get user input (this will block, but that's okay for fallback mode)
                    user_input = await self._get_user_input()
                    
                    if not user_input:
                        continue
                    
                    user_input = user_input.strip()
                    
                    # Check for exit commands
                    if user_input.lower() in ['quit', 'exit', 'stop', 'bye']:
                        self.log("User requested exit")
                        break
                    
                    # Process the command
                    await self._process_text_command(user_input)
                    
                except KeyboardInterrupt:
                    self.log("Keyboard interrupt received")
                    break
                except Exception as e:
                    self.log(f"Error in text input loop: {e}", "error")
                    print(f"Error: {e}")
                    
        except Exception as e:
            self.log(f"Text input loop error: {e}", "error")
        finally:
            self.is_active = False
            self.log("Text input loop stopped")
    
    async def _get_user_input(self) -> str:
        """Get user input asynchronously"""
        # For now, use simple input - in a real implementation,
        # you might want to use aioconsole or similar for true async input
        loop = asyncio.get_event_loop()
        
        try:
            # Run input in executor to avoid blocking
            user_input = await loop.run_in_executor(None, self._blocking_input)
            return user_input
        except Exception as e:
            self.log(f"Error getting user input: {e}", "error")
            return ""
    
    def _blocking_input(self) -> str:
        """Blocking input function"""
        try:
            return input("🗣️  You: ")
        except (EOFError, KeyboardInterrupt):
            return "quit"
    
    async def _process_text_command(self, command: str):
        """Process text command"""
        try:
            self.stats['text_commands_processed'] += 1
            self.log(f"Processing text command: '{command}'")
            
            print(f"🤖 SAGE: I heard '{command}'")
            print("    Processing with enhanced NLP and calendar system...")
            
            # Call the callback if set
            if self.on_command_received:
                try:
                    await self.on_command_received(command, confidence=1.0)
                except Exception as e:
                    self.log(f"Error in command callback: {e}", "error")
                    print(f"🤖 SAGE: Sorry, I had trouble processing that: {e}")
            else:
                print("🤖 SAGE: Command received but no processor connected.")
            
            print()  # Add spacing for next input
            
        except Exception as e:
            self.log(f"Error processing text command: {e}", "error")
            print(f"🤖 SAGE: Error processing command: {e}")
    
    async def stop(self):
        """Stop fallback input"""
        if not self.is_active:
            return
        
        try:
            self.log("Stopping fallback input...")
            self.is_active = False
            
            if self.input_task:
                self.input_task.cancel()
                try:
                    await self.input_task
                except asyncio.CancelledError:
                    pass
            
            self.log("Fallback input stopped")
            
        except Exception as e:
            self.log(f"Error stopping fallback input: {e}", "error")
    
    def set_callbacks(self, 
                     on_command_received: Optional[Callable] = None,
                     on_text_input: Optional[Callable] = None):
        """Set callback functions"""
        self.on_command_received = on_command_received
        self.on_text_input = on_text_input
    
    def get_status(self) -> Dict[str, Any]:
        """Get fallback input status"""
        return {
            'active': self.is_active,
            'text_input_enabled': self.text_input_enabled,
            'push_to_talk_enabled': self.push_to_talk_enabled,
            'statistics': self.stats.copy()
        }
    
    async def shutdown(self):
        """Shutdown fallback input"""
        await self.stop()
        self.log("Fallback input shutdown complete")


class VoiceFallbackDemo:
    """Demo class to show fallback input working with SAGE systems"""
    
    def __init__(self):
        self.fallback_input = FallbackInputManager()
        self.nlp_analyzer = None
        self.meeting_manager = None
    
    async def initialize(self):
        """Initialize demo components"""
        try:
            # Initialize NLP and Calendar (import here to avoid issues)
            import sys
            from pathlib import Path
            sys.path.insert(0, str(Path(__file__).parent.parent.parent))
            
            from modules.nlp.intent_analyzer import IntentAnalyzer
            from modules.calendar.meeting_manager import MeetingManager
            
            self.nlp_analyzer = IntentAnalyzer()
            self.meeting_manager = MeetingManager("data/fallback_demo.db")
            
            # Initialize fallback input
            await self.fallback_input.initialize()
            
            # Set callback
            self.fallback_input.set_callbacks(
                on_command_received=self._process_command
            )
            
            return True
            
        except Exception as e:
            print(f"Failed to initialize demo: {e}")
            return False
    
    async def _process_command(self, command: str, confidence: float):
        """Process command through NLP and calendar"""
        try:
            # NLP Processing
            intent_result = self.nlp_analyzer.analyze_intent(command)
            print(f"    🧠 Intent: {intent_result['intent']} (confidence: {intent_result['confidence']:.2f})")
            
            # Calendar processing
            if intent_result['intent'] == 'schedule_meeting':
                result = await self.meeting_manager.create_meeting_from_text(command)
                
                if result['success'] and result.get('needs_followup'):
                    print(f"🤖 SAGE: {result['question']}")
                elif result['success']:
                    print(f"🤖 SAGE: {result['confirmation']}")
                else:
                    print(f"🤖 SAGE: Error: {result.get('error')}")
                    
            elif intent_result['intent'] == 'check_calendar':
                from datetime import datetime, timedelta
                tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
                meetings = await self.meeting_manager.get_meetings_for_date(tomorrow)
                
                if meetings:
                    print(f"🤖 SAGE: You have {len(meetings)} meeting{'s' if len(meetings) != 1 else ''} tomorrow:")
                    for meeting in meetings:
                        print(f"    • {meeting['title']} at {meeting['time']}")
                else:
                    print("🤖 SAGE: You don't have any meetings scheduled for tomorrow.")
                    
            else:
                print(f"🤖 SAGE: I understand you want to {intent_result['intent']}. Let me help with that!")
                
        except Exception as e:
            print(f"🤖 SAGE: Sorry, I had trouble processing that: {e}")
    
    async def run_demo(self):
        """Run the fallback input demo"""
        if await self.initialize():
            await self.fallback_input.start_text_input_mode()
        else:
            print("Failed to initialize demo")
    
    async def shutdown(self):
        """Shutdown demo"""
        await self.fallback_input.shutdown()


async def main():
    """Main demo function"""
    demo = VoiceFallbackDemo()
    
    try:
        await demo.run_demo()
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        await demo.shutdown()


if __name__ == "__main__":
    asyncio.run(main())