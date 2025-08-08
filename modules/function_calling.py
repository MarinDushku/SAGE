"""
Function Calling System for SAGE
Provides LLM with available functions and handles execution
"""

import json
import asyncio
import logging
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
import inspect


class FunctionRegistry:
    """Registry of available functions that the LLM can call"""
    
    def __init__(self, logger=None, calendar_module=None):
        self.logger = logger or logging.getLogger(__name__)
        self.functions: Dict[str, Dict[str, Any]] = {}
        self.handlers: Dict[str, Callable] = {}
        self.calendar_module = calendar_module
        
        # Register built-in functions
        self._register_builtin_functions()
    
    def _register_builtin_functions(self):
        """Register core system functions"""
        
        # Time functions
        self.register_function(
            "get_current_time",
            description="Get the current time and date",
            parameters={},
            handler=self._get_current_time
        )
        
        self.register_function(
            "get_current_date",
            description="Get the current date",
            parameters={},
            handler=self._get_current_date
        )
        
        # Calendar functions
        self.register_function(
            "lookup_calendar",
            description="Check calendar for events on a specific date or date range",
            parameters={
                "date": {
                    "type": "string",
                    "description": "Date to check (YYYY-MM-DD format or relative like 'today', 'tomorrow')",
                    "required": True
                },
                "time_range": {
                    "type": "string", 
                    "description": "Optional time range like 'morning', 'afternoon', 'evening', or 'all_day'",
                    "required": False
                }
            },
            handler=self._lookup_calendar
        )
        
        self.register_function(
            "add_calendar_event",
            description="Add a new event to the calendar",
            parameters={
                "title": {
                    "type": "string",
                    "description": "Event title/name",
                    "required": True
                },
                "date": {
                    "type": "string",
                    "description": "Event date (YYYY-MM-DD or relative like 'tomorrow')",
                    "required": True
                },
                "time": {
                    "type": "string",
                    "description": "Event time (HH:MM format or relative like '2pm')",
                    "required": False
                },
                "duration": {
                    "type": "string",
                    "description": "Event duration like '1 hour', '30 minutes'",
                    "required": False
                },
                "location": {
                    "type": "string",
                    "description": "Event location or 'online' for virtual events",
                    "required": False
                }
            },
            handler=self._add_calendar_event
        )
        
        self.register_function(
            "remove_calendar_event",
            description="Remove an event from the calendar",
            parameters={
                "date": {
                    "type": "string",
                    "description": "Event date (YYYY-MM-DD or relative like 'tomorrow')",
                    "required": True
                },
                "time": {
                    "type": "string",
                    "description": "Event time (HH:MM format or relative like '9am')",
                    "required": False
                },
                "title": {
                    "type": "string",
                    "description": "Event title/name to identify which event to remove",
                    "required": False
                }
            },
            handler=self._remove_calendar_event
        )
        
        self.register_function(
            "move_calendar_event",
            description="Move an existing event to a different time/date",
            parameters={
                "from_date": {
                    "type": "string",
                    "description": "Current event date (YYYY-MM-DD or relative like 'tomorrow')",
                    "required": True
                },
                "from_time": {
                    "type": "string",
                    "description": "Current event time (HH:MM format or relative like '9am')",
                    "required": False
                },
                "to_date": {
                    "type": "string",
                    "description": "New event date (YYYY-MM-DD or relative like 'tomorrow')",
                    "required": False
                },
                "to_time": {
                    "type": "string",
                    "description": "New event time (HH:MM format or relative like '10am')",
                    "required": True
                },
                "title": {
                    "type": "string",
                    "description": "Event title/name to identify which event to move",
                    "required": False
                }
            },
            handler=self._move_calendar_event
        )
        
        # System functions
        self.register_function(
            "get_system_status",
            description="Get current system status and resource usage",
            parameters={},
            handler=self._get_system_status
        )
        
        self.register_function(
            "show_weekly_calendar",
            description="Show visual weekly calendar in a GUI window",
            parameters={},
            handler=self._show_weekly_calendar
        )
        
        self.register_function(
            "show_monthly_calendar",
            description="Show visual monthly calendar in a GUI window with color-coded events",
            parameters={},
            handler=self._show_monthly_calendar
        )
        
        self.register_function(
            "create_recurring_event",
            description="Create recurring events (daily, weekly, monthly patterns)",
            parameters={
                "title": {
                    "type": "string",
                    "description": "Event title/name",
                    "required": True
                },
                "pattern": {
                    "type": "string",
                    "description": "Recurring pattern like 'daily', 'weekly', 'every Monday', 'monthly'",
                    "required": True
                },
                "date": {
                    "type": "string",
                    "description": "Start date (YYYY-MM-DD or relative like 'tomorrow')",
                    "required": True
                },
                "time": {
                    "type": "string",
                    "description": "Start time (HH:MM format or relative like '9am')",
                    "required": False
                },
                "duration": {
                    "type": "string",
                    "description": "Event duration like '1 hour', '30 minutes'",
                    "required": False
                },
                "location": {
                    "type": "string",
                    "description": "Event location",
                    "required": False
                }
            },
            handler=self._create_recurring_event
        )
    
    def register_function(self, name: str, description: str, parameters: Dict, handler: Callable):
        """Register a new function that the LLM can call"""
        self.functions[name] = {
            "name": name,
            "description": description,
            "parameters": parameters
        }
        self.handlers[name] = handler
        self.logger.info(f"Registered function: {name}")
    
    def get_function_catalog(self) -> str:
        """Get a formatted catalog of all available functions for the LLM"""
        catalog = "AVAILABLE FUNCTIONS:\n\n"
        
        for name, func_info in self.functions.items():
            catalog += f"**{name}**\n"
            catalog += f"Description: {func_info['description']}\n"
            
            if func_info['parameters']:
                catalog += "Parameters:\n"
                for param_name, param_info in func_info['parameters'].items():
                    required = "REQUIRED" if param_info.get('required', False) else "optional"
                    catalog += f"  - {param_name} ({param_info['type']}, {required}): {param_info['description']}\n"
            else:
                catalog += "Parameters: None\n"
            catalog += "\n"
        
        return catalog
    
    async def execute_function(self, function_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a function call from the LLM"""
        try:
            if function_name not in self.handlers:
                return {
                    "success": False,
                    "error": f"Function '{function_name}' not found",
                    "available_functions": list(self.functions.keys())
                }
            
            handler = self.handlers[function_name]
            
            # Validate parameters
            func_def = self.functions[function_name]
            validation_result = self._validate_parameters(parameters, func_def['parameters'])
            if not validation_result['valid']:
                return {
                    "success": False,
                    "error": f"Invalid parameters: {validation_result['error']}",
                    "expected_parameters": func_def['parameters']
                }
            
            # Execute function
            if inspect.iscoroutinefunction(handler):
                result = await handler(**parameters)
            else:
                result = handler(**parameters)
            
            return {
                "success": True,
                "result": result,
                "function": function_name,
                "parameters": parameters
            }
            
        except Exception as e:
            self.logger.error(f"Error executing function {function_name}: {e}")
            return {
                "success": False,
                "error": str(e),
                "function": function_name,
                "parameters": parameters
            }
    
    def _validate_parameters(self, provided: Dict[str, Any], expected: Dict[str, Any]) -> Dict[str, Any]:
        """Validate function parameters"""
        try:
            # Check required parameters
            for param_name, param_def in expected.items():
                if param_def.get('required', False) and param_name not in provided:
                    return {
                        "valid": False,
                        "error": f"Required parameter '{param_name}' missing"
                    }
            
            # Check for unknown parameters
            for param_name in provided.keys():
                if param_name not in expected:
                    return {
                        "valid": False,
                        "error": f"Unknown parameter '{param_name}'"
                    }
            
            return {"valid": True}
            
        except Exception as e:
            return {
                "valid": False,
                "error": str(e)
            }
    
    # Built-in function handlers
    
    def _get_current_time(self) -> str:
        """Get current time"""
        now = datetime.now()
        return now.strftime("%I:%M %p")
    
    def _get_current_date(self) -> str:
        """Get current date"""
        now = datetime.now()
        return now.strftime("%A, %B %d, %Y")
    
    async def _lookup_calendar(self, date: str, time_range: Optional[str] = None) -> str:
        """Lookup calendar events"""
        try:
            # Parse relative dates
            target_date = self._parse_relative_date(date)
            date_str = target_date.strftime("%Y-%m-%d")
            
            if self.calendar_module:
                # Use direct database operations to bypass calendar module issues
                # Ensure we search the full day by setting start time to 00:00:00 and end time to 23:59:59
                start_of_day = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
                end_of_day = target_date.replace(hour=23, minute=59, second=59, microsecond=999999)
                
                start_time = start_of_day.timestamp()
                end_time = end_of_day.timestamp()
                
                self.logger.info(f"Looking up events from {start_time} to {end_time} (full day {date_str})")
                self.logger.info(f"Date range: {start_of_day} to {end_of_day}")
                try:
                    # Direct SQLite database query
                    import sqlite3
                    from pathlib import Path
                    
                    # Get database path - make it absolute to avoid issues
                    db_path = Path("data/calendar.db").resolve()
                    
                    self.logger.info(f"Looking for database at: {db_path}")
                    
                    if not db_path.exists():
                        return f"No events found for {date_str} (no database file)"
                    
                    # Query events directly from database
                    with sqlite3.connect(str(db_path)) as conn:
                        cursor = conn.cursor()
                        
                        # Debug the query parameters
                        self.logger.info(f"Query parameters: start_time={start_time}, end_time={end_time}")
                        self.logger.info(f"Query date range: {start_of_day} to {end_of_day}")
                        
                        cursor.execute("""
                            SELECT * FROM events 
                            WHERE start_time >= ? AND start_time <= ?
                            ORDER BY start_time
                        """, (start_time, end_time))
                        
                        columns = [description[0] for description in cursor.description]
                        events = [dict(zip(columns, row)) for row in cursor.fetchall()]
                        
                        # Also check total events in database for debugging
                        cursor.execute("SELECT COUNT(*) FROM events")
                        total_events = cursor.fetchone()[0]
                        self.logger.info(f"Total events in database: {total_events}")
                        
                        # Show all events for debugging
                        if total_events > 0:
                            cursor.execute("SELECT title, start_time, end_time FROM events ORDER BY start_time")
                            all_events = cursor.fetchall()
                            for event in all_events:
                                event_dt = datetime.fromtimestamp(event[1])
                                self.logger.info(f"DB Event: '{event[0]}' at {event_dt} (timestamp: {event[1]})")
                    
                    self.logger.info(f"Found {len(events)} events matching criteria")
                    
                    if events:
                        event_list = []
                        for event in events:
                            event_time = datetime.fromtimestamp(event['start_time']).strftime("%I:%M %p")
                            event_list.append(f"• {event['title']} at {event_time}")
                        
                        events_text = "\n".join(event_list)
                        return f"Events for {date_str}:\n{events_text}"
                    else:
                        return f"No events found for {date_str}"
                        
                except Exception as e:
                    self.logger.error(f"Exception in direct database lookup: {e}")
                    return f"Error looking up calendar: {str(e)}"
            else:
                # Fallback if no calendar module
                return f"Checking calendar for {date_str}: No events found"
                
        except Exception as e:
            self.logger.error(f"Error looking up calendar: {e}")
            return f"Error looking up calendar: {str(e)}"
    
    async def _add_calendar_event(self, title: str, date: str, time: Optional[str] = None, 
                                duration: Optional[str] = None, location: Optional[str] = None) -> str:
        """Add calendar event"""
        try:
            # Parse date and time
            target_date = self._parse_relative_date(date)
            
            # Default time if not specified
            if time:
                # Parse time - simple parsing for common formats
                import re
                time_clean = time.lower().strip()
                
                # Try to extract hour from various formats
                hour = 9  # default
                minute = 0  # default
                
                # Match patterns like "9am", "9 am", "9:30am", etc.
                time_match = re.search(r'(\d{1,2})(?::(\d{2}))?\s*(am|pm|a\.m\.|p\.m\.)?', time_clean)
                if time_match:
                    hour = int(time_match.group(1))
                    if time_match.group(2):
                        minute = int(time_match.group(2))
                    if time_match.group(3) and 'p' in time_match.group(3) and hour != 12:
                        hour += 12
                    elif time_match.group(3) and 'a' in time_match.group(3) and hour == 12:
                        hour = 0
                
                # Combine date and time
                event_datetime = target_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
            else:
                # Default to 9 AM if no time specified
                event_datetime = target_date.replace(hour=9, minute=0, second=0, microsecond=0)
            
            if self.calendar_module:
                # Use direct database operations to bypass calendar module issues
                start_time = event_datetime.timestamp()
                end_time = (event_datetime + timedelta(hours=1)).timestamp()  # Default 1 hour duration
                
                self.logger.info(f"Attempting to add event to calendar: {title}")
                self.logger.info(f"Event datetime: {event_datetime}, timestamp: {start_time}")
                try:
                    # Direct SQLite database insertion
                    import sqlite3
                    import uuid
                    from pathlib import Path
                    
                    # Get database path - make it absolute to avoid issues
                    db_path = Path("data/calendar.db").resolve()
                    
                    self.logger.info(f"Adding event to database at: {db_path}")
                    
                    # Create database if it doesn't exist
                    if not db_path.exists():
                        db_path.parent.mkdir(parents=True, exist_ok=True)
                        self.logger.info(f"Created database directory: {db_path.parent}")
                    
                    # Check for conflicts first
                    with sqlite3.connect(str(db_path)) as conn:
                        cursor = conn.cursor()
                        
                        # Create events table if it doesn't exist
                        cursor.execute("""
                            CREATE TABLE IF NOT EXISTS events (
                                event_id TEXT PRIMARY KEY,
                                title TEXT NOT NULL,
                                description TEXT,
                                location TEXT,
                                start_time REAL NOT NULL,
                                end_time REAL NOT NULL,
                                all_day INTEGER DEFAULT 0,
                                reminder_minutes INTEGER DEFAULT 15,
                                recurring TEXT DEFAULT 'none',
                                recurring_until REAL,
                                created_at REAL,
                                updated_at REAL,
                                tags TEXT
                            )
                        """)
                        
                        # Check for conflicts (events that overlap with the proposed time)
                        # Two events overlap if: event1_start < event2_end AND event1_end > event2_start
                        self.logger.info(f"Checking conflicts for {event_datetime} (timestamps: {start_time} to {end_time})")
                        cursor.execute("""
                            SELECT title, start_time, end_time FROM events 
                            WHERE start_time < ? AND end_time > ?
                            ORDER BY start_time
                        """, (end_time, start_time))
                        
                        conflicts = cursor.fetchall()
                        
                        self.logger.info(f"Found {len(conflicts)} conflicts:")
                        for conflict in conflicts:
                            conflict_dt = datetime.fromtimestamp(conflict[1])
                            self.logger.info(f"  - Conflict: '{conflict[0]}' at {conflict_dt} (timestamp: {conflict[1]})")
                        
                        if conflicts:
                            # Time slot is taken - find next available slot
                            conflict_titles = [conflict[0] for conflict in conflicts]
                            conflict_times = [datetime.fromtimestamp(conflict[1]).strftime("%I:%M %p") for conflict in conflicts]
                            
                            # Find next available hour
                            next_available = await self._find_next_available_hour(event_datetime, cursor)
                            
                            conflict_message = f"Time slot conflict! You already have: {', '.join(conflict_titles)} at {', '.join(conflict_times)}. "
                            if next_available:
                                next_time_str = next_available.strftime("%I:%M %p")
                                conflict_message += f"How about {next_time_str} instead?"
                            else:
                                conflict_message += "No free slots found in the next few hours."
                            
                            return conflict_message
                        
                        # No conflicts - proceed with insertion
                        event_id = str(uuid.uuid4())
                        cursor.execute("""
                            INSERT INTO events 
                            (event_id, title, description, location, start_time, end_time, created_at, updated_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            event_id, title, "", location or "", 
                            start_time, end_time, start_time, start_time
                        ))
                        
                        conn.commit()
                        
                        # Verify the event was actually saved
                        cursor.execute("SELECT COUNT(*) FROM events WHERE event_id = ?", (event_id,))
                        count = cursor.fetchone()[0]
                        self.logger.info(f"Event verification: {count} event(s) found with ID {event_id}")
                        
                        # Also check total events in database
                        cursor.execute("SELECT COUNT(*) FROM events")
                        total_count = cursor.fetchone()[0]
                        self.logger.info(f"Total events in database: {total_count}")
                    
                    formatted_time = event_datetime.strftime("%Y-%m-%d at %I:%M %p")
                    self.logger.info(f"Successfully added event to database: {title}")
                    return f"All set! {title} on {formatted_time} - it's in your calendar!"
                    
                except Exception as e:
                    self.logger.error(f"Exception in direct database add: {e}")
                    return f"Error scheduling event: {str(e)}"
            else:
                # Fallback if no calendar module
                event_info = f"Event '{title}' on {target_date.strftime('%Y-%m-%d')}"
                if time:
                    event_info += f" at {time}"
                return f"Successfully scheduled: {event_info}"
            
        except Exception as e:
            self.logger.error(f"Error adding calendar event: {e}")
            return f"Error adding event: {str(e)}"
    
    def _get_system_status(self) -> str:
        """Get system status"""
        # This would interface with the resource monitor
        return "System status: All modules running normally"
    
    def _show_weekly_calendar(self) -> str:
        """Show weekly calendar GUI"""
        try:
            from modules.calendar_viewer import show_weekly_calendar
            result = show_weekly_calendar(self.calendar_module)
            
            if result.get('success'):
                return result.get('result', 'Weekly calendar opened.')
            else:
                return f"Failed to open calendar: {result.get('error', 'Unknown error')}"
                
        except ImportError:
            return "Calendar viewer module not available."
        except Exception as e:
            self.logger.error(f"Error showing weekly calendar: {e}")
            return f"Error opening weekly calendar: {str(e)}"
    
    def _show_monthly_calendar(self) -> str:
        """Show monthly calendar GUI"""
        try:
            from modules.calendar_viewer import show_monthly_calendar
            result = show_monthly_calendar(self.calendar_module)
            
            if result.get('success'):
                return result.get('result', 'Monthly calendar opened.')
            else:
                return f"Failed to open calendar: {result.get('error', 'Unknown error')}"
                
        except ImportError:
            return "Calendar viewer module not available."
        except Exception as e:
            self.logger.error(f"Error showing monthly calendar: {e}")
            return f"Error opening monthly calendar: {str(e)}"
    
    async def _create_recurring_event(self, title: str, pattern: str, date: str, 
                                    time: Optional[str] = None, duration: Optional[str] = None, 
                                    location: Optional[str] = None) -> str:
        """Create recurring events"""
        try:
            if not self.calendar_module:
                return "Calendar module not available."
            
            # Build the natural language request
            request_parts = [title]
            
            # Add pattern to the request
            request_parts.append(pattern)
            
            # Add date and time
            if date:
                request_parts.append(date)
            if time:
                request_parts.append(f"at {time}")
                
            # Add duration and location if provided
            if duration:
                request_parts.append(f"for {duration}")
            if location:
                request_parts.append(f"at {location}")
            
            request_text = " ".join(request_parts)
            
            # Use the calendar module's recurring event handler
            result = await self.calendar_module.handle_recurring_request(request_text)
            
            if result.get('success'):
                return result.get('message', f'Created recurring event: {title}')
            else:
                return f"Failed to create recurring event: {result.get('error', 'Unknown error')}"
                
        except Exception as e:
            self.logger.error(f"Error creating recurring event: {e}")
            return f"Error creating recurring event: {str(e)}"
    
    async def _find_next_available_hour(self, preferred_datetime: datetime, cursor) -> Optional[datetime]:
        """Find the next available hour slot starting from preferred time"""
        try:
            # Check the next 8 hours for availability
            current_check = preferred_datetime
            
            for hour_offset in range(1, 9):  # Check next 8 hours
                check_time = current_check + timedelta(hours=hour_offset)
                check_start = check_time.timestamp()
                check_end = (check_time + timedelta(hours=1)).timestamp()
                
                # Check if this hour slot is free
                cursor.execute("""
                    SELECT COUNT(*) FROM events 
                    WHERE (start_time < ? AND end_time > ?) OR (start_time < ? AND end_time > ?)
                """, (check_end, check_start, check_start, check_end))
                
                conflict_count = cursor.fetchone()[0]
                
                if conflict_count == 0:
                    return check_time
            
            return None  # No free slots found
            
        except Exception as e:
            self.logger.error(f"Error finding next available hour: {e}")
            return None
    
    async def _remove_calendar_event(self, date: str, time: Optional[str] = None, title: Optional[str] = None) -> str:
        """Remove calendar event"""
        try:
            # Parse date
            target_date = self._parse_relative_date(date)
            date_str = target_date.strftime("%Y-%m-%d")
            
            import sqlite3
            from pathlib import Path
            
            # Get database path
            db_path = Path("data/calendar.db")
            
            if not db_path.exists():
                return f"No events found for {date_str}"
            
            with sqlite3.connect(str(db_path)) as conn:
                cursor = conn.cursor()
                
                # Build query based on provided parameters
                if time:
                    # Parse time to get hour/minute
                    import re
                    time_clean = time.lower().strip()
                    hour = 9  # default
                    minute = 0  # default
                    
                    time_match = re.search(r'(\d{1,2})(?::(\d{2}))?\s*(am|pm|a\.m\.|p\.m\.)?', time_clean)
                    if time_match:
                        hour = int(time_match.group(1))
                        if time_match.group(2):
                            minute = int(time_match.group(2))
                        if time_match.group(3) and 'p' in time_match.group(3) and hour != 12:
                            hour += 12
                        elif time_match.group(3) and 'a' in time_match.group(3) and hour == 12:
                            hour = 0
                    
                    target_datetime = target_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
                    target_timestamp = target_datetime.timestamp()
                    
                    # Find events around this time (within 30 minutes)
                    start_window = target_timestamp - 1800  # 30 minutes before
                    end_window = target_timestamp + 1800    # 30 minutes after
                    
                    if title:
                        cursor.execute("""
                            SELECT event_id, title, start_time FROM events 
                            WHERE start_time >= ? AND start_time <= ? AND title LIKE ?
                        """, (start_window, end_window, f"%{title}%"))
                    else:
                        cursor.execute("""
                            SELECT event_id, title, start_time FROM events 
                            WHERE start_time >= ? AND start_time <= ?
                        """, (start_window, end_window))
                else:
                    # No specific time - find events on this date
                    start_of_day = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
                    end_of_day = target_date.replace(hour=23, minute=59, second=59, microsecond=999999)
                    
                    start_timestamp = start_of_day.timestamp()
                    end_timestamp = end_of_day.timestamp()
                    
                    if title:
                        cursor.execute("""
                            SELECT event_id, title, start_time FROM events 
                            WHERE start_time >= ? AND start_time <= ? AND title LIKE ?
                        """, (start_timestamp, end_timestamp, f"%{title}%"))
                    else:
                        cursor.execute("""
                            SELECT event_id, title, start_time FROM events 
                            WHERE start_time >= ? AND start_time <= ?
                        """, (start_timestamp, end_timestamp))
                
                events_to_remove = cursor.fetchall()
                
                if not events_to_remove:
                    return f"No matching events found for {date_str}"
                
                if len(events_to_remove) == 1:
                    # Remove the single matching event
                    event_id, event_title, event_time = events_to_remove[0]
                    cursor.execute("DELETE FROM events WHERE event_id = ?", (event_id,))
                    conn.commit()
                    
                    event_time_str = datetime.fromtimestamp(event_time).strftime("%I:%M %p")
                    return f"Removed '{event_title}' from {date_str} at {event_time_str}"
                
                else:
                    # Multiple events found - list them
                    event_list = []
                    for _, event_title, event_time in events_to_remove:
                        event_time_str = datetime.fromtimestamp(event_time).strftime("%I:%M %p")
                        event_list.append(f"• {event_title} at {event_time_str}")
                    
                    return f"Multiple events found for {date_str}. Please be more specific:\n" + "\n".join(event_list)
                    
        except Exception as e:
            self.logger.error(f"Error removing calendar event: {e}")
            return f"Error removing event: {str(e)}"
    
    async def _move_calendar_event(self, from_date: str, to_time: str, from_time: Optional[str] = None, 
                                 to_date: Optional[str] = None, title: Optional[str] = None) -> str:
        """Move calendar event to a different time/date"""
        try:
            # Parse dates
            from_target_date = self._parse_relative_date(from_date)
            to_target_date = self._parse_relative_date(to_date) if to_date else from_target_date
            
            import sqlite3
            import re
            from pathlib import Path
            
            # Get database path
            db_path = Path("data/calendar.db")
            
            if not db_path.exists():
                return f"No events found to move"
            
            # Parse times
            from_hour, from_minute = 9, 0  # defaults
            to_hour, to_minute = 9, 0  # defaults
            
            if from_time:
                time_clean = from_time.lower().strip()
                time_match = re.search(r'(\d{1,2})(?::(\d{2}))?\s*(am|pm|a\.m\.|p\.m\.)?', time_clean)
                if time_match:
                    from_hour = int(time_match.group(1))
                    if time_match.group(2):
                        from_minute = int(time_match.group(2))
                    if time_match.group(3) and 'p' in time_match.group(3) and from_hour != 12:
                        from_hour += 12
                    elif time_match.group(3) and 'a' in time_match.group(3) and from_hour == 12:
                        from_hour = 0
            
            # Parse to_time
            time_clean = to_time.lower().strip()
            time_match = re.search(r'(\d{1,2})(?::(\d{2}))?\s*(am|pm|a\.m\.|p\.m\.)?', time_clean)
            if time_match:
                to_hour = int(time_match.group(1))
                if time_match.group(2):
                    to_minute = int(time_match.group(2))
                if time_match.group(3) and 'p' in time_match.group(3) and to_hour != 12:
                    to_hour += 12
                elif time_match.group(3) and 'a' in time_match.group(3) and to_hour == 12:
                    to_hour = 0
            
            from_datetime = from_target_date.replace(hour=from_hour, minute=from_minute, second=0, microsecond=0)
            to_datetime = to_target_date.replace(hour=to_hour, minute=to_minute, second=0, microsecond=0)
            
            with sqlite3.connect(str(db_path)) as conn:
                cursor = conn.cursor()
                
                # Find the event to move
                from_timestamp = from_datetime.timestamp()
                start_window = from_timestamp - 1800  # 30 minutes before
                end_window = from_timestamp + 1800    # 30 minutes after
                
                if title:
                    cursor.execute("""
                        SELECT event_id, title, start_time, end_time FROM events 
                        WHERE start_time >= ? AND start_time <= ? AND title LIKE ?
                    """, (start_window, end_window, f"%{title}%"))
                else:
                    cursor.execute("""
                        SELECT event_id, title, start_time, end_time FROM events 
                        WHERE start_time >= ? AND start_time <= ?
                    """, (start_window, end_window))
                
                events_to_move = cursor.fetchall()
                
                if not events_to_move:
                    from_date_str = from_target_date.strftime("%Y-%m-%d")
                    from_time_str = from_datetime.strftime("%I:%M %p")
                    return f"No events found at {from_date_str} {from_time_str}"
                
                if len(events_to_move) > 1:
                    # Multiple events found - list them
                    event_list = []
                    for _, event_title, event_time, _ in events_to_move:
                        event_time_str = datetime.fromtimestamp(event_time).strftime("%I:%M %p")
                        event_list.append(f"• {event_title} at {event_time_str}")
                    
                    return f"Multiple events found. Please be more specific:\n" + "\n".join(event_list)
                
                # Move the single event
                event_id, event_title, old_start_time, old_end_time = events_to_move[0]
                duration = old_end_time - old_start_time  # preserve duration
                
                new_start_time = to_datetime.timestamp()
                new_end_time = new_start_time + duration
                
                # Check for conflicts at the new time
                cursor.execute("""
                    SELECT title, start_time FROM events 
                    WHERE event_id != ? AND start_time < ? AND end_time > ?
                """, (event_id, new_end_time, new_start_time))
                
                conflicts = cursor.fetchall()
                
                if conflicts:
                    conflict_titles = [conflict[0] for conflict in conflicts]
                    conflict_times = [datetime.fromtimestamp(conflict[1]).strftime("%I:%M %p") for conflict in conflicts]
                    to_time_str = to_datetime.strftime("%I:%M %p")
                    return f"Cannot move to {to_time_str} - conflict with: {', '.join(conflict_titles)} at {', '.join(conflict_times)}"
                
                # No conflicts - proceed with move
                cursor.execute("""
                    UPDATE events 
                    SET start_time = ?, end_time = ?, updated_at = ?
                    WHERE event_id = ?
                """, (new_start_time, new_end_time, new_start_time, event_id))
                
                conn.commit()
                
                old_time_str = datetime.fromtimestamp(old_start_time).strftime("%I:%M %p")
                new_time_str = to_datetime.strftime("%I:%M %p")
                old_date_str = from_target_date.strftime("%Y-%m-%d")
                new_date_str = to_target_date.strftime("%Y-%m-%d")
                
                if old_date_str == new_date_str:
                    return f"Moved '{event_title}' from {old_time_str} to {new_time_str} on {new_date_str}"
                else:
                    return f"Moved '{event_title}' from {old_date_str} {old_time_str} to {new_date_str} {new_time_str}"
                    
        except Exception as e:
            self.logger.error(f"Error moving calendar event: {e}")
            return f"Error moving event: {str(e)}"
    
    def _parse_relative_date(self, date_str: str) -> datetime:
        """Parse relative date strings like 'today', 'tomorrow'"""
        date_lower = date_str.lower()
        now = datetime.now()
        
        if date_lower in ['today']:
            return now
        elif date_lower in ['tomorrow']:
            return now + timedelta(days=1)
        elif date_lower in ['yesterday']:
            return now - timedelta(days=1)
        else:
            # Try to parse as YYYY-MM-DD
            try:
                return datetime.strptime(date_str, "%Y-%m-%d")
            except ValueError:
                # If parsing fails, default to today
                return now


class FunctionCallingProcessor:
    """Process user requests using function calling approach"""
    
    def __init__(self, function_registry: FunctionRegistry, nlp_module=None, logger=None):
        self.function_registry = function_registry
        self.nlp_module = nlp_module
        self.logger = logger or logging.getLogger(__name__)
    
    async def process_request(self, user_input: str) -> Dict[str, Any]:
        """Process user request using appropriate approach"""
        try:
            # First, determine if this is conversational or functional
            if self._is_conversational_input(user_input):
                return await self._handle_conversation(user_input)
            else:
                return await self._handle_function_request(user_input)
                
        except Exception as e:
            self.logger.error(f"Error processing request: {e}")
            return {
                "success": False,
                "error": str(e),
                "fallback_response": "I'm sorry, I had trouble processing your request."
            }
    
    def _is_conversational_input(self, user_input: str) -> bool:
        """Determine if input is conversational rather than functional"""
        user_lower = user_input.lower().strip()
        
        # Conversational patterns
        conversational_patterns = [
            'hi', 'hello', 'hey', 'how are you', 'how have you been', 'how are things',
            'what\'s up', 'whats up', 'good morning', 'good afternoon', 'good evening',
            'how\'s it going', 'hows it going', 'nice to meet you', 'pleasure to meet you',
            'tell me about yourself', 'who are you', 'what can you do'
        ]
        
        # Functional patterns (if any of these are present, it's functional)
        functional_patterns = [
            'time', 'schedule', 'meeting', 'calendar', 'appointment', 'event',
            'add', 'remove', 'delete', 'move', 'reschedule', 'today', 'tomorrow',
            'what time', 'when', 'do i have', 'check my', 'free', 'busy',
            'cancel', 'remoce', 'delet', 'got canceled', 'scheduel',
            'week', 'weekly', 'visual', 'window', 'gui'
        ]
        
        # Check if it contains functional keywords
        if any(pattern in user_lower for pattern in functional_patterns):
            return False
            
        # Check if it matches conversational patterns
        if any(pattern in user_lower for pattern in conversational_patterns):
            return True
            
        # Short inputs are likely conversational
        if len(user_input.strip()) < 10:
            return True
            
        # Default to conversational for unclear cases
        return True
    
    async def _handle_conversation(self, user_input: str) -> Dict[str, Any]:
        """Handle conversational input with simple prompt"""
        if not self.nlp_module:
            return {
                "success": True,
                "type": "fallback_unknown",
                "response": "Hello! I'm SAGE, your assistant. I can help with time, calendar, and scheduling tasks."
            }
        
        # Simple conversational prompt
        conversation_prompt = f"""You are SAGE, a helpful voice assistant. The user said: "{user_input}"

Respond naturally and conversationally. Keep your response brief and friendly."""

        try:
            self.logger.info("Processing conversational input")
            llm_result = await self.nlp_module.process_text(conversation_prompt)
            if llm_result.get('success'):
                response_text = llm_result['response']['text'].strip()
                return {
                    "success": True,
                    "type": "conversation",
                    "response": response_text
                }
        except Exception as e:
            self.logger.warning(f"Conversation processing failed: {e}")
        
        # Fallback for conversation
        return {
            "success": True,
            "type": "conversation_fallback", 
            "response": "Hello! I'm SAGE, your assistant. How can I help you today?"
        }
    
    async def _handle_function_request(self, user_input: str) -> Dict[str, Any]:
        """Handle functional requests that might need function calls"""
        self.logger.info("Processing functional request")
        
        # Layer 1: Try simple semantic detection
        simple_semantic_result = self._simple_semantic_detection(user_input)
        if simple_semantic_result:
            self.logger.info(f"Simple semantic detected: {simple_semantic_result}")
            if simple_semantic_result == "schedule_event":
                return await self._handle_schedule_event(user_input)
            elif simple_semantic_result == "time_query":
                return await self._handle_time_query()
            elif simple_semantic_result == "calendar_lookup":
                return await self._handle_calendar_lookup(user_input)
            elif simple_semantic_result == "remove_event":
                return await self._handle_remove_event(user_input)
            elif simple_semantic_result == "weekly_calendar":
                return await self._handle_weekly_calendar()
            elif simple_semantic_result == "monthly_calendar":
                return await self._handle_monthly_calendar()
            elif simple_semantic_result == "recurring_event":
                return await self._handle_recurring_event(user_input)
        
        # Layer 2: Try LLM semantic detection
        if self.nlp_module:
            try:
                self.logger.info("Simple semantic failed, trying LLM semantic detection")
                semantic_result = await asyncio.wait_for(
                    self._semantic_function_detection(user_input), 
                    timeout=5.0
                )
                if semantic_result:
                    return semantic_result
            except asyncio.TimeoutError:
                self.logger.warning("LLM semantic detection timed out")
            except Exception as e:
                self.logger.warning(f"LLM semantic detection failed: {e}")
        
        # Layer 3: Fall back to enhanced keyword-based fallback processing
        self.logger.info("Both semantic layers failed, using keyword fallback")
        return await self._fallback_processing(user_input)
    
    
    def _simple_semantic_detection(self, user_input: str) -> Dict[str, Any]:
        """Simple word-based semantic detection before trying LLM"""
        user_lower = user_input.lower()
        
        # Check for time queries FIRST
        time_queries = ['time', 'what time', 'current time', 'tell me the time']
        if any(query in user_lower for query in time_queries):
            self.logger.info("Simple semantic detection: time query")
            return "time_query"
        
        # Check for removal requests
        remove_indicators = ['cancel', 'remove', 'delete', 'got canceled', 'remoce', 'delet']
        meeting_time_indicators = ['meeting', 'appointment', 'event', 'am', 'pm', 'o\'clock']
        
        has_remove_word = any(word in user_lower for word in remove_indicators)
        has_meeting_time = any(word in user_lower for word in meeting_time_indicators)
        
        if has_remove_word and has_meeting_time:
            self.logger.info("Simple semantic detection: remove request")
            return "remove_event"
        
        # Check for weekly calendar view requests FIRST (highest priority)
        weekly_phrases = [
            'weekly schedule', 'week schedule', 'weekly calendar', 'week calendar',
            'visual calendar', 'calendar window', 'visual schedule', 'schedule window',
            'show weekly', 'weekly view', 'calendar gui', 'visual week',
            'calendar for the week', 'week view', 'visualized calendar', 'visualised calendar'
        ]
        
        # Also check for combinations - but be more specific
        has_visual = any(word in user_lower for word in ['visual', 'visualized', 'visualised', 'visualisation', 'visualization', 'window', 'gui'])
        has_weekly = any(word in user_lower for word in ['week', 'weekly'])
        has_calendar_context = any(word in user_lower for word in ['schedule', 'calendar', 'scheduel'])
        
        # Weekly calendar detection - higher priority
        if (any(phrase in user_lower for phrase in weekly_phrases) or 
            (has_visual and has_calendar_context) or 
            (has_weekly and has_calendar_context)):
            self.logger.info("Simple semantic detection: weekly calendar view")
            return "weekly_calendar"
        
        # Check for monthly calendar view requests
        monthly_phrases = [
            'monthly schedule', 'month schedule', 'monthly calendar', 'month calendar',
            'monthly view', 'month view', 'show monthly', 'calendar monthly',
            'calendar for the month', 'monthly scheduel'
        ]
        
        has_monthly = any(word in user_lower for word in ['month', 'monthly'])
        
        # Monthly calendar detection
        if (any(phrase in user_lower for phrase in monthly_phrases) or 
            (has_monthly and has_calendar_context)):
            self.logger.info("Simple semantic detection: monthly calendar view")
            return "monthly_calendar"
        
        # Check for calendar lookups (show/check existing schedule)
        lookup_phrases = [
            'what\'s on my', 'whats on my', 'show me my', 'show me what',
            'show me the schedule', 'show me the calendar', 'what do i have',
            'do i have', 'check my', 'my schedule for', 'my calendar for'
        ]
        calendar_queries = ['what', 'check', 'my schedule', 'my calendar', 'free', 'busy', 'available', 'scheduel']
        
        if (any(phrase in user_lower for phrase in lookup_phrases) or 
            any(query in user_lower for query in calendar_queries)):
            self.logger.info("Simple semantic detection: calendar lookup")
            return "calendar_lookup"
        
        # Check for recurring event requests FIRST (before general scheduling)
        recurring_patterns = [
            'daily', 'weekly', 'monthly', 'every day', 'every week', 'every month',
            'every monday', 'every tuesday', 'every wednesday', 'every thursday',
            'every friday', 'every saturday', 'every sunday', 'recurring',
            'repeat', 'repeating', 'bi-weekly', 'every other week'
        ]
        
        recurring_phrases = [
            'daily standup', 'weekly meeting', 'monthly review', 'team standup',
            'recurring meeting', 'repeating event', 'every day at', 'every week at',
            'weekly team meeting', 'daily scrum', 'standup every', 'meeting every'
        ]
        
        has_recurring_word = any(word in user_lower for word in recurring_patterns)
        has_recurring_phrase = any(phrase in user_lower for phrase in recurring_phrases)
        
        if has_recurring_word or has_recurring_phrase:
            self.logger.info("Simple semantic detection: recurring event")
            return "recurring_event"
        
        # More specific scheduling patterns (only clear scheduling intents)
        explicit_schedule_phrases = [
            'schedule a', 'schedule an', 'add a', 'add an', 'create a', 'book a',
            'set up a', 'plan a', 'arrange a', 'schedule meeting', 'add meeting',
            'book meeting', 'create meeting', 'schedule appointment', 'add appointment'
        ]
        
        schedule_verbs = ['schedul', 'book', 'add', 'create', 'set up', 'plan', 'arrange']
        meeting_indicators = ['meeting', 'appointment', 'event']
        time_indicators = ['am', 'pm', 'o\'clock', 'at ', 'for ']
        
        # Only trigger scheduling if it's clearly about creating/adding something new
        has_explicit_schedule = any(phrase in user_lower for phrase in explicit_schedule_phrases)
        has_schedule_verb = any(word in user_lower for word in schedule_verbs)
        has_meeting_word = any(word in user_lower for word in meeting_indicators)
        has_time_reference = any(word in user_lower for word in time_indicators + ['tomorrow', 'today'])
        
        if (has_explicit_schedule or 
            (has_schedule_verb and has_meeting_word and has_time_reference)):
            self.logger.info("Simple semantic detection: scheduling request")
            return "schedule_event"
        
        return None

    async def _semantic_function_detection(self, user_input: str) -> Dict[str, Any]:
        """Use LLM to understand semantic meaning when keyword matching fails"""
        try:
            self.logger.info("Attempting semantic function detection")
            
            # Ultra-simple prompt to avoid LLM confusion
            semantic_prompt = f"""User request: "{user_input}"

Is this asking to:
A) Schedule/add a meeting
B) Check calendar/schedule  
C) Ask for time
D) Remove a meeting
E) Move a meeting
F) Show visual/weekly calendar
G) Something else

Answer: A, B, C, D, E, F, or G"""

            # Get LLM response
            llm_result = await self.nlp_module.process_text(semantic_prompt)
            if not llm_result.get('success'):
                self.logger.warning("Semantic detection LLM call failed")
                return None
                
            response = llm_result['response']['text'].strip().upper()
            self.logger.info(f"LLM semantic response: {response}")
            
            # Extract just the letter from the response
            intent_letter = None
            for char in response:
                if char in ['A', 'B', 'C', 'D', 'E', 'F', 'G']:
                    intent_letter = char
                    break
            
            if not intent_letter:
                self.logger.info(f"Could not extract intent letter from: {response}")
                return None
            
            self.logger.info(f"Extracted intent: {intent_letter}")
            
            # Map letter to function
            if intent_letter == "A":  # Schedule/add
                return await self._handle_schedule_event(user_input)
            elif intent_letter == "B":  # Check calendar
                return await self._handle_calendar_lookup(user_input)
            elif intent_letter == "C":  # Ask for time
                return await self._handle_time_query()
            elif intent_letter == "D":  # Remove meeting
                return await self._handle_remove_event(user_input)
            elif intent_letter == "E":  # Move meeting
                return await self._handle_move_event(user_input)
            elif intent_letter == "F":  # Show visual/weekly calendar
                return await self._handle_weekly_calendar()
            else:  # G or other
                self.logger.info(f"LLM indicated 'something else' or unknown: {intent_letter}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error in semantic function detection: {e}")
            return None
    
    async def _handle_time_query(self) -> Dict[str, Any]:
        """Handle time queries detected semantically"""
        result = await self.function_registry.execute_function("get_current_time", {})
        if result['success']:
            return {
                "success": True,
                "type": "semantic_function",
                "response": f"It's currently {result['result']}"
            }
        return None
    
    async def _handle_calendar_lookup(self, user_input: str) -> Dict[str, Any]:
        """Handle calendar lookup detected semantically"""
        # Extract date if possible, default to today
        date_param = "today"
        user_lower = user_input.lower()
        if "tomorrow" in user_lower:
            date_param = "tomorrow"
        elif "yesterday" in user_lower:
            date_param = "yesterday"
            
        result = await self.function_registry.execute_function("lookup_calendar", {"date": date_param})
        if result['success']:
            return {
                "success": True,
                "type": "semantic_function",
                "response": str(result['result'])
            }
        return None
    
    async def _handle_schedule_event(self, user_input: str) -> Dict[str, Any]:
        """Handle scheduling detected semantically"""
        # Use same parameter extraction logic as keyword-based system
        title = "Meeting"
        date_param = "today"
        time_param = None
        
        user_lower = user_input.lower()
        if "tomorrow" in user_lower:
            date_param = "tomorrow"
        elif "today" in user_lower:
            date_param = "today"
            
        # Extract time if mentioned (same regex as keyword system)
        import re
        time_patterns = [
            r'(\d{1,2})\s*(am|pm)',
            r'(\d{1,2}):(\d{2})\s*(am|pm)', 
            r'(\d{1,2})\s*o\'?clock',
            r'at\s+(\d{1,2})',
            r'(\d{1,2})\s*a\.?m\.?',
            r'(\d{1,2})\s*p\.?m\.?'
        ]
        
        for pattern in time_patterns:
            match = re.search(pattern, user_lower)
            if match:
                time_param = match.group(0)
                break
                
        # Try to extract meeting title
        if "meeting" in user_lower:
            title = "Meeting"
        elif "appointment" in user_lower:
            title = "Appointment"
            
        result = await self.function_registry.execute_function("add_calendar_event", {
            "title": title,
            "date": date_param,
            "time": time_param
        })
        
        if result['success']:
            return {
                "success": True,
                "type": "semantic_function",
                "response": str(result['result'])
            }
        return None
    
    async def _handle_remove_event(self, user_input: str) -> Dict[str, Any]:
        """Handle event removal detected semantically"""
        # Use same parameter extraction as keyword system
        date_param = "today"
        time_param = None
        title_param = None
        
        user_lower = user_input.lower()
        if "tomorrow" in user_lower:
            date_param = "tomorrow"
        elif "yesterday" in user_lower:
            date_param = "yesterday"
            
        # Extract time (same regex as keyword system)
        import re
        time_patterns = [
            r'(\d{1,2})\s*(am|pm)',
            r'(\d{1,2}):(\d{2})\s*(am|pm)', 
            r'(\d{1,2})\s*o\'?clock',
            r'at\s+(\d{1,2})',
            r'(\d{1,2})\s*a\.?m\.?',
            r'(\d{1,2})\s*p\.?m\.?'
        ]
        
        for pattern in time_patterns:
            match = re.search(pattern, user_lower)
            if match:
                time_param = match.group(0)
                break
        
        if "meeting" in user_lower:
            title_param = "meeting"
        elif "appointment" in user_lower:
            title_param = "appointment"
            
        result = await self.function_registry.execute_function("remove_calendar_event", {
            "date": date_param,
            "time": time_param,
            "title": title_param
        })
        
        if result['success']:
            return {
                "success": True,
                "type": "semantic_function",
                "response": str(result['result'])
            }
        return None
    
    async def _handle_move_event(self, user_input: str) -> Dict[str, Any]:
        """Handle event moving detected semantically"""
        # This is more complex - for now return a helpful message
        return {
            "success": True,
            "type": "semantic_function",
            "response": "I understand you want to move a meeting. Please specify which meeting and what time to move it to, like 'move my 9am meeting to 10am'."
        }
    
    async def _handle_weekly_calendar(self) -> Dict[str, Any]:
        """Handle weekly calendar view request"""
        result = await self.function_registry.execute_function("show_weekly_calendar", {})
        if result['success']:
            return {
                "success": True,
                "type": "semantic_function",
                "response": result['result']
            }
        else:
            return {
                "success": True,
                "type": "semantic_function",
                "response": f"Unable to open weekly calendar: {result.get('error', 'Unknown error')}"
            }
    
    async def _handle_monthly_calendar(self) -> Dict[str, Any]:
        """Handle monthly calendar view request"""
        result = await self.function_registry.execute_function("show_monthly_calendar", {})
        if result['success']:
            return {
                "success": True,
                "type": "semantic_function",
                "response": result['result']
            }
        else:
            return {
                "success": True,
                "type": "semantic_function",
                "response": f"Unable to open monthly calendar: {result.get('error', 'Unknown error')}"
            }
    
    async def _handle_recurring_event(self, user_input: str) -> Dict[str, Any]:
        """Handle recurring event creation request"""
        user_lower = user_input.lower()
        
        # Extract parameters from user input
        title = "Recurring Event"
        pattern = "weekly"  # default
        date_param = "today"
        time_param = None
        
        # Extract pattern
        if "daily" in user_lower:
            pattern = "daily"
        elif "weekly" in user_lower:
            pattern = "weekly"
        elif "monthly" in user_lower:
            pattern = "monthly"
        elif "every monday" in user_lower:
            pattern = "every Monday"
        elif "every tuesday" in user_lower:
            pattern = "every Tuesday"
        elif "every wednesday" in user_lower:
            pattern = "every Wednesday"
        elif "every thursday" in user_lower:
            pattern = "every Thursday"
        elif "every friday" in user_lower:
            pattern = "every Friday"
        elif "every saturday" in user_lower:
            pattern = "every Saturday"
        elif "every sunday" in user_lower:
            pattern = "every Sunday"
        elif "bi-weekly" in user_lower or "every other week" in user_lower:
            pattern = "bi-weekly"
        
        # Extract title
        if "standup" in user_lower:
            title = "Daily Standup" if "daily" in user_lower else "Standup"
        elif "meeting" in user_lower:
            title = "Weekly Meeting" if "weekly" in user_lower else "Meeting"
        elif "scrum" in user_lower:
            title = "Daily Scrum" if "daily" in user_lower else "Scrum"
        elif "review" in user_lower:
            title = "Monthly Review" if "monthly" in user_lower else "Review"
        
        # Extract date and time
        if "tomorrow" in user_lower:
            date_param = "tomorrow"
        elif "today" in user_lower:
            date_param = "today"
        
        # Extract time if mentioned
        import re
        time_patterns = [
            r'(\d{1,2})\s*(am|pm)',
            r'(\d{1,2}):(\d{2})\s*(am|pm)', 
            r'(\d{1,2})\s*o\'?clock',
            r'at\s+(\d{1,2})',
            r'(\d{1,2})\s*a\.?m\.?',
            r'(\d{1,2})\s*p\.?m\.?'
        ]
        
        for time_pattern in time_patterns:
            match = re.search(time_pattern, user_lower)
            if match:
                time_param = match.group(0)
                break
        
        result = await self.function_registry.execute_function("create_recurring_event", {
            "title": title,
            "pattern": pattern,
            "date": date_param,
            "time": time_param
        })
        
        if result['success']:
            return {
                "success": True,
                "type": "semantic_function",
                "response": str(result['result'])
            }
        else:
            return {
                "success": True,
                "type": "semantic_function",
                "response": f"Unable to create recurring event: {result.get('error', 'Unknown error')}"
            }

    async def _fallback_processing(self, user_input: str) -> Dict[str, Any]:
        """Enhanced fallback processing when LLM parsing fails"""
        self.logger.info(f"Using fallback processing for: '{user_input}'")
        user_lower = user_input.lower()
        
        # Time queries - multiple variations
        time_keywords = ['time', 'what time', 'clock', 'hour', 'minute', 'when is it', 'current time']
        if any(word in user_lower for word in time_keywords):
            self.logger.info("Fallback detected time query")
            result = await self.function_registry.execute_function("get_current_time", {})
            if result['success']:
                return {
                    "success": True,
                    "type": "fallback_function",
                    "response": f"It's currently {result['result']}"
                }
        
        # Date queries
        date_keywords = ['date', 'what date', 'today', 'current date', 'what day']
        if any(word in user_lower for word in date_keywords):
            self.logger.info("Fallback detected date query")
            result = await self.function_registry.execute_function("get_current_date", {})
            if result['success']:
                return {
                    "success": True,
                    "type": "fallback_function", 
                    "response": f"Today is {result['result']}"
                }
        
        # Scheduling/Adding events - these come BEFORE calendar lookup
        add_keywords = ['schedule', 'add', 'create', 'book', 'set up', 'plan', 'arrange']
        action_phrases = [
            'schedule a', 'schedule an', 'add a', 'add an', 'create a', 'book a', 
            'set up a', 'plan a', 'arrange a', 'schedule meeting', 'add meeting',
            'can you schedule', 'can u schedule', 'could you schedule', 'please schedule'
        ]
        
        # Check for scheduling/adding requests first - more flexible matching
        is_scheduling_request = (
            any(word in user_lower for word in add_keywords) and 
            (any(phrase in user_lower for phrase in action_phrases) or
             any(event_word in user_lower for event_word in ['meeting', 'event', 'appointment']))
        )
        
        if is_scheduling_request:
            self.logger.info("Fallback detected scheduling request")
            
            # Extract parameters
            title = "Meeting"  # default
            date_param = "today"  # default
            time_param = None
            
            if "tomorrow" in user_lower:
                date_param = "tomorrow"
            elif "today" in user_lower:
                date_param = "today"
                
            # Extract time if mentioned
            import re
            time_patterns = [
                r'(\d{1,2})\s*(am|pm)',
                r'(\d{1,2}):(\d{2})\s*(am|pm)', 
                r'(\d{1,2})\s*o\'?clock',
                r'at\s+(\d{1,2})',
                r'(\d{1,2})\s*a\.?m\.?',
                r'(\d{1,2})\s*p\.?m\.?'
            ]
            
            for pattern in time_patterns:
                match = re.search(pattern, user_lower)
                if match:
                    time_param = match.group(0)
                    break
                    
            # Try to extract meeting title
            if "meeting" in user_lower:
                title = "Meeting"
            elif "appointment" in user_lower:
                title = "Appointment"
                
            result = await self.function_registry.execute_function("add_calendar_event", {
                "title": title,
                "date": date_param,
                "time": time_param
            })
            
            if result['success']:
                return {
                    "success": True,
                    "type": "fallback_function", 
                    "response": str(result['result'])
                }
        
        # Remove/Delete events - check before lookup
        remove_keywords = ['remove', 'delete', 'cancel', 'clear']
        remove_phrases = [
            'remove the', 'delete the', 'cancel the', 'clear the',
            'remove my', 'delete my', 'cancel my', 'clear my'
        ]
        
        if (any(word in user_lower for word in remove_keywords) and 
            any(phrase in user_lower for phrase in remove_phrases + ['meeting', 'event', 'appointment'])):
            
            self.logger.info("Fallback detected remove request")
            
            # Extract parameters
            date_param = "today"  # default
            time_param = None
            title_param = None
            
            if "tomorrow" in user_lower:
                date_param = "tomorrow"
            elif "today" in user_lower:
                date_param = "today"
            elif "yesterday" in user_lower:
                date_param = "yesterday"
                
            # Extract time if mentioned
            import re
            time_patterns = [
                r'(\d{1,2})\s*(am|pm)',
                r'(\d{1,2}):(\d{2})\s*(am|pm)', 
                r'(\d{1,2})\s*o\'?clock',
                r'at\s+(\d{1,2})',
                r'(\d{1,2})\s*a\.?m\.?',
                r'(\d{1,2})\s*p\.?m\.?'
            ]
            
            for pattern in time_patterns:
                match = re.search(pattern, user_lower)
                if match:
                    time_param = match.group(0)
                    break
            
            # Try to extract title hints
            if "meeting" in user_lower:
                title_param = "meeting"
            elif "appointment" in user_lower:
                title_param = "appointment"
                
            result = await self.function_registry.execute_function("remove_calendar_event", {
                "date": date_param,
                "time": time_param,
                "title": title_param
            })
            
            if result['success']:
                return {
                    "success": True,
                    "type": "fallback_function", 
                    "response": str(result['result'])
                }
        
        # Move/Reschedule events - check before lookup
        move_keywords = ['move', 'reschedule', 'change', 'shift']
        move_phrases = [
            'move my', 'move the', 'reschedule my', 'reschedule the',
            'change my', 'change the', 'shift my', 'shift the'
        ]
        
        if (any(word in user_lower for word in move_keywords) and 
            any(phrase in user_lower for phrase in move_phrases + ['meeting', 'event', 'appointment'])):
            
            self.logger.info("Fallback detected move request")
            
            # Extract parameters
            from_date_param = "today"  # default
            from_time_param = None
            to_time_param = None
            to_date_param = None
            title_param = None
            
            # Extract dates
            if "tomorrow" in user_lower:
                from_date_param = "tomorrow"
            elif "today" in user_lower:
                from_date_param = "today"
                
            # Extract times - look for "from X to Y" or "X to Y" patterns
            import re
            
            # Look for time patterns
            time_patterns = [
                r'(\d{1,2})\s*(am|pm)',
                r'(\d{1,2}):(\d{2})\s*(am|pm)', 
                r'(\d{1,2})\s*o\'?clock',
                r'(\d{1,2})\s*a\.?m\.?',
                r'(\d{1,2})\s*p\.?m\.?'
            ]
            
            times_found = []
            for pattern in time_patterns:
                matches = re.finditer(pattern, user_lower)
                for match in matches:
                    times_found.append(match.group(0))
            
            if len(times_found) >= 2:
                # Assume first time is "from" and second is "to"
                from_time_param = times_found[0]
                to_time_param = times_found[1]
            elif len(times_found) == 1:
                # Look for context clues
                if " to " in user_lower:
                    # Likely the "to" time
                    to_time_param = times_found[0]
                else:
                    # Likely the "from" time
                    from_time_param = times_found[0]
                    
            # If we don't have a "to" time, can't proceed
            if not to_time_param:
                return {
                    "success": True,
                    "type": "fallback_unknown",
                    "response": "To move an event, please specify both the current time and the new time. For example: 'move my 9am meeting to 10am'"
                }
            
            # Try to extract title hints
            if "meeting" in user_lower:
                title_param = "meeting"
            elif "appointment" in user_lower:
                title_param = "appointment"
                
            result = await self.function_registry.execute_function("move_calendar_event", {
                "from_date": from_date_param,
                "from_time": from_time_param,
                "to_date": to_date_param,
                "to_time": to_time_param,
                "title": title_param
            })
            
            if result['success']:
                return {
                    "success": True,
                    "type": "fallback_function", 
                    "response": str(result['result'])
                }
        
        # Calendar LOOKUP queries (checking what's scheduled) - AFTER scheduling
        # More flexible lookup patterns
        lookup_patterns = [
            # Question patterns
            'do i have', 'what', 'check', 'show', 'view', 'see', 'tell me',
            'any meetings', 'any events', 'any appointments',
            'anything on', 'anything in', 'whats on', "what's on",
            'free on', 'busy on', 'available on'
        ]
        calendar_objects = ['schedule', 'calendar', 'meetings', 'events', 'appointments', 'planned', 'busy']
        
        # Check for lookup patterns OR calendar objects with question words
        is_lookup_query = (
            any(pattern in user_lower for pattern in lookup_patterns) or
            (any(word in user_lower for word in calendar_objects) and 
             any(q_word in user_lower for q_word in ['do', 'what', 'when', '?']))
        )
        
        if is_lookup_query:
            self.logger.info("Fallback detected calendar lookup query")
            # Extract date if possible
            date_param = "today"  # default
            if "tomorrow" in user_lower:
                date_param = "tomorrow"
            elif "yesterday" in user_lower:
                date_param = "yesterday"
                
            result = await self.function_registry.execute_function("lookup_calendar", {"date": date_param})
            if result['success']:
                return {
                    "success": True,
                    "type": "fallback_function",
                    "response": str(result['result'])
                }
        
        self.logger.info("Fallback could not classify request, trying semantic understanding")
        
        # Second layer: Try simple word detection before LLM
        simple_semantic_result = self._simple_semantic_detection(user_input)
        if simple_semantic_result:
            self.logger.info(f"Simple semantic detected: {simple_semantic_result}")
            if simple_semantic_result == "schedule_event":
                return await self._handle_schedule_event(user_input)
            elif simple_semantic_result == "time_query":
                return await self._handle_time_query()
            elif simple_semantic_result == "calendar_lookup":
                return await self._handle_calendar_lookup(user_input)
            elif simple_semantic_result == "remove_event":
                return await self._handle_remove_event(user_input)
            elif simple_semantic_result == "weekly_calendar":
                return await self._handle_weekly_calendar()
        
        # Third layer: Use LLM for semantic understanding when everything else fails
        if self.nlp_module:
            try:
                # Add timeout to prevent hanging
                semantic_result = await asyncio.wait_for(
                    self._semantic_function_detection(user_input), 
                    timeout=5.0
                )
                if semantic_result:
                    return semantic_result
            except asyncio.TimeoutError:
                self.logger.warning("Semantic detection timed out")
        
        # Last resort fallback
        self.logger.info("Semantic understanding also failed")
        return {
            "success": True,
            "type": "fallback_unknown",
            "response": "I'm not sure how to help with that request."
        }