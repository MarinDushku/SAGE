"""
Enhanced Voice Recognition - Fixed threading and async issues with comprehensive debugging
"""

import asyncio
import logging
import threading
import time
import queue
from typing import Dict, Any, Optional, Callable, List
from pathlib import Path
import json
from concurrent.futures import ThreadPoolExecutor

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


class EnhancedVoiceRecognition:
    """Enhanced voice recognition with proper async/threading and comprehensive debugging"""
    
    def __init__(self, config: Dict[str, Any], cache_manager=None, logger=None):
        self.config = config
        self.cache = cache_manager
        self.logger = logger or logging.getLogger(__name__)
        
        # Configuration
        self.engine_type = config.get('engine', 'whisper')
        self.model_name = config.get('model', 'tiny')
        self.language = config.get('language', 'en')
        self.energy_threshold = config.get('energy_threshold', 300)
        self.pause_threshold = config.get('pause_threshold', 0.8)
        self.timeout = config.get('timeout', 5)
        self.phrase_timeout = config.get('phrase_timeout', 0.3)
        
        # Enhanced debugging
        self.debug_mode = config.get('debug_mode', True)
        self.audio_monitoring = config.get('audio_monitoring', True)
        
        # State
        self.is_initialized = False
        self.is_listening = False
        self.recognition_active = False
        
        # Components
        self.recognizer = None
        self.microphone = None
        self.whisper_model = None
        
        # Enhanced async handling
        self.audio_queue = asyncio.Queue(maxsize=10)
        self.text_queue = asyncio.Queue(maxsize=20)  # Queue for recognized text
        self.event_loop = None
        self.executor = ThreadPoolExecutor(max_workers=2)
        
        # Threading
        self.background_thread = None
        self.stop_event = threading.Event()
        
        # Callbacks
        self.on_speech_detected: Optional[Callable] = None
        self.on_text_recognized: Optional[Callable] = None
        self.on_error: Optional[Callable] = None
        self.on_audio_level: Optional[Callable] = None
        
        # Enhanced statistics and debugging
        self.stats = {
            'recognitions_attempted': 0,
            'recognitions_successful': 0,
            'recognitions_failed': 0,
            'average_response_time': 0.0,
            'audio_callbacks_received': 0,
            'audio_level_samples': 0,
            'last_audio_level': 0,
            'microphone_working': False,
            'engine_used': self.engine_type,
            'initialization_time': 0,
            'calibration_successful': False
        }
        
        # Audio monitoring
        self.audio_levels = []
        self.silence_counter = 0
        
        self.log("Enhanced Voice Recognition initialized", "info")
    
    def log(self, message: str, level: str = "info"):
        """Enhanced logging with voice module prefix"""
        if self.logger:
            getattr(self.logger, level)(f"[VOICE] {message}")
        else:
            print(f"[VOICE-{level.upper()}] {message}")
    
    async def initialize(self) -> bool:
        """Initialize the enhanced voice recognition system"""
        try:
            start_time = time.time()
            self.log("Starting enhanced voice recognition initialization...")
            
            # Store event loop for proper async handling
            self.event_loop = asyncio.get_event_loop()
            
            # Check dependencies
            if not self._check_dependencies():
                return False
            
            # Initialize speech recognition with enhanced error handling
            if SPEECH_RECOGNITION_AVAILABLE:
                self.recognizer = sr.Recognizer()
                self.recognizer.energy_threshold = self.energy_threshold
                self.recognizer.pause_threshold = self.pause_threshold
                self.recognizer.phrase_threshold = self.phrase_timeout
                self.log(f"Speech recognizer initialized with energy threshold: {self.energy_threshold}")
            else:
                self.log("Speech recognition not available", "error")
                return False
            
            # Initialize microphone with comprehensive testing
            if PYAUDIO_AVAILABLE and SPEECH_RECOGNITION_AVAILABLE:
                await self._initialize_microphone()
            else:
                self.log("PyAudio not available - voice input disabled", "error")
                return False
            
            # Initialize Whisper model if needed
            if self.engine_type == 'whisper' and WHISPER_AVAILABLE:
                await self._load_whisper_model()
            
            self.is_initialized = True
            self.stats['initialization_time'] = time.time() - start_time
            self.log(f"Voice recognition initialized successfully in {self.stats['initialization_time']:.2f}s")
            
            return True
            
        except Exception as e:
            self.log(f"Failed to initialize voice recognition: {e}", "error")
            return False
    
    async def _initialize_microphone(self):
        """Initialize microphone with comprehensive testing and calibration"""
        try:
            self.log("Testing microphone availability...")
            
            # Test microphone access
            try:
                test_mic = sr.Microphone()
                with test_mic as source:
                    # Very brief test
                    pass
                self.log("Microphone access test successful")
            except Exception as e:
                self.log(f"Microphone access failed: {e}", "error")
                raise
            
            # Initialize main microphone
            self.microphone = sr.Microphone()
            
            # Enhanced calibration with monitoring
            self.log("Starting microphone calibration...")
            with self.microphone as source:
                self.log("Listening to ambient noise for calibration...")
                
                # Get initial reading
                initial_energy = self.recognizer.energy_threshold
                
                # Calibrate for ambient noise
                self.recognizer.adjust_for_ambient_noise(source, duration=2)
                
                # Get post-calibration reading
                final_energy = self.recognizer.energy_threshold
                
                self.log(f"Calibration complete:")
                self.log(f"  Initial energy threshold: {initial_energy}")
                self.log(f"  Final energy threshold: {final_energy}")
                self.log(f"  Adjustment: {final_energy - initial_energy:+.0f}")
                
                self.stats['calibration_successful'] = True
                self.stats['microphone_working'] = True
                
        except Exception as e:
            self.log(f"Microphone initialization failed: {e}", "error")
            self.stats['microphone_working'] = False
            raise
    
    async def _load_whisper_model(self):
        """Load Whisper model in executor to avoid blocking"""
        try:
            self.log(f"Loading Whisper model: {self.model_name}")
            
            def load_model():
                return whisper.load_model(self.model_name)
            
            # Load in executor to avoid blocking
            self.whisper_model = await self.event_loop.run_in_executor(
                self.executor, load_model
            )
            
            self.log(f"Whisper model {self.model_name} loaded successfully")
            
        except Exception as e:
            self.log(f"Failed to load Whisper model: {e}", "error")
            raise
    
    def _check_dependencies(self) -> bool:
        """Check if required dependencies are available with detailed reporting"""
        missing_deps = []
        
        self.log("Checking voice recognition dependencies...")
        
        if not SPEECH_RECOGNITION_AVAILABLE:
            missing_deps.append("speech_recognition")
            self.log("❌ speech_recognition not available", "error")
        else:
            self.log("✅ speech_recognition available")
            
        if not PYAUDIO_AVAILABLE:
            missing_deps.append("pyaudio")
            self.log("❌ pyaudio not available", "error")
        else:
            self.log("✅ pyaudio available")
            
        if self.engine_type == 'whisper' and not WHISPER_AVAILABLE:
            missing_deps.append("openai-whisper")
            self.log("❌ openai-whisper not available", "error")
        else:
            self.log("✅ whisper available" if WHISPER_AVAILABLE else "ℹ️ whisper not needed")
        
        if missing_deps:
            self.log(f"Missing dependencies: {missing_deps}", "error")
            self.log("Install with: pip install " + " ".join(missing_deps), "error")
            return False
        
        self.log("All dependencies available", "info")
        return True
    
    async def start_listening(self) -> bool:
        """Start enhanced continuous listening with proper async handling"""
        if not self.is_initialized:
            self.log("Voice recognition not initialized", "error")
            return False
        
        if self.is_listening:
            self.log("Already listening", "warning")
            return True
        
        try:
            if not self.microphone or not self.recognizer:
                self.log("Microphone or recognizer not available", "error")
                return False
            
            self.log("Starting enhanced voice recognition...")
            self.is_listening = True
            self.recognition_active = True
            self.stop_event.clear()
            
            # Start background listening thread with enhanced callback
            self.background_thread = threading.Thread(
                target=self._background_listening_thread,
                daemon=True
            )
            self.background_thread.start()
            
            # Start audio processing task
            asyncio.create_task(self._process_audio_queue())
            
            self.log("Enhanced voice recognition started - listening for speech")
            return True
            
        except Exception as e:
            self.log(f"Failed to start listening: {e}", "error")
            self.is_listening = False
            return False
    
    def _background_listening_thread(self):
        """Background thread for continuous listening with enhanced error handling"""
        self.log("Background listening thread started")
        
        try:
            while not self.stop_event.is_set() and self.recognition_active:
                try:
                    with self.microphone as source:
                        # Listen with timeout
                        self.log("Listening for audio...", "debug" if not self.debug_mode else "info")
                        
                        audio = self.recognizer.listen(
                            source, 
                            timeout=1,  # Short timeout to check stop event frequently
                            phrase_time_limit=self.timeout
                        )
                        
                        self.stats['audio_callbacks_received'] += 1
                        
                        # Calculate audio level for monitoring
                        if self.audio_monitoring:
                            audio_level = self._calculate_audio_level(audio)
                            self.stats['last_audio_level'] = audio_level
                            self.stats['audio_level_samples'] += 1
                            
                            if self.on_audio_level:
                                try:
                                    self.on_audio_level(audio_level)
                                except Exception as e:
                                    self.log(f"Error in audio level callback: {e}", "warning")
                        
                        self.log(f"Audio captured, level: {self.stats['last_audio_level']:.1f}")
                        
                        # Put audio in queue for async processing
                        try:
                            if self.event_loop and not self.event_loop.is_closed():
                                # Use call_soon_threadsafe for more reliable cross-thread communication
                                def queue_audio():
                                    if not self.audio_queue.full():
                                        try:
                                            self.audio_queue.put_nowait(audio)
                                            self.log("Audio queued for processing", "debug")
                                        except asyncio.QueueFull:
                                            self.log("Audio queue full, dropping audio", "warning")
                                
                                self.event_loop.call_soon_threadsafe(queue_audio)
                            else:
                                self.log("Event loop not available for audio processing", "warning")
                        except Exception as e:
                            self.log(f"Failed to queue audio for processing: {e}", "error")
                        
                except sr.WaitTimeoutError:
                    # Timeout is normal - continue listening
                    self.silence_counter += 1
                    if self.silence_counter % 10 == 0:  # Log every 10 seconds of silence
                        self.log(f"Listening... ({self.silence_counter}s of silence)")
                    continue
                    
                except Exception as e:
                    self.log(f"Error in listening loop: {e}", "error")
                    time.sleep(1)  # Brief pause before retrying
                    
        except Exception as e:
            self.log(f"Background listening thread error: {e}", "error")
        finally:
            self.log("Background listening thread stopped")
    
    def _calculate_audio_level(self, audio) -> float:
        """Calculate audio level for monitoring"""
        try:
            import numpy as np
            audio_data = np.frombuffer(audio.get_raw_data(), dtype=np.int16)
            rms = np.sqrt(np.mean(audio_data**2))
            return float(rms)
        except Exception:
            return 0.0
    
    async def _process_audio_queue(self):
        """Process audio from the queue asynchronously"""
        self.log("Audio processing task started")
        
        try:
            while self.recognition_active:
                try:
                    # Wait for audio with timeout
                    audio = await asyncio.wait_for(self.audio_queue.get(), timeout=1.0)
                    self.log("Audio retrieved from queue for processing")
                    await self._process_single_audio(audio)
                    
                except asyncio.TimeoutError:
                    # Timeout is normal - continue processing
                    continue
                except Exception as e:
                    self.log(f"Error processing audio queue: {e}", "error")
                    
        except Exception as e:
            self.log(f"Audio processing task error: {e}", "error")
        finally:
            self.log("Audio processing task stopped")
    
    async def _process_single_audio(self, audio):
        """Process a single audio sample"""
        try:
            start_time = time.time()
            self.stats['recognitions_attempted'] += 1
            
            self.log("Processing audio sample...")
            
            # Call speech detected callback
            if self.on_speech_detected:
                try:
                    await self._safe_callback(self.on_speech_detected, audio)
                except Exception as e:
                    self.log(f"Error in speech detected callback: {e}", "warning")
            
            # Perform recognition
            text, confidence = await self._recognize_audio(audio)
            
            processing_time = time.time() - start_time
            
            if text and text.strip():
                self.stats['recognitions_successful'] += 1
                self._update_average_response_time(processing_time)
                
                self.log(f"✅ Recognition successful: '{text}' (confidence: {confidence:.2f}, time: {processing_time:.2f}s)")
                
                # Add to text queue for main app to retrieve
                try:
                    result = {
                        'text': text,
                        'confidence': confidence,
                        'timestamp': time.time(),
                        'processing_time': processing_time
                    }
                    self.text_queue.put_nowait(result)
                except asyncio.QueueFull:
                    self.log("Text queue full, dropping oldest result", "warning")
                    try:
                        self.text_queue.get_nowait()  # Remove oldest
                        self.text_queue.put_nowait(result)  # Add new
                    except asyncio.QueueEmpty:
                        pass
                
                # Call text recognized callback
                if self.on_text_recognized:
                    try:
                        await self._safe_callback(self.on_text_recognized, text, confidence)
                    except Exception as e:
                        self.log(f"Error in text recognized callback: {e}", "error")
            else:
                self.stats['recognitions_failed'] += 1
                self.log(f"❌ Recognition failed - no text extracted (time: {processing_time:.2f}s)")
                
        except Exception as e:
            self.log(f"Error processing audio: {e}", "error")
            self.stats['recognitions_failed'] += 1
            
            if self.on_error:
                try:
                    await self._safe_callback(self.on_error, str(e))
                except Exception as callback_error:
                    self.log(f"Error in error callback: {callback_error}", "error")
    
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
            self.log(f"Recognition failed: {e}", "error")
            return None, 0.0
    
    async def _recognize_with_whisper(self, audio) -> tuple[Optional[str], float]:
        """Recognize speech using Whisper in executor"""
        try:
            def transcribe():
                # Convert audio to format Whisper expects
                audio_data = audio.get_raw_data(convert_rate=16000, convert_width=2)
                
                # Convert to numpy array
                import numpy as np
                audio_np = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
                
                # Transcribe
                result = self.whisper_model.transcribe(audio_np, language=self.language)
                return result['text'].strip(), 0.8
            
            # Run in executor to avoid blocking
            text, confidence = await self.event_loop.run_in_executor(
                self.executor, transcribe
            )
            
            return text if text else None, confidence
            
        except Exception as e:
            self.log(f"Whisper recognition failed: {e}", "error")
            return None, 0.0
    
    async def _recognize_with_google(self, audio) -> tuple[Optional[str], float]:
        """Recognize speech using Google Speech Recognition in executor"""
        try:
            def recognize():
                return self.recognizer.recognize_google(audio, language=self.language), 0.9
            
            # Run in executor to avoid blocking
            text, confidence = await self.event_loop.run_in_executor(
                self.executor, recognize
            )
            
            return text.strip(), confidence
            
        except sr.UnknownValueError:
            self.log("Could not understand audio", "debug")
            return None, 0.0
        except sr.RequestError as e:
            self.log(f"Google recognition service error: {e}", "error")
            return None, 0.0
        except Exception as e:
            self.log(f"Google recognition failed: {e}", "error")
            return None, 0.0
    
    async def _safe_callback(self, callback, *args):
        """Safely execute callback function"""
        try:
            if asyncio.iscoroutinefunction(callback):
                await callback(*args)
            else:
                callback(*args)
        except Exception as e:
            self.log(f"Error in callback: {e}", "error")
    
    def _update_average_response_time(self, response_time: float):
        """Update average response time statistics"""
        successful = self.stats['recognitions_successful']
        current_avg = self.stats['average_response_time']
        
        self.stats['average_response_time'] = (
            (current_avg * (successful - 1) + response_time) / successful
        )
    
    async def stop_listening(self) -> bool:
        """Stop voice recognition"""
        try:
            if not self.is_listening:
                return True
            
            self.log("Stopping voice recognition...")
            self.recognition_active = False
            self.stop_event.set()
            
            # Wait for background thread to stop
            if self.background_thread and self.background_thread.is_alive():
                self.background_thread.join(timeout=2)
                if self.background_thread.is_alive():
                    self.log("Background thread did not stop gracefully", "warning")
            
            self.is_listening = False
            self.log("Voice recognition stopped")
            return True
            
        except Exception as e:
            self.log(f"Error stopping voice recognition: {e}", "error")
            return False
    
    async def shutdown(self):
        """Shutdown voice recognition"""
        await self.stop_listening()
        
        # Shutdown executor
        if self.executor:
            self.executor.shutdown(wait=True)
        
        self.is_initialized = False
        self.log("Voice recognition shutdown complete")
    
    def set_callbacks(self, 
                     on_speech_detected: Optional[Callable] = None,
                     on_text_recognized: Optional[Callable] = None,
                     on_error: Optional[Callable] = None,
                     on_audio_level: Optional[Callable] = None):
        """Set callback functions for recognition events"""
        self.on_speech_detected = on_speech_detected
        self.on_text_recognized = on_text_recognized
        self.on_error = on_error
        self.on_audio_level = on_audio_level
    
    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive recognition status"""
        return {
            'initialized': self.is_initialized,
            'listening': self.is_listening,
            'recognition_active': self.recognition_active,
            'engine': self.engine_type,
            'model': self.model_name,
            'language': self.language,
            'microphone_working': self.stats['microphone_working'],
            'calibration_successful': self.stats['calibration_successful'],
            'whisper_model_loaded': self.whisper_model is not None,
            'dependencies': {
                'speech_recognition': SPEECH_RECOGNITION_AVAILABLE,
                'whisper': WHISPER_AVAILABLE,
                'pyaudio': PYAUDIO_AVAILABLE
            },
            'statistics': self.stats.copy(),
            'config': {
                'energy_threshold': self.energy_threshold,
                'pause_threshold': self.pause_threshold,
                'timeout': self.timeout,
                'debug_mode': self.debug_mode,
                'audio_monitoring': self.audio_monitoring
            }
        }
    
    def get_debug_info(self) -> Dict[str, Any]:
        """Get detailed debug information"""
        return {
            'audio_queue_size': self.audio_queue.qsize() if hasattr(self.audio_queue, 'qsize') else 0,
            'text_queue_size': self.text_queue.qsize() if hasattr(self.text_queue, 'qsize') else 0,
            'background_thread_alive': self.background_thread.is_alive() if self.background_thread else False,
            'stop_event_set': self.stop_event.is_set(),
            'event_loop_running': self.event_loop and not self.event_loop.is_closed(),
            'executor_shutdown': self.executor._shutdown if self.executor else True,
            'recent_audio_levels': self.audio_levels[-10:] if self.audio_levels else [],
            'silence_counter': self.silence_counter
        }
    
    async def get_recognized_text(self) -> Optional[Dict[str, Any]]:
        """Get the next recognized text from the queue (non-blocking)"""
        try:
            return self.text_queue.get_nowait()
        except asyncio.QueueEmpty:
            return None
        except Exception as e:
            self.log(f"Error getting recognized text: {e}", "error")
            return None