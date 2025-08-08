"""
Calendar Module - Smart scheduling and reminder system for SAGE
"""

import asyncio
import json
import sqlite3
import time
import logging
import re
import hashlib
import calendar as cal
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, asdict
from collections import defaultdict
import threading

from modules import BaseModule, EventType, Event

# Try to import date parsing libraries
try:
    import dateutil.parser as date_parser
    from dateutil.relativedelta import relativedelta
    DATEUTIL_AVAILABLE = True
except ImportError:
    DATEUTIL_AVAILABLE = False


@dataclass
class CalendarEvent:
    """Data class for calendar events"""
    event_id: str
    title: str
    description: str
    start_time: float
    end_time: float
    all_day: bool = False
    location: str = ""
    reminder_minutes: int = 15
    recurring: str = "none"  # none, daily, weekly, monthly, yearly
    recurring_until: Optional[float] = None
    created_at: float = None
    updated_at: float = None
    tags: List[str] = None
    event_type: str = "meeting"  # meeting, appointment, task, personal, work, etc.
    priority: str = "medium"  # low, medium, high, urgent
    attendees: List[str] = None
    recurring_pattern: Dict[str, Any] = None  # Advanced recurring options
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = time.time()
        if self.updated_at is None:
            self.updated_at = time.time()
        if self.tags is None:
            self.tags = []
        if self.attendees is None:
            self.attendees = []
        if self.recurring_pattern is None:
            self.recurring_pattern = {}


@dataclass
class Reminder:
    """Data class for reminders"""
    reminder_id: str
    event_id: str
    reminder_time: float
    message: str
    delivered: bool = False
    delivery_method: str = "notification"  # notification, voice, both


class NaturalLanguageParser:
    """Parse natural language date and time expressions"""
    
    def __init__(self):
        self.time_patterns = [
            # Time patterns
            (r'\b(\d{1,2}):(\d{2})\s*(am|pm)?\b', self._parse_time),
            (r'\b(\d{1,2})\s*(am|pm)\b', self._parse_time_simple),
            (r'\bmidnight\b', lambda m: (0, 0)),
            (r'\bnoon\b', lambda m: (12, 0)),
            
            # Relative time patterns
            (r'\bin\s+(\d+)\s*(minute|minutes|min|hour|hours|hr|day|days)\b', self._parse_relative_time),
            (r'\b(\d+)\s*(minute|minutes|min|hour|hours|hr|day|days)\s+from\s+now\b', self._parse_relative_time),
        ]
        
        self.date_patterns = [
            # Date patterns
            (r'\btoday\b', lambda m: datetime.now().date()),
            (r'\btomorrow\b', lambda m: (datetime.now() + timedelta(days=1)).date()),
            (r'\byesterday\b', lambda m: (datetime.now() - timedelta(days=1)).date()),
            (r'\bnext\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b', self._parse_next_weekday),
            (r'\bthis\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b', self._parse_this_weekday),
            (r'\bin\s+(\d+)\s+days?\b', self._parse_days_from_now),
        ]
        
        self.weekdays = {
            'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
            'friday': 4, 'saturday': 5, 'sunday': 6
        }
    
    def _parse_time(self, match):
        """Parse time in HH:MM AM/PM format"""
        hour = int(match.group(1))
        minute = int(match.group(2))
        ampm = match.group(3)
        
        if ampm and ampm.lower() == 'pm' and hour != 12:
            hour += 12
        elif ampm and ampm.lower() == 'am' and hour == 12:
            hour = 0
            
        return (hour, minute)
    
    def _parse_time_simple(self, match):
        """Parse time in H AM/PM format"""
        hour = int(match.group(1))
        ampm = match.group(2)
        
        if ampm.lower() == 'pm' and hour != 12:
            hour += 12
        elif ampm.lower() == 'am' and hour == 12:
            hour = 0
            
        return (hour, 0)
    
    def _parse_relative_time(self, match):
        """Parse relative time expressions"""
        amount = int(match.group(1))
        unit = match.group(2).lower()
        
        now = datetime.now()
        if unit.startswith('min'):
            return now + timedelta(minutes=amount)
        elif unit.startswith('hour') or unit == 'hr':
            return now + timedelta(hours=amount)
        elif unit.startswith('day'):
            return now + timedelta(days=amount)
        
        return now
    
    def _parse_next_weekday(self, match):
        """Parse 'next Monday' etc."""
        weekday_name = match.group(1).lower()
        target_weekday = self.weekdays[weekday_name]
        
        today = datetime.now().date()
        days_ahead = target_weekday - today.weekday()
        if days_ahead <= 0:  # Target day already happened this week
            days_ahead += 7
            
        return today + timedelta(days=days_ahead)
    
    def _parse_this_weekday(self, match):
        """Parse 'this Monday' etc."""
        weekday_name = match.group(1).lower()
        target_weekday = self.weekdays[weekday_name]
        
        today = datetime.now().date()
        days_ahead = target_weekday - today.weekday()
        if days_ahead < 0:  # Already passed this week
            days_ahead += 7
            
        return today + timedelta(days=days_ahead)
    
    def _parse_days_from_now(self, match):
        """Parse 'in 3 days' etc."""
        days = int(match.group(1))
        return (datetime.now() + timedelta(days=days)).date()
    
    def parse_datetime(self, text: str) -> Optional[datetime]:
        """Parse natural language text into datetime"""
        text = text.lower().strip()
        
        # Try dateutil first if available
        if DATEUTIL_AVAILABLE:
            try:
                parsed = date_parser.parse(text, fuzzy=True)
                return parsed
            except:
                pass
        
        # Fallback to manual parsing
        date_obj = None
        time_tuple = None
        
        # Parse date
        for pattern, handler in self.date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                date_obj = handler(match)
                break
        
        # Parse time
        for pattern, handler in self.time_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result = handler(match)
                if isinstance(result, tuple):
                    time_tuple = result
                elif isinstance(result, datetime):
                    return result
                break
        
        # Combine date and time
        if date_obj and time_tuple:
            return datetime.combine(date_obj, datetime.min.time().replace(
                hour=time_tuple[0], minute=time_tuple[1]
            ))
        elif date_obj:
            return datetime.combine(date_obj, datetime.min.time().replace(hour=9))  # Default 9 AM
        elif time_tuple:
            today = datetime.now().date()
            return datetime.combine(today, datetime.min.time().replace(
                hour=time_tuple[0], minute=time_tuple[1]
            ))
        
        return None


class CalendarModule(BaseModule):
    """Calendar and scheduling module for SAGE"""
    
    def __init__(self, name: str = "calendar"):
        super().__init__(name)
        self.db_path = Path("data/calendar.db")
        self.db_lock = threading.Lock()
        self.reminder_scheduler = None
        self.parser = NaturalLanguageParser()
        self.active_reminders = {}
        
        # Initialize stats
        self.stats = {
            'total_events': 0,
            'total_reminders': 0,
            'events_created': 0,
            'reminders_delivered': 0
        }
        
    async def initialize(self) -> bool:
        """Initialize the calendar module"""
        try:
            self.log("Initializing Calendar Module...")
            
            # Ensure data directory exists
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Initialize database
            self._init_database()
            
            # Start reminder scheduler
            self.reminder_scheduler = asyncio.create_task(self._reminder_loop())
            
            # Subscribe to relevant events
            self.subscribe_events([
                EventType.VOICE_COMMAND,
                EventType.INTENT_PARSED,
                EventType.LLM_RESPONSE
            ])
            
            self.is_loaded = True
            self.log("Calendar Module initialized successfully")
            return True
            
        except Exception as e:
            self.log(f"Failed to initialize Calendar Module: {e}", "error")
            return False
    
    async def shutdown(self) -> None:
        """Shutdown the calendar module"""
        self.log("Shutting down Calendar Module...")
        
        if self.reminder_scheduler:
            self.reminder_scheduler.cancel()
            try:
                await self.reminder_scheduler
            except asyncio.CancelledError:
                pass
        
        self.is_loaded = False
        self.log("Calendar Module shutdown complete")
    
    def _init_database(self):
        """Initialize the calendar database"""
        with self.db_lock:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            # Create events table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    event_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT,
                    start_time REAL NOT NULL,
                    end_time REAL NOT NULL,
                    all_day BOOLEAN DEFAULT FALSE,
                    location TEXT,
                    reminder_minutes INTEGER DEFAULT 15,
                    recurring TEXT DEFAULT 'none',
                    recurring_until REAL,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    tags TEXT
                )
            """)
            
            # Create reminders table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS reminders (
                    reminder_id TEXT PRIMARY KEY,
                    event_id TEXT NOT NULL,
                    reminder_time REAL NOT NULL,
                    message TEXT NOT NULL,
                    delivered BOOLEAN DEFAULT FALSE,
                    delivery_method TEXT DEFAULT 'notification',
                    FOREIGN KEY (event_id) REFERENCES events (event_id)
                )
            """)
            
            # Migrate database to add new columns if they don't exist
            self._migrate_database(cursor)
            
            conn.commit()
            conn.close()
    
    def _migrate_database(self, cursor):
        """Add new columns for enhanced calendar features"""
        try:
            # Check if event_type column exists, if not add it
            cursor.execute("PRAGMA table_info(events)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'event_type' not in columns:
                cursor.execute("ALTER TABLE events ADD COLUMN event_type TEXT DEFAULT 'meeting'")
                self.log("Added event_type column to events table")
            
            if 'priority' not in columns:
                cursor.execute("ALTER TABLE events ADD COLUMN priority TEXT DEFAULT 'medium'")
                self.log("Added priority column to events table")
            
            if 'attendees' not in columns:
                cursor.execute("ALTER TABLE events ADD COLUMN attendees TEXT DEFAULT '[]'")
                self.log("Added attendees column to events table")
            
            if 'recurring_pattern' not in columns:
                cursor.execute("ALTER TABLE events ADD COLUMN recurring_pattern TEXT DEFAULT '{}'")
                self.log("Added recurring_pattern column to events table")
                
        except Exception as e:
            self.log(f"Database migration error: {e}", "error")
    
    async def handle_event(self, event: Event) -> Optional[Any]:
        """Handle events from other modules"""
        try:
            if event.type == EventType.INTENT_PARSED:
                intent = event.data.get('intent', '')
                confidence = event.data.get('confidence', 0.0)
                text = event.data.get('text', '')
                
                if confidence > 0.6 and self._is_calendar_intent(intent, text):
                    return await self._handle_calendar_request(text, intent)
                    
            elif event.type == EventType.VOICE_COMMAND:
                command = event.data.get('command', '').lower()
                if any(keyword in command for keyword in ['schedule', 'remind', 'calendar', 'appointment', 'meeting']):
                    return await self._handle_calendar_request(command, 'schedule')
            
        except Exception as e:
            self.log(f"Error handling event: {e}", "error")
        
        return None
    
    def _is_calendar_intent(self, intent: str, text: str) -> bool:
        """Check if intent is calendar-related"""
        calendar_intents = ['schedule', 'remind', 'calendar', 'appointment', 'meeting', 'event', 'time']
        calendar_keywords = ['schedule', 'remind', 'calendar', 'appointment', 'meeting', 'tomorrow', 'today', 'next week', 'what\'s on', 'show me', 'list', 'events']
        
        text_lower = text.lower()
        intent_lower = intent.lower()
        
        # Check intent match
        if intent_lower in calendar_intents:
            return True
            
        # Check keyword match
        if any(keyword in text_lower for keyword in calendar_keywords):
            return True
            
        # Check for time-related phrases
        time_phrases = ['at ', 'on ', 'tomorrow', 'today', 'next ', 'this ']
        if any(phrase in text_lower for phrase in time_phrases):
            return True
            
        return False
    
    async def _handle_calendar_request(self, text: str, intent: str) -> Dict[str, Any]:
        """Handle calendar-related requests"""
        try:
            # Parse the request
            if 'list' in text.lower() or 'show' in text.lower() or 'what' in text.lower():
                return await self._list_events(text)
            elif 'remind' in text.lower():
                return await self._create_reminder(text)
            elif any(word in text.lower() for word in ['schedule', 'add', 'create', 'book']):
                return await self._create_event(text)
            elif 'cancel' in text.lower() or 'delete' in text.lower():
                return await self._cancel_event(text)
            else:
                return await self._create_event(text)  # Default to creating event
                
        except Exception as e:
            self.log(f"Error handling calendar request: {e}", "error")
            return {
                'success': False,
                'error': f"Calendar error: {str(e)}",
                'type': 'calendar_error'
            }
    
    async def _create_event(self, text: str) -> Dict[str, Any]:
        """Create a new calendar event"""
        try:
            # Parse the text for event details
            event_title = self._extract_event_title(text)
            event_datetime = self.parser.parse_datetime(text)
            
            if not event_datetime:
                return {
                    'success': False,
                    'error': "Could not parse date/time from your request",
                    'type': 'parse_error'
                }
            
            # Create event ID
            event_id = hashlib.md5(f"{event_title}_{event_datetime.timestamp()}".encode()).hexdigest()[:12]
            
            # Default end time (1 hour later)
            end_datetime = event_datetime + timedelta(hours=1)
            
            # Create event object
            event = CalendarEvent(
                event_id=event_id,
                title=event_title,
                description=f"Created from: {text}",
                start_time=event_datetime.timestamp(),
                end_time=end_datetime.timestamp(),
                reminder_minutes=self.config.get('reminder_lead_time', 15)
            )
            
            # Save to database
            await self._save_event(event)
            
            # Create reminder
            await self._create_event_reminder(event)
            
            # Emit event
            self.emit_event(EventType.SCHEDULE_UPDATED, {
                'action': 'created',
                'event_id': event_id,
                'title': event_title,
                'start_time': event_datetime.isoformat()
            })
            
            return {
                'success': True,
                'message': f"Created event '{event_title}' for {event_datetime.strftime('%A, %B %d at %I:%M %p')}",
                'event_id': event_id,
                'type': 'event_created'
            }
            
        except Exception as e:
            self.log(f"Error creating event: {e}", "error")
            return {
                'success': False,
                'error': f"Failed to create event: {str(e)}",
                'type': 'creation_error'
            }
    
    async def _create_reminder(self, text: str) -> Dict[str, Any]:
        """Create a simple reminder"""
        try:
            # Parse reminder text
            reminder_text = self._extract_reminder_text(text)
            reminder_datetime = self.parser.parse_datetime(text)
            
            if not reminder_datetime:
                return {
                    'success': False,
                    'error': "Could not parse date/time for reminder",
                    'type': 'parse_error'
                }
            
            # Create a reminder event (short duration)
            event_id = hashlib.md5(f"reminder_{reminder_text}_{reminder_datetime.timestamp()}".encode()).hexdigest()[:12]
            
            event = CalendarEvent(
                event_id=event_id,
                title=f"Reminder: {reminder_text}",
                description=f"Reminder created from: {text}",
                start_time=reminder_datetime.timestamp(),
                end_time=(reminder_datetime + timedelta(minutes=5)).timestamp(),
                reminder_minutes=0  # Remind at exact time
            )
            
            await self._save_event(event)
            await self._create_event_reminder(event)
            
            return {
                'success': True,
                'message': f"Set reminder '{reminder_text}' for {reminder_datetime.strftime('%A, %B %d at %I:%M %p')}",
                'event_id': event_id,
                'type': 'reminder_created'
            }
            
        except Exception as e:
            self.log(f"Error creating reminder: {e}", "error")
            return {
                'success': False,
                'error': f"Failed to create reminder: {str(e)}",
                'type': 'reminder_error'
            }
    
    async def _list_events(self, text: str = "") -> Dict[str, Any]:
        """List upcoming events"""
        try:
            # Determine time range
            now = time.time()
            if 'today' in text.lower():
                start_time = datetime.now().replace(hour=0, minute=0, second=0).timestamp()
                end_time = datetime.now().replace(hour=23, minute=59, second=59).timestamp()
                period = "today"
            elif 'tomorrow' in text.lower():
                tomorrow = datetime.now() + timedelta(days=1)
                start_time = tomorrow.replace(hour=0, minute=0, second=0).timestamp()
                end_time = tomorrow.replace(hour=23, minute=59, second=59).timestamp()
                period = "tomorrow"
            elif 'week' in text.lower():
                start_time = now
                end_time = now + (7 * 24 * 60 * 60)
                period = "this week"
            else:
                start_time = now
                end_time = now + (24 * 60 * 60)  # Next 24 hours
                period = "today"
            
            # Query database
            events = await self._get_events_in_range(start_time, end_time)
            
            if not events:
                return {
                    'success': True,
                    'message': f"No events scheduled for {period}",
                    'events': [],
                    'type': 'events_list'
                }
            
            # Format events
            event_list = []
            for event in events:
                start_dt = datetime.fromtimestamp(event['start_time'])
                event_list.append({
                    'title': event['title'],
                    'start_time': start_dt.strftime('%I:%M %p'),
                    'date': start_dt.strftime('%A, %B %d'),
                    'location': event.get('location', ''),
                    'description': event.get('description', '')
                })
            
            message = f"You have {len(events)} event{'s' if len(events) != 1 else ''} {period}:\n"
            for event in event_list:
                message += f"• {event['title']} at {event['start_time']}\n"
            
            return {
                'success': True,
                'message': message.strip(),
                'events': event_list,
                'type': 'events_list'
            }
            
        except Exception as e:
            self.log(f"Error listing events: {e}", "error")
            return {
                'success': False,
                'error': f"Failed to list events: {str(e)}",
                'type': 'list_error'
            }
    
    async def _save_event(self, event: CalendarEvent):
        """Save event to database"""
        with self.db_lock:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO events 
                (event_id, title, description, start_time, end_time, all_day, 
                 location, reminder_minutes, recurring, recurring_until, 
                 created_at, updated_at, tags, event_type, priority, attendees, recurring_pattern)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                event.event_id, event.title, event.description,
                event.start_time, event.end_time, event.all_day,
                event.location, event.reminder_minutes, event.recurring,
                event.recurring_until, event.created_at, event.updated_at,
                json.dumps(event.tags), event.event_type, event.priority,
                json.dumps(event.attendees), json.dumps(event.recurring_pattern)
            ))
            
            conn.commit()
            conn.close()
    
    async def _create_event_reminder(self, event: CalendarEvent):
        """Create reminder for an event"""
        reminder_time = event.start_time - (event.reminder_minutes * 60)
        
        if reminder_time > time.time():  # Only create future reminders
            reminder_id = f"{event.event_id}_reminder"
            
            reminder = Reminder(
                reminder_id=reminder_id,
                event_id=event.event_id,
                reminder_time=reminder_time,
                message=f"Reminder: {event.title} in {event.reminder_minutes} minutes"
            )
            
            # Save to database
            with self.db_lock:
                conn = sqlite3.connect(str(self.db_path))
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT OR REPLACE INTO reminders 
                    (reminder_id, event_id, reminder_time, message, delivered, delivery_method)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    reminder.reminder_id, reminder.event_id, reminder.reminder_time,
                    reminder.message, reminder.delivered, reminder.delivery_method
                ))
                
                conn.commit()
                conn.close()
    
    async def _get_events_in_range(self, start_time: float, end_time: float) -> List[Dict]:
        """Get events within time range"""
        with self.db_lock:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM events 
                WHERE start_time >= ? AND start_time <= ?
                ORDER BY start_time
            """, (start_time, end_time))
            
            columns = [description[0] for description in cursor.description]
            events = [dict(zip(columns, row)) for row in cursor.fetchall()]
            
            conn.close()
            return events
    
    async def handle_natural_language(self, text: str) -> Dict[str, Any]:
        """Handle natural language calendar requests"""
        try:
            text_lower = text.lower()
            
            # Check for schedule/meeting keywords
            if any(word in text_lower for word in ['schedule', 'meeting', 'appointment', 'remind', 'event']):
                # Try to parse the request
                parsed_dt = self.parser.parse_datetime(text)
                
                if parsed_dt:
                    # Extract title from text
                    title = self._extract_title_from_text(text)
                    
                    # Generate event ID
                    import hashlib
                    event_id = hashlib.md5(f"{title}_{parsed_dt.timestamp()}_{time.time()}".encode()).hexdigest()[:12]
                    
                    # Create event
                    event = CalendarEvent(
                        event_id=event_id,
                        title=title or "New Event",
                        start_time=parsed_dt.timestamp(),
                        end_time=parsed_dt.timestamp() + 3600,  # 1 hour default
                        description=f"Event created from: {text}",
                        location="",
                        reminder_minutes=15
                    )
                    
                    # Add to calendar
                    success = await self.add_event(event)
                    
                    if success:
                        return {
                            'success': True,
                            'event_created': True,
                            'event': {
                                'title': event.title,
                                'start_time': time.strftime('%Y-%m-%d %H:%M', time.localtime(event.start_time)),
                                'reminder': f"{event.reminder_minutes} minutes before"
                            },
                            'message': f"Scheduled '{event.title}' for {time.strftime('%Y-%m-%d %H:%M', time.localtime(event.start_time))}"
                        }
                
            return {
                'success': False,
                'event_created': False,
                'message': "Could not parse calendar request. Try: 'Schedule meeting tomorrow at 2pm'"
            }
            
        except Exception as e:
            return {
                'success': False,
                'event_created': False,
                'error': str(e),
                'message': "Error processing calendar request"
            }
    
    def _extract_title_from_text(self, text: str) -> str:
        """Extract event title from natural language text"""
        # Simple title extraction
        text_lower = text.lower()
        
        # Remove common schedule words
        for word in ['schedule', 'add', 'create', 'set up', 'book', 'plan']:
            text_lower = text_lower.replace(word, '')
        
        # Remove time-related words
        for word in ['tomorrow', 'today', 'next week', 'at', 'pm', 'am', 'o\'clock']:
            text_lower = text_lower.replace(word, '')
        
        # Clean up and capitalize
        title = text_lower.strip()
        if not title:
            title = "Meeting"
        
        return title.title()

    async def add_event(self, event: CalendarEvent) -> bool:
        """Add an event to the calendar database"""
        try:
            with self.db_lock:
                conn = sqlite3.connect(str(self.db_path))
                cursor = conn.cursor()
                
                # Insert the event
                cursor.execute("""
                    INSERT INTO events 
                    (event_id, title, description, location, start_time, end_time, 
                     all_day, reminder_minutes, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    event.event_id, event.title, event.description, event.location,
                    event.start_time, event.end_time, event.all_day, event.reminder_minutes,
                    time.time(), time.time()
                ))
                
                conn.commit()
                conn.close()
                
                # Create reminder if needed
                if event.reminder_minutes > 0:
                    await self._schedule_reminder(event)
                
                # Update statistics
                self.stats['total_events'] += 1
                self.log(f"Successfully added event: {event.title} at {time.strftime('%Y-%m-%d %H:%M', time.localtime(event.start_time))}")
                
                return True
                
        except Exception as e:
            self.log(f"Failed to add event: {e}", "error")
            return False

    async def _schedule_reminder(self, event: CalendarEvent):
        """Schedule a reminder for an event"""
        try:
            reminder_time = event.start_time - (event.reminder_minutes * 60)
            
            if reminder_time > time.time():  # Only create future reminders
                reminder_id = f"{event.event_id}_reminder"
                
                reminder = Reminder(
                    reminder_id=reminder_id,
                    event_id=event.event_id,
                    reminder_time=reminder_time,
                    message=f"Reminder: {event.title} in {event.reminder_minutes} minutes"
                )
                
                # Save to database
                with self.db_lock:
                    conn = sqlite3.connect(str(self.db_path))
                    cursor = conn.cursor()
                    
                    cursor.execute("""
                        INSERT OR REPLACE INTO reminders 
                        (reminder_id, event_id, reminder_time, message, delivered, delivery_method)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        reminder.reminder_id, reminder.event_id, reminder.reminder_time,
                        reminder.message, reminder.delivered, reminder.delivery_method
                    ))
                    
                    conn.commit()
                    conn.close()
                    
                self.log(f"Scheduled reminder for event: {event.title}")
                
        except Exception as e:
            self.log(f"Failed to schedule reminder: {e}", "error")

    async def _reminder_loop(self):
        """Background loop to check for due reminders"""
        while True:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds
                
                current_time = time.time()
                
                # Get due reminders
                with self.db_lock:
                    conn = sqlite3.connect(str(self.db_path))
                    cursor = conn.cursor()
                    
                    cursor.execute("""
                        SELECT * FROM reminders 
                        WHERE reminder_time <= ? AND delivered = FALSE
                    """, (current_time,))
                    
                    columns = [description[0] for description in cursor.description]
                    due_reminders = [dict(zip(columns, row)) for row in cursor.fetchall()]
                    
                    conn.close()
                
                # Process due reminders
                for reminder_data in due_reminders:
                    await self._deliver_reminder(reminder_data)
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.log(f"Error in reminder loop: {e}", "error")
    
    async def _deliver_reminder(self, reminder_data: Dict):
        """Deliver a reminder"""
        try:
            # Emit reminder event
            self.emit_event(EventType.REMINDER_DUE, {
                'reminder_id': reminder_data['reminder_id'],
                'event_id': reminder_data['event_id'],
                'message': reminder_data['message']
            })
            
            # Mark as delivered
            with self.db_lock:
                conn = sqlite3.connect(str(self.db_path))
                cursor = conn.cursor()
                
                cursor.execute("""
                    UPDATE reminders SET delivered = TRUE WHERE reminder_id = ?
                """, (reminder_data['reminder_id'],))
                
                conn.commit()
                conn.close()
            
            self.log(f"Delivered reminder: {reminder_data['message']}")
            
        except Exception as e:
            self.log(f"Error delivering reminder: {e}", "error")
    
    def _extract_event_title(self, text: str) -> str:
        """Extract event title from text"""
        # Remove common calendar keywords
        keywords = ['schedule', 'add', 'create', 'book', 'set up', 'remind me', 'meeting', 'appointment']
        
        clean_text = text.lower()
        for keyword in keywords:
            clean_text = clean_text.replace(keyword, '').strip()
        
        # Remove time/date parts
        time_words = ['at', 'on', 'tomorrow', 'today', 'next', 'this', 'am', 'pm', 'o\'clock']
        words = clean_text.split()
        
        # Find where the time/date part starts
        title_words = []
        for word in words:
            if any(tw in word for tw in time_words) or word.isdigit() or ':' in word:
                break
            title_words.append(word)
        
        title = ' '.join(title_words).strip()
        return title.title() if title else "New Event"
    
    def _extract_reminder_text(self, text: str) -> str:
        """Extract reminder text"""
        # Remove reminder keywords
        keywords = ['remind me to', 'remind me', 'reminder', 'set reminder']
        
        clean_text = text.lower()
        for keyword in keywords:
            clean_text = clean_text.replace(keyword, '').strip()
        
        # Find content before time expressions
        time_words = ['at', 'on', 'tomorrow', 'today', 'next', 'this', 'in']
        words = clean_text.split()
        
        reminder_words = []
        for word in words:
            if any(tw in word for tw in time_words) or word.isdigit():
                break
            reminder_words.append(word)
        
        reminder_text = ' '.join(reminder_words).strip()
        return reminder_text.title() if reminder_text else "Reminder"
    
    def get_status(self) -> Dict[str, Any]:
        """Get module status"""
        try:
            with self.db_lock:
                conn = sqlite3.connect(str(self.db_path))
                cursor = conn.cursor()
                
                # Count events
                cursor.execute("SELECT COUNT(*) FROM events")
                total_events = cursor.fetchone()[0]
                
                # Count upcoming events
                now = time.time()
                cursor.execute("SELECT COUNT(*) FROM events WHERE start_time > ?", (now,))
                upcoming_events = cursor.fetchone()[0]
                
                # Count pending reminders
                cursor.execute("SELECT COUNT(*) FROM reminders WHERE delivered = FALSE")
                pending_reminders = cursor.fetchone()[0]
                
                conn.close()
            
            return {
                'module': 'calendar',
                'status': 'active' if self.is_loaded else 'inactive',
                'statistics': {
                    'total_events': total_events,
                    'upcoming_events': upcoming_events,
                    'pending_reminders': pending_reminders,
                    'database_path': str(self.db_path)
                },
                'capabilities': [
                    'Natural language scheduling',
                    'Smart reminders',
                    'Event management',
                    'Time parsing'
                ]
            }
            
        except Exception as e:
            return {
                'module': 'calendar',
                'status': 'error',
                'error': str(e)
            }
    
    # Recurring Events Functionality
    def parse_recurring_pattern(self, text: str) -> Dict[str, Any]:
        """Parse recurring pattern from natural language"""
        text_lower = text.lower()
        pattern = {}
        
        # Daily patterns
        if 'daily' in text_lower or 'every day' in text_lower:
            pattern = {
                'type': 'daily',
                'interval': 1,
                'days_of_week': None
            }
        
        # Weekly patterns
        elif 'weekly' in text_lower or 'every week' in text_lower:
            pattern = {
                'type': 'weekly',
                'interval': 1,
                'days_of_week': [datetime.now().weekday()]  # Same day each week
            }
        
        # Specific weekdays
        elif 'every monday' in text_lower:
            pattern = {'type': 'weekly', 'interval': 1, 'days_of_week': [0]}
        elif 'every tuesday' in text_lower:
            pattern = {'type': 'weekly', 'interval': 1, 'days_of_week': [1]}
        elif 'every wednesday' in text_lower:
            pattern = {'type': 'weekly', 'interval': 1, 'days_of_week': [2]}
        elif 'every thursday' in text_lower:
            pattern = {'type': 'weekly', 'interval': 1, 'days_of_week': [3]}
        elif 'every friday' in text_lower:
            pattern = {'type': 'weekly', 'interval': 1, 'days_of_week': [4]}
        elif 'every saturday' in text_lower:
            pattern = {'type': 'weekly', 'interval': 1, 'days_of_week': [5]}
        elif 'every sunday' in text_lower:
            pattern = {'type': 'weekly', 'interval': 1, 'days_of_week': [6]}
        
        # Monthly patterns
        elif 'monthly' in text_lower or 'every month' in text_lower:
            pattern = {
                'type': 'monthly',
                'interval': 1,
                'day_of_month': datetime.now().day
            }
        
        # Bi-weekly patterns
        elif 'bi-weekly' in text_lower or 'every two weeks' in text_lower or 'every other week' in text_lower:
            pattern = {
                'type': 'weekly',
                'interval': 2,
                'days_of_week': [datetime.now().weekday()]
            }
        
        return pattern
    
    async def create_recurring_event(self, base_event: CalendarEvent, pattern: Dict[str, Any], end_date: datetime = None) -> List[str]:
        """Create recurring events based on pattern"""
        created_events = []
        
        if not pattern:
            return created_events
        
        # Default end date: 1 year from now
        if not end_date:
            end_date = datetime.fromtimestamp(base_event.start_time) + timedelta(days=365)
        
        current_dt = datetime.fromtimestamp(base_event.start_time)
        pattern_type = pattern.get('type', 'none')
        interval = pattern.get('interval', 1)
        
        try:
            if pattern_type == 'daily':
                # Create daily recurring events
                while current_dt <= end_date:
                    if current_dt.timestamp() > base_event.start_time:  # Skip the original event
                        new_event = self._create_recurring_instance(base_event, current_dt, pattern)
                        await self._save_event(new_event)
                        created_events.append(new_event.event_id)
                    
                    current_dt += timedelta(days=interval)
            
            elif pattern_type == 'weekly':
                days_of_week = pattern.get('days_of_week', [current_dt.weekday()])
                
                # Find next occurrence for each day of week
                for target_weekday in days_of_week:
                    temp_dt = current_dt
                    
                    # Adjust to target weekday
                    days_ahead = target_weekday - temp_dt.weekday()
                    if days_ahead < 0:
                        days_ahead += 7
                    temp_dt += timedelta(days=days_ahead)
                    
                    # Create weekly instances
                    while temp_dt <= end_date:
                        if temp_dt.timestamp() > base_event.start_time:
                            new_event = self._create_recurring_instance(base_event, temp_dt, pattern)
                            await self._save_event(new_event)
                            created_events.append(new_event.event_id)
                        
                        temp_dt += timedelta(weeks=interval)
            
            elif pattern_type == 'monthly':
                day_of_month = pattern.get('day_of_month', current_dt.day)
                
                while current_dt <= end_date:
                    try:
                        # Try to create event on same day of month
                        next_month_dt = current_dt.replace(day=day_of_month)
                        if next_month_dt.month != current_dt.month:
                            # Move to next month
                            if current_dt.month == 12:
                                next_month_dt = current_dt.replace(year=current_dt.year + 1, month=1, day=day_of_month)
                            else:
                                next_month_dt = current_dt.replace(month=current_dt.month + 1, day=day_of_month)
                        
                        if next_month_dt.timestamp() > base_event.start_time and next_month_dt <= end_date:
                            new_event = self._create_recurring_instance(base_event, next_month_dt, pattern)
                            await self._save_event(new_event)
                            created_events.append(new_event.event_id)
                        
                        # Move to next month
                        if current_dt.month == 12:
                            current_dt = current_dt.replace(year=current_dt.year + 1, month=1)
                        else:
                            current_dt = current_dt.replace(month=current_dt.month + 1)
                            
                    except ValueError:  # Day doesn't exist in month (e.g., Feb 31st)
                        # Use last day of month instead
                        if current_dt.month == 12:
                            current_dt = current_dt.replace(year=current_dt.year + 1, month=1)
                        else:
                            current_dt = current_dt.replace(month=current_dt.month + 1)
                        
                        last_day = cal.monthrange(current_dt.year, current_dt.month)[1]
                        next_month_dt = current_dt.replace(day=min(day_of_month, last_day))
                        
                        if next_month_dt.timestamp() > base_event.start_time and next_month_dt <= end_date:
                            new_event = self._create_recurring_instance(base_event, next_month_dt, pattern)
                            await self._save_event(new_event)
                            created_events.append(new_event.event_id)
        
        except Exception as e:
            self.log(f"Error creating recurring events: {e}", "error")
        
        return created_events
    
    def _create_recurring_instance(self, base_event: CalendarEvent, occurrence_dt: datetime, pattern: Dict[str, Any]) -> CalendarEvent:
        """Create a single instance of a recurring event"""
        import hashlib
        
        # Calculate duration
        duration = base_event.end_time - base_event.start_time
        
        # Create new event ID
        instance_id = hashlib.md5(f"{base_event.event_id}_{occurrence_dt.timestamp()}".encode()).hexdigest()[:12]
        
        new_event = CalendarEvent(
            event_id=instance_id,
            title=base_event.title,
            description=f"{base_event.description} (Recurring)",
            start_time=occurrence_dt.timestamp(),
            end_time=occurrence_dt.timestamp() + duration,
            all_day=base_event.all_day,
            location=base_event.location,
            reminder_minutes=base_event.reminder_minutes,
            recurring=base_event.recurring,
            recurring_until=base_event.recurring_until,
            tags=base_event.tags.copy() if base_event.tags else [],
            event_type=base_event.event_type,
            priority=base_event.priority,
            attendees=base_event.attendees.copy() if base_event.attendees else [],
            recurring_pattern=pattern
        )
        
        return new_event
    
    async def handle_recurring_request(self, text: str) -> Dict[str, Any]:
        """Handle requests for recurring events"""
        try:
            # Parse the recurring pattern
            pattern = self.parse_recurring_pattern(text)
            
            if not pattern:
                return {
                    'success': False,
                    'error': 'Could not parse recurring pattern from your request',
                    'type': 'parse_error'
                }
            
            # Parse the base event details
            event_title = self._extract_event_title(text)
            event_datetime = self.parser.parse_datetime(text)
            
            if not event_datetime:
                return {
                    'success': False,
                    'error': 'Could not parse date/time from your request',
                    'type': 'parse_error'
                }
            
            # Determine event type from text
            event_type = 'meeting'  # default
            if 'standup' in text.lower() or 'daily' in text.lower():
                event_type = 'task'
            elif 'appointment' in text.lower():
                event_type = 'appointment'
            elif 'personal' in text.lower():
                event_type = 'personal'
            
            # Create base event
            event_id = hashlib.md5(f"{event_title}_{event_datetime.timestamp()}".encode()).hexdigest()[:12]
            end_datetime = event_datetime + timedelta(hours=1)  # Default 1 hour
            
            base_event = CalendarEvent(
                event_id=event_id,
                title=event_title,
                description=f"Recurring event created from: {text}",
                start_time=event_datetime.timestamp(),
                end_time=end_datetime.timestamp(),
                event_type=event_type,
                recurring=pattern.get('type', 'none'),
                recurring_pattern=pattern
            )
            
            # Save the base event
            await self._save_event(base_event)
            
            # Create recurring instances
            recurring_ids = await self.create_recurring_event(base_event, pattern)
            
            return {
                'success': True,
                'message': f"Created recurring '{event_title}' starting {event_datetime.strftime('%A, %B %d at %I:%M %p')} ({len(recurring_ids) + 1} total instances)",
                'event_id': event_id,
                'recurring_instances': len(recurring_ids),
                'pattern': pattern,
                'type': 'recurring_event_created'
            }
            
        except Exception as e:
            self.log(f"Error handling recurring request: {e}", "error")
            return {
                'success': False,
                'error': f"Failed to create recurring event: {str(e)}",
                'type': 'recurring_error'
            }