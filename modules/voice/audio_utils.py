"""
Audio Processing Utilities - Audio handling and processing for SAGE
"""

import asyncio
import logging
import numpy as np
import threading
import time
import wave
import io
from typing import Dict, Any, Optional, List, Tuple, Union
from pathlib import Path

# Try to import audio libraries
try:
    import pyaudio
    PYAUDIO_AVAILABLE = True
except ImportError:
    pyaudio = None
    PYAUDIO_AVAILABLE = False

try:
    import webrtcvad
    WEBRTCVAD_AVAILABLE = True
except ImportError:
    webrtcvad = None
    WEBRTCVAD_AVAILABLE = False

# Try to import advanced audio processing libraries
try:
    import scipy.signal
    import scipy.fft
    SCIPY_AVAILABLE = True
except ImportError:
    scipy = None
    SCIPY_AVAILABLE = False

try:
    import librosa
    LIBROSA_AVAILABLE = True
except ImportError:
    librosa = None
    LIBROSA_AVAILABLE = False

try:
    import soundfile as sf
    SOUNDFILE_AVAILABLE = True
except ImportError:
    sf = None
    SOUNDFILE_AVAILABLE = False


class AudioProcessor:
    """Audio processing and utilities"""
    
    def __init__(self, config: Dict[str, Any], logger=None):
        self.config = config
        self.logger = logger or logging.getLogger(__name__)
        
        # Basic Configuration
        self.sample_rate = config.get('sample_rate', 16000)
        self.chunk_size = config.get('chunk_size', 1024)
        self.channels = config.get('channels', 1)
        self.format = config.get('format', 'int16')
        self.bit_depth = config.get('bit_depth', 16)
        
        # Voice Activity Detection
        self.vad_enabled = config.get('vad_enabled', True)
        self.vad_aggressiveness = config.get('vad_aggressiveness', 1)  # 0-3
        self.vad_frame_duration = config.get('vad_frame_duration', 30)  # ms
        
        # Advanced Audio Processing
        self.noise_reduction_enabled = config.get('noise_reduction_enabled', True)
        self.noise_gate_threshold = config.get('noise_gate_threshold', -40)  # dB
        self.auto_gain_control = config.get('auto_gain_control', True)
        self.target_loudness = config.get('target_loudness', -23)  # LUFS
        
        # Audio Enhancement
        self.echo_cancellation = config.get('echo_cancellation', True)
        self.high_pass_filter = config.get('high_pass_filter', 80)  # Hz
        self.low_pass_filter = config.get('low_pass_filter', 8000)  # Hz
        self.compressor_enabled = config.get('compressor_enabled', True)
        self.compressor_ratio = config.get('compressor_ratio', 4.0)
        self.compressor_threshold = config.get('compressor_threshold', -20)  # dB
        
        # Audio Quality
        self.resampling_quality = config.get('resampling_quality', 'high')  # low, medium, high
        self.windowing_function = config.get('windowing_function', 'hann')
        self.overlap_ratio = config.get('overlap_ratio', 0.5)
        
        # Processing Pipeline
        self.preprocessing_enabled = config.get('preprocessing_enabled', True)
        self.postprocessing_enabled = config.get('postprocessing_enabled', True)
        self.real_time_processing = config.get('real_time_processing', True)
        
        # Buffer Management
        self.buffer_size = config.get('buffer_size', 4096)
        self.max_buffer_duration = config.get('max_buffer_duration', 10.0)  # seconds
        self.adaptive_buffering = config.get('adaptive_buffering', True)
        
        # State
        self.is_initialized = False
        self.is_processing = False
        self.processing_thread = None
        
        # Components
        self.vad = None
        self.audio_buffer = []
        self.noise_profile = None
        self.gain_controller = None
        
        # Processing Locks
        self.buffer_lock = threading.Lock()
        self.processing_lock = threading.Lock()
        
        # Enhanced Statistics
        self.stats = {
            'audio_chunks_processed': 0,
            'voice_activity_detected': 0,
            'silence_detected': 0,
            'noise_reduction_applied': 0,
            'gain_adjustments': 0,
            'format_conversions': 0,
            'buffer_overruns': 0,
            'processing_errors': 0,
            'average_processing_time': 0.0,
            'peak_amplitude': 0.0,
            'rms_level': 0.0,
            'signal_to_noise_ratio': 0.0,
            'dynamic_range': 0.0,
            'frequency_spectrum': {},
            'processing_latency': 0.0
        }
        
        # Audio Analysis
        self.spectrum_analyzer = None
        self.level_meter = None
        self.quality_analyzer = None
        
    async def initialize(self) -> bool:
        """Initialize enhanced audio processing pipeline"""
        try:
            self.logger.info("Initializing enhanced audio processor...")
            
            # Check dependencies
            if not self._check_dependencies():
                return False
            
            # Initialize Voice Activity Detection
            if self.vad_enabled and WEBRTCVAD_AVAILABLE:
                self.vad = webrtcvad.Vad(self.vad_aggressiveness)
                self.logger.info(f"VAD initialized with aggressiveness: {self.vad_aggressiveness}")
            elif self.vad_enabled:
                self.logger.warning("WebRTC VAD not available. Install with: pip install webrtcvad")
                
            # Initialize audio processing components
            await self._initialize_processing_components()
            
            # Initialize audio analysis tools
            if SCIPY_AVAILABLE:
                await self._initialize_analysis_tools()
                
            # Initialize buffer management
            self._initialize_buffers()
            
            self.is_initialized = True
            self.logger.info("Enhanced audio processor initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize audio processor: {e}")
            return False
            
    async def detect_voice_activity(self, audio_data: Union[bytes, np.ndarray]) -> Tuple[bool, float]:
        """Enhanced voice activity detection with confidence score"""
        try:
            start_time = time.time()
            
            # Convert audio data to numpy array if needed
            if isinstance(audio_data, bytes):
                audio_array = np.frombuffer(audio_data, dtype=np.int16)
            else:
                audio_array = audio_data
                
            # Basic VAD using WebRTC
            vad_result = True
            vad_confidence = 0.5
            
            if self.vad and isinstance(audio_data, bytes):
                # WebRTC VAD expects specific sample rates
                if self.sample_rate in [8000, 16000, 32000, 48000]:
                    vad_result = self.vad.is_speech(audio_data, self.sample_rate)
                    vad_confidence = 0.8 if vad_result else 0.2
                    
            # Enhanced VAD using energy and spectral analysis
            if SCIPY_AVAILABLE:
                energy_vad, energy_confidence = self._energy_based_vad(audio_array)
                spectral_vad, spectral_confidence = self._spectral_based_vad(audio_array)
                
                # Combine VAD results
                combined_confidence = (vad_confidence + energy_confidence + spectral_confidence) / 3
                final_result = combined_confidence > 0.5
            else:
                final_result = vad_result
                combined_confidence = vad_confidence
                
            # Update statistics
            self.stats['audio_chunks_processed'] += 1
            processing_time = time.time() - start_time
            self._update_processing_stats(processing_time)
            
            if final_result:
                self.stats['voice_activity_detected'] += 1
            else:
                self.stats['silence_detected'] += 1
                
            return final_result, combined_confidence
            
        except Exception as e:
            self.logger.error(f"Error in voice activity detection: {e}")
            self.stats['processing_errors'] += 1
            return True, 0.5  # Default to assuming voice activity
            
    async def normalize_audio(self, audio_data: Union[bytes, np.ndarray], 
                             target_level: float = -23.0) -> Union[bytes, np.ndarray]:
        """Advanced audio normalization with loudness standardization"""
        try:
            start_time = time.time()
            
            # Convert to numpy array
            if isinstance(audio_data, bytes):
                audio_array = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32)
                return_bytes = True
            else:
                audio_array = audio_data.astype(np.float32)
                return_bytes = False
                
            # Normalize to [-1, 1] range
            if np.max(np.abs(audio_array)) > 0:
                audio_array = audio_array / np.max(np.abs(audio_array))
                
            # Apply auto gain control if enabled
            if self.auto_gain_control:
                audio_array = await self._apply_auto_gain_control(audio_array, target_level)
                
            # Apply dynamic range compression if enabled
            if self.compressor_enabled:
                audio_array = self._apply_compression(audio_array)
                
            # Update statistics
            self.stats['gain_adjustments'] += 1
            processing_time = time.time() - start_time
            self._update_processing_stats(processing_time)
            
            # Convert back to original format if needed
            if return_bytes:
                # Scale back to int16 range
                audio_array = (audio_array * 32767).astype(np.int16)
                return audio_array.tobytes()
            else:
                return audio_array
                
        except Exception as e:
            self.logger.error(f"Error normalizing audio: {e}")
            self.stats['processing_errors'] += 1
            return audio_data
            
    async def filter_noise(self, audio_data: Union[bytes, np.ndarray]) -> Union[bytes, np.ndarray]:
        """Advanced noise filtering with spectral subtraction and adaptive filtering"""
        try:
            start_time = time.time()
            
            # Convert to numpy array
            if isinstance(audio_data, bytes):
                audio_array = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32767.0
                return_bytes = True
            else:
                audio_array = audio_data.astype(np.float32)
                return_bytes = False
                
            filtered_audio = audio_array.copy()
            
            # Apply frequency domain filtering if scipy is available
            if SCIPY_AVAILABLE:
                # High-pass filter to remove low-frequency noise
                if self.high_pass_filter > 0:
                    filtered_audio = self._apply_high_pass_filter(filtered_audio, self.high_pass_filter)
                    
                # Low-pass filter to remove high-frequency noise
                if self.low_pass_filter < self.sample_rate // 2:
                    filtered_audio = self._apply_low_pass_filter(filtered_audio, self.low_pass_filter)
                    
                # Spectral subtraction for noise reduction
                if self.noise_reduction_enabled:
                    filtered_audio = await self._apply_spectral_subtraction(filtered_audio)
                    
                # Adaptive noise gate
                filtered_audio = self._apply_noise_gate(filtered_audio)
                
            # Update statistics
            self.stats['noise_reduction_applied'] += 1
            processing_time = time.time() - start_time
            self._update_processing_stats(processing_time)
            
            # Convert back to original format if needed
            if return_bytes:
                # Scale back to int16 range
                filtered_audio = (filtered_audio * 32767).astype(np.int16)
                return filtered_audio.tobytes()
            else:
                return filtered_audio
                
        except Exception as e:
            self.logger.error(f"Error filtering noise: {e}")
            self.stats['processing_errors'] += 1
            return audio_data
            
    def get_audio_devices(self) -> list:
        """Get list of available audio devices"""
        devices = []
        
        if not PYAUDIO_AVAILABLE:
            return devices
            
        try:
            audio = pyaudio.PyAudio()
            
            for i in range(audio.get_device_count()):
                device_info = audio.get_device_info_by_index(i)
                devices.append({
                    'index': i,
                    'name': device_info['name'],
                    'channels': device_info['maxInputChannels'],
                    'sample_rate': device_info['defaultSampleRate']
                })
                
            audio.terminate()
            
        except Exception as e:
            self.logger.error(f"Error getting audio devices: {e}")
            
        return devices
        
    async def shutdown(self):
        """Shutdown audio processor"""
        self.is_initialized = False
        self.logger.info("Audio processor shutdown complete")
        
    def get_status(self) -> Dict[str, Any]:
        """Get audio processor status"""
        return {
            'initialized': self.is_initialized,
            'processing': self.is_processing,
            'sample_rate': self.sample_rate,
            'chunk_size': self.chunk_size,
            'channels': self.channels,
            'format': self.format,
            'bit_depth': self.bit_depth,
            'vad_enabled': self.vad_enabled,
            'vad_available': self.vad is not None,
            'noise_reduction_enabled': self.noise_reduction_enabled,
            'auto_gain_control': self.auto_gain_control,
            'compressor_enabled': self.compressor_enabled,
            'preprocessing_enabled': self.preprocessing_enabled,
            'postprocessing_enabled': self.postprocessing_enabled,
            'buffer_size': len(self.audio_buffer),
            'dependencies': {
                'pyaudio': PYAUDIO_AVAILABLE,
                'webrtcvad': WEBRTCVAD_AVAILABLE,
                'scipy': SCIPY_AVAILABLE,
                'librosa': LIBROSA_AVAILABLE,
                'soundfile': SOUNDFILE_AVAILABLE
            },
            'statistics': self.stats.copy()
        }
        
    # Helper methods for enhanced audio processing
    def _check_dependencies(self) -> bool:
        """Check if required dependencies are available"""
        return True  # Basic functionality always available
        
    async def _initialize_processing_components(self):
        """Initialize audio processing components"""
        try:
            # Initialize gain controller
            self.gain_controller = {
                'target_level': self.target_loudness,
                'current_gain': 1.0,
                'adaptation_rate': 0.1
            }
            
            # Initialize noise profile for spectral subtraction
            self.noise_profile = np.zeros(self.chunk_size // 2 + 1)
            
            self.logger.info("Audio processing components initialized")
            
        except Exception as e:
            self.logger.error(f"Error initializing processing components: {e}")
            
    async def _initialize_analysis_tools(self):
        """Initialize audio analysis tools"""
        try:
            # Initialize spectrum analyzer
            self.spectrum_analyzer = {
                'window_size': self.chunk_size,
                'overlap': int(self.chunk_size * self.overlap_ratio),
                'window_function': self.windowing_function
            }
            
            # Initialize level meter
            self.level_meter = {
                'peak_hold_time': 1.0,
                'rms_window_size': int(self.sample_rate * 0.1)  # 100ms window
            }
            
            self.logger.info("Audio analysis tools initialized")
            
        except Exception as e:
            self.logger.error(f"Error initializing analysis tools: {e}")
            
    def _initialize_buffers(self):
        """Initialize audio buffers"""
        try:
            max_buffer_samples = int(self.max_buffer_duration * self.sample_rate)
            self.audio_buffer = []
            
            self.logger.info(f"Audio buffers initialized (max duration: {self.max_buffer_duration}s)")
            
        except Exception as e:
            self.logger.error(f"Error initializing buffers: {e}")
            
    def _update_processing_stats(self, processing_time: float):
        """Update processing statistics"""
        try:
            # Update average processing time
            current_avg = self.stats['average_processing_time']
            processed_chunks = self.stats['audio_chunks_processed']
            
            if processed_chunks > 0:
                self.stats['average_processing_time'] = (
                    (current_avg * (processed_chunks - 1) + processing_time) / processed_chunks
                )
            else:
                self.stats['average_processing_time'] = processing_time
                
            # Update processing latency
            self.stats['processing_latency'] = processing_time * 1000  # Convert to ms
            
        except Exception as e:
            self.logger.error(f"Error updating processing stats: {e}")
            
    def _energy_based_vad(self, audio_array: np.ndarray) -> Tuple[bool, float]:
        """Energy-based voice activity detection"""
        try:
            # Calculate RMS energy
            rms_energy = np.sqrt(np.mean(audio_array ** 2))
            
            # Adaptive threshold based on recent energy levels
            energy_threshold = np.mean([s for s in getattr(self, '_energy_history', [0.01])]) * 2
            
            # Update energy history
            if not hasattr(self, '_energy_history'):
                self._energy_history = []
            self._energy_history.append(rms_energy)
            if len(self._energy_history) > 100:
                self._energy_history.pop(0)
                
            is_voice = rms_energy > energy_threshold
            confidence = min(1.0, rms_energy / (energy_threshold + 1e-10))
            
            return is_voice, confidence
            
        except Exception as e:
            self.logger.error(f"Error in energy-based VAD: {e}")
            return True, 0.5
            
    def _spectral_based_vad(self, audio_array: np.ndarray) -> Tuple[bool, float]:
        """Spectral-based voice activity detection"""
        try:
            # Compute power spectral density
            freqs, psd = scipy.signal.welch(audio_array, self.sample_rate, nperseg=min(256, len(audio_array)))
            
            # Voice typically has energy in 300-3400 Hz range
            voice_band_mask = (freqs >= 300) & (freqs <= 3400)
            voice_energy = np.sum(psd[voice_band_mask])
            total_energy = np.sum(psd)
            
            # Calculate spectral centroid
            if total_energy > 0:
                spectral_centroid = np.sum(freqs * psd) / total_energy
                voice_ratio = voice_energy / total_energy
                
                # Voice typically has centroid in 500-2000 Hz range
                centroid_score = 1.0 - abs(spectral_centroid - 1250) / 1250
                centroid_score = max(0, min(1, centroid_score))
                
                confidence = (voice_ratio + centroid_score) / 2
                is_voice = confidence > 0.3
            else:
                is_voice = False
                confidence = 0.0
                
            return is_voice, confidence
            
        except Exception as e:
            self.logger.error(f"Error in spectral-based VAD: {e}")
            return True, 0.5
            
    async def _apply_auto_gain_control(self, audio_array: np.ndarray, target_level: float) -> np.ndarray:
        """Apply automatic gain control to maintain consistent loudness"""
        try:
            if self.gain_controller is None:
                return audio_array
                
            # Calculate current RMS level in dB
            rms = np.sqrt(np.mean(audio_array ** 2))
            current_level_db = 20 * np.log10(rms + 1e-10)
            
            # Calculate required gain adjustment
            gain_adjustment_db = target_level - current_level_db
            gain_adjustment_linear = 10 ** (gain_adjustment_db / 20)
            
            # Apply adaptive gain adjustment
            adaptation_rate = self.gain_controller['adaptation_rate']
            current_gain = self.gain_controller['current_gain']
            
            new_gain = current_gain + adaptation_rate * (gain_adjustment_linear - current_gain)
            self.gain_controller['current_gain'] = new_gain
            
            # Apply gain to audio
            return audio_array * new_gain
            
        except Exception as e:
            self.logger.error(f"Error in auto gain control: {e}")
            return audio_array
            
    def _apply_compression(self, audio_array: np.ndarray) -> np.ndarray:
        """Apply dynamic range compression"""
        try:
            threshold_linear = 10 ** (self.compressor_threshold / 20)
            ratio = self.compressor_ratio
            
            # Calculate compression
            abs_audio = np.abs(audio_array)
            compressed = np.where(
                abs_audio > threshold_linear,
                threshold_linear + (abs_audio - threshold_linear) / ratio,
                abs_audio
            )
            
            # Maintain original sign
            return np.sign(audio_array) * compressed
            
        except Exception as e:
            self.logger.error(f"Error in compression: {e}")
            return audio_array
            
    def _apply_high_pass_filter(self, audio_array: np.ndarray, cutoff_freq: float) -> np.ndarray:
        """Apply high-pass filter to remove low-frequency noise"""
        try:
            nyquist = self.sample_rate / 2
            normalized_cutoff = cutoff_freq / nyquist
            
            b, a = scipy.signal.butter(4, normalized_cutoff, btype='high')
            return scipy.signal.filtfilt(b, a, audio_array)
            
        except Exception as e:
            self.logger.error(f"Error in high-pass filter: {e}")
            return audio_array
            
    def _apply_low_pass_filter(self, audio_array: np.ndarray, cutoff_freq: float) -> np.ndarray:
        """Apply low-pass filter to remove high-frequency noise"""
        try:
            nyquist = self.sample_rate / 2
            normalized_cutoff = cutoff_freq / nyquist
            
            b, a = scipy.signal.butter(4, normalized_cutoff, btype='low')
            return scipy.signal.filtfilt(b, a, audio_array)
            
        except Exception as e:
            self.logger.error(f"Error in low-pass filter: {e}")
            return audio_array
            
    async def _apply_spectral_subtraction(self, audio_array: np.ndarray) -> np.ndarray:
        """Apply spectral subtraction for noise reduction"""
        try:
            # Convert to frequency domain
            fft = scipy.fft.fft(audio_array)
            magnitude = np.abs(fft)
            phase = np.angle(fft)
            
            # Update noise profile (assuming first few frames are noise)
            if np.mean(self.noise_profile) == 0:
                self.noise_profile = magnitude[:len(self.noise_profile)]
            else:
                # Adaptive noise profile update
                alpha = 0.1
                self.noise_profile = (1 - alpha) * self.noise_profile + alpha * magnitude[:len(self.noise_profile)]
                
            # Apply spectral subtraction
            # Extend noise profile to match magnitude length
            extended_noise_profile = np.tile(self.noise_profile, (len(magnitude) // len(self.noise_profile)) + 1)[:len(magnitude)]
            
            subtraction_factor = 2.0
            magnitude_cleaned = np.maximum(
                magnitude - subtraction_factor * extended_noise_profile,
                0.1 * magnitude  # Floor to prevent artifacts
            )
            
            # Convert back to time domain
            fft_cleaned = magnitude_cleaned * np.exp(1j * phase)
            return np.real(scipy.fft.ifft(fft_cleaned))
            
        except Exception as e:
            self.logger.error(f"Error in spectral subtraction: {e}")
            return audio_array
            
    def _apply_noise_gate(self, audio_array: np.ndarray) -> np.ndarray:
        """Apply noise gate to suppress low-level noise"""
        try:
            # Convert threshold from dB to linear
            threshold_linear = 10 ** (self.noise_gate_threshold / 20)
            
            # Calculate envelope
            envelope = np.abs(audio_array)
            
            # Apply smoothing to envelope to avoid clicks
            if SCIPY_AVAILABLE:
                from scipy.ndimage import uniform_filter1d
                smoothed_envelope = uniform_filter1d(envelope, size=int(self.sample_rate * 0.01))  # 10ms smoothing
            else:
                smoothed_envelope = envelope
                
            # Create gate signal
            gate = np.where(smoothed_envelope > threshold_linear, 1.0, 0.0)
            
            # Apply gentle gating with attack/release
            gated_audio = audio_array * gate
            
            return gated_audio
            
        except Exception as e:
            self.logger.error(f"Error in noise gate: {e}")
            return audio_array
            
    def _get_window(self, window_size: int) -> np.ndarray:
        """Get windowing function for audio processing"""
        try:
            if self.windowing_function.lower() == 'hann':
                return np.hanning(window_size)
            elif self.windowing_function.lower() == 'hamming':
                return np.hamming(window_size)
            elif self.windowing_function.lower() == 'blackman':
                return np.blackman(window_size)
            else:
                return np.ones(window_size)  # Rectangular window
                
        except Exception as e:
            self.logger.error(f"Error creating window: {e}")
            return np.ones(window_size)
            
    def _apply_pre_emphasis(self, audio_array: np.ndarray, alpha: float = 0.97) -> np.ndarray:
        """Apply pre-emphasis filter to balance frequency spectrum"""
        try:
            if len(audio_array) < 2:
                return audio_array
                
            # Pre-emphasis: y[n] = x[n] - alpha * x[n-1]
            emphasized = np.zeros_like(audio_array)
            emphasized[0] = audio_array[0]
            emphasized[1:] = audio_array[1:] - alpha * audio_array[:-1]
            
            return emphasized
            
        except Exception as e:
            self.logger.error(f"Error in pre-emphasis: {e}")
            return audio_array
            
    def _apply_echo_cancellation(self, audio_array: np.ndarray) -> np.ndarray:
        """Apply basic echo cancellation"""
        try:
            # Simple echo cancellation using adaptive filtering
            # This is a basic implementation - real echo cancellation is more complex
            
            if not hasattr(self, '_echo_history'):
                self._echo_history = np.zeros(int(self.sample_rate * 0.05))  # 50ms history
                
            # Simple delay-based echo suppression
            delay_samples = int(self.sample_rate * 0.02)  # 20ms delay
            
            if len(audio_array) > delay_samples:
                echo_estimate = np.roll(audio_array, delay_samples) * 0.3
                return audio_array - echo_estimate
            else:
                return audio_array
                
        except Exception as e:
            self.logger.error(f"Error in echo cancellation: {e}")
            return audio_array
            
    def _apply_final_gain(self, audio_array: np.ndarray, gain_db: float = 0.0) -> np.ndarray:
        """Apply final gain adjustment"""
        try:
            if gain_db == 0.0:
                return audio_array
                
            gain_linear = 10 ** (gain_db / 20)
            return audio_array * gain_linear
            
        except Exception as e:
            self.logger.error(f"Error in final gain: {e}")
            return audio_array
            
    def _apply_dithering(self, audio_array: np.ndarray) -> np.ndarray:
        """Apply dithering for better quantization"""
        try:
            # Add small amount of noise to reduce quantization artifacts
            dither_amplitude = 1.0 / 32768  # For 16-bit quantization
            dither_noise = np.random.uniform(-dither_amplitude, dither_amplitude, len(audio_array))
            
            return audio_array + dither_noise
            
        except Exception as e:
            self.logger.error(f"Error in dithering: {e}")
            return audio_array
            
    def _resample_audio(self, audio_array: np.ndarray, target_sample_rate: int) -> np.ndarray:
        """Resample audio using scipy"""
        try:
            # Calculate resampling ratio
            ratio = target_sample_rate / self.sample_rate
            
            # Use scipy's resample function
            num_samples = int(len(audio_array) * ratio)
            resampled = scipy.signal.resample(audio_array, num_samples)
            
            return resampled.astype(audio_array.dtype)
            
        except Exception as e:
            self.logger.error(f"Error resampling audio: {e}")
            return audio_array
            
    # Main processing pipeline methods
    async def process_audio_stream(self, audio_stream) -> np.ndarray:
        """Process continuous audio stream with full pipeline"""
        try:
            processed_chunks = []
            
            async for chunk in audio_stream:
                # Apply preprocessing pipeline
                if self.preprocessing_enabled:
                    chunk = await self.preprocess_audio(chunk)
                    
                # Apply main processing
                chunk = await self.filter_noise(chunk)
                chunk = await self.normalize_audio(chunk)
                
                # Apply voice activity detection
                has_voice, confidence = await self.detect_voice_activity(chunk)
                
                if has_voice:
                    # Apply postprocessing pipeline
                    if self.postprocessing_enabled:
                        chunk = await self.postprocess_audio(chunk)
                        
                    processed_chunks.append(chunk)
                    
            return np.concatenate(processed_chunks) if processed_chunks else np.array([])
            
        except Exception as e:
            self.logger.error(f"Error processing audio stream: {e}")
            return np.array([])
            
    async def preprocess_audio(self, audio_data: Union[bytes, np.ndarray]) -> np.ndarray:
        """Apply audio preprocessing pipeline"""
        try:
            # Convert to numpy array
            if isinstance(audio_data, bytes):
                audio_array = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32767.0
            else:
                audio_array = audio_data.astype(np.float32)
                
            # Apply DC offset removal
            audio_array = audio_array - np.mean(audio_array)
            
            # Apply pre-emphasis filter to balance frequency spectrum
            if SCIPY_AVAILABLE:
                audio_array = self._apply_pre_emphasis(audio_array)
                
            # Apply windowing for better frequency analysis
            if len(audio_array) > 0:
                window = self._get_window(len(audio_array))
                audio_array = audio_array * window
                
            return audio_array
            
        except Exception as e:
            self.logger.error(f"Error in audio preprocessing: {e}")
            return audio_data if isinstance(audio_data, np.ndarray) else np.array([])
            
    async def postprocess_audio(self, audio_data: np.ndarray) -> np.ndarray:
        """Apply audio postprocessing pipeline"""
        try:
            processed_audio = audio_data.copy()
            
            # Apply echo cancellation if enabled
            if self.echo_cancellation:
                processed_audio = self._apply_echo_cancellation(processed_audio)
                
            # Apply final gain adjustment
            processed_audio = self._apply_final_gain(processed_audio)
            
            # Apply dithering for better quantization
            if SCIPY_AVAILABLE:
                processed_audio = self._apply_dithering(processed_audio)
                
            return processed_audio
            
        except Exception as e:
            self.logger.error(f"Error in audio postprocessing: {e}")
            return audio_data
            
    async def convert_audio_format(self, audio_data: Union[bytes, np.ndarray], 
                                  target_format: str, target_sample_rate: int = None) -> Union[bytes, np.ndarray]:
        """Convert audio between different formats and sample rates"""
        try:
            start_time = time.time()
            
            # Convert input to numpy array
            if isinstance(audio_data, bytes):
                if self.format == 'int16':
                    audio_array = np.frombuffer(audio_data, dtype=np.int16)
                elif self.format == 'int32':
                    audio_array = np.frombuffer(audio_data, dtype=np.int32)
                else:
                    audio_array = np.frombuffer(audio_data, dtype=np.float32)
            else:
                audio_array = audio_data
                
            # Resample if needed
            if target_sample_rate and target_sample_rate != self.sample_rate:
                if LIBROSA_AVAILABLE:
                    audio_array = librosa.resample(
                        audio_array.astype(np.float32), 
                        orig_sr=self.sample_rate, 
                        target_sr=target_sample_rate
                    )
                elif SCIPY_AVAILABLE:
                    # Use scipy for resampling
                    audio_array = self._resample_audio(audio_array, target_sample_rate)
                    
            # Convert to target format
            if target_format == 'int16':
                if audio_array.dtype != np.int16:
                    if audio_array.dtype == np.float32:
                        audio_array = (audio_array * 32767).astype(np.int16)
                    else:
                        audio_array = audio_array.astype(np.int16)
            elif target_format == 'int32':
                if audio_array.dtype != np.int32:
                    if audio_array.dtype == np.float32:
                        audio_array = (audio_array * 2147483647).astype(np.int32)
                    else:
                        audio_array = audio_array.astype(np.int32)
            elif target_format == 'float32':
                if audio_array.dtype != np.float32:
                    if audio_array.dtype == np.int16:
                        audio_array = audio_array.astype(np.float32) / 32767.0
                    elif audio_array.dtype == np.int32:
                        audio_array = audio_array.astype(np.float32) / 2147483647.0
                    else:
                        audio_array = audio_array.astype(np.float32)
                        
            # Update statistics
            self.stats['format_conversions'] += 1
            processing_time = time.time() - start_time
            self._update_processing_stats(processing_time)
            
            # Return in requested format
            if target_format in ['int16', 'int32']:
                return audio_array.tobytes()
            else:
                return audio_array
                
        except Exception as e:
            self.logger.error(f"Error converting audio format: {e}")
            self.stats['processing_errors'] += 1
            return audio_data
            
    def analyze_audio_quality(self, audio_data: np.ndarray) -> Dict[str, float]:
        """Analyze audio quality metrics"""
        try:
            metrics = {}
            
            # Basic level metrics
            rms_level = np.sqrt(np.mean(audio_data ** 2))
            peak_level = np.max(np.abs(audio_data))
            
            metrics['rms_level_db'] = 20 * np.log10(rms_level + 1e-10)
            metrics['peak_level_db'] = 20 * np.log10(peak_level + 1e-10)
            metrics['crest_factor'] = peak_level / (rms_level + 1e-10)
            
            # Dynamic range
            sorted_samples = np.sort(np.abs(audio_data))
            p99 = sorted_samples[int(0.99 * len(sorted_samples))]
            p1 = sorted_samples[int(0.01 * len(sorted_samples))]
            metrics['dynamic_range_db'] = 20 * np.log10((p99 + 1e-10) / (p1 + 1e-10))
            
            # Frequency domain analysis if scipy available
            if SCIPY_AVAILABLE:
                freqs, psd = scipy.signal.welch(audio_data, self.sample_rate)
                
                # Spectral centroid
                spectral_centroid = np.sum(freqs * psd) / np.sum(psd)
                metrics['spectral_centroid'] = spectral_centroid
                
                # Spectral bandwidth
                spectral_bandwidth = np.sqrt(np.sum(((freqs - spectral_centroid) ** 2) * psd) / np.sum(psd))
                metrics['spectral_bandwidth'] = spectral_bandwidth
                
                # Signal-to-noise ratio estimation
                signal_power = np.sum(psd[freqs < 4000])  # Assume speech below 4kHz
                noise_power = np.sum(psd[freqs > 6000])   # Assume noise above 6kHz
                metrics['estimated_snr_db'] = 10 * np.log10((signal_power + 1e-10) / (noise_power + 1e-10))
                
            # Update internal statistics
            self.stats['rms_level'] = float(rms_level)
            self.stats['peak_amplitude'] = float(peak_level)
            self.stats['dynamic_range'] = metrics.get('dynamic_range_db', 0)
            self.stats['signal_to_noise_ratio'] = metrics.get('estimated_snr_db', 0)
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Error analyzing audio quality: {e}")
            return {}
            
    async def save_audio_file(self, audio_data: np.ndarray, filename: str, 
                             format: str = 'wav') -> bool:
        """Save audio data to file"""
        try:
            file_path = Path(filename)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            if SOUNDFILE_AVAILABLE:
                # Use soundfile for better format support
                sf.write(str(file_path), audio_data, self.sample_rate, format=format)
            else:
                # Fallback to wave module for WAV files
                if format.lower() == 'wav':
                    with wave.open(str(file_path), 'wb') as wav_file:
                        wav_file.setnchannels(self.channels)
                        wav_file.setsampwidth(2)  # 16-bit
                        wav_file.setframerate(self.sample_rate)
                        
                        # Convert to int16 if needed
                        if audio_data.dtype != np.int16:
                            if audio_data.dtype == np.float32:
                                audio_data = (audio_data * 32767).astype(np.int16)
                            else:
                                audio_data = audio_data.astype(np.int16)
                                
                        wav_file.writeframes(audio_data.tobytes())
                else:
                    self.logger.error(f"Format {format} not supported without soundfile library")
                    return False
                    
            self.logger.info(f"Audio saved to: {file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving audio file: {e}")
            return False
            
    async def load_audio_file(self, filename: str) -> Tuple[np.ndarray, int]:
        """Load audio data from file"""
        try:
            file_path = Path(filename)
            
            if not file_path.exists():
                self.logger.error(f"Audio file not found: {file_path}")
                return np.array([]), 0
                
            if SOUNDFILE_AVAILABLE:
                # Use soundfile for better format support
                audio_data, sample_rate = sf.read(str(file_path))
                
                # Convert to mono if needed
                if len(audio_data.shape) > 1:
                    audio_data = np.mean(audio_data, axis=1)
                    
            elif LIBROSA_AVAILABLE:
                # Use librosa as fallback
                audio_data, sample_rate = librosa.load(str(file_path), sr=None)
                
            else:
                # Fallback to wave module for WAV files
                if file_path.suffix.lower() == '.wav':
                    with wave.open(str(file_path), 'rb') as wav_file:
                        frames = wav_file.readframes(wav_file.getnframes())
                        sample_rate = wav_file.getframerate()
                        
                        # Convert bytes to numpy array
                        if wav_file.getsampwidth() == 2:
                            audio_data = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32767.0
                        else:
                            self.logger.error("Only 16-bit WAV files supported")
                            return np.array([]), 0
                else:
                    self.logger.error(f"File format not supported: {file_path.suffix}")
                    return np.array([]), 0
                    
            self.logger.info(f"Audio loaded from: {file_path} (duration: {len(audio_data)/sample_rate:.2f}s)")
            return audio_data, sample_rate
            
        except Exception as e:
            self.logger.error(f"Error loading audio file: {e}")
            return np.array([]), 0