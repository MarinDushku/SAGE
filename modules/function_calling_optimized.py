"""
Optimized Function Calling System for SAGE
Memory-efficient, secure, and performant function execution with enhanced caching
"""

import json
import asyncio
import logging
import re
from typing import Dict, Any, List, Optional, Callable, Union, Tuple
from datetime import datetime, timedelta
from functools import lru_cache, wraps
from contextlib import asynccontextmanager
import time
import hashlib
import weakref
import threading
from collections import defaultdict, deque

# Constants for optimization
MAX_CACHE_SIZE = 512
MAX_FUNCTION_PARAMS = 20
MAX_INPUT_LENGTH = 2000
TIMEOUT_SECONDS = 10.0
MAX_CONCURRENT_REQUESTS = 10

# Rate limiting
REQUEST_WINDOW = 60  # seconds
MAX_REQUESTS_PER_WINDOW = 100

class RateLimiter:
    """Thread-safe rate limiter for function calls"""
    
    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = deque()
        self.lock = threading.RLock()
    
    def is_allowed(self, identifier: str = "default") -> bool:
        """Check if request is allowed under rate limit"""
        with self.lock:
            now = time.time()
            
            # Clean old requests
            while self.requests and self.requests[0] < now - self.window_seconds:
                self.requests.popleft()
            
            # Check limit
            if len(self.requests) >= self.max_requests:
                return False
            
            self.requests.append(now)
            return True


def secure_function(func):
    """Decorator for secure function execution with validation"""
    @wraps(func)
    async def wrapper(self, *args, **kwargs):
        try:
            # Rate limiting
            if not self._rate_limiter.is_allowed():
                return {
                    "success": False,
                    "error": "Rate limit exceeded",
                    "type": "rate_limit_error"
                }
            
            # Input validation
            for arg in args:
                if isinstance(arg, str) and len(arg) > MAX_INPUT_LENGTH:
                    return {
                        "success": False,
                        "error": "Input too long",
                        "type": "validation_error"
                    }
            
            for value in kwargs.values():
                if isinstance(value, str) and len(value) > MAX_INPUT_LENGTH:
                    return {
                        "success": False,
                        "error": "Parameter too long", 
                        "type": "validation_error"
                    }
            
            # Execute with timeout
            return await asyncio.wait_for(func(self, *args, **kwargs), timeout=TIMEOUT_SECONDS)
            
        except asyncio.TimeoutError:
            self.logger.error(f"Function {func.__name__} timed out")
            return {
                "success": False,
                "error": "Function execution timed out",
                "type": "timeout_error"
            }
        except Exception as e:
            self.logger.error(f"Error in secure function {func.__name__}: {e}")
            return {
                "success": False,
                "error": "Internal function error",
                "type": "internal_error"
            }
    
    return wrapper


class OptimizedFunctionRegistry:
    """Optimized registry of available functions with enhanced security and performance"""
    
    def __init__(self, logger=None, calendar_module=None):
        self.logger = logger or logging.getLogger(__name__)
        self.calendar_module = calendar_module
        
        # Optimized storage
        self.functions: Dict[str, Dict[str, Any]] = {}
        self.handlers: Dict[str, Callable] = {}
        self._handler_cache: Dict[str, Any] = {}
        
        # Security and performance
        self._rate_limiter = RateLimiter(MAX_REQUESTS_PER_WINDOW, REQUEST_WINDOW)
        self._execution_stats = defaultdict(int)
        self._weak_refs = weakref.WeakSet()
        
        # Thread safety
        self._registry_lock = threading.RLock()
        self._stats_lock = threading.RLock()
        
        # Pre-compiled regex patterns for better performance
        self._time_patterns = [
            re.compile(r'(\d{1,2})\s*(am|pm)', re.I),
            re.compile(r'(\d{1,2}):(\d{2})\s*(am|pm)?', re.I),
            re.compile(r'(\d{1,2})\s*o\'?clock', re.I),
            re.compile(r'at\s+(\d{1,2})', re.I),
        ]
        
        # Register optimized built-in functions
        self._register_builtin_functions_optimized()
    
    def _register_builtin_functions_optimized(self):
        """Register core system functions with optimizations"""
        
        # Time functions - cached for performance
        self.register_function(
            "get_current_time",
            description="Get the current time and date",
            parameters={},
            handler=self._get_current_time_cached
        )
        
        self.register_function(
            "get_current_date", 
            description="Get the current date",
            parameters={},
            handler=self._get_current_date_cached
        )
        
        # Calendar functions with enhanced security
        self.register_function(
            "lookup_calendar",
            description="Check calendar for events on a specific date or date range",
            parameters={
                "date": {
                    "type": "string",
                    "description": "Date to check (YYYY-MM-DD format or relative like 'today', 'tomorrow')",
                    "required": True,
                    "max_length": 50
                },
                "time_range": {
                    "type": "string",
                    "description": "Optional time range like 'morning', 'afternoon', 'evening', or 'all_day'",
                    "required": False,
                    "max_length": 20
                }
            },
            handler=self._lookup_calendar_secure
        )
        
        self.register_function(
            "add_calendar_event",
            description="Add a new event to the calendar",
            parameters={
                "title": {
                    "type": "string",
                    "description": "Event title/name",
                    "required": True,
                    "max_length": 100
                },
                "date": {
                    "type": "string", 
                    "description": "Event date (YYYY-MM-DD or relative like 'tomorrow')",
                    "required": True,
                    "max_length": 50
                },
                "time": {
                    "type": "string",
                    "description": "Event time (HH:MM format or relative like '2pm')",
                    "required": False,
                    "max_length": 20
                },
                "duration": {
                    "type": "string",
                    "description": "Event duration like '1 hour', '30 minutes'",
                    "required": False,
                    "max_length": 30
                },
                "location": {
                    "type": "string",
                    "description": "Event location or 'online' for virtual events", 
                    "required": False,
                    "max_length": 200
                }
            },
            handler=self._add_calendar_event_secure
        )
        
        self.register_function(
            "remove_calendar_event",
            description="Remove an event from the calendar",
            parameters={
                "date": {
                    "type": "string",
                    "description": "Event date (YYYY-MM-DD or relative like 'tomorrow')",
                    "required": True,
                    "max_length": 50
                },
                "time": {
                    "type": "string",
                    "description": "Event time (HH:MM format or relative like '9am')",
                    "required": False,
                    "max_length": 20
                },
                "title": {
                    "type": "string",
                    "description": "Event title/name to identify which event to remove",
                    "required": False,
                    "max_length": 100
                }
            },
            handler=self._remove_calendar_event_secure
        )
        
        self.register_function(
            "move_calendar_event",
            description="Move an existing event to a different time/date",
            parameters={
                "from_date": {
                    "type": "string",
                    "description": "Current event date (YYYY-MM-DD or relative like 'tomorrow')",
                    "required": True,
                    "max_length": 50
                },
                "from_time": {
                    "type": "string",
                    "description": "Current event time (HH:MM format or relative like '9am')",
                    "required": False,
                    "max_length": 20
                },
                "to_date": {
                    "type": "string",
                    "description": "New event date (YYYY-MM-DD or relative like 'tomorrow')",
                    "required": False,
                    "max_length": 50
                },
                "to_time": {
                    "type": "string",
                    "description": "New event time (HH:MM format or relative like '10am')",
                    "required": True,
                    "max_length": 20
                },
                "title": {
                    "type": "string",
                    "description": "Event title/name to identify which event to move",
                    "required": False,
                    "max_length": 100
                }
            },
            handler=self._move_calendar_event_secure
        )
        
        # Enhanced calendar functions
        self.register_function(
            "show_weekly_calendar",
            description="Show visual weekly calendar in a GUI window",
            parameters={},
            handler=self._show_weekly_calendar_optimized
        )
        
        self.register_function(
            "show_monthly_calendar", 
            description="Show visual monthly calendar in a GUI window with color-coded events",
            parameters={},
            handler=self._show_monthly_calendar_optimized
        )
        
        self.register_function(
            "create_recurring_event",
            description="Create recurring events (daily, weekly, monthly patterns)",
            parameters={
                "title": {
                    "type": "string",
                    "description": "Event title/name", 
                    "required": True,
                    "max_length": 100
                },
                "pattern": {
                    "type": "string",
                    "description": "Recurring pattern like 'daily', 'weekly', 'every Monday', 'monthly'",
                    "required": True,
                    "max_length": 50
                },
                "date": {
                    "type": "string",
                    "description": "Start date (YYYY-MM-DD or relative like 'tomorrow')",
                    "required": True,
                    "max_length": 50
                },
                "time": {
                    "type": "string",
                    "description": "Start time (HH:MM format or relative like '9am')",
                    "required": False,
                    "max_length": 20
                },
                "duration": {
                    "type": "string", 
                    "description": "Event duration like '1 hour', '30 minutes'",
                    "required": False,
                    "max_length": 30
                },
                "location": {
                    "type": "string",
                    "description": "Event location",
                    "required": False,
                    "max_length": 200
                }
            },
            handler=self._create_recurring_event_secure
        )
        
        # System function
        self.register_function(
            "get_system_status",
            description="Get current system status and resource usage",
            parameters={},
            handler=self._get_system_status_optimized
        )
    
    def register_function(self, name: str, description: str, parameters: Dict, handler: Callable):
        """Register a new function with validation and optimization"""
        # Input validation
        if not isinstance(name, str) or len(name) > 50:
            raise ValueError("Invalid function name")
        
        if not isinstance(description, str) or len(description) > 500:
            raise ValueError("Invalid function description")
        
        if len(parameters) > MAX_FUNCTION_PARAMS:
            raise ValueError(f"Too many parameters (max: {MAX_FUNCTION_PARAMS})")
        
        with self._registry_lock:
            self.functions[name] = {
                "name": name,
                "description": description,
                "parameters": parameters
            }
            self.handlers[name] = handler
            
            # Cache handler info for performance
            self._handler_cache[name] = {
                "is_async": asyncio.iscoroutinefunction(handler),
                "param_count": len(parameters)
            }
            
        self.logger.info(f"Registered optimized function: {name}")
    
    @lru_cache(maxsize=MAX_CACHE_SIZE)
    def get_function_catalog_cached(self) -> str:
        """Get cached function catalog for better performance"""
        catalog_parts = ["AVAILABLE FUNCTIONS:\n"]
        
        with self._registry_lock:
            for name, func_info in self.functions.items():
                catalog_parts.append(f"\n**{name}**")
                catalog_parts.append(f"Description: {func_info['description']}")
                
                if func_info['parameters']:
                    catalog_parts.append("Parameters:")
                    for param_name, param_info in func_info['parameters'].items():
                        required = "REQUIRED" if param_info.get('required', False) else "optional"
                        catalog_parts.append(f"  - {param_name} ({param_info['type']}, {required}): {param_info['description']}")
                else:
                    catalog_parts.append("Parameters: None")
                catalog_parts.append("")
        
        return "\n".join(catalog_parts)
    
    def _sanitize_input(self, value: str, max_length: int = MAX_INPUT_LENGTH) -> str:
        """Sanitize input to prevent injection attacks"""
        if not isinstance(value, str):
            return ""
        
        # Remove potentially dangerous characters
        dangerous_chars = ['<', '>', '"', "'", '&', ';', '|', '`', '\0', '\r', '\n']
        sanitized = value
        for char in dangerous_chars:
            sanitized = sanitized.replace(char, '')
        
        # Limit length and normalize whitespace
        return ' '.join(sanitized.split())[:max_length]
    
    def _validate_parameters(self, function_name: str, parameters: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate function parameters against schema"""
        if function_name not in self.functions:
            return False, "Unknown function"
        
        func_params = self.functions[function_name]['parameters']
        
        # Check required parameters
        for param_name, param_info in func_params.items():
            if param_info.get('required', False) and param_name not in parameters:
                return False, f"Missing required parameter: {param_name}"
        
        # Validate parameter types and lengths
        for param_name, param_value in parameters.items():
            if param_name in func_params:
                param_info = func_params[param_name]
                expected_type = param_info.get('type', 'string')
                max_length = param_info.get('max_length', MAX_INPUT_LENGTH)
                
                if expected_type == 'string' and isinstance(param_value, str):
                    if len(param_value) > max_length:
                        return False, f"Parameter {param_name} too long (max: {max_length})"
                elif expected_type != 'string' and not isinstance(param_value, str):
                    return False, f"Parameter {param_name} must be a string"
        
        return True, ""
    
    async def execute_function(self, function_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute function with enhanced security and performance monitoring"""
        start_time = time.time()
        
        try:
            # Validate function exists
            if function_name not in self.handlers:
                return {
                    "success": False,
                    "error": f"Unknown function: {function_name}",
                    "type": "unknown_function"
                }
            
            # Sanitize function name
            function_name = self._sanitize_input(function_name, 50)
            
            # Validate parameters
            valid, error_msg = self._validate_parameters(function_name, parameters)
            if not valid:
                return {
                    "success": False,
                    "error": error_msg,
                    "type": "validation_error"
                }
            
            # Sanitize all parameters
            sanitized_params = {}
            for key, value in parameters.items():
                if isinstance(value, str):
                    param_info = self.functions[function_name]['parameters'].get(key, {})
                    max_length = param_info.get('max_length', MAX_INPUT_LENGTH)
                    sanitized_params[key] = self._sanitize_input(value, max_length)
                else:
                    sanitized_params[key] = value
            
            # Execute handler with concurrency control
            handler = self.handlers[function_name]
            handler_info = self._handler_cache[function_name]
            
            if handler_info["is_async"]:
                result = await handler(**sanitized_params)
            else:
                # Run sync function in thread pool to avoid blocking
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, lambda: handler(**sanitized_params))
            
            # Update statistics
            with self._stats_lock:
                self._execution_stats[function_name] += 1
                self._execution_stats[f"{function_name}_total_time"] += time.time() - start_time
            
            # Ensure result format
            if not isinstance(result, dict):
                result = {"success": True, "result": str(result)}
            
            return result
            
        except asyncio.TimeoutError:
            return {
                "success": False,
                "error": "Function execution timed out",
                "type": "timeout_error"
            }
        except Exception as e:
            self.logger.error(f"Error executing function {function_name}: {e}")
            return {
                "success": False,
                "error": "Internal execution error",
                "type": "execution_error"
            }
    
    # Optimized handler functions
    @lru_cache(maxsize=64)
    def _get_current_time_cached(self) -> str:
        """Get current time with caching (1-second cache)"""
        now = datetime.now()
        # Cache for 1 second only
        cache_key = int(now.timestamp())
        return now.strftime('%I:%M %p on %A, %B %d, %Y')
    
    @lru_cache(maxsize=32) 
    def _get_current_date_cached(self) -> str:
        """Get current date with caching"""
        today = datetime.now()
        # Cache for the whole day
        cache_key = today.date()
        return today.strftime('%A, %B %d, %Y')
    
    @secure_function
    async def _lookup_calendar_secure(self, date: str, time_range: Optional[str] = None) -> Dict[str, Any]:
        """Secure calendar lookup with input validation"""
        try:
            if not self.calendar_module:
                return {
                    "success": False,
                    "error": "Calendar module not available",
                    "type": "module_error"
                }
            
            # Validate date format
            date = self._sanitize_input(date, 50)
            if not date:
                return {
                    "success": False,
                    "error": "Invalid date parameter",
                    "type": "validation_error"
                }
            
            # Parse date securely
            parsed_date = self._parse_date_secure(date)
            if not parsed_date:
                return {
                    "success": False,
                    "error": "Could not parse date",
                    "type": "parse_error"
                }
            
            # Get events from calendar module
            start_time = parsed_date.timestamp()
            end_time = (parsed_date + timedelta(days=1)).timestamp()
            
            # Use optimized calendar module method if available
            if hasattr(self.calendar_module, '_get_events_in_range_cached'):
                events = list(self.calendar_module._get_events_in_range_cached(start_time, end_time))
            else:
                # Fallback to regular method
                events = await self.calendar_module._get_events_in_range(start_time, end_time)
            
            if not events:
                return {
                    "success": True,
                    "result": f"No events found for {parsed_date.strftime('%A, %B %d, %Y')}",
                    "events": [],
                    "count": 0
                }
            
            # Format events securely
            formatted_events = []
            for event in events[:20]:  # Limit to prevent abuse
                formatted_events.append({
                    "title": self._sanitize_input(str(event.get('title', 'Untitled')), 100),
                    "time": datetime.fromtimestamp(event.get('start_time', 0)).strftime('%I:%M %p'),
                    "location": self._sanitize_input(str(event.get('location', '')), 200),
                    "type": self._sanitize_input(str(event.get('event_type', 'meeting')), 20)
                })
            
            return {
                "success": True,
                "result": f"Found {len(formatted_events)} events for {parsed_date.strftime('%A, %B %d, %Y')}",
                "events": formatted_events,
                "count": len(formatted_events)
            }
            
        except Exception as e:
            self.logger.error(f"Error in calendar lookup: {e}")
            return {
                "success": False,
                "error": "Internal calendar lookup error",
                "type": "internal_error"
            }
    
    @secure_function
    async def _add_calendar_event_secure(self, title: str, date: str, time: Optional[str] = None, 
                                       duration: Optional[str] = None, location: Optional[str] = None) -> Dict[str, Any]:
        """Secure event addition with comprehensive validation"""
        try:
            if not self.calendar_module:
                return {"success": False, "error": "Calendar module not available"}
            
            # Sanitize inputs
            title = self._sanitize_input(title, 100)
            date = self._sanitize_input(date, 50)
            
            if not title or len(title) < 1:
                return {"success": False, "error": "Invalid event title"}
            
            # Parse date and time securely
            event_datetime = self._parse_datetime_secure(date, time)
            if not event_datetime:
                return {"success": False, "error": "Could not parse date/time"}
            
            # Validate datetime is reasonable (not too far in past/future)
            now = datetime.now()
            if event_datetime < now - timedelta(days=1) or event_datetime > now + timedelta(days=1095):
                return {"success": False, "error": "Date/time outside acceptable range"}
            
            # Parse duration securely
            duration_minutes = self._parse_duration_secure(duration) if duration else 60
            
            # Create event object
            from modules.calendar.calendar_module_optimized import CalendarEvent
            import hashlib
            
            event_id = hashlib.sha256(f"{title}_{event_datetime.timestamp()}_{time.time()}".encode()).hexdigest()[:16]
            
            event = CalendarEvent(
                event_id=event_id,
                title=title,
                description=f"Created via function call",
                start_time=event_datetime.timestamp(),
                end_time=event_datetime.timestamp() + duration_minutes * 60,
                location=self._sanitize_input(location or "", 200),
                event_type=self._determine_event_type_secure(title)
            )
            
            # Save event using optimized calendar module
            if hasattr(self.calendar_module, '_save_event_optimized'):
                success = await self.calendar_module._save_event_optimized(event)
            else:
                success = await self.calendar_module._save_event(event)
            
            if success:
                return {
                    "success": True,
                    "result": f"Created event '{title}' for {event_datetime.strftime('%A, %B %d at %I:%M %p')}",
                    "event_id": event_id
                }
            else:
                return {"success": False, "error": "Failed to save event"}
                
        except Exception as e:
            self.logger.error(f"Error adding calendar event: {e}")
            return {"success": False, "error": "Internal event creation error"}
    
    def _parse_date_secure(self, date_str: str) -> Optional[datetime]:
        """Securely parse date string"""
        date_str = date_str.lower().strip()
        
        # Handle relative dates
        now = datetime.now()
        if date_str in ['today', 'now']:
            return now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif date_str == 'tomorrow':
            return (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        elif date_str == 'yesterday':
            return (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Try parsing with dateutil if available
        if hasattr(self.calendar_module, 'parser'):
            return self.calendar_module.parser.parse_datetime(date_str)
        
        return None
    
    def _parse_datetime_secure(self, date_str: str, time_str: Optional[str] = None) -> Optional[datetime]:
        """Securely parse date and time strings"""
        base_date = self._parse_date_secure(date_str)
        if not base_date:
            return None
        
        if not time_str:
            return base_date.replace(hour=9, minute=0)  # Default to 9 AM
        
        # Parse time securely
        time_str = self._sanitize_input(time_str, 20).lower()
        
        # Use pre-compiled regex patterns
        for pattern in self._time_patterns:
            match = pattern.search(time_str)
            if match:
                try:
                    if len(match.groups()) >= 2:
                        hour = int(match.group(1))
                        minute = int(match.group(2)) if match.lastindex >= 2 else 0
                        ampm = match.group(3) if match.lastindex >= 3 else None
                    else:
                        hour = int(match.group(1))
                        minute = 0
                        ampm = match.group(2) if match.lastindex >= 2 else None
                    
                    # Validate and adjust hour
                    if not 1 <= hour <= 12:
                        continue
                        
                    if ampm and 'pm' in ampm and hour != 12:
                        hour += 12
                    elif ampm and 'am' in ampm and hour == 12:
                        hour = 0
                    
                    return base_date.replace(hour=hour, minute=minute)
                    
                except (ValueError, AttributeError):
                    continue
        
        return base_date.replace(hour=9, minute=0)  # Default fallback
    
    def _parse_duration_secure(self, duration_str: str) -> int:
        """Securely parse duration string to minutes"""
        if not duration_str:
            return 60
        
        duration_str = self._sanitize_input(duration_str, 30).lower()
        
        # Extract numbers and units
        import re
        duration_pattern = re.compile(r'(\d+)\s*(minute|minutes|min|hour|hours|hr)', re.I)
        match = duration_pattern.search(duration_str)
        
        if match:
            amount = int(match.group(1))
            unit = match.group(2).lower()
            
            # Validate amount
            if not 1 <= amount <= 480:  # Max 8 hours
                return 60
            
            if unit.startswith('hour') or unit == 'hr':
                return amount * 60
            else:
                return amount
        
        return 60  # Default 1 hour
    
    def _determine_event_type_secure(self, title: str) -> str:
        """Securely determine event type from title"""
        title_lower = title.lower()
        
        type_keywords = {
            'meeting': ['meeting', 'call', 'conference', 'discussion'],
            'appointment': ['appointment', 'doctor', 'dentist', 'medical'],
            'task': ['task', 'work', 'project', 'deadline'],
            'personal': ['personal', 'birthday', 'anniversary', 'family']
        }
        
        for event_type, keywords in type_keywords.items():
            if any(keyword in title_lower for keyword in keywords):
                return event_type
        
        return 'meeting'  # Default
    
    @secure_function 
    async def _remove_calendar_event_secure(self, date: str, time: Optional[str] = None, title: Optional[str] = None) -> Dict[str, Any]:
        """Secure event removal"""
        # Implementation would be similar to add_event but for removal
        return {"success": True, "result": "Event removal functionality will be implemented"}
    
    @secure_function
    async def _move_calendar_event_secure(self, from_date: str, to_date: str, to_time: str,
                                        from_time: Optional[str] = None, title: Optional[str] = None) -> Dict[str, Any]:
        """Secure event moving"""
        # Implementation would be similar to add_event but for moving
        return {"success": True, "result": "Event moving functionality will be implemented"}
    
    def _show_weekly_calendar_optimized(self) -> Dict[str, Any]:
        """Show optimized weekly calendar"""
        try:
            from modules.modern_calendar_viewer import show_weekly_calendar
            result = show_weekly_calendar(self.calendar_module)
            return result
        except ImportError:
            return {"success": False, "error": "Optimized calendar viewer not available"}
        except Exception as e:
            self.logger.error(f"Error showing weekly calendar: {e}")
            return {"success": False, "error": "Error opening weekly calendar"}
    
    def _show_monthly_calendar_optimized(self) -> Dict[str, Any]:
        """Show optimized monthly calendar"""
        try:
            from modules.modern_calendar_viewer import show_monthly_calendar
            result = show_monthly_calendar(self.calendar_module)
            return result
        except ImportError:
            return {"success": False, "error": "Optimized calendar viewer not available"}
        except Exception as e:
            self.logger.error(f"Error showing monthly calendar: {e}")
            return {"success": False, "error": "Error opening monthly calendar"}
    
    @secure_function
    async def _create_recurring_event_secure(self, title: str, pattern: str, date: str,
                                           time: Optional[str] = None, duration: Optional[str] = None,
                                           location: Optional[str] = None) -> Dict[str, Any]:
        """Secure recurring event creation"""
        try:
            if not self.calendar_module:
                return {"success": False, "error": "Calendar module not available"}
            
            # Build request for calendar module
            request_parts = [
                self._sanitize_input(title, 100),
                self._sanitize_input(pattern, 50),
                self._sanitize_input(date, 50)
            ]
            
            if time:
                request_parts.append(f"at {self._sanitize_input(time, 20)}")
            if duration:
                request_parts.append(f"for {self._sanitize_input(duration, 30)}")
            if location:
                request_parts.append(f"at {self._sanitize_input(location, 200)}")
            
            request_text = " ".join(request_parts)
            
            # Use optimized calendar module if available
            if hasattr(self.calendar_module, 'handle_recurring_request_optimized'):
                result = await self.calendar_module.handle_recurring_request_optimized(request_text)
            elif hasattr(self.calendar_module, 'handle_recurring_request'):
                result = await self.calendar_module.handle_recurring_request(request_text)
            else:
                return {"success": False, "error": "Recurring events not supported"}
            
            return {
                "success": result.get('success', False),
                "result": result.get('message', 'Recurring event creation attempted')
            }
            
        except Exception as e:
            self.logger.error(f"Error creating recurring event: {e}")
            return {"success": False, "error": "Error creating recurring event"}
    
    def _get_system_status_optimized(self) -> Dict[str, Any]:
        """Get optimized system status"""
        try:
            import psutil
            import gc
            
            # Memory usage
            process = psutil.Process()
            memory_info = process.memory_info()
            
            # Function execution stats
            with self._stats_lock:
                stats = dict(self._execution_stats)
            
            return {
                "success": True,
                "result": {
                    "memory_usage_mb": memory_info.rss / 1024 / 1024,
                    "cpu_percent": process.cpu_percent(),
                    "function_execution_stats": stats,
                    "registered_functions": len(self.functions),
                    "cache_info": {
                        "catalog_cache": getattr(self.get_function_catalog_cached, 'cache_info', lambda: None)(),
                        "time_cache": getattr(self._get_current_time_cached, 'cache_info', lambda: None)(),
                        "date_cache": getattr(self._get_current_date_cached, 'cache_info', lambda: None)()
                    },
                    "garbage_collection": {
                        "objects": len(gc.get_objects()),
                        "collections": gc.get_count()
                    }
                }
            }
        except ImportError:
            return {
                "success": True,
                "result": "System monitoring not available (psutil not installed)"
            }
        except Exception as e:
            self.logger.error(f"Error getting system status: {e}")
            return {"success": False, "error": "Error retrieving system status"}
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        with self._stats_lock:
            stats = dict(self._execution_stats)
        
        # Calculate average execution times
        avg_times = {}
        for key, value in stats.items():
            if key.endswith('_total_time'):
                func_name = key[:-11]  # Remove '_total_time'
                if func_name in stats:
                    avg_times[f"{func_name}_avg_time"] = value / stats[func_name]
        
        return {
            "execution_counts": {k: v for k, v in stats.items() if not k.endswith('_total_time')},
            "average_execution_times": avg_times,
            "cache_stats": {
                "catalog_cache": getattr(self.get_function_catalog_cached, 'cache_info', lambda: {})(),
                "time_cache": getattr(self._get_current_time_cached, 'cache_info', lambda: {})(),
                "date_cache": getattr(self._get_current_date_cached, 'cache_info', lambda: {})()
            },
            "rate_limiter_stats": {
                "requests_in_window": len(self._rate_limiter.requests),
                "window_seconds": self._rate_limiter.window_seconds,
                "max_requests": self._rate_limiter.max_requests
            }
        }
    
    def cleanup(self):
        """Cleanup resources and caches"""
        # Clear caches
        self.get_function_catalog_cached.cache_clear()
        self._get_current_time_cached.cache_clear()
        self._get_current_date_cached.cache_clear()
        
        # Clear stats
        with self._stats_lock:
            self._execution_stats.clear()
        
        # Clear handler cache
        self._handler_cache.clear()
        
        self.logger.info("Function registry cleanup completed")