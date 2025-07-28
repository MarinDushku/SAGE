"""
SAGE Modules - Modular components for the Smart Adaptive General Executive
"""

from abc import ABC, abstractmethod
import asyncio
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum
import time


class EventType(Enum):
    # Voice events
    VOICE_COMMAND = "voice.command"
    VOICE_TRANSCRIPTION = "voice.transcription"
    SPEAK_REQUEST = "voice.speak"
    WAKE_WORD_DETECTED = "voice.wake_word"
    
    # Vision events
    FACE_DETECTED = "vision.face_detected"
    OBJECT_DETECTED = "vision.object_detected"
    SCREEN_CAPTURED = "vision.screen_captured"
    
    # NLP events
    INTENT_PARSED = "nlp.intent_parsed"
    LLM_RESPONSE = "nlp.llm_response"
    CONTEXT_UPDATED = "nlp.context_updated"
    
    # Calendar events
    REMINDER_DUE = "calendar.reminder_due"
    SCHEDULE_UPDATED = "calendar.schedule_updated"
    
    # System events
    MODULE_LOADED = "system.module_loaded"
    MODULE_UNLOADED = "system.module_unloaded"
    ERROR_OCCURRED = "system.error"
    RESOURCE_WARNING = "system.resource_warning"
    SHUTDOWN_REQUESTED = "system.shutdown"
    SYSTEM_SHUTDOWN = "system.shutdown_immediate"


@dataclass
class Event:
    type: EventType
    data: Dict[str, Any]
    source_module: str
    priority: int = 5  # 1-10, higher is more important
    timestamp: float = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()


class BaseModule(ABC):
    """Base class for all SAGE modules"""
    
    def __init__(self, name: str):
        self.name = name
        self.event_bus = None
        self.config = None
        self.cache = None
        self.logger = None
        self.is_loaded = False
        self.subscribed_events: List[EventType] = []
        
    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize the module. Return True if successful."""
        pass
    
    @abstractmethod
    async def shutdown(self) -> None:
        """Clean up resources and shutdown the module."""
        pass
    
    @abstractmethod
    async def handle_event(self, event: Event) -> Optional[Any]:
        """Process events from other modules."""
        pass
    
    def subscribe_events(self, event_types: List[EventType]) -> None:
        """Subscribe to specific event types."""
        self.subscribed_events.extend(event_types)
        if self.event_bus:
            for event_type in event_types:
                self.event_bus.subscribe(event_type, self)
    
    def emit_event(self, event_type: EventType, data: Dict[str, Any]) -> None:
        """Send event to other modules."""
        if self.event_bus:
            event = Event(
                type=event_type,
                data=data,
                source_module=self.name
            )
            self.event_bus.emit(event)
    
    def log(self, message: str, level: str = "info") -> None:
        """Log a message with the module name."""
        if self.logger:
            getattr(self.logger, level)(f"[{self.name}] {message}")
    
    async def get_resource_usage(self) -> Dict[str, Any]:
        """Get current resource usage for this module."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        return {
            "cpu_percent": process.cpu_percent(),
            "memory_mb": process.memory_info().rss / 1024 / 1024,
            "is_loaded": self.is_loaded
        }


__all__ = ['BaseModule', 'Event', 'EventType']