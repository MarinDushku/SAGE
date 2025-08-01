#!/usr/bin/env python3
"""
SAGE - Smart Adaptive General Executive
Zero-cost AI desktop assistant main entry point
"""

import asyncio
import sys
import signal
import argparse
from pathlib import Path
from typing import Optional

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from core.event_bus import EventBus
from core.plugin_manager import PluginManager
from core.config_manager import ConfigManager
from core.resource_monitor import ResourceMonitor
from core.cache_manager import CacheManager
from core.logger import Logger


class SAGEApplication:
    """Main SAGE application manager"""
    
    def __init__(self, config_file: str = "config.yaml"):
        self.config_file = config_file
        self.running = False
        
        # Core components
        self.logger = None
        self.config_manager = None
        self.event_bus = None
        self.plugin_manager = None
        self.resource_monitor = None
        self.cache_manager = None
        
        # Signal handling
        self.shutdown_event = asyncio.Event()
        
    async def initialize(self) -> bool:
        """Initialize all SAGE components"""
        try:
            print("🚀 Starting SAGE - Smart Adaptive General Executive")
            print("   Zero-Cost AI Desktop Assistant")
            print("=" * 50)
            
            # Initialize logger first
            self.logger = Logger("SAGE")
            main_log = self.logger.get_logger("main")
            main_log.info("Initializing SAGE application...")
            
            # Initialize configuration manager
            self.config_manager = ConfigManager(self.config_file)
            if not self.config_manager.load_config():
                main_log.error("Failed to load configuration")
                return False
                
            # Set log level from config
            log_level = self.config_manager.get("core.log_level", "INFO")
            self.logger.set_level(log_level)
            
            main_log.info(f"Configuration loaded from {self.config_file}")
            
            # Validate configuration
            issues = self.config_manager.validate_config()
            if issues["errors"]:
                main_log.error(f"Configuration errors: {issues['errors']}")
                return False
            if issues["warnings"]:
                main_log.warning(f"Configuration warnings: {issues['warnings']}")
                
            # Initialize cache manager
            cache_config = self.config_manager.get_performance_config()
            self.cache_manager = CacheManager(
                max_memory_mb=cache_config.get("cache_size_mb", 200),
                default_ttl=3600
            )
            main_log.info("Cache manager initialized")
            
            # Initialize event bus
            queue_size = self.config_manager.get("core.event_queue_size", 1000)
            self.event_bus = EventBus(max_queue_size=queue_size)
            await self.event_bus.start()
            main_log.info("Event bus started")
            
            # Initialize resource monitor
            monitor_interval = self.config_manager.get("core.resource_monitor_interval", 30)
            self.resource_monitor = ResourceMonitor(check_interval=monitor_interval)
            
            # Set resource thresholds
            perf_config = self.config_manager.get_performance_config()
            if "max_memory_mb" in perf_config:
                self.resource_monitor.set_threshold("sage_memory_mb", perf_config["max_memory_mb"])
            if "max_cpu_percent" in perf_config:
                self.resource_monitor.set_threshold("cpu_percent", perf_config["max_cpu_percent"])
                
            # Add resource monitoring callbacks
            self.resource_monitor.add_callback("sage_memory_limit", self._handle_memory_warning)
            self.resource_monitor.add_callback("high_cpu", self._handle_cpu_warning)
            
            await self.resource_monitor.start()
            main_log.info("Resource monitor started")
            
            # Initialize plugin manager
            self.plugin_manager = PluginManager()
            self.plugin_manager.set_dependencies(
                event_bus=self.event_bus,
                config_manager=self.config_manager,
                cache_manager=self.cache_manager,
                logger=self.logger
            )
            main_log.info("Plugin manager initialized")
            
            # Load auto-load modules
            auto_load_modules = self.config_manager.get_auto_load_modules()
            if auto_load_modules:
                main_log.info(f"Loading auto-load modules: {auto_load_modules}")
                load_results = await self.plugin_manager.load_all_modules(auto_load_modules)
                
                loaded_count = sum(1 for success in load_results.values() if success)
                main_log.info(f"Loaded {loaded_count}/{len(auto_load_modules)} modules successfully")
                
                # Log any failures
                for module_name, success in load_results.items():
                    if not success:
                        main_log.error(f"Failed to load module: {module_name}")
            else:
                main_log.info("No auto-load modules configured")
                
            self.running = True
            main_log.info("SAGE initialization completed successfully")
            
            return True
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to initialize SAGE: {e}", "main")
            else:
                print(f"❌ Failed to initialize SAGE: {e}")
            return False
            
    async def shutdown(self) -> None:
        """Shutdown SAGE gracefully"""
        try:
            if not self.running:
                return
                
            self.running = False
            main_log = self.logger.get_logger("main") if self.logger else None
            
            if main_log:
                main_log.info("Starting SAGE shutdown...")
            else:
                print("🔄 Shutting down SAGE...")
                
            # Shutdown modules first
            if self.plugin_manager:
                await self.plugin_manager.unload_all_modules()
                if main_log:
                    main_log.info("All modules unloaded")
                    
            # Shutdown core components
            if self.resource_monitor:
                await self.resource_monitor.stop()
                if main_log:
                    main_log.info("Resource monitor stopped")
                    
            if self.event_bus:
                await self.event_bus.stop()
                if main_log:
                    main_log.info("Event bus stopped")
                    
            # Clean up cache
            if self.cache_manager:
                self.cache_manager.cleanup()
                if main_log:
                    main_log.info("Cache cleaned up")
                    
            # Save configuration
            if self.config_manager:
                self.config_manager.save_config()
                if main_log:
                    main_log.info("Configuration saved")
                    
            # Final log and cleanup
            if self.logger:
                main_log.info("SAGE shutdown completed")
                self.logger.flush_logs()
            else:
                print("✅ SAGE shutdown completed")
                
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error during shutdown: {e}", "main")
            else:
                print(f"❌ Error during shutdown: {e}")
                
    def _handle_memory_warning(self, snapshot) -> None:
        """Handle memory usage warnings"""
        if self.logger:
            self.logger.warning(
                f"High memory usage: {snapshot.sage_memory_mb:.1f}MB", 
                "resources"
            )
            
        # Trigger cache cleanup
        if self.cache_manager:
            self.cache_manager.cleanup()
            
        # Trigger resource optimization  
        if self.resource_monitor:
            asyncio.create_task(self.resource_monitor.optimize_performance())
            
    def _handle_cpu_warning(self, snapshot) -> None:
        """Handle CPU usage warnings"""
        if self.logger:
            self.logger.warning(
                f"High CPU usage: {snapshot.cpu_percent:.1f}%", 
                "resources"
            )
            
    async def run(self) -> None:
        """Main application run loop"""
        try:
            # Setup signal handlers
            def signal_handler(signum, frame):
                print(f"\n🛑 Received signal {signum}, shutting down...")
                self.shutdown_event.set()
                
            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)
            
            main_log = self.logger.get_logger("main")
            main_log.info("SAGE is running. Press Ctrl+C to stop.")
            print("✅ SAGE is running. Press Ctrl+C to stop.")
            
            # Print status information
            self._print_status()
            
            # Welcome message
            print("\n🤖 Hello! I'm SAGE, your AI assistant.")
            print("💬 What can I help you with today?")
            print("📝 You can:")
            print("   • Ask me questions")
            print("   • Schedule calendar events")
            print("   • Have conversations that I'll remember")
            print("   • Use voice commands (if microphone available)")
            print("\n💡 Try running 'python demo_sage.py' in another terminal for interactive mode!")
            print("-" * 60)
            
            # Speak welcome message
            await self._speak_welcome_message()
            
            # Start voice listening if available
            voice_task = None
            voice_module = self.plugin_manager.get_module('voice')
            if voice_module and hasattr(voice_module, 'start_listening'):
                try:
                    print("🎤 Starting voice recognition...")
                    voice_listening_started = await voice_module.start_listening()
                    if voice_listening_started:
                        print("✅ Voice recognition active - say 'Hey Sage' or 'Sage' to interact")
                        # Create voice processing task
                        voice_task = asyncio.create_task(self._process_voice_commands())
                    else:
                        print("⚠️  Voice recognition not available (microphone/audio issues)")
                except Exception as e:
                    print(f"⚠️  Could not start voice recognition: {e}")
                    main_log.warning(f"Voice recognition startup failed: {e}")

            # Main event loop
            try:
                while self.running and not self.shutdown_event.is_set():
                    try:
                        # Wait for shutdown signal or timeout
                        await asyncio.wait_for(
                            self.shutdown_event.wait(), 
                            timeout=10.0
                        )
                        break
                    except asyncio.TimeoutError:
                        # Timeout is normal - continue running
                        continue
                    except Exception as e:
                        main_log.error(f"Error in main loop: {e}")
                        await asyncio.sleep(1)
            finally:
                # Stop voice recognition
                if voice_task:
                    voice_task.cancel()
                    try:
                        await voice_task
                    except asyncio.CancelledError:
                        pass
                        
                if voice_module and hasattr(voice_module, 'stop_listening'):
                    try:
                        await voice_module.stop_listening()
                        print("🔇 Voice recognition stopped")
                    except Exception as e:
                        main_log.warning(f"Error stopping voice recognition: {e}")
                    
        except KeyboardInterrupt:
            print("\n🛑 Keyboard interrupt received")
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error in main run loop: {e}", "main")
            else:
                print(f"❌ Error in main run loop: {e}")
        finally:
            await self.shutdown()
            
    async def _speak_welcome_message(self) -> None:
        """Speak a welcome message using voice synthesis"""
        try:
            if not self.plugin_manager:
                return
                
            voice_module = self.plugin_manager.get_module('voice')
            if voice_module and hasattr(voice_module, 'speak_text'):
                welcome_text = "Hello! I'm SAGE, your AI assistant. What can I help you with today?"
                
                # Try to speak the welcome message
                result = await voice_module.speak_text(welcome_text)
                
                if result:
                    print("🔊 Spoken welcome message delivered!")
                else:
                    print("🔇 Voice synthesis unavailable (audio hardware not accessible)")
                    
        except Exception as e:
            print(f"🔇 Could not speak welcome message: {e}")
            print("   Note: This is normal in WSL or systems without audio hardware")
    
    async def _process_voice_commands(self) -> None:
        """Process incoming voice commands from voice recognition"""
        try:
            voice_module = self.plugin_manager.get_module('voice')
            nlp_module = self.plugin_manager.get_module('nlp')
            main_log = self.logger.get_logger("voice")
            
            if not voice_module:
                main_log.error("Voice module not available for command processing")
                return
                
            main_log.info("Voice command processing started")
            
            while self.running and not self.shutdown_event.is_set():
                try:
                    # Check for voice input with timeout (longer to allow transcription time)
                    voice_input = await asyncio.wait_for(
                        voice_module.get_voice_input(), 
                        timeout=0.5
                    )
                    
                    if voice_input and voice_input.get('text'):
                        text = voice_input['text'].strip()
                        confidence = voice_input.get('confidence', 0.0)
                        
                        main_log.info(f"Voice input received: '{text}' (confidence: {confidence:.2f})")
                        print(f"🗣️  Heard: '{text}' (confidence: {confidence:.2f})")
                        
                        # Check for wake words
                        wake_words = ['sage', 'hey sage', 'computer', 'hey computer']
                        text_lower = text.lower()
                        
                        wake_word_detected = False
                        command_text = text_lower
                        
                        for wake_word in wake_words:
                            if wake_word in text_lower:
                                wake_word_detected = True
                                # Remove wake word from command
                                command_text = text_lower.replace(wake_word, '').strip()
                                break
                        
                        if wake_word_detected and command_text:
                            print(f"✅ Wake word detected! Processing: '{command_text}'")
                            main_log.info(f"Processing command: '{command_text}'")
                            
                            # Completely stop listening BEFORE processing to prevent feedback
                            print("🔇 Stopping listening during processing...")
                            await voice_module.stop_listening()
                            
                            # Wait for audio resources to fully release
                            print("⏸️ Waiting for audio resources to release...")
                            await asyncio.sleep(1.5)  # Longer delay to ensure complete audio release
                            
                            # Process command through NLP
                            if nlp_module:
                                try:
                                    # Analyze intent
                                    intent_result = await nlp_module.analyze_intent(command_text)
                                    print(f"🧠 Intent: {intent_result.get('intent', 'unknown')} (confidence: {intent_result.get('confidence', 0):.2f})")
                                    
                                    # Route to appropriate module (this includes TTS)
                                    await self._route_voice_command(command_text, intent_result)
                                    
                                except Exception as e:
                                    main_log.error(f"NLP processing failed: {e}")
                                    print(f"❌ Could not process command: {e}")
                                    await voice_module.speak_text("Sorry, I couldn't understand that command.")
                            else:
                                # Basic fallback without NLP
                                print("🔄 Processing without NLP module...")
                                await self._route_voice_command(command_text, {'intent': 'unknown'})
                            
                            # Wait for voice synthesis to complete
                            print("⏸️ Waiting for speech to complete...")
                            await asyncio.sleep(2.0)  # Give time for TTS to finish
                            
                            # Restart listening after speech
                            print("🎤 Restarting listening for next command...")
                            await voice_module.start_listening()
                                
                        elif wake_word_detected:
                            print("👋 Wake word detected but no command given")
                            print("🔇 Stopping listening during speech...")
                            await voice_module.stop_listening()
                            
                            await voice_module.speak_text("Yes? What can I help you with?")
                            print("⏸️ Waiting for speech to complete...")
                            await asyncio.sleep(3.0)  # Give time for TTS to finish
                            print("🎤 Restarting listening for next command...")
                            await voice_module.start_listening()
                        else:
                            # No wake word - ignore and resume listening immediately
                            print(f"⚠️  No wake word detected in: '{text}'")
                            voice_module.resume_listening()
                    
                except asyncio.TimeoutError:
                    # Normal timeout - give brief moment for transcription to complete
                    await asyncio.sleep(0.01)
                    continue
                except Exception as e:
                    main_log.error(f"Error processing voice input: {e}")
                    await asyncio.sleep(1)
                    
        except Exception as e:
            main_log.error(f"Voice command processing failed: {e}")
            print(f"❌ Voice command processing error: {e}")
    
    async def _route_voice_command(self, command_text: str, intent_result: dict) -> None:
        """Route voice commands to appropriate modules"""
        try:
            main_log = self.logger.get_logger("voice")
            voice_module = self.plugin_manager.get_module('voice')
            
            intent = intent_result.get('intent', 'unknown')
            confidence = intent_result.get('confidence', 0.0)
            
            main_log.info(f"Routing command '{command_text}' with intent '{intent}' (confidence: {confidence:.2f})")
            
            # Calendar commands
            if intent in ['calendar', 'schedule', 'meeting', 'event', 'appointment']:
                calendar_module = self.plugin_manager.get_module('calendar')
                if calendar_module:
                    try:
                        print("📅 Processing calendar command...")
                        result = await calendar_module.process_voice_command(command_text)
                        
                        if result.get('success'):
                            response = result.get('response', 'Calendar command processed.')
                            print(f"✅ Calendar: {response}")
                            await voice_module.speak_text(response)
                        else:
                            error_msg = result.get('error', 'Calendar command failed.')
                            print(f"❌ Calendar error: {error_msg}")
                            await voice_module.speak_text(f"Sorry, {error_msg}")
                            
                    except Exception as e:
                        main_log.error(f"Calendar processing error: {e}")
                        await voice_module.speak_text("Sorry, I had trouble with your calendar request.")
                else:
                    await voice_module.speak_text("Calendar module is not available.")
            
            # Time queries
            elif intent in ['time', 'clock', 'current_time', 'time_query']:
                try:
                    from datetime import datetime
                    current_time = datetime.now().strftime("%I:%M %p")
                    response = f"It's currently {current_time}"
                    print(f"🕐 {response}")
                    await voice_module.speak_text(response)
                except Exception as e:
                    main_log.error(f"Time query error: {e}")
                    await voice_module.speak_text("Sorry, I couldn't get the current time.")
            
            # General conversation/questions
            elif intent in ['question', 'conversation', 'general', 'unknown']:
                nlp_module = self.plugin_manager.get_module('nlp')
                if nlp_module:
                    try:
                        print("🤖 Processing general query...")
                        result = await nlp_module.process_text(command_text)
                        
                        if result.get('success'):
                            response = result['response']['text']
                            print(f"💬 Response: {response[:100]}...")
                            await voice_module.speak_text(response)
                        else:
                            error_msg = result.get('error', 'Could not process request.')
                            print(f"❌ NLP error: {error_msg}")
                            await voice_module.speak_text("Sorry, I couldn't process that request.")
                            
                    except Exception as e:
                        main_log.error(f"NLP processing error: {e}")
                        await voice_module.speak_text("Sorry, I had trouble understanding your request.")
                else:
                    await voice_module.speak_text("I can hear you, but my language processing isn't available right now.")
            
            # System commands
            elif intent in ['status', 'health', 'system']:
                try:
                    status = await self.get_status()
                    modules = list(status.get('modules', {}).keys())
                    module_count = len(modules)
                    
                    response = f"I'm running normally with {module_count} modules loaded: {', '.join(modules[:3])}"
                    if len(modules) > 3:
                        response += f" and {len(modules) - 3} others"
                    
                    print(f"🔧 System status: {response}")
                    await voice_module.speak_text(response)
                    
                except Exception as e:
                    main_log.error(f"Status query error: {e}")
                    await voice_module.speak_text("I'm having trouble checking my system status.")
            
            # Unknown/unsupported commands
            else:
                main_log.warning(f"Unsupported intent: {intent}")
                fallback_responses = [
                    "I'm not sure how to help with that.",
                    "Could you rephrase that request?",
                    "I didn't understand that command. Try asking about the time, calendar, or general questions.",
                ]
                
                import random
                response = random.choice(fallback_responses)
                print(f"❓ Unknown command: {response}")
                await voice_module.speak_text(response)
                
        except Exception as e:
            main_log.error(f"Command routing error: {e}")
            print(f"❌ Error routing command: {e}")
            
            if voice_module:
                await voice_module.speak_text("Sorry, I encountered an error processing your request.")
    
    def _print_status(self) -> None:
        """Print current SAGE status"""
        try:
            print("\n📊 SAGE Status:")
            print("-" * 30)
            
            # Loaded modules
            if self.plugin_manager:
                loaded_modules = self.plugin_manager.get_loaded_modules()
                print(f"Loaded modules: {', '.join(loaded_modules) if loaded_modules else 'None'}")
                
            # Resource usage
            if self.resource_monitor:
                current = self.resource_monitor.get_current_snapshot()
                if current:
                    print(f"Memory usage: {current.sage_memory_mb:.1f}MB")
                    print(f"CPU usage: {current.sage_cpu_percent:.1f}%")
                    
            # Cache statistics
            if self.cache_manager:
                cache_stats = self.cache_manager.get_statistics()
                memory_cache = cache_stats.get("memory_cache", {})
                print(f"Cache usage: {memory_cache.get('size_mb', 0):.1f}MB ({memory_cache.get('entries', 0)} entries)")
                
            print("-" * 30)
            
        except Exception as e:
            print(f"⚠️  Error printing status: {e}")
            
    async def get_status(self) -> dict:
        """Get comprehensive system status"""
        try:
            status = {
                "running": self.running,
                "config_file": str(self.config_file),
                "modules": {},
                "resources": {},
                "cache": {},
                "events": {}
            }
            
            # Module status
            if self.plugin_manager:
                status["modules"] = await self.plugin_manager.get_module_status()
                
            # Resource status
            if self.resource_monitor:
                status["resources"] = self.resource_monitor.get_statistics()
                
            # Cache status
            if self.cache_manager:
                status["cache"] = self.cache_manager.get_statistics()
                
            # Event bus status
            if self.event_bus:
                status["events"] = self.event_bus.get_statistics()
                
            return status
            
        except Exception as e:
            return {"error": str(e)}


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="SAGE - Smart Adaptive General Executive")
    parser.add_argument(
        "--config", 
        default="config.yaml",
        help="Configuration file path (default: config.yaml)"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode"
    )
    parser.add_argument(
        "--status",
        action="store_true", 
        help="Show status and exit"
    )
    
    args = parser.parse_args()
    
    # Create SAGE application
    app = SAGEApplication(config_file=args.config)
    
    try:
        # Initialize application
        if not await app.initialize():
            print("❌ Failed to initialize SAGE")
            return 1
            
        if args.status:
            # Show status and exit
            status = await app.get_status()
            print("\n📊 SAGE Status:")
            print("=" * 50)
            for key, value in status.items():
                print(f"{key.title()}: {value}")
            return 0
            
        # Run application
        await app.run()
        return 0
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    # Ensure proper asyncio event loop on Windows
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        
    # Run the application
    exit_code = asyncio.run(main())
    sys.exit(exit_code)