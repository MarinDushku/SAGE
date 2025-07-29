"""
Audio Processing Utilities - Audio handling and processing for SAGE
"""

import asyncio
import logging
from typing import Dict, Any, Optional

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


class AudioProcessor:
    """Audio processing and utilities"""
    
    def __init__(self, config: Dict[str, Any], logger=None):
        self.config = config
        self.logger = logger or logging.getLogger(__name__)
        
        # Configuration
        self.sample_rate = config.get('sample_rate', 16000)
        self.chunk_size = config.get('chunk_size', 1024)
        self.channels = config.get('channels', 1)
        self.format = config.get('format', 'int16')
        
        # Voice Activity Detection
        self.vad_enabled = config.get('vad_enabled', True)
        self.vad_aggressiveness = config.get('vad_aggressiveness', 1)  # 0-3
        
        # State
        self.is_initialized = False
        self.vad = None
        
        # Statistics
        self.stats = {
            'audio_chunks_processed': 0,
            'voice_activity_detected': 0,
            'silence_detected': 0
        }
        
    async def initialize(self) -> bool:
        """Initialize audio processing"""
        try:
            self.logger.info("Initializing audio processor...")
            
            # Initialize Voice Activity Detection
            if self.vad_enabled and WEBRTCVAD_AVAILABLE:
                self.vad = webrtcvad.Vad(self.vad_aggressiveness)
                self.logger.info(f"VAD initialized with aggressiveness: {self.vad_aggressiveness}")
            elif self.vad_enabled:
                self.logger.warning("WebRTC VAD not available. Install with: pip install webrtcvad")
                
            self.is_initialized = True
            self.logger.info("Audio processor initialized")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize audio processor: {e}")
            return False
            
    async def detect_voice_activity(self, audio_data: bytes) -> bool:
        """Detect voice activity in audio data"""
        try:
            if not self.vad:
                return True  # Assume voice activity if VAD not available
                
            # WebRTC VAD expects specific sample rates
            if self.sample_rate not in [8000, 16000, 32000, 48000]:
                return True  # Skip VAD for unsupported sample rates
                
            self.stats['audio_chunks_processed'] += 1
            
            # Check if audio contains voice
            is_speech = self.vad.is_speech(audio_data, self.sample_rate)
            
            if is_speech:
                self.stats['voice_activity_detected'] += 1
            else:
                self.stats['silence_detected'] += 1
                
            return is_speech
            
        except Exception as e:
            self.logger.error(f"Error in voice activity detection: {e}")
            return True  # Default to assuming voice activity
            
    async def normalize_audio(self, audio_data: bytes) -> bytes:
        """Normalize audio data"""
        try:
            # Basic normalization - can be enhanced
            return audio_data
            
        except Exception as e:
            self.logger.error(f"Error normalizing audio: {e}")
            return audio_data
            
    async def filter_noise(self, audio_data: bytes) -> bytes:
        """Apply noise filtering to audio data"""
        try:
            # Basic noise filtering - can be enhanced with spectral subtraction
            return audio_data
            
        except Exception as e:
            self.logger.error(f"Error filtering noise: {e}")
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
            'sample_rate': self.sample_rate,
            'chunk_size': self.chunk_size,
            'channels': self.channels,
            'format': self.format,
            'vad_enabled': self.vad_enabled,
            'vad_available': self.vad is not None,
            'dependencies': {
                'pyaudio': PYAUDIO_AVAILABLE,
                'webrtcvad': WEBRTCVAD_AVAILABLE
            },
            'statistics': self.stats.copy()
        }