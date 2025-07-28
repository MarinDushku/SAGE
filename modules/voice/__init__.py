"""
Voice Module - Speech recognition and synthesis for SAGE
"""

import asyncio
import logging
from typing import Dict, Any, Optional

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
        """Handle text-to-speech requests"""
        try:
            text = event.data.get('text', '')
            voice_config = event.data.get('voice_config', {})
            
            if not text:
                self.log("Empty text in speak request", "warning")
                return False
                
            if self.synthesis_engine:
                success = await self.synthesis_engine.speak(text, voice_config)
                return success
            else:
                self.log("Synthesis engine not available", "error")
                return False
                
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


__all__ = ['VoiceModule']