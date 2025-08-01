"""
Voice Synthesis Engine - Text-to-speech for SAGE
"""

import asyncio
import logging
import threading
import time
import hashlib
import json
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path

# Try to import TTS libraries
try:
    import pyttsx3
    PYTTSX3_AVAILABLE = True
except ImportError:
    pyttsx3 = None
    PYTTSX3_AVAILABLE = False

# Try to import alternative TTS engines
try:
    import gtts  # Google Text-to-Speech
    GTTS_AVAILABLE = True
except ImportError:
    gtts = None
    GTTS_AVAILABLE = False

try:
    import edge_tts  # Microsoft Edge TTS
    EDGE_TTS_AVAILABLE = True
except ImportError:
    edge_tts = None
    EDGE_TTS_AVAILABLE = False


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
        
        # Advanced TTS features
        self.pitch = config.get('pitch', 0)  # -50 to 50
        self.emotion = config.get('emotion', 'neutral')  # neutral, happy, sad, excited
        self.speaking_style = config.get('speaking_style', 'normal')  # normal, newscast, cheerful, sad
        self.language = config.get('language', 'en-US')
        
        # Caching configuration
        self.cache_enabled = config.get('cache_enabled', True)
        self.cache_dir = Path(config.get('cache_dir', 'cache/tts'))
        self.cache_max_age = config.get('cache_max_age', 86400)  # 24 hours
        
        # Voice profiles for different contexts
        self.voice_profiles = config.get('voice_profiles', {
            'default': {'rate': 200, 'volume': 0.8, 'emotion': 'neutral'},
            'notification': {'rate': 180, 'volume': 0.9, 'emotion': 'neutral'},
            'alert': {'rate': 160, 'volume': 1.0, 'emotion': 'excited'},
            'reading': {'rate': 220, 'volume': 0.7, 'emotion': 'neutral'},
            'conversation': {'rate': 190, 'volume': 0.8, 'emotion': 'friendly'}
        })
        
        # State
        self.is_initialized = False
        self.is_speaking = False
        
        # Components
        self.tts_engine = None
        self.synthesis_lock = threading.Lock()
        
        # Enhanced statistics
        self.stats = {
            'texts_synthesized': 0,
            'synthesis_failures': 0,
            'total_characters': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'average_synthesis_time': 0.0,
            'engine_used': self.engine_type,
            'voice_profiles_used': {},
            'languages_used': {},
            'synthesis_history': []  # Last 100 syntheses
        }
        
        # Create cache directory
        if self.cache_enabled:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        
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
                    
                    # Configure voice - try to find a working voice
                    voices = engine.getProperty('voices')
                    voice_set = False
                    
                    if self.voice_id and voices:
                        # Try to find the specified voice
                        for voice in voices:
                            if voice and (self.voice_id in str(voice.id) or self.voice_id in str(voice.name)):
                                try:
                                    engine.setProperty('voice', voice.id)
                                    voice_set = True
                                    break
                                except:
                                    continue
                    
                    # If no voice was set, use the first available voice
                    if not voice_set and voices:
                        for voice in voices:
                            if voice and voice.id:
                                try:
                                    engine.setProperty('voice', voice.id)
                                    voice_set = True
                                    break
                                except:
                                    continue
                                    
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
        
    async def speak(self, text: str, voice_config: Optional[Dict[str, Any]] = None, 
                   profile: str = 'default', priority: str = 'normal') -> bool:
        """Synthesize and speak text with advanced options"""
        if not self.is_initialized:
            self.logger.error("Voice synthesis not initialized")
            return False
            
        if not text or not text.strip():
            self.logger.warning("Empty text provided for synthesis")
            return False
            
        start_time = time.time()
        
        try:
            # Handle priority and queuing
            if priority == 'urgent' and self.is_speaking:
                await self.stop_speaking()
            elif self.is_speaking and priority == 'normal':
                self.logger.info("Already speaking, queuing request")
                # Could implement a queue here for future enhancement
                return False
                
            with self.synthesis_lock:
                self.is_speaking = True
                
            self.logger.info(f"Speaking ({profile}): '{text[:50]}{'...' if len(text) > 50 else ''}'")
            
            # Apply voice profile
            effective_config = await self._get_effective_config(profile, voice_config)
            
            # Check cache first
            cache_key = None
            if self.cache_enabled:
                cache_key = self._generate_cache_key(text, effective_config)
                cached_result = await self._get_cached_synthesis(cache_key)
                if cached_result:
                    self.stats['cache_hits'] += 1
                    success = await self._play_cached_audio(cached_result)
                    self._update_synthesis_stats(text, profile, time.time() - start_time, success)
                    return success
                else:
                    self.stats['cache_misses'] += 1
            
            # Apply voice configuration
            await self._apply_voice_config(effective_config)
                
            # Synthesize speech
            success = await self._synthesize_text(text, effective_config, cache_key)
            
            # Update statistics
            self._update_synthesis_stats(text, profile, time.time() - start_time, success)
                
            return success
            
        except Exception as e:
            self.logger.error(f"Speech synthesis failed: {e}")
            self.stats['synthesis_failures'] += 1
            self._update_synthesis_stats(text, profile, time.time() - start_time, False)
            return False
        finally:
            self.is_speaking = False
            
    async def _apply_voice_config(self, voice_config: Dict[str, Any]):
        """Apply temporary voice configuration"""
        if not self.tts_engine:
            return
            
        try:
            def apply_config():
                try:
                    if 'rate' in voice_config:
                        self.tts_engine.setProperty('rate', voice_config['rate'])
                        
                    if 'volume' in voice_config:
                        self.tts_engine.setProperty('volume', voice_config['volume'])
                        
                    if 'voice_id' in voice_config and voice_config['voice_id']:
                        voices = self.tts_engine.getProperty('voices')
                        if voices:
                            for voice in voices:
                                try:
                                    voice_id = getattr(voice, 'id', None) or ""
                                    voice_name = getattr(voice, 'name', None) or ""
                                    if voice_config['voice_id'] and (voice_config['voice_id'] in voice_id or voice_config['voice_id'] in voice_name):
                                        self.tts_engine.setProperty('voice', voice.id)
                                        break
                                except Exception:
                                    continue
                except Exception as e:
                    # Log specific error for debugging
                    self.logger.warning(f"Voice config application error: {e}")
                            
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, apply_config)
            
        except Exception as e:
            self.logger.warning(f"Failed to apply voice config: {e}")
            
    async def _synthesize_text(self, text: str, config: Dict[str, Any], 
                              cache_key: Optional[str] = None) -> bool:
        """Synthesize text using the configured engine with caching"""
        try:
            success = False
            
            if self.engine_type == 'pyttsx3' and self.tts_engine:
                success = await self._synthesize_with_pyttsx3(text, config)
            elif self.engine_type == 'gtts' and GTTS_AVAILABLE:
                success = await self._synthesize_with_gtts(text, config, cache_key)
            elif self.engine_type == 'edge_tts' and EDGE_TTS_AVAILABLE:
                success = await self._synthesize_with_edge_tts(text, config, cache_key)
            else:
                self.logger.error(f"No synthesis engine available for: {self.engine_type}")
                return False
                
            return success
                
        except Exception as e:
            self.logger.error(f"Text synthesis failed: {e}")
            return False
            
    async def _synthesize_with_pyttsx3(self, text: str, config: Dict[str, Any]) -> bool:
        """Synthesize speech using pyttsx3 with advanced configuration"""
        try:
            def speak_text():
                # Apply emotion/style modifications to text
                modified_text = self._apply_emotion_to_text(text, config.get('emotion', 'neutral'))
                
                import time
                self.logger.info(f"🗣️ Starting TTS: '{modified_text}'")
                start_time = time.time()
                
                # Create a completely fresh TTS engine instance to avoid resource conflicts
                import pyttsx3
                fresh_engine = pyttsx3.init()
                
                # Configure the fresh engine with same settings
                fresh_engine.setProperty('rate', config.get('rate', self.rate))
                fresh_engine.setProperty('volume', config.get('volume', self.volume))
                
                # Set voice if specified
                voices = fresh_engine.getProperty('voices')
                if voices and self.voice_id:
                    for voice in voices:
                        try:
                            voice_id = getattr(voice, 'id', None) or ""
                            voice_name = getattr(voice, 'name', None) or ""
                            if self.voice_id and (self.voice_id in voice_id or self.voice_id in voice_name):
                                fresh_engine.setProperty('voice', voice.id)
                                break
                        except Exception:
                            continue
                
                self.logger.info("🔄 TTS runAndWait() starting...")
                fresh_engine.say(modified_text)
                fresh_engine.runAndWait()
                
                # Properly cleanup the fresh engine
                try:
                    fresh_engine.stop()
                    del fresh_engine
                except Exception:
                    pass
                
                end_time = time.time()
                duration = end_time - start_time
                self.logger.info(f"✅ TTS completed in {duration:.2f} seconds")
                
                # Sanity check - if TTS completed too quickly, something went wrong
                if duration < 1.0 and len(modified_text) > 10:
                    self.logger.warning(f"⚠️ TTS completed suspiciously fast ({duration:.2f}s) for text length {len(modified_text)}")
                    return False
                
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
        
    async def _synthesize_with_gtts(self, text: str, config: Dict[str, Any], 
                                   cache_key: Optional[str] = None) -> bool:
        """Synthesize speech using Google Text-to-Speech"""
        try:
            import tempfile
            import pygame
            
            def create_gtts():
                tts = gtts.gTTS(
                    text=text,
                    lang=config.get('language', 'en'),
                    slow=config.get('rate', 200) < 150
                )
                
                # Save to temporary file or cache
                if cache_key and self.cache_enabled:
                    audio_file = self.cache_dir / f"{cache_key}.mp3"
                    tts.save(str(audio_file))
                    return str(audio_file)
                else:
                    temp_file = tempfile.NamedTemporaryFile(suffix='.mp3', delete=False)
                    tts.save(temp_file.name)
                    return temp_file.name
                    
            loop = asyncio.get_event_loop()
            audio_file = await loop.run_in_executor(None, create_gtts)
            
            # Play the audio file
            return await self._play_audio_file(audio_file)
            
        except Exception as e:
            self.logger.error(f"gTTS synthesis failed: {e}")
            return False
            
    async def _synthesize_with_edge_tts(self, text: str, config: Dict[str, Any], 
                                       cache_key: Optional[str] = None) -> bool:
        """Synthesize speech using Microsoft Edge TTS"""
        try:
            # Implementation would go here for Edge TTS
            # This is a placeholder for the advanced TTS engine
            self.logger.info("Edge TTS not fully implemented yet")
            return False
            
        except Exception as e:
            self.logger.error(f"Edge TTS synthesis failed: {e}")
            return False
    
    def get_available_voices(self) -> List[Dict[str, Any]]:
        """Get list of available voices across all engines"""
        voices = []
        
        # pyttsx3 voices
        if self.tts_engine and PYTTSX3_AVAILABLE:
            try:
                pyttsx3_voices = self.tts_engine.getProperty('voices')
                for voice in pyttsx3_voices:
                    voice_info = {
                        'engine': 'pyttsx3',
                        'id': voice.id,
                        'name': voice.name,
                        'languages': getattr(voice, 'languages', []),
                        'gender': getattr(voice, 'gender', 'unknown'),
                        'age': getattr(voice, 'age', 'unknown')
                    }
                    voices.append(voice_info)
            except Exception as e:
                self.logger.error(f"Error getting pyttsx3 voices: {e}")
                
        # Add gTTS languages
        if GTTS_AVAILABLE:
            gtts_languages = [
                {'engine': 'gtts', 'id': 'en', 'name': 'English', 'languages': ['en'], 'gender': 'female'},
                {'engine': 'gtts', 'id': 'es', 'name': 'Spanish', 'languages': ['es'], 'gender': 'female'},
                {'engine': 'gtts', 'id': 'fr', 'name': 'French', 'languages': ['fr'], 'gender': 'female'},
                {'engine': 'gtts', 'id': 'de', 'name': 'German', 'languages': ['de'], 'gender': 'female'},
            ]
            voices.extend(gtts_languages)
                
        return voices
            
    def get_status(self) -> Dict[str, Any]:
        """Get current synthesis status with enhanced information"""
        return {
            'initialized': self.is_initialized,
            'speaking': self.is_speaking,
            'engine': self.engine_type,
            'rate': self.rate,
            'volume': self.volume,
            'voice_id': self.voice_id,
            'pitch': self.pitch,
            'emotion': self.emotion,
            'speaking_style': self.speaking_style,
            'language': self.language,
            'cache_enabled': self.cache_enabled,
            'available_profiles': list(self.voice_profiles.keys()),
            'dependencies': {
                'pyttsx3': PYTTSX3_AVAILABLE,
                'gtts': GTTS_AVAILABLE,
                'edge_tts': EDGE_TTS_AVAILABLE
            },
            'statistics': self.stats.copy()
        }
        
    async def _get_effective_config(self, profile: str, voice_config: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Get effective voice configuration by merging profile and custom config"""
        effective_config = self.voice_profiles.get(profile, self.voice_profiles['default']).copy()
        
        # Merge with instance defaults
        effective_config.update({
            'rate': self.rate,
            'volume': self.volume,
            'voice_id': self.voice_id,
            'pitch': self.pitch,
            'emotion': self.emotion,
            'speaking_style': self.speaking_style,
            'language': self.language
        })
        
        # Apply custom configuration
        if voice_config:
            effective_config.update(voice_config)
            
        return effective_config
        
    def _generate_cache_key(self, text: str, config: Dict[str, Any]) -> str:
        """Generate cache key for TTS synthesis"""
        cache_data = {
            'text': text,
            'engine': self.engine_type,
            'rate': config.get('rate'),
            'volume': config.get('volume'),
            'voice_id': config.get('voice_id'),
            'language': config.get('language'),
            'emotion': config.get('emotion')
        }
        
        cache_string = json.dumps(cache_data, sort_keys=True)
        return hashlib.md5(cache_string.encode()).hexdigest()
        
    async def _get_cached_synthesis(self, cache_key: str) -> Optional[str]:
        """Get cached synthesis result if available and not expired"""
        try:
            cache_file = self.cache_dir / f"{cache_key}.mp3"
            if cache_file.exists():
                # Check if cache is still valid
                cache_age = time.time() - cache_file.stat().st_mtime
                if cache_age < self.cache_max_age:
                    return str(cache_file)
                else:
                    # Remove expired cache
                    cache_file.unlink()
            return None
            
        except Exception as e:
            self.logger.error(f"Error checking cache: {e}")
            return None
            
    async def _play_cached_audio(self, audio_file: str) -> bool:
        """Play cached audio file"""
        return await self._play_audio_file(audio_file)
        
    async def _play_audio_file(self, audio_file: str) -> bool:
        """Play audio file using available audio library"""
        try:
            # Try to use pygame for audio playback
            try:
                import pygame
                pygame.mixer.init()
                pygame.mixer.music.load(audio_file)
                pygame.mixer.music.play()
                
                # Wait for playback to finish
                while pygame.mixer.music.get_busy():
                    await asyncio.sleep(0.1)
                    
                return True
                
            except ImportError:
                # Fallback to system audio player
                import subprocess
                process = await asyncio.create_subprocess_exec(
                    'aplay' if audio_file.endswith('.wav') else 'mpg123',
                    audio_file,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL
                )
                await process.wait()
                return process.returncode == 0
                
        except Exception as e:
            self.logger.error(f"Error playing audio file: {e}")
            return False
            
    def _apply_emotion_to_text(self, text: str, emotion: str) -> str:
        """Apply emotional modifications to text for better synthesis"""
        if emotion == 'happy' or emotion == 'excited':
            # Add emphasis and exclamation
            text = text.replace('.', '!')
            text = f"*excited* {text}"
        elif emotion == 'sad':
            # Slower, more subdued
            text = f"*sadly* {text}"
        elif emotion == 'cheerful':
            text = f"*cheerfully* {text}"
        elif emotion == 'friendly':
            text = f"Hey! {text}"
            
        return text
        
    def _update_synthesis_stats(self, text: str, profile: str, duration: float, success: bool):
        """Update detailed synthesis statistics"""
        try:
            if success:
                self.stats['texts_synthesized'] += 1
                self.stats['total_characters'] += len(text)
                
                # Update average synthesis time
                total_time = self.stats['average_synthesis_time'] * (self.stats['texts_synthesized'] - 1)
                self.stats['average_synthesis_time'] = (total_time + duration) / self.stats['texts_synthesized']
                
                # Track profile usage
                if profile not in self.stats['voice_profiles_used']:
                    self.stats['voice_profiles_used'][profile] = 0
                self.stats['voice_profiles_used'][profile] += 1
                
                # Track language usage
                lang = self.language
                if lang not in self.stats['languages_used']:
                    self.stats['languages_used'][lang] = 0
                self.stats['languages_used'][lang] += 1
                
            else:
                self.stats['synthesis_failures'] += 1
                
            # Add to synthesis history (keep last 100)
            self.stats['synthesis_history'].append({
                'timestamp': time.time(),
                'text_length': len(text),
                'profile': profile,
                'duration': duration,
                'success': success
            })
            
            # Keep only last 100 entries
            if len(self.stats['synthesis_history']) > 100:
                self.stats['synthesis_history'] = self.stats['synthesis_history'][-100:]
                
        except Exception as e:
            self.logger.error(f"Error updating synthesis stats: {e}")

    async def set_voice_profile(self, profile_name: str, profile_config: Dict[str, Any]):
        """Set or update a voice profile"""
        self.voice_profiles[profile_name] = profile_config
        self.logger.info(f"Voice profile '{profile_name}' updated")
        
    async def get_voice_profiles(self) -> Dict[str, Dict[str, Any]]:
        """Get all available voice profiles"""
        return self.voice_profiles.copy()
        
    async def speak_with_emotion(self, text: str, emotion: str, intensity: float = 1.0) -> bool:
        """Speak text with specific emotion and intensity"""
        voice_config = {
            'emotion': emotion,
            'volume': min(1.0, self.volume * (1.0 + intensity * 0.2)),
            'rate': self.rate * (1.0 + intensity * 0.1) if emotion == 'excited' else self.rate
        }
        
        return await self.speak(text, voice_config, profile='default')
        
    async def speak_notification(self, text: str) -> bool:
        """Speak text using notification profile"""
        return await self.speak(text, profile='notification')
        
    async def speak_alert(self, text: str) -> bool:
        """Speak text using alert profile"""
        return await self.speak(text, profile='alert', priority='urgent')

    def get_statistics(self) -> Dict[str, Any]:
        """Get enhanced synthesis statistics"""
        stats = self.stats.copy()
        
        total_requests = stats['texts_synthesized'] + stats['synthesis_failures']
        if total_requests > 0:
            stats['success_rate'] = stats['texts_synthesized'] / total_requests
            stats['cache_hit_rate'] = stats['cache_hits'] / total_requests
        else:
            stats['success_rate'] = 0.0
            stats['cache_hit_rate'] = 0.0
            
        if stats['texts_synthesized'] > 0:
            stats['average_text_length'] = stats['total_characters'] / stats['texts_synthesized']
        else:
            stats['average_text_length'] = 0.0
            
        return stats