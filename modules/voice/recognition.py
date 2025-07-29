"""
Voice Recognition Engine - Speech-to-text processing for SAGE
"""

import asyncio
import logging
import threading
import time
from typing import Dict, Any, Optional, Callable, List
from pathlib import Path
import json

# Try to import speech recognition libraries
try:
    import speech_recognition as sr
    SPEECH_RECOGNITION_AVAILABLE = True
except ImportError:
    sr = None
    SPEECH_RECOGNITION_AVAILABLE = False

try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    whisper = None
    WHISPER_AVAILABLE = False

try:
    import pyaudio
    PYAUDIO_AVAILABLE = True
except ImportError:
    pyaudio = None
    PYAUDIO_AVAILABLE = False


class VoiceRecognition:
    """Speech recognition engine supporting multiple backends"""
    
    def __init__(self, config: Dict[str, Any], cache_manager=None, logger=None):
        self.config = config
        self.cache = cache_manager
        self.logger = logger or logging.getLogger(__name__)
        
        # Configuration
        self.engine_type = config.get('engine', 'whisper')  # whisper, google, vosk
        self.model_name = config.get('model', 'tiny')
        self.language = config.get('language', 'en')
        self.energy_threshold = config.get('energy_threshold', 300)
        self.pause_threshold = config.get('pause_threshold', 0.8)
        self.timeout = config.get('timeout', 5)
        self.phrase_timeout = config.get('phrase_timeout', 0.3)
        
        # State
        self.is_initialized = False
        self.is_listening = False
        self.recognition_active = False
        
        # Components
        self.recognizer = None
        self.microphone = None
        self.whisper_model = None
        self.audio_queue = asyncio.Queue()
        self.recognition_thread = None
        self.stop_listening_func = None
        
        # Callbacks
        self.on_speech_detected: Optional[Callable] = None
        self.on_text_recognized: Optional[Callable] = None
        self.on_error: Optional[Callable] = None
        
        # Statistics
        self.stats = {
            'recognitions_attempted': 0,
            'recognitions_successful': 0,
            'recognitions_failed': 0,
            'total_audio_duration': 0.0,
            'average_confidence': 0.0,
            'engine_used': self.engine_type
        }
        
    async def initialize(self) -> bool:
        """Initialize the voice recognition system"""
        try:
            self.logger.info(f"Initializing voice recognition with engine: {self.engine_type}")
            
            # Check dependencies
            if not self._check_dependencies():
                return False
                
            # Initialize speech recognition
            if SPEECH_RECOGNITION_AVAILABLE:
                self.recognizer = sr.Recognizer()
                self.recognizer.energy_threshold = self.energy_threshold
                self.recognizer.pause_threshold = self.pause_threshold
                self.recognizer.phrase_threshold = self.phrase_timeout
                
            # Initialize microphone
            if PYAUDIO_AVAILABLE and SPEECH_RECOGNITION_AVAILABLE:
                try:
                    self.microphone = sr.Microphone()
                    # Calibrate for ambient noise
                    with self.microphone as source:
                        self.logger.info("Calibrating microphone for ambient noise...")
                        self.recognizer.adjust_for_ambient_noise(source, duration=1)
                    self.logger.info(f"Microphone calibrated. Energy threshold: {self.recognizer.energy_threshold}")
                except Exception as e:
                    self.logger.warning(f"Microphone initialization failed: {e}")
                    self.microphone = None
                    
            # Initialize Whisper model if needed
            if self.engine_type == 'whisper' and WHISPER_AVAILABLE:
                await self._load_whisper_model()
                
            self.is_initialized = True
            self.logger.info("Voice recognition initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize voice recognition: {e}")
            return False
            
    def _check_dependencies(self) -> bool:
        """Check if required dependencies are available"""
        missing_deps = []
        
        if not SPEECH_RECOGNITION_AVAILABLE:
            missing_deps.append("speech_recognition")
            
        if self.engine_type == 'whisper' and not WHISPER_AVAILABLE:
            missing_deps.append("openai-whisper")
            
        if not PYAUDIO_AVAILABLE:
            missing_deps.append("pyaudio")
            
        if missing_deps:
            self.logger.error(f"Missing dependencies: {missing_deps}")
            self.logger.error("Install with: pip install " + " ".join(missing_deps))
            return False
            
        return True
        
    async def _load_whisper_model(self):
        """Load Whisper model"""
        try:
            self.logger.info(f"Loading Whisper model: {self.model_name}")
            
            # Check cache first
            cache_key = f"whisper_model_{self.model_name}"
            if self.cache:
                cached_model = self.cache.get("voice", cache_key)
                if cached_model:
                    self.whisper_model = cached_model
                    self.logger.info("Loaded Whisper model from cache")
                    return
                    
            # Load model in thread to avoid blocking
            def load_model():
                return whisper.load_model(self.model_name)
                
            loop = asyncio.get_event_loop()
            self.whisper_model = await loop.run_in_executor(None, load_model)
            
            # Cache the model
            if self.cache:
                self.cache.set("voice", cache_key, self.whisper_model, ttl=3600)
                
            self.logger.info(f"Whisper model {self.model_name} loaded successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to load Whisper model: {e}")
            raise
            
    async def start_listening(self) -> bool:
        """Start continuous listening for speech"""
        if not self.is_initialized:
            self.logger.error("Voice recognition not initialized")
            return False
            
        if self.is_listening:
            self.logger.warning("Already listening")
            return True
            
        try:
            if not self.microphone or not self.recognizer:
                self.logger.error("Microphone or recognizer not available")
                return False
                
            self.logger.info("Starting voice recognition...")
            self.is_listening = True
            self.recognition_active = True
            
            # Start background listening
            self.stop_listening_func = self.recognizer.listen_in_background(
                self.microphone, 
                self._audio_callback,
                phrase_time_limit=self.timeout
            )
            
            self.logger.info("Voice recognition started - listening for speech")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start listening: {e}")
            self.is_listening = False
            return False
            
    def _audio_callback(self, recognizer, audio):
        """Handle audio data from microphone"""
        if not self.recognition_active:
            return
            
        try:
            # Put audio in queue for processing
            asyncio.create_task(self._process_audio(audio))
            
        except Exception as e:
            self.logger.error(f"Error in audio callback: {e}")
            
    async def _process_audio(self, audio):
        """Process audio data and perform recognition"""
        try:
            self.stats['recognitions_attempted'] += 1
            
            # Call speech detected callback
            if self.on_speech_detected:
                await self._safe_callback(self.on_speech_detected, audio)
                
            # Perform recognition based on engine
            text, confidence = await self._recognize_audio(audio)
            
            if text:
                self.stats['recognitions_successful'] += 1
                self.stats['average_confidence'] = (
                    (self.stats['average_confidence'] * (self.stats['recognitions_successful'] - 1) + confidence) 
                    / self.stats['recognitions_successful']
                )
                
                self.logger.info(f"Recognized: '{text}' (confidence: {confidence:.2f})")
                
                # Call text recognized callback
                if self.on_text_recognized:
                    await self._safe_callback(self.on_text_recognized, text, confidence)
                    
            else:
                self.stats['recognitions_failed'] += 1
                
        except Exception as e:
            self.logger.error(f"Error processing audio: {e}")
            self.stats['recognitions_failed'] += 1
            
            if self.on_error:
                await self._safe_callback(self.on_error, str(e))
                
    async def _recognize_audio(self, audio) -> tuple[Optional[str], float]:
        """Recognize text from audio using configured engine"""
        try:
            if self.engine_type == 'whisper' and self.whisper_model:
                return await self._recognize_with_whisper(audio)
            elif self.engine_type == 'google':
                return await self._recognize_with_google(audio)
            else:
                # Fallback to Google
                return await self._recognize_with_google(audio)
                
        except Exception as e:
            self.logger.error(f"Recognition failed: {e}")
            return None, 0.0
            
    async def _recognize_with_whisper(self, audio) -> tuple[Optional[str], float]:
        """Recognize speech using Whisper"""
        try:
            # Convert audio to format Whisper expects
            def transcribe():
                # Get raw audio data
                audio_data = audio.get_raw_data(convert_rate=16000, convert_width=2)
                
                # Convert to numpy array (Whisper expects this)
                import numpy as np
                audio_np = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
                
                # Transcribe
                result = self.whisper_model.transcribe(audio_np, language=self.language)
                return result['text'].strip(), 0.8  # Whisper doesn't provide confidence
                
            loop = asyncio.get_event_loop()
            text, confidence = await loop.run_in_executor(None, transcribe)
            
            return text if text else None, confidence
            
        except Exception as e:
            self.logger.error(f"Whisper recognition failed: {e}")
            return None, 0.0
            
    async def _recognize_with_google(self, audio) -> tuple[Optional[str], float]:
        """Recognize speech using Google Speech Recognition"""
        try:
            def recognize():
                return self.recognizer.recognize_google(audio, language=self.language), 0.9
                
            loop = asyncio.get_event_loop()
            text, confidence = await loop.run_in_executor(None, recognize)
            
            return text.strip(), confidence
            
        except sr.UnknownValueError:
            self.logger.debug("Could not understand audio")
            return None, 0.0
        except sr.RequestError as e:
            self.logger.error(f"Google recognition service error: {e}")
            return None, 0.0
        except Exception as e:
            self.logger.error(f"Google recognition failed: {e}")
            return None, 0.0
            
    async def _safe_callback(self, callback, *args):
        """Safely execute callback function"""
        try:
            if asyncio.iscoroutinefunction(callback):
                await callback(*args)
            else:
                callback(*args)
        except Exception as e:
            self.logger.error(f"Error in callback: {e}")
            
    async def stop_listening(self) -> bool:
        """Stop voice recognition"""
        try:
            if not self.is_listening:
                return True
                
            self.logger.info("Stopping voice recognition...")
            self.recognition_active = False
            
            if self.stop_listening_func:
                self.stop_listening_func(wait_for_stop=False)
                self.stop_listening_func = None
                
            self.is_listening = False
            self.logger.info("Voice recognition stopped")
            return True
            
        except Exception as e:
            self.logger.error(f"Error stopping voice recognition: {e}")
            return False
            
    async def shutdown(self):
        """Shutdown voice recognition"""
        await self.stop_listening()
        self.is_initialized = False
        self.logger.info("Voice recognition shutdown complete")
        
    def set_callbacks(self, 
                     on_speech_detected: Optional[Callable] = None,
                     on_text_recognized: Optional[Callable] = None,
                     on_error: Optional[Callable] = None):
        """Set callback functions for recognition events"""
        self.on_speech_detected = on_speech_detected
        self.on_text_recognized = on_text_recognized
        self.on_error = on_error
        
    async def recognize_once(self, timeout: Optional[float] = None) -> Optional[str]:
        """Recognize speech from a single audio capture"""
        if not self.is_initialized or not self.microphone or not self.recognizer:
            return None
            
        try:
            self.logger.info("Listening for single speech input...")
            
            def listen_and_recognize():
                with self.microphone as source:
                    audio = self.recognizer.listen(source, timeout=timeout or self.timeout)
                return audio
                
            loop = asyncio.get_event_loop()
            audio = await loop.run_in_executor(None, listen_and_recognize)
            
            text, confidence = await self._recognize_audio(audio)
            
            if text:
                self.logger.info(f"Single recognition result: '{text}' (confidence: {confidence:.2f})")
            
            return text
            
        except Exception as e:
            self.logger.error(f"Single recognition failed: {e}")
            return None
            
    def get_status(self) -> Dict[str, Any]:
        """Get current recognition status"""
        return {
            'initialized': self.is_initialized,
            'listening': self.is_listening,
            'engine': self.engine_type,
            'model': self.model_name,
            'language': self.language,
            'microphone_available': self.microphone is not None,
            'whisper_model_loaded': self.whisper_model is not None,
            'dependencies': {
                'speech_recognition': SPEECH_RECOGNITION_AVAILABLE,
                'whisper': WHISPER_AVAILABLE,
                'pyaudio': PYAUDIO_AVAILABLE
            },
            'statistics': self.stats.copy()
        }
        
    def get_statistics(self) -> Dict[str, Any]:
        """Get recognition statistics"""
        stats = self.stats.copy()
        
        if stats['recognitions_attempted'] > 0:
            stats['success_rate'] = stats['recognitions_successful'] / stats['recognitions_attempted']
        else:
            stats['success_rate'] = 0.0
            
        return stats