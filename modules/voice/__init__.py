"""
Voice Module - Speech recognition and synthesis for SAGE
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List

from modules import BaseModule, EventType, Event


class VoiceModule(BaseModule):
    """Main voice processing module for SAGE"""
    
    def __init__(self, name: str = "voice"):
        super().__init__(name)
        self.recognition_engine = None
        self.synthesis_engine = None
        self.wake_word_detector = None
        self.audio_processor = None
        
        # Subscribe to relevant events
        self.subscribed_events = [
            EventType.SPEAK_REQUEST,
            EventType.VOICE_COMMAND,
        ]
        
    async def initialize(self) -> bool:
        """Initialize the voice module"""
        try:
            self.log("Initializing voice module...")
            
            # Get module configuration
            config = self.config or {}
            
            # Initialize recognition engine
            from .recognition import VoiceRecognition
            self.recognition_engine = VoiceRecognition(
                config.get('recognition', {}),
                self.cache,
                self.logger
            )
            
            # Initialize synthesis engine
            from .synthesis import VoiceSynthesis
            self.synthesis_engine = VoiceSynthesis(
                config.get('synthesis', {}),
                self.logger
            )
            
            # Initialize wake word detector if enabled
            wake_config = config.get('wake_word', {})
            if wake_config.get('enabled', True):
                from .wake_word import WakeWordDetector
                self.wake_word_detector = WakeWordDetector(
                    wake_config,
                    self.logger
                )
                
            # Initialize audio processor
            from .audio_utils import AudioProcessor
            self.audio_processor = AudioProcessor(
                config.get('audio', {}),
                self.logger
            )
            
            # Initialize all components
            init_results = await asyncio.gather(
                self.recognition_engine.initialize(),
                self.synthesis_engine.initialize(),
                self.wake_word_detector.initialize() if self.wake_word_detector else asyncio.sleep(0),
                self.audio_processor.initialize(),
                return_exceptions=True
            )
            
            # Check for initialization failures
            for i, result in enumerate(init_results):
                if isinstance(result, Exception):
                    component_names = ["recognition", "synthesis", "wake_word", "audio"]
                    self.log(f"Failed to initialize {component_names[i]}: {result}", "error")
                    
            # Set up recognition callbacks
            if self.recognition_engine:
                self.recognition_engine.set_callbacks(
                    on_text_recognized=self._on_text_recognized,
                    on_error=self._on_recognition_error
                )
                
            # Set up wake word callback
            if self.wake_word_detector:
                self.wake_word_detector.set_callback(self._on_wake_word_detected)
                    
            self.is_loaded = True
            self.log("Voice module initialized successfully")
            return True
            
        except Exception as e:
            self.log(f"Failed to initialize voice module: {e}", "error")
            return False
            
    async def shutdown(self) -> None:
        """Shutdown the voice module"""
        try:
            self.log("Shutting down voice module...")
            
            # Shutdown all components
            shutdown_tasks = []
            
            if self.recognition_engine:
                shutdown_tasks.append(self.recognition_engine.shutdown())
                
            if self.synthesis_engine:
                shutdown_tasks.append(self.synthesis_engine.shutdown())
                
            if self.wake_word_detector:
                shutdown_tasks.append(self.wake_word_detector.shutdown())
                
            if self.audio_processor:
                shutdown_tasks.append(self.audio_processor.shutdown())
                
            if shutdown_tasks:
                await asyncio.gather(*shutdown_tasks, return_exceptions=True)
                
            self.is_loaded = False
            self.log("Voice module shutdown completed")
            
        except Exception as e:
            self.log(f"Error during voice module shutdown: {e}", "error")
            
    async def handle_event(self, event: Event) -> Optional[Any]:
        """Handle events from other modules"""
        try:
            if event.type == EventType.SPEAK_REQUEST:
                return await self._handle_speak_request(event)
            elif event.type == EventType.VOICE_COMMAND:
                return await self._handle_voice_command(event)
            else:
                self.log(f"Unhandled event type: {event.type}", "warning")
                
        except Exception as e:
            self.log(f"Error handling event {event.type}: {e}", "error")
            return None
            
    async def _handle_speak_request(self, event: Event) -> bool:
        """Handle enhanced text-to-speech requests"""
        try:
            text = event.data.get('text', '')
            voice_config = event.data.get('voice_config', {})
            profile = event.data.get('profile', 'default')
            priority = event.data.get('priority', 'normal')
            emotion = event.data.get('emotion')
            intensity = event.data.get('intensity', 1.0)
            
            if not text:
                self.log("Empty text in speak request", "warning")
                return False
                
            if not self.synthesis_engine:
                self.log("Synthesis engine not available", "error")
                return False
                
            # Handle different types of speech requests
            if emotion:
                success = await self.synthesis_engine.speak_with_emotion(text, emotion, intensity)
            elif profile == 'notification':
                success = await self.synthesis_engine.speak_notification(text)
            elif profile == 'alert':
                success = await self.synthesis_engine.speak_alert(text)
            else:
                success = await self.synthesis_engine.speak(text, voice_config, profile, priority)
                
            return success
                
        except Exception as e:
            self.log(f"Error in speak request: {e}", "error")
            return False
            
    async def _handle_voice_command(self, event: Event) -> None:
        """Handle voice commands from recognition"""
        try:
            command = event.data.get('command', '')
            confidence = event.data.get('confidence', 0.0)
            
            self.log(f"Processing voice command: {command} (confidence: {confidence:.2f})")
            
            # Emit parsed intent event for NLP module to handle
            self.emit_event(EventType.INTENT_PARSED, {
                'text': command,
                'source': 'voice',
                'confidence': confidence,
                'raw_data': event.data
            })
            
        except Exception as e:
            self.log(f"Error processing voice command: {e}", "error")
            
    async def start_listening(self) -> bool:
        """Start voice recognition"""
        try:
            if self.recognition_engine:
                return await self.recognition_engine.start_listening()
            return False
        except Exception as e:
            self.log(f"Error starting voice recognition: {e}", "error")
            return False
            
    async def stop_listening(self) -> bool:
        """Stop voice recognition"""
        try:
            if self.recognition_engine:
                return await self.recognition_engine.stop_listening()
            return False
        except Exception as e:
            self.log(f"Error stopping voice recognition: {e}", "error")
            return False
            
    async def speak(self, text: str, voice_config: Optional[Dict[str, Any]] = None) -> bool:
        """Speak text using TTS"""
        try:
            if self.synthesis_engine:
                return await self.synthesis_engine.speak(text, voice_config or {})
            return False
        except Exception as e:
            self.log(f"Error in TTS speak: {e}", "error")
            return False
            
    async def is_listening(self) -> bool:
        """Check if voice recognition is active"""
        try:
            if self.recognition_engine:
                return await self.recognition_engine.is_listening()
            return False
        except Exception as e:
            self.log(f"Error checking listening status: {e}", "error")
            return False
            
    def get_voice_status(self) -> Dict[str, Any]:
        """Get current voice module status"""
        try:
            status = {
                "loaded": self.is_loaded,
                "recognition_available": self.recognition_engine is not None,
                "synthesis_available": self.synthesis_engine is not None,
                "wake_word_available": self.wake_word_detector is not None,
                "audio_processor_available": self.audio_processor is not None
            }
            
            # Add detailed status from components
            if self.recognition_engine:
                status["recognition_status"] = self.recognition_engine.get_status()
                
            if self.synthesis_engine:
                status["synthesis_status"] = self.synthesis_engine.get_status()
                
            if self.wake_word_detector:
                status["wake_word_status"] = self.wake_word_detector.get_status()
                
            return status
            
        except Exception as e:
            self.log(f"Error getting voice status: {e}", "error")
            return {"error": str(e)}
            
    # Callback methods for voice events
    async def _on_text_recognized(self, text: str, confidence: float):
        """Handle recognized speech text"""
        try:
            import time
            self.log(f"Speech recognized: '{text}' (confidence: {confidence:.2f})")
            
            # Emit voice command event
            self.emit_event(EventType.VOICE_COMMAND, {
                'command': text,
                'confidence': confidence,
                'timestamp': time.time(),
                'source': 'voice_recognition'
            })
            
        except Exception as e:
            self.log(f"Error handling recognized text: {e}", "error")
            
    async def _on_recognition_error(self, error: str):
        """Handle recognition errors"""
        self.log(f"Recognition error: {error}", "error")
        
        # Emit error event
        import time
        self.emit_event(EventType.SYSTEM_ERROR, {
            'error': error,
            'component': 'voice_recognition',
            'timestamp': time.time()
        })
        
    async def _on_wake_word_detected(self):
        """Handle wake word detection"""
        self.log("Wake word detected - activating voice recognition")
        
        # Start listening for voice commands
        if self.recognition_engine:
            await self.recognition_engine.start_listening()
            
        # Emit wake word event
        import time
        self.emit_event(EventType.WAKE_WORD_DETECTED, {
            'timestamp': time.time(),
            'keyword': self.wake_word_detector.keyword if self.wake_word_detector else 'unknown'
        })
        
    # Voice control methods
    async def start_voice_recognition(self) -> bool:
        """Start continuous voice recognition"""
        try:
            if not self.recognition_engine:
                self.log("Recognition engine not available", "error")
                return False
                
            result = await self.recognition_engine.start_listening()
            if result:
                self.log("Voice recognition started")
            return result
            
        except Exception as e:
            self.log(f"Error starting voice recognition: {e}", "error")
            return False
            
    async def stop_voice_recognition(self) -> bool:
        """Stop voice recognition"""
        try:
            if not self.recognition_engine:
                return True
                
            result = await self.recognition_engine.stop_listening()
            if result:
                self.log("Voice recognition stopped")
            return result
            
        except Exception as e:
            self.log(f"Error stopping voice recognition: {e}", "error")
            return False
            
    async def recognize_once(self, timeout: float = 5.0) -> Optional[str]:
        """Recognize speech from a single input"""
        try:
            if not self.recognition_engine:
                return None
                
            result = await self.recognition_engine.recognize_once(timeout)
            if result:
                self.log(f"Single recognition result: '{result}'")
            return result
            
        except Exception as e:
            self.log(f"Error in single recognition: {e}", "error")
            return None
            
    async def speak_text(self, text: str, voice_config: Optional[Dict[str, Any]] = None, 
                        profile: str = 'default', priority: str = 'normal') -> bool:
        """Synthesize and speak text with advanced options"""  
        try:
            if not self.synthesis_engine:
                self.log("Synthesis engine not available", "error")
                return False
                
            result = await self.synthesis_engine.speak(text, voice_config, profile, priority)
            return result
            
        except Exception as e:
            self.log(f"Error speaking text: {e}", "error")
            return False
            
    async def speak_with_emotion(self, text: str, emotion: str, intensity: float = 1.0) -> bool:
        """Speak text with specific emotion and intensity"""
        try:
            if not self.synthesis_engine:
                self.log("Synthesis engine not available", "error")
                return False
                
            result = await self.synthesis_engine.speak_with_emotion(text, emotion, intensity)
            return result
            
        except Exception as e:
            self.log(f"Error speaking with emotion: {e}", "error")
            return False
            
    async def speak_notification(self, text: str) -> bool:
        """Speak notification using optimized notification profile"""
        try:
            if not self.synthesis_engine:
                self.log("Synthesis engine not available", "error")
                return False
                
            result = await self.synthesis_engine.speak_notification(text)
            return result
            
        except Exception as e:
            self.log(f"Error speaking notification: {e}", "error")
            return False
            
    async def speak_alert(self, text: str) -> bool:
        """Speak urgent alert with high priority"""
        try:
            if not self.synthesis_engine:
                self.log("Synthesis engine not available", "error")
                return False
                
            result = await self.synthesis_engine.speak_alert(text)
            return result
            
        except Exception as e:
            self.log(f"Error speaking alert: {e}", "error")
            return False
            
    async def get_available_voices(self) -> List[Dict[str, Any]]:
        """Get list of available voices across all TTS engines"""
        try:
            if not self.synthesis_engine:
                return []
                
            return self.synthesis_engine.get_available_voices()
            
        except Exception as e:
            self.log(f"Error getting available voices: {e}", "error")
            return []
            
    async def set_voice_profile(self, profile_name: str, profile_config: Dict[str, Any]) -> bool:
        """Set or update a voice profile"""
        try:
            if not self.synthesis_engine:
                self.log("Synthesis engine not available", "error")
                return False
                
            await self.synthesis_engine.set_voice_profile(profile_name, profile_config)
            self.log(f"Voice profile '{profile_name}' updated")
            return True
            
        except Exception as e:
            self.log(f"Error setting voice profile: {e}", "error")
            return False
            
    async def get_voice_profiles(self) -> Dict[str, Dict[str, Any]]:
        """Get all available voice profiles"""
        try:
            if not self.synthesis_engine:
                return {}
                
            return await self.synthesis_engine.get_voice_profiles()
            
        except Exception as e:
            self.log(f"Error getting voice profiles: {e}", "error")
            return {}


__all__ = ['VoiceModule']