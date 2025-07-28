"""
Event Bus - Central message passing system for SAGE modules
"""

import asyncio
from typing import Dict, List, Callable, Any, Optional
from collections import defaultdict, deque
import time
import logging
from threading import Lock

from modules import Event, EventType, BaseModule


class EventBus:
    """Async event bus for inter-module communication"""
    
    def __init__(self, max_queue_size: int = 1000):
        self.subscribers: Dict[EventType, List[BaseModule]] = defaultdict(list)
        self.event_queue: deque = deque(maxlen=max_queue_size)
        self.event_history: deque = deque(maxlen=100)  # Keep last 100 events
        self.running = False
        self.processing_task: Optional[asyncio.Task] = None
        self.lock = Lock()
        self.logger = logging.getLogger(__name__)
        
    async def start(self) -> None:
        """Start the event processing loop"""
        if self.running:
            return
            
        self.running = True
        self.processing_task = asyncio.create_task(self._process_events())
        self.logger.info("Event bus started")
        
    async def stop(self) -> None:
        """Stop the event processing loop"""
        self.running = False
        if self.processing_task:
            self.processing_task.cancel()
            try:
                await self.processing_task
            except asyncio.CancelledError:
                pass
        self.logger.info("Event bus stopped")
        
    def subscribe(self, event_type: EventType, module: BaseModule) -> None:
        """Subscribe a module to specific event types"""
        with self.lock:
            if module not in self.subscribers[event_type]:
                self.subscribers[event_type].append(module)
                self.logger.debug(f"Module {module.name} subscribed to {event_type.value}")
                
    def unsubscribe(self, event_type: EventType, module: BaseModule) -> None:
        """Unsubscribe a module from event types"""
        with self.lock:
            if module in self.subscribers[event_type]:
                self.subscribers[event_type].remove(module)
                self.logger.debug(f"Module {module.name} unsubscribed from {event_type.value}")
                
    def emit(self, event: Event) -> None:
        """Emit an event to be processed"""
        if not self.running:
            self.logger.warning("Event bus not running, dropping event")
            return
            
        with self.lock:
            self.event_queue.append(event)
            
    async def _process_events(self) -> None:
        """Main event processing loop"""
        while self.running:
            try:
                if not self.event_queue:
                    await asyncio.sleep(0.01)  # Small delay to prevent busy waiting
                    continue
                    
                with self.lock:
                    event = self.event_queue.popleft()
                    
                await self._handle_event(event)
                
            except Exception as e:
                self.logger.error(f"Error processing event: {e}")
                
    async def _handle_event(self, event: Event) -> None:
        """Handle a single event by dispatching to subscribers"""
        try:
            # Add to history
            self.event_history.append(event)
            
            # Get subscribers for this event type
            subscribers = self.subscribers.get(event.type, [])
            
            if not subscribers:
                self.logger.debug(f"No subscribers for event {event.type.value}")
                return
                
            # Process events by priority
            tasks = []
            for module in subscribers:
                if module.is_loaded:
                    task = asyncio.create_task(
                        self._safe_handle_event(module, event)
                    )
                    tasks.append(task)
                    
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
                
        except Exception as e:
            self.logger.error(f"Error handling event {event.type.value}: {e}")
            
    async def _safe_handle_event(self, module: BaseModule, event: Event) -> None:
        """Safely handle an event for a module with timeout"""
        try:
            # Timeout to prevent modules from blocking the bus
            await asyncio.wait_for(
                module.handle_event(event), 
                timeout=5.0
            )
        except asyncio.TimeoutError:
            self.logger.warning(f"Module {module.name} timed out handling {event.type.value}")
        except Exception as e:
            self.logger.error(f"Module {module.name} error handling {event.type.value}: {e}")
            
    def get_statistics(self) -> Dict[str, Any]:
        """Get event bus statistics"""
        with self.lock:
            return {
                "queue_size": len(self.event_queue),
                "total_subscribers": sum(len(subs) for subs in self.subscribers.values()),
                "event_types": len(self.subscribers),
                "running": self.running,
                "recent_events": len(self.event_history)
            }
            
    def get_recent_events(self, limit: int = 10) -> List[Event]:
        """Get recent events from history"""
        with self.lock:
            return list(self.event_history)[-limit:]