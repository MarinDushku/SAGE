"""
Event Bus - Central message passing system for SAGE modules
"""

import asyncio
from typing import Dict, List, Callable, Any, Optional, Set
from collections import defaultdict, deque
import time
import logging
from threading import Lock
import heapq
import pickle
from pathlib import Path
from dataclasses import dataclass, field

from modules import Event, EventType, BaseModule


@dataclass
class EventFilter:
    """Filter for event routing"""
    event_types: Set[EventType] = field(default_factory=set)
    source_modules: Set[str] = field(default_factory=set)
    min_priority: int = 1
    max_priority: int = 10
    
    def matches(self, event: Event) -> bool:
        """Check if event matches this filter"""
        if self.event_types and event.type not in self.event_types:
            return False
        if self.source_modules and event.source_module not in self.source_modules:
            return False
        if not (self.min_priority <= event.priority <= self.max_priority):
            return False
        return True


@dataclass
class PriorityEvent:
    """Event wrapper for priority queue"""
    priority: int
    timestamp: float
    event: Event
    
    def __lt__(self, other):
        # Higher priority first, then by timestamp (older first)
        if self.priority != other.priority:
            return self.priority > other.priority
        return self.timestamp < other.timestamp


class EventBus:
    """Enhanced async event bus for inter-module communication"""
    
    def __init__(self, 
                 max_queue_size: int = 1000,
                 persistence_dir: Optional[str] = None,
                 enable_persistence: bool = False):
        # Core components
        self.subscribers: Dict[EventType, List[BaseModule]] = defaultdict(list)
        self.event_queue: List[PriorityEvent] = []  # Priority queue
        self.event_history: deque = deque(maxlen=100)
        self.running = False
        self.processing_task: Optional[asyncio.Task] = None
        self.lock = Lock()
        self.logger = logging.getLogger(__name__)
        
        # Configuration
        self.max_queue_size = max_queue_size
        self.enable_persistence = enable_persistence
        self.persistence_dir = Path(persistence_dir) if persistence_dir else None
        
        # Event filtering and routing
        self.filters: Dict[str, EventFilter] = {}  # filter_name -> filter
        self.filtered_subscribers: Dict[str, List[BaseModule]] = defaultdict(list)
        
        # Performance tracking
        self.stats = {
            "events_processed": 0,
            "events_dropped": 0,
            "avg_processing_time": 0.0,
            "high_priority_events": 0,
            "filtered_events": 0
        }
        
        # Setup persistence if enabled
        if self.enable_persistence and self.persistence_dir:
            self.persistence_dir.mkdir(parents=True, exist_ok=True)
            self._load_persistent_events()
        
    async def start(self) -> None:
        """Start the event processing loop"""
        if self.running:
            return
            
        self.running = True
        self._start_time = time.time()
        self.processing_task = asyncio.create_task(self._process_events())
        self.logger.info("Enhanced event bus started with priority handling")
        
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
        """Emit an event to be processed with priority handling"""
        if not self.running:
            self.logger.warning("Event bus not running, dropping event")
            self.stats["events_dropped"] += 1
            return
            
        with self.lock:
            # Check queue size limit
            if len(self.event_queue) >= self.max_queue_size:
                # Drop lowest priority event if queue is full
                if self.event_queue and self.event_queue[0].priority < event.priority:
                    dropped = heapq.heappop(self.event_queue)
                    self.logger.warning(f"Dropped low priority event: {dropped.event.type.value}")
                    self.stats["events_dropped"] += 1
                else:
                    self.logger.warning(f"Queue full, dropping event: {event.type.value}")
                    self.stats["events_dropped"] += 1
                    return
            
            # Create priority event and add to queue
            priority_event = PriorityEvent(
                priority=event.priority,
                timestamp=event.timestamp,
                event=event
            )
            
            heapq.heappush(self.event_queue, priority_event)
            
            # Track high priority events
            if event.priority >= 8:
                self.stats["high_priority_events"] += 1
                
            # Persist critical events
            if self.enable_persistence and event.priority >= 9:
                self._persist_event(event)
            
    async def _process_events(self) -> None:
        """Enhanced event processing loop with priority handling"""
        while self.running:
            try:
                # Try to get an event from the queue
                with self.lock:
                    if not self.event_queue:
                        # Queue is empty, sleep and continue
                        pass
                    else:
                        priority_event = heapq.heappop(self.event_queue)
                        event = priority_event.event
                        
                        # Track processing time
                        start_time = time.time()
                        await self._handle_event(event)
                        processing_time = time.time() - start_time
                        
                        # Update statistics
                        self.stats["events_processed"] += 1
                        self.stats["avg_processing_time"] = (
                            (self.stats["avg_processing_time"] * (self.stats["events_processed"] - 1) + processing_time) 
                            / self.stats["events_processed"]
                        )
                        continue  # Process next event immediately
                
                # If we get here, queue was empty
                await asyncio.sleep(0.01)  # Wait a bit before checking again
                
            except Exception as e:
                self.logger.error(f"Error processing event: {e}")
                await asyncio.sleep(0.01)
                
    async def _handle_event(self, event: Event) -> None:
        """Enhanced event handling with filtering and routing"""
        try:
            # Add to history
            self.event_history.append(event)
            
            # Get regular subscribers
            subscribers = self.subscribers.get(event.type, [])
            
            # Get filtered subscribers
            filtered_subscribers = []
            for filter_name, event_filter in self.filters.items():
                if event_filter.matches(event):
                    filtered_subscribers.extend(self.filtered_subscribers[filter_name])
                    self.stats["filtered_events"] += 1
            
            # Combine all subscribers (remove duplicates)
            all_subscribers = list(set(subscribers + filtered_subscribers))
            
            if not all_subscribers:
                self.logger.debug(f"No subscribers for event {event.type.value}")
                return
                
            # Create tasks for all subscribers
            tasks = []
            for module in all_subscribers:
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
            
    def add_filter(self, name: str, event_filter: EventFilter) -> None:
        """Add an event filter for routing"""
        with self.lock:
            self.filters[name] = event_filter
            self.logger.info(f"Added event filter: {name}")
            
    def remove_filter(self, name: str) -> None:
        """Remove an event filter"""
        with self.lock:
            if name in self.filters:
                del self.filters[name]
                if name in self.filtered_subscribers:
                    del self.filtered_subscribers[name]
                self.logger.info(f"Removed event filter: {name}")
                
    def subscribe_with_filter(self, filter_name: str, module: BaseModule) -> None:
        """Subscribe a module to events matching a filter"""
        with self.lock:
            if filter_name in self.filters:
                if module not in self.filtered_subscribers[filter_name]:
                    self.filtered_subscribers[filter_name].append(module)
                    self.logger.debug(f"Module {module.name} subscribed to filter {filter_name}")
            else:
                self.logger.warning(f"Filter {filter_name} not found")
                
    def _persist_event(self, event: Event) -> None:
        """Persist a critical event to disk"""
        if not self.persistence_dir:
            return
            
        try:
            filename = f"critical_event_{int(event.timestamp)}_{event.type.value}.pkl"
            filepath = self.persistence_dir / filename
            
            with open(filepath, 'wb') as f:
                pickle.dump(event, f)
                
            self.logger.debug(f"Persisted critical event: {event.type.value}")
            
        except Exception as e:
            self.logger.error(f"Failed to persist event: {e}")
            
    def _load_persistent_events(self) -> None:
        """Load persisted events on startup"""
        if not self.persistence_dir or not self.persistence_dir.exists():
            return
            
        try:
            for filepath in self.persistence_dir.glob("critical_event_*.pkl"):
                try:
                    with open(filepath, 'rb') as f:
                        event = pickle.load(f)
                        
                    # Re-emit the event if it's recent (within 1 hour)
                    if time.time() - event.timestamp < 3600:
                        self.emit(event)
                        self.logger.info(f"Restored critical event: {event.type.value}")
                    
                    # Clean up old event files
                    filepath.unlink()
                    
                except Exception as e:
                    self.logger.error(f"Failed to load persistent event {filepath}: {e}")
                    
        except Exception as e:
            self.logger.error(f"Failed to load persistent events: {e}")
            
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get detailed performance metrics"""
        with self.lock:
            return {
                "events_processed": self.stats["events_processed"],
                "events_dropped": self.stats["events_dropped"],
                "avg_processing_time_ms": self.stats["avg_processing_time"] * 1000,
                "high_priority_events": self.stats["high_priority_events"],
                "filtered_events": self.stats["filtered_events"],
                "queue_utilization": len(self.event_queue) / self.max_queue_size * 100,
                "throughput_eps": self.stats["events_processed"] / max(time.time() - getattr(self, '_start_time', time.time()), 1)
            }
            
    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive event bus statistics"""
        with self.lock:
            return {
                "queue_size": len(self.event_queue),
                "max_queue_size": self.max_queue_size,
                "total_subscribers": sum(len(subs) for subs in self.subscribers.values()),
                "filtered_subscribers": sum(len(subs) for subs in self.filtered_subscribers.values()),
                "event_types": len(self.subscribers),
                "active_filters": len(self.filters),
                "running": self.running,
                "recent_events": len(self.event_history),
                "persistence_enabled": self.enable_persistence,
                **self.get_performance_metrics()
            }
            
    def get_recent_events(self, limit: int = 10) -> List[Event]:
        """Get recent events from history"""
        with self.lock:
            return list(self.event_history)[-limit:]
            
    def get_queue_status(self) -> Dict[str, Any]:
        """Get current queue status with priority breakdown"""
        with self.lock:
            if not self.event_queue:
                return {"empty": True, "priority_breakdown": {}}
                
            priority_counts = {}
            for priority_event in self.event_queue:
                priority = priority_event.priority
                priority_counts[priority] = priority_counts.get(priority, 0) + 1
                
            return {
                "empty": False,
                "total_events": len(self.event_queue),
                "next_priority": self.event_queue[0].priority if self.event_queue else None,
                "priority_breakdown": priority_counts
            }
            
    async def flush_queue(self) -> int:
        """Process all queued events immediately"""
        events_processed = 0
        
        while self.event_queue and self.running:
            try:
                with self.lock:
                    priority_event = heapq.heappop(self.event_queue)
                    event = priority_event.event
                    
                await self._handle_event(event)
                events_processed += 1
                
            except IndexError:
                break
            except Exception as e:
                self.logger.error(f"Error during queue flush: {e}")
                break
                
        self.logger.info(f"Flushed {events_processed} events from queue")
        return events_processed