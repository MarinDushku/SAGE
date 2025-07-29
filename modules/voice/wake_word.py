"""
Wake Word Detector - Always-listening wake word detection for SAGE
"""

import asyncio
import logging
from typing import Dict, Any, Optional, Callable

# Try to import wake word libraries
try:
    import pvporcupine
    PORCUPINE_AVAILABLE = True
except ImportError:
    pvporcupine = None
    PORCUPINE_AVAILABLE = False


class WakeWordDetector:
    """Wake word detection system"""
    
    def __init__(self, config: Dict[str, Any], logger=None):
        self.config = config
        self.logger = logger or logging.getLogger(__name__)
        
        # Configuration
        self.enabled = config.get('enabled', True)
        self.keyword = config.get('keyword', 'sage')
        self.sensitivity = config.get('sensitivity', 0.5)
        
        # State
        self.is_initialized = False
        self.is_detecting = False
        
        # Callbacks
        self.on_wake_word_detected: Optional[Callable] = None
        
        # Statistics
        self.stats = {
            'detections': 0,
            'false_positives': 0,
            'keyword_used': self.keyword
        }
        
    async def initialize(self) -> bool:
        """Initialize wake word detection"""
        try:
            if not self.enabled:
                self.logger.info("Wake word detection disabled")
                self.is_initialized = True
                return True
                
            self.logger.info(f"Initializing wake word detection for: '{self.keyword}'")
            
            # For now, just mark as initialized
            # Real implementation would initialize Porcupine or similar
            if not PORCUPINE_AVAILABLE:
                self.logger.warning("Porcupine not available. Wake word detection disabled.")
                self.logger.info("Install with: pip install pvporcupine")
                self.enabled = False
                
            self.is_initialized = True
            self.logger.info("Wake word detection initialized")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize wake word detection: {e}")
            return False
            
    async def start_detection(self) -> bool:
        """Start wake word detection"""
        if not self.is_initialized or not self.enabled:
            return False
            
        try:
            self.is_detecting = True
            self.logger.info(f"Started wake word detection for: '{self.keyword}'")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start wake word detection: {e}")
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
        
    def set_callback(self, callback: Callable):
        """Set callback for wake word detection"""
        self.on_wake_word_detected = callback
        
    def get_status(self) -> Dict[str, Any]:
        """Get wake word detection status"""
        return {
            'initialized': self.is_initialized,
            'enabled': self.enabled,
            'detecting': self.is_detecting,
            'keyword': self.keyword,
            'sensitivity': self.sensitivity,
            'dependencies': {
                'porcupine': PORCUPINE_AVAILABLE
            },
            'statistics': self.stats.copy()
        }