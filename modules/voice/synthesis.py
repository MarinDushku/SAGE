"""
Voice Synthesis Engine - Text-to-speech for SAGE
"""

import asyncio
import logging
import threading
from typing import Dict, Any, Optional

# Try to import TTS libraries
try:
    import pyttsx3
    PYTTSX3_AVAILABLE = True
except ImportError:
    pyttsx3 = None
    PYTTSX3_AVAILABLE = False


class VoiceSynthesis:
    """Text-to-speech synthesis engine"""
    
    def __init__(self, config: Dict[str, Any], logger=None):
        self.config = config
        self.logger = logger or logging.getLogger(__name__)
        
        # Configuration
        self.engine_type = config.get('engine', 'pyttsx3')
        self.rate = config.get('rate', 200)
        self.volume = config.get('volume', 0.8)
        self.voice_id = config.get('voice_id', None)
        
        # State
        self.is_initialized = False
        self.is_speaking = False
        
        # Components
        self.tts_engine = None
        self.synthesis_lock = threading.Lock()
        
        # Statistics
        self.stats = {
            'texts_synthesized': 0,
            'synthesis_failures': 0,
            'total_characters': 0,
            'engine_used': self.engine_type
        }
        
    async def initialize(self) -> bool:
        """Initialize the text-to-speech system"""
        try:
            self.logger.info(f"Initializing voice synthesis with engine: {self.engine_type}")
            
            # Check dependencies
            if not self._check_dependencies():
                return False
                
            # Initialize TTS engine
            if self.engine_type == 'pyttsx3' and PYTTSX3_AVAILABLE:
                def init_pyttsx3():
                    engine = pyttsx3.init()
                    
                    # Configure rate
                    engine.setProperty('rate', self.rate)
                    
                    # Configure volume
                    engine.setProperty('volume', self.volume)
                    
                    # Configure voice if specified
                    if self.voice_id:
                        voices = engine.getProperty('voices')
                        for voice in voices:
                            if self.voice_id in voice.id or self.voice_id in voice.name:
                                engine.setProperty('voice', voice.id)
                                break
                                
                    return engine
                    
                loop = asyncio.get_event_loop()
                self.tts_engine = await loop.run_in_executor(None, init_pyttsx3)
                
            self.is_initialized = True
            self.logger.info("Voice synthesis initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize voice synthesis: {e}")
            return False
            
    def _check_dependencies(self) -> bool:
        """Check if required dependencies are available"""
        if self.engine_type == 'pyttsx3' and not PYTTSX3_AVAILABLE:
            self.logger.error("pyttsx3 not available. Install with: pip install pyttsx3")
            return False
            
        return True
        
    async def speak(self, text: str, voice_config: Optional[Dict[str, Any]] = None) -> bool:
        """Synthesize and speak text"""
        if not self.is_initialized:
            self.logger.error("Voice synthesis not initialized")
            return False
            
        if not text or not text.strip():
            self.logger.warning("Empty text provided for synthesis")
            return False
            
        try:
            with self.synthesis_lock:
                if self.is_speaking:
                    self.logger.warning("Already speaking, skipping new request")
                    return False
                    
                self.is_speaking = True
                
            self.logger.info(f"Speaking: '{text[:50]}{'...' if len(text) > 50 else ''}'")
            
            # Apply voice configuration if provided
            if voice_config:
                await self._apply_voice_config(voice_config)
                
            # Synthesize speech
            success = await self._synthesize_text(text)
            
            # Update statistics
            if success:
                self.stats['texts_synthesized'] += 1
                self.stats['total_characters'] += len(text)
            else:
                self.stats['synthesis_failures'] += 1
                
            return success
            
        except Exception as e:
            self.logger.error(f"Speech synthesis failed: {e}")
            self.stats['synthesis_failures'] += 1
            return False
        finally:
            self.is_speaking = False
            
    async def _apply_voice_config(self, voice_config: Dict[str, Any]):
        """Apply temporary voice configuration"""
        if not self.tts_engine:
            return
            
        try:
            def apply_config():
                if 'rate' in voice_config:
                    self.tts_engine.setProperty('rate', voice_config['rate'])
                    
                if 'volume' in voice_config:
                    self.tts_engine.setProperty('volume', voice_config['volume'])
                    
                if 'voice_id' in voice_config:
                    voices = self.tts_engine.getProperty('voices')
                    for voice in voices:
                        if voice_config['voice_id'] in voice.id or voice_config['voice_id'] in voice.name:
                            self.tts_engine.setProperty('voice', voice.id)
                            break
                            
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, apply_config)
            
        except Exception as e:
            self.logger.warning(f"Failed to apply voice config: {e}")
            
    async def _synthesize_text(self, text: str) -> bool:
        """Synthesize text using the configured engine"""
        try:
            if self.engine_type == 'pyttsx3' and self.tts_engine:
                return await self._synthesize_with_pyttsx3(text)
            else:
                self.logger.error(f"No synthesis engine available for: {self.engine_type}")
                return False
                
        except Exception as e:
            self.logger.error(f"Text synthesis failed: {e}")
            return False
            
    async def _synthesize_with_pyttsx3(self, text: str) -> bool:
        """Synthesize speech using pyttsx3"""
        try:
            def speak_text():
                self.tts_engine.say(text)
                self.tts_engine.runAndWait()
                return True
                
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, speak_text)
            
            return result
            
        except Exception as e:
            self.logger.error(f"pyttsx3 synthesis failed: {e}")
            return False
            
    async def stop_speaking(self) -> bool:
        """Stop current speech synthesis"""
        try:
            if not self.is_speaking:
                return True
                
            if self.tts_engine:
                def stop_engine():
                    self.tts_engine.stop()
                    
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, stop_engine)
                
            self.is_speaking = False
            self.logger.info("Speech synthesis stopped")
            return True
            
        except Exception as e:
            self.logger.error(f"Error stopping speech: {e}")
            return False
            
    async def shutdown(self):
        """Shutdown voice synthesis"""
        await self.stop_speaking()
        self.is_initialized = False
        self.logger.info("Voice synthesis shutdown complete")
        
    def get_available_voices(self) -> list:
        """Get list of available voices"""
        if not self.tts_engine:
            return []
            
        try:
            voices = self.tts_engine.getProperty('voices')
            voice_list = []
            
            for voice in voices:
                voice_info = {
                    'id': voice.id,
                    'name': voice.name,
                    'languages': getattr(voice, 'languages', []),
                    'gender': getattr(voice, 'gender', 'unknown'),
                    'age': getattr(voice, 'age', 'unknown')
                }
                voice_list.append(voice_info)
                
            return voice_list
            
        except Exception as e:
            self.logger.error(f"Error getting available voices: {e}")
            return []
            
    def get_status(self) -> Dict[str, Any]:
        """Get current synthesis status"""
        return {
            'initialized': self.is_initialized,
            'speaking': self.is_speaking,
            'engine': self.engine_type,
            'rate': self.rate,
            'volume': self.volume,
            'voice_id': self.voice_id,
            'dependencies': {
                'pyttsx3': PYTTSX3_AVAILABLE
            },
            'statistics': self.stats.copy()
        }
        
    def get_statistics(self) -> Dict[str, Any]:
        """Get synthesis statistics"""
        stats = self.stats.copy()
        
        total_requests = stats['texts_synthesized'] + stats['synthesis_failures']
        if total_requests > 0:
            stats['success_rate'] = stats['texts_synthesized'] / total_requests
        else:
            stats['success_rate'] = 0.0
            
        if stats['texts_synthesized'] > 0:
            stats['average_text_length'] = stats['total_characters'] / stats['texts_synthesized']
        else:
            stats['average_text_length'] = 0.0
            
        return stats