"""
Wake Word Detector - Always-listening wake word detection for SAGE
"""

import asyncio
import logging
import threading
import time
import struct
import numpy as np
from typing import Dict, Any, Optional, Callable, List, Tuple
from pathlib import Path

# Try to import wake word libraries
try:
    import pvporcupine
    PORCUPINE_AVAILABLE = True
except ImportError:
    pvporcupine = None
    PORCUPINE_AVAILABLE = False

# Try to import audio libraries
try:
    import pyaudio
    PYAUDIO_AVAILABLE = True
except ImportError:
    pyaudio = None
    PYAUDIO_AVAILABLE = False

# Try to import alternative detection libraries
try:
    import speech_recognition as sr
    SPEECH_RECOGNITION_AVAILABLE = True
except ImportError:
    sr = None
    SPEECH_RECOGNITION_AVAILABLE = False


class WakeWordDetector:
    """Wake word detection system"""
    
    def __init__(self, config: Dict[str, Any], logger=None):
        self.config = config
        self.logger = logger or logging.getLogger(__name__)
        
        # Configuration
        self.enabled = config.get('enabled', True)
        self.keywords = config.get('keywords', ['sage'])  # Support multiple keywords
        self.primary_keyword = config.get('keyword', 'sage')  # Backward compatibility
        self.keyword = self.primary_keyword  # Backward compatibility
        self.sensitivity = config.get('sensitivity', 0.5)
        
        # Advanced configuration
        self.detection_threshold = config.get('detection_threshold', 0.7)
        self.min_detection_interval = config.get('min_detection_interval', 2.0)  # seconds
        self.auto_sensitivity_adjustment = config.get('auto_sensitivity_adjustment', True)
        self.background_noise_suppression = config.get('background_noise_suppression', True)
        
        # Audio configuration
        self.sample_rate = config.get('sample_rate', 16000)
        self.frame_length = config.get('frame_length', 512)
        self.audio_device_index = config.get('audio_device_index', None)
        
        # Custom wake word models
        self.custom_model_path = config.get('custom_model_path', None)
        self.model_sensitivity_map = config.get('model_sensitivity_map', {})
        
        # State
        self.is_initialized = False
        self.is_detecting = False
        self.last_detection_time = 0
        self.detection_thread = None
        
        # Components
        self.porcupine = None
        self.audio_stream = None
        self.pa = None
        
        # Callbacks
        self.on_wake_word_detected: Optional[Callable] = None
        self.on_false_positive: Optional[Callable] = None
        self.on_sensitivity_adjusted: Optional[Callable] = None
        
        # Enhanced statistics
        self.stats = {
            'total_detections': 0,
            'confirmed_detections': 0,
            'false_positives': 0,
            'sensitivity_adjustments': 0,
            'average_detection_confidence': 0.0,
            'detection_history': [],  # Last 50 detections
            'keyword_usage': {kw: 0 for kw in self.keywords},
            'detection_times': [],  # For pattern analysis
            'background_noise_level': 0.0,
            'current_sensitivity': self.sensitivity
        }
        
        # Background noise monitoring
        self.noise_samples = []
        self.noise_sample_size = 100
        self.adaptive_threshold = self.detection_threshold
        
    async def initialize(self) -> bool:
        """Initialize enhanced wake word detection system"""
        try:
            if not self.enabled:
                self.logger.info("Wake word detection disabled")
                self.is_initialized = True
                return True
                
            self.logger.info(f"Initializing wake word detection for keywords: {self.keywords}")
            
            # Check dependencies
            if not self._check_dependencies():
                return False
                
            # Initialize Porcupine engine
            if PORCUPINE_AVAILABLE:
                success = await self._initialize_porcupine()
                if not success:
                    return False
            else:
                self.logger.warning("Porcupine not available, using fallback detection")
                
            # Initialize audio stream
            if PYAUDIO_AVAILABLE:
                success = await self._initialize_audio_stream()
                if not success:
                    return False
                    
            self.is_initialized = True
            self.logger.info("Enhanced wake word detection initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize wake word detection: {e}")
            return False
            
    async def start_detection(self) -> bool:
        """Start enhanced wake word detection"""
        if not self.is_initialized or not self.enabled:
            return False
            
        try:
            if self.is_detecting:
                self.logger.warning("Wake word detection already running")
                return True
                
            self.is_detecting = True
            
            # Start detection thread
            self.detection_thread = threading.Thread(
                target=self._detection_loop,
                daemon=True
            )
            self.detection_thread.start()
            
            self.logger.info(f"Started enhanced wake word detection for: {self.keywords}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start wake word detection: {e}")
            self.is_detecting = False
            return False
            
    async def stop_detection(self) -> bool:
        """Stop wake word detection"""
        try:
            self.is_detecting = False
            self.logger.info("Wake word detection stopped")
            return True
            
        except Exception as e:
            self.logger.error(f"Error stopping wake word detection: {e}")
            return False
            
    async def shutdown(self):
        """Shutdown wake word detection"""
        await self.stop_detection()
        self.is_initialized = False
        self.logger.info("Wake word detection shutdown complete")
        
    def set_callbacks(self, on_detected: Callable = None, 
                     on_false_positive: Callable = None,
                     on_sensitivity_adjusted: Callable = None):
        """Set multiple callbacks for wake word events"""
        if on_detected:
            self.on_wake_word_detected = on_detected
        if on_false_positive:
            self.on_false_positive = on_false_positive
        if on_sensitivity_adjusted:
            self.on_sensitivity_adjusted = on_sensitivity_adjusted
            
    def set_callback(self, callback: Callable):
        """Set callback for wake word detection (backward compatibility)"""
        self.on_wake_word_detected = callback
        
    def get_status(self) -> Dict[str, Any]:
        """Get enhanced wake word detection status"""
        return {
            'initialized': self.is_initialized,
            'enabled': self.enabled,
            'detecting': self.is_detecting,
            'keywords': self.keywords,
            'primary_keyword': self.primary_keyword,
            'keyword': self.keyword,  # Backward compatibility
            'sensitivity': self.sensitivity,
            'adaptive_threshold': self.adaptive_threshold,
            'detection_threshold': self.detection_threshold,
            'min_detection_interval': self.min_detection_interval,
            'auto_sensitivity_adjustment': self.auto_sensitivity_adjustment,
            'background_noise_level': self.stats['background_noise_level'],
            'dependencies': {
                'porcupine': PORCUPINE_AVAILABLE,
                'pyaudio': PYAUDIO_AVAILABLE,
                'speech_recognition': SPEECH_RECOGNITION_AVAILABLE
            },
            'audio_config': {
                'sample_rate': self.sample_rate,
                'frame_length': self.frame_length,
                'device_index': self.audio_device_index
            },
            'statistics': self.stats.copy()
        }
        
    def _check_dependencies(self) -> bool:
        """Check if required dependencies are available"""
        if not PORCUPINE_AVAILABLE and not SPEECH_RECOGNITION_AVAILABLE:
            self.logger.error("No wake word detection libraries available")
            self.logger.info("Install with: pip install pvporcupine or pip install SpeechRecognition")
            self.enabled = False
            return False
            
        if not PYAUDIO_AVAILABLE:
            self.logger.error("PyAudio not available for audio input")
            self.logger.info("Install with: pip install pyaudio")
            self.enabled = False
            return False
            
        return True
        
    async def _initialize_porcupine(self) -> bool:
        """Initialize Porcupine wake word engine"""
        try:
            # Map keywords to Porcupine built-in keywords or custom models
            keyword_paths = []
            sensitivities = []
            
            for keyword in self.keywords:
                if keyword.lower() in ['porcupine', 'picovoice', 'bumblebee', 'alexa', 'americano', 'blueberry', 'bradley', 'brooklyn', 'computer', 'grapefruit', 'grasshopper', 'hey google', 'hey siri', 'jarvis', 'ok google', 'pico clock', 'snowboy', 'terminator', 'view glass']:
                    # Use built-in keyword
                    keyword_paths.append(pvporcupine.KEYWORD_PATHS[keyword.lower()])
                else:
                    # Use custom model if available
                    if self.custom_model_path and Path(self.custom_model_path).exists():
                        keyword_paths.append(self.custom_model_path)
                    else:
                        self.logger.warning(f"Custom keyword '{keyword}' not supported, using 'porcupine'")
                        keyword_paths.append(pvporcupine.KEYWORD_PATHS['porcupine'])
                        
                # Set sensitivity for this keyword
                sensitivity = self.model_sensitivity_map.get(keyword, self.sensitivity)
                sensitivities.append(sensitivity)
                
            # Initialize Porcupine
            self.porcupine = pvporcupine.create(
                keywords=keyword_paths,
                sensitivities=sensitivities
            )
            
            self.logger.info(f"Porcupine initialized with {len(keyword_paths)} keywords")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Porcupine: {e}")
            return False
            
    async def _initialize_audio_stream(self) -> bool:
        """Initialize audio input stream"""
        try:
            self.pa = pyaudio.PyAudio()
            
            # Find appropriate audio device
            device_info = None
            if self.audio_device_index is not None:
                device_info = self.pa.get_device_info_by_index(self.audio_device_index)
            else:
                device_info = self.pa.get_default_input_device_info()
                
            self.logger.info(f"Using audio device: {device_info['name']}")
            
            # Create audio stream
            self.audio_stream = self.pa.open(
                rate=self.sample_rate,
                channels=1,
                format=pyaudio.paInt16,
                input=True,
                frames_per_buffer=self.frame_length,
                input_device_index=self.audio_device_index
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize audio stream: {e}")
            return False
            
    def _detection_loop(self):
        """Main detection loop running in separate thread"""
        try:
            self.logger.info("Wake word detection loop started")
            
            while self.is_detecting:
                try:
                    # Read audio frame
                    if not self.audio_stream:
                        break
                        
                    audio_frame = self.audio_stream.read(
                        self.frame_length,
                        exception_on_overflow=False
                    )
                    
                    # Convert to required format
                    pcm = struct.unpack_from("h" * self.frame_length, audio_frame)
                    
                    # Update background noise level
                    self._update_noise_level(pcm)
                    
                    # Process with Porcupine if available
                    if self.porcupine:
                        keyword_index = self.porcupine.process(pcm)
                        
                        if keyword_index >= 0:
                            detected_keyword = self.keywords[keyword_index] if keyword_index < len(self.keywords) else 'unknown'
                            asyncio.run_coroutine_threadsafe(self._handle_detection(detected_keyword, 0.9), asyncio.get_event_loop())
                            
                    # Add small delay to prevent CPU overload
                    time.sleep(0.01)
                    
                except Exception as e:
                    if self.is_detecting:
                        self.logger.error(f"Error in detection loop: {e}")
                    break
                    
        except Exception as e:
            self.logger.error(f"Detection loop failed: {e}")
        finally:
            self.logger.info("Wake word detection loop ended")
            
    def _update_noise_level(self, pcm_data):
        """Update background noise level for adaptive thresholding"""
        try:
            # Calculate RMS of audio frame
            rms = np.sqrt(np.mean(np.square(pcm_data)))
            
            # Update noise samples
            self.noise_samples.append(rms)
            if len(self.noise_samples) > self.noise_sample_size:
                self.noise_samples.pop(0)
                
            # Calculate average noise level
            if self.noise_samples:
                self.stats['background_noise_level'] = np.mean(self.noise_samples)
                
                # Adaptive threshold adjustment
                if self.auto_sensitivity_adjustment:
                    self._adjust_adaptive_threshold()
                    
        except Exception as e:
            self.logger.error(f"Error updating noise level: {e}")
            
    def _adjust_adaptive_threshold(self):
        """Adjust detection threshold based on background noise"""
        try:
            noise_level = self.stats['background_noise_level']
            
            # Adjust threshold based on noise level
            if noise_level > 1000:  # High noise
                new_threshold = min(0.9, self.detection_threshold + 0.1)
            elif noise_level < 100:  # Low noise
                new_threshold = max(0.3, self.detection_threshold - 0.1)
            else:
                new_threshold = self.detection_threshold
                
            if abs(new_threshold - self.adaptive_threshold) > 0.05:
                self.adaptive_threshold = new_threshold
                self.stats['sensitivity_adjustments'] += 1
                
                self.logger.info(f"Adjusted detection threshold to {new_threshold:.2f} (noise: {noise_level:.1f})")
                
                # Notify callback
                if self.on_sensitivity_adjusted:
                    try:
                        self.on_sensitivity_adjusted(new_threshold, noise_level)
                    except Exception as e:
                        self.logger.error(f"Error in sensitivity callback: {e}")
                        
        except Exception as e:
            self.logger.error(f"Error adjusting adaptive threshold: {e}")
            
    async def _handle_detection(self, keyword: str, confidence: float):
        """Handle wake word detection with validation"""
        try:
            current_time = time.time()
            
            # Check minimum detection interval
            if current_time - self.last_detection_time < self.min_detection_interval:
                self.logger.debug(f"Detection ignored (too soon): {keyword}")
                return
                
            # Validate detection confidence
            if confidence < self.adaptive_threshold:
                self.stats['false_positives'] += 1
                self.logger.debug(f"Detection ignored (low confidence): {keyword} ({confidence:.2f})")
                
                if self.on_false_positive:
                    try:
                        self.on_false_positive(keyword, confidence)
                    except Exception as e:
                        self.logger.error(f"Error in false positive callback: {e}")
                return
                
            # Valid detection
            self.last_detection_time = current_time
            self.stats['total_detections'] += 1
            self.stats['confirmed_detections'] += 1
            
            # Update keyword usage
            if keyword in self.stats['keyword_usage']:
                self.stats['keyword_usage'][keyword] += 1
                
            # Update detection history
            detection_info = {
                'timestamp': current_time,
                'keyword': keyword,
                'confidence': confidence,
                'noise_level': self.stats['background_noise_level']
            }
            
            self.stats['detection_history'].append(detection_info)
            if len(self.stats['detection_history']) > 50:
                self.stats['detection_history'].pop(0)
                
            # Update average confidence
            total_confidence = sum(d['confidence'] for d in self.stats['detection_history'])
            self.stats['average_detection_confidence'] = total_confidence / len(self.stats['detection_history'])
            
            # Store detection times for pattern analysis
            self.stats['detection_times'].append(current_time)
            if len(self.stats['detection_times']) > 100:
                self.stats['detection_times'].pop(0)
                
            self.logger.info(f"Wake word detected: '{keyword}' (confidence: {confidence:.2f})")
            
            # Trigger callback
            if self.on_wake_word_detected:
                try:
                    if asyncio.iscoroutinefunction(self.on_wake_word_detected):
                        await self.on_wake_word_detected(keyword, confidence)
                    else:
                        self.on_wake_word_detected(keyword, confidence)
                except Exception as e:
                    self.logger.error(f"Error in wake word callback: {e}")
                    
        except Exception as e:
            self.logger.error(f"Error handling detection: {e}")
            
    # Advanced methods for customization
    async def add_keyword(self, keyword: str, sensitivity: Optional[float] = None) -> bool:
        """Add a new wake word keyword"""
        try:
            if keyword not in self.keywords:
                self.keywords.append(keyword)
                self.stats['keyword_usage'][keyword] = 0
                
                if sensitivity is not None:
                    self.model_sensitivity_map[keyword] = sensitivity
                    
                self.logger.info(f"Added wake word keyword: '{keyword}'")
                
                # Reinitialize if currently running
                if self.is_detecting:
                    await self.stop_detection()
                    await self._initialize_porcupine()
                    await self.start_detection()
                    
                return True
            else:
                self.logger.warning(f"Keyword '{keyword}' already exists")
                return False
                
        except Exception as e:
            self.logger.error(f"Error adding keyword '{keyword}': {e}")
            return False
            
    async def remove_keyword(self, keyword: str) -> bool:
        """Remove a wake word keyword"""
        try:
            if keyword in self.keywords and len(self.keywords) > 1:
                self.keywords.remove(keyword)
                
                if keyword in self.stats['keyword_usage']:
                    del self.stats['keyword_usage'][keyword]
                    
                if keyword in self.model_sensitivity_map:
                    del self.model_sensitivity_map[keyword]
                    
                self.logger.info(f"Removed wake word keyword: '{keyword}'")
                
                # Reinitialize if currently running
                if self.is_detecting:
                    await self.stop_detection()
                    await self._initialize_porcupine()
                    await self.start_detection()
                    
                return True
            else:
                self.logger.warning(f"Cannot remove keyword '{keyword}' (not found or last keyword)")
                return False
                
        except Exception as e:
            self.logger.error(f"Error removing keyword '{keyword}': {e}")
            return False
            
    async def set_sensitivity(self, sensitivity: float, keyword: Optional[str] = None) -> bool:
        """Set sensitivity for all keywords or specific keyword"""
        try:
            if not 0.0 <= sensitivity <= 1.0:
                self.logger.error("Sensitivity must be between 0.0 and 1.0")
                return False
                
            if keyword:
                if keyword in self.keywords:
                    self.model_sensitivity_map[keyword] = sensitivity
                    self.logger.info(f"Set sensitivity for '{keyword}': {sensitivity}")
                else:
                    self.logger.error(f"Keyword '{keyword}' not found")
                    return False
            else:
                self.sensitivity = sensitivity
                self.stats['current_sensitivity'] = sensitivity
                self.logger.info(f"Set global sensitivity: {sensitivity}")
                
            # Reinitialize if currently running
            if self.is_detecting:
                await self.stop_detection()
                await self._initialize_porcupine()
                await self.start_detection()
                
            return True
            
        except Exception as e:
            self.logger.error(f"Error setting sensitivity: {e}")
            return False
            
    def get_detection_patterns(self) -> Dict[str, Any]:
        """Analyze detection patterns for insights"""
        try:
            if not self.stats['detection_times']:
                return {'patterns': 'No detection data available'}
                
            detection_times = self.stats['detection_times']
            intervals = [detection_times[i] - detection_times[i-1] for i in range(1, len(detection_times))]
            
            patterns = {
                'total_detections': len(detection_times),
                'average_interval': np.mean(intervals) if intervals else 0,
                'detection_frequency': len(detection_times) / (detection_times[-1] - detection_times[0]) if len(detection_times) > 1 else 0,
                'most_common_keyword': max(self.stats['keyword_usage'], key=self.stats['keyword_usage'].get) if self.stats['keyword_usage'] else None,
                'keyword_distribution': self.stats['keyword_usage'].copy(),
                'average_confidence': self.stats['average_detection_confidence'],
                'false_positive_rate': self.stats['false_positives'] / max(1, self.stats['total_detections'])
            }
            
            return patterns
            
        except Exception as e:
            self.logger.error(f"Error analyzing detection patterns: {e}")
            return {'error': str(e)}