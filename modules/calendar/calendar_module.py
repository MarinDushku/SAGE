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
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = time.time()
        if self.updated_at is None:
            self.updated_at = time.time()
        if self.tags is None:
            self.tags = []


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
            
            conn.commit()
            conn.close()
    
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
                 created_at, updated_at, tags)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                event.event_id, event.title, event.description,
                event.start_time, event.end_time, event.all_day,
                event.location, event.reminder_minutes, event.recurring,
                event.recurring_until, event.created_at, event.updated_at,
                json.dumps(event.tags)
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
                parsed = self.parser.parse_datetime(text)
                
                if parsed['datetime']:
                    # Extract title from text
                    title = self._extract_title_from_text(text)
                    
                    # Create event
                    event = CalendarEvent(
                        title=title or "New Event",
                        start_time=parsed['datetime'],
                        end_time=parsed['datetime'] + 3600,  # 1 hour default
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