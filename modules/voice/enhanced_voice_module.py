"""
Enhanced Voice Module - Complete voice interface with improved recognition and NLP integration
"""

import asyncio
import logging
import time
from typing import Dict, Any, Optional, List
from pathlib import Path

from modules import BaseModule, EventType, Event
from .enhanced_recognition import EnhancedVoiceRecognition
from .synthesis import VoiceSynthesis  # We'll create this if needed


class EnhancedVoiceModule(BaseModule):
    """Enhanced voice module with fixed recognition and integrated conversation flow"""
    
    def __init__(self, name: str = "voice"):
        super().__init__(name)
        
        # Voice components
        self.recognition = None
        self.synthesis = None
        
        # Conversation state
        self.listening_for_response = False
        self.conversation_context = {}
        self.wake_word_active = True
        
        # Configuration (will be loaded from config)
        self.wake_words = ['sage', 'hey sage', 'computer']
        self.continuous_mode = False
        self.push_to_talk_mode = False
        
        # Statistics
        self.stats = {
            'voice_commands_processed': 0,
            'successful_recognitions': 0,
            'failed_recognitions': 0,
            'text_responses_spoken': 0,
            'conversation_turns': 0,
            'wake_word_detections': 0
        }
        
        # Audio monitoring
        self.current_audio_level = 0
        self.mic_working = False
    
    async def initialize(self) -> bool:
        """Initialize the enhanced voice module"""
        try:
            self.log("Initializing Enhanced Voice Module...")
            
            # Load voice configuration
            voice_config = self._load_voice_config()
            
            # Initialize enhanced recognition
            self.recognition = EnhancedVoiceRecognition(
                config=voice_config.get('recognition', {}),
                cache_manager=self.cache_manager,
                logger=self.logger
            )
            
            # Set recognition callbacks
            self.recognition.set_callbacks(
                on_speech_detected=self._on_speech_detected,
                on_text_recognized=self._on_text_recognized,
                on_error=self._on_recognition_error,
                on_audio_level=self._on_audio_level
            )
            
            # Initialize recognition
            if not await self.recognition.initialize():
                self.log("Failed to initialize voice recognition", "error")
                return False
            
            # Initialize voice synthesis (basic for now)
            await self._initialize_synthesis(voice_config.get('synthesis', {}))
            
            # Subscribe to events
            self.subscribe_events([
                EventType.LLM_RESPONSE,
                EventType.SCHEDULE_UPDATED,
                EventType.REMINDER_DUE
            ])
            
            self.is_loaded = True
            self.log("Enhanced Voice Module initialized successfully")
            
            # Get microphone status
            status = self.recognition.get_status()
            self.mic_working = status.get('microphone_working', False)
            
            if self.mic_working:
                self.log("✅ Microphone working - voice input enabled")
            else:
                self.log("❌ Microphone not working - voice input disabled", "warning")
            
            return True
            
        except Exception as e:
            self.log(f"Failed to initialize Enhanced Voice Module: {e}", "error")
            return False
    
    async def shutdown(self) -> None:
        """Shutdown the voice module"""
        self.log("Shutting down Enhanced Voice Module...")
        
        if self.recognition:
            await self.recognition.shutdown()
        
        if self.synthesis:
            await self.synthesis.shutdown()
        
        self.is_loaded = False
        self.log("Enhanced Voice Module shutdown complete")
    
    def _load_voice_config(self) -> Dict[str, Any]:
        """Load voice configuration with enhanced defaults"""
        config = self.config if self.config else {}
        
        # Enhanced recognition config
        recognition_config = config.get('recognition', {})
        recognition_config.setdefault('engine', 'whisper')
        recognition_config.setdefault('model', 'tiny')
        recognition_config.setdefault('language', 'en')
        recognition_config.setdefault('energy_threshold', 300)
        recognition_config.setdefault('debug_mode', True)
        recognition_config.setdefault('audio_monitoring', True)
        
        # Synthesis config
        synthesis_config = config.get('synthesis', {})
        synthesis_config.setdefault('engine', 'pyttsx3')
        synthesis_config.setdefault('rate', 200)
        synthesis_config.setdefault('volume', 0.8)
        
        return {
            'recognition': recognition_config,
            'synthesis': synthesis_config,
            'wake_word': config.get('wake_word', {}),
            'features': config.get('features', {})
        }
    
    async def _initialize_synthesis(self, synthesis_config: Dict[str, Any]):
        """Initialize voice synthesis"""
        try:
            # For now, use a simple synthesis class
            # We can enhance this later with more advanced TTS
            self.synthesis = SimpleTTS(synthesis_config, logger=self.logger)
            await self.synthesis.initialize()
            self.log("Voice synthesis initialized")
            
        except Exception as e:
            self.log(f"Voice synthesis initialization failed: {e}", "warning")
            self.synthesis = None
    
    async def start_listening(self) -> bool:
        """Start voice recognition"""
        if not self.recognition:
            self.log("Voice recognition not initialized", "error")
            return False
        
        if not self.mic_working:
            self.log("Microphone not working - cannot start listening", "error")
            return False
        
        self.log("Starting voice listening...")
        success = await self.recognition.start_listening()
        
        if success:
            self.log("🎤 Voice recognition started - say 'Hey Sage' or 'Sage' to begin")
            
            # Announce that we're listening
            await self._speak("Voice recognition started. I'm listening for your commands.")
            
        return success
    
    async def stop_listening(self) -> bool:
        """Stop voice recognition"""
        if not self.recognition:
            return True
        
        self.log("Stopping voice listening...")
        return await self.recognition.stop_listening()
    
    async def _on_speech_detected(self, audio):
        """Handle speech detection"""
        self.log("Speech detected, processing...", "debug")
    
    async def _on_text_recognized(self, text: str, confidence: float):
        """Handle recognized text"""
        try:
            text_clean = text.strip().lower()
            
            if not text_clean:
                return
            
            self.stats['successful_recognitions'] += 1
            self.log(f"🗣️  Recognized: '{text}' (confidence: {confidence:.2f})")
            
            # Check for wake word activation
            if not self.listening_for_response and not self._check_wake_word(text_clean):
                self.log(f"No wake word detected in: '{text_clean}'", "debug")
                return
            
            # Remove wake word from command
            command_text = self._remove_wake_word(text_clean)
            
            if not command_text.strip():
                # Just wake word, acknowledge
                await self._speak("Yes? How can I help you?")
                self.listening_for_response = True
                return
            
            # Process the command
            await self._process_voice_command(command_text, confidence)
            
        except Exception as e:
            self.log(f"Error handling recognized text: {e}", "error")
    
    async def _on_recognition_error(self, error: str):
        """Handle recognition errors"""
        self.stats['failed_recognitions'] += 1
        self.log(f"Recognition error: {error}", "error")
    
    async def _on_audio_level(self, level: float):
        """Handle audio level updates"""
        self.current_audio_level = level
        # Could be used for visual feedback or debugging
    
    def _check_wake_word(self, text: str) -> bool:
        """Check if text contains wake word"""
        if self.listening_for_response:
            return True  # Already activated
        
        for wake_word in self.wake_words:
            if wake_word in text:
                self.stats['wake_word_detections'] += 1
                self.log(f"Wake word '{wake_word}' detected")
                return True
        
        return False
    
    def _remove_wake_word(self, text: str) -> str:
        """Remove wake word from command text"""
        for wake_word in self.wake_words:
            if text.startswith(wake_word):
                return text[len(wake_word):].strip()
            # Also check if wake word is anywhere in the text
            text = text.replace(wake_word, "").strip()
        
        return text
    
    async def _process_voice_command(self, command: str, confidence: float):
        """Process voice command through NLP and generate response"""
        try:
            self.stats['voice_commands_processed'] += 1
            self.stats['conversation_turns'] += 1
            
            self.log(f"Processing command: '{command}'")
            
            # Emit voice command event for NLP processing
            self.emit_event(EventType.VOICE_COMMAND, {
                'command': command,
                'confidence': confidence,
                'source': 'voice',
                'timestamp': time.time()
            })
            
            # Reset listening state after processing
            self.listening_for_response = False
            
        except Exception as e:
            self.log(f"Error processing voice command: {e}", "error")
            await self._speak("Sorry, I had trouble processing that command.")
    
    async def handle_event(self, event: Event) -> Optional[Any]:
        """Handle events from other modules"""
        try:
            if event.type == EventType.LLM_RESPONSE:
                # Speak LLM responses
                response_text = event.data.get('response', {}).get('text', '')
                if response_text:
                    await self._speak_response(response_text)
                    
            elif event.type == EventType.SCHEDULE_UPDATED:
                # Announce schedule updates
                action = event.data.get('action', 'updated')
                if action == 'created':
                    await self._speak("Meeting scheduled successfully.")
                    
            elif event.type == EventType.REMINDER_DUE:
                # Speak reminders
                message = event.data.get('message', 'You have a reminder.')
                await self._speak(f"Reminder: {message}")
                
        except Exception as e:
            self.log(f"Error handling event: {e}", "error")
        
        return None
    
    async def _speak_response(self, text: str):
        """Speak a response from the system"""
        try:
            # Handle different response types
            if isinstance(text, dict):
                if 'message' in text:
                    text = text['message']
                elif 'text' in text:
                    text = text['text']
                else:
                    text = str(text)
            
            # Clean up text for speech
            text = self._clean_text_for_speech(text)
            
            if text:
                await self._speak(text)
                
        except Exception as e:
            self.log(f"Error speaking response: {e}", "error")
    
    def _clean_text_for_speech(self, text: str) -> str:
        """Clean text for better speech synthesis"""
        if not text:
            return ""
        
        # Remove markdown-style formatting
        text = text.replace('**', '')
        text = text.replace('*', '')
        text = text.replace('`', '')
        
        # Remove excessive newlines
        text = text.replace('\n\n', '. ')
        text = text.replace('\n', '. ')
        
        # Clean up bullet points
        text = text.replace('•', '')
        text = text.replace('- ', '')
        
        # Limit length for speech
        max_length = 500
        if len(text) > max_length:
            # Find a good breaking point
            sentences = text.split('. ')
            result = ""
            for sentence in sentences:
                if len(result + sentence) < max_length:
                    result += sentence + ". "
                else:
                    break
            text = result.strip()
        
        return text.strip()
    
    async def _speak(self, text: str):
        """Speak text using voice synthesis"""
        try:
            if not text or not text.strip():
                return
            
            self.log(f"🔊 Speaking: '{text}'")
            
            if self.synthesis:
                success = await self.synthesis.speak(text)
                if success:
                    self.stats['text_responses_spoken'] += 1
                else:
                    self.log("Voice synthesis failed", "warning")
            else:
                self.log("Voice synthesis not available", "warning")
                
        except Exception as e:
            self.log(f"Error speaking text: {e}", "error")
    
    async def speak_text(self, text: str) -> bool:
        """Public method to speak text"""
        try:
            await self._speak(text)
            return True
        except Exception as e:
            self.log(f"Error in speak_text: {e}", "error")
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """Get voice module status"""
        recognition_status = self.recognition.get_status() if self.recognition else {}
        
        return {
            'module': 'enhanced_voice',
            'status': 'active' if self.is_loaded else 'inactive',
            'microphone_working': self.mic_working,
            'listening': recognition_status.get('listening', False),
            'current_audio_level': self.current_audio_level,
            'listening_for_response': self.listening_for_response,
            'wake_word_active': self.wake_word_active,
            'recognition_status': recognition_status,
            'statistics': self.stats.copy(),
            'capabilities': [
                'Wake word detection',
                'Continuous voice recognition',
                'Natural language processing integration',
                'Text-to-speech responses',
                'Conversation context tracking',
                'Audio level monitoring'
            ]
        }
    
    def get_debug_info(self) -> Dict[str, Any]:
        """Get detailed debug information"""
        debug = {
            'module_debug': {
                'listening_for_response': self.listening_for_response,
                'conversation_context': self.conversation_context,
                'current_audio_level': self.current_audio_level,
                'wake_words': self.wake_words
            }
        }
        
        if self.recognition:
            debug['recognition_debug'] = self.recognition.get_debug_info()
        
        return debug


class SimpleTTS:
    """Simple text-to-speech implementation"""
    
    def __init__(self, config: Dict[str, Any], logger=None):
        self.config = config
        self.logger = logger or logging.getLogger(__name__)
        self.engine = None
        
        # Try to import pyttsx3
        try:
            import pyttsx3
            self.pyttsx3 = pyttsx3
            self.pyttsx3_available = True
        except ImportError:
            self.pyttsx3 = None
            self.pyttsx3_available = False
    
    async def initialize(self) -> bool:
        """Initialize TTS engine"""
        try:
            if self.pyttsx3_available:
                self.engine = self.pyttsx3.init()
                
                # Configure voice settings
                rate = self.config.get('rate', 200)
                volume = self.config.get('volume', 0.8)
                
                self.engine.setProperty('rate', rate)
                self.engine.setProperty('volume', volume)
                
                # Try to set voice
                voices = self.engine.getProperty('voices')
                if voices:
                    # Use first available voice
                    self.engine.setProperty('voice', voices[0].id)
                
                return True
            else:
                self.logger.warning("pyttsx3 not available - TTS disabled")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to initialize TTS: {e}")
            return False
    
    async def speak(self, text: str) -> bool:
        """Speak text"""
        try:
            if not self.engine:
                return False
            
            self.engine.say(text)
            self.engine.runAndWait()
            return True
            
        except Exception as e:
            self.logger.error(f"TTS error: {e}")
            return False
    
    async def shutdown(self):
        """Shutdown TTS"""
        if self.engine:
            try:
                self.engine.stop()
            except:
                pass