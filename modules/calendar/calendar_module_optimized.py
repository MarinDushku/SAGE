"""
Optimized Calendar Module - Smart scheduling and reminder system for SAGE
Memory-efficient, secure, and performant calendar operations
"""

import asyncio
import json
import sqlite3
import time
import logging
import re
import hashlib
import calendar as cal
from typing import Dict, Any, Optional, List, Tuple, Union
from pathlib import Path
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, field
from collections import defaultdict
from contextlib import asynccontextmanager, contextmanager
from functools import lru_cache
import threading
import weakref

from modules import BaseModule, EventType, Event

# Constants for optimization
MAX_RECURRING_INSTANCES = 365  # Limit recurring events to 1 year
CACHE_SIZE = 256
MAX_EVENTS_QUERY = 10000
DB_TIMEOUT = 30.0
MAX_STRING_LENGTH = 1000

# Try to import date parsing libraries with error handling
try:
    import dateutil.parser as date_parser
    from dateutil.relativedelta import relativedelta
    DATEUTIL_AVAILABLE = True
except ImportError:
    DATEUTIL_AVAILABLE = False
    logging.warning("dateutil not available - using basic date parsing")


@dataclass
class CalendarEvent:
    """Optimized data class for calendar events with validation"""
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
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    tags: List[str] = field(default_factory=list)
    event_type: str = "meeting"  # meeting, appointment, task, personal, work
    priority: str = "medium"  # low, medium, high, urgent
    attendees: List[str] = field(default_factory=list)
    recurring_pattern: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate and sanitize data on initialization"""
        # Validate and sanitize strings
        self.title = self._sanitize_string(self.title, 100)
        self.description = self._sanitize_string(self.description, MAX_STRING_LENGTH)
        self.location = self._sanitize_string(self.location, 200)
        self.event_type = self._sanitize_string(self.event_type, 20)
        self.priority = self._sanitize_string(self.priority, 20)
        
        # Validate enum values
        if self.recurring not in ["none", "daily", "weekly", "monthly", "yearly"]:
            self.recurring = "none"
        
        if self.event_type not in ["meeting", "appointment", "task", "personal", "work"]:
            self.event_type = "meeting"
            
        if self.priority not in ["low", "medium", "high", "urgent"]:
            self.priority = "medium"
        
        # Validate time constraints
        if self.start_time >= self.end_time:
            self.end_time = self.start_time + 3600  # Default 1 hour
        
        # Validate reminder minutes
        if not 0 <= self.reminder_minutes <= 10080:  # Max 1 week
            self.reminder_minutes = 15
        
        # Sanitize lists
        self.tags = [self._sanitize_string(tag, 50) for tag in self.tags if tag][:10]  # Max 10 tags
        self.attendees = [self._sanitize_string(att, 100) for att in self.attendees if att][:50]  # Max 50 attendees
    
    @staticmethod
    def _sanitize_string(value: str, max_length: int) -> str:
        """Sanitize string input to prevent injection and limit length"""
        if not isinstance(value, str):
            return ""
        
        # Remove potentially dangerous characters
        dangerous_chars = ['<', '>', '"', "'", '&', ';', '|', '`', '\0']
        sanitized = value
        for char in dangerous_chars:
            sanitized = sanitized.replace(char, '')
        
        # Limit length and strip whitespace
        return sanitized.strip()[:max_length]


@dataclass
class Reminder:
    """Optimized data class for reminders"""
    reminder_id: str
    event_id: str
    reminder_time: float
    message: str
    delivered: bool = False
    delivery_method: str = "notification"  # notification, voice, both
    
    def __post_init__(self):
        """Validate reminder data"""
        self.message = CalendarEvent._sanitize_string(self.message, 500)
        if self.delivery_method not in ["notification", "voice", "both"]:
            self.delivery_method = "notification"


class OptimizedNaturalLanguageParser:
    """Memory-efficient natural language parser with caching"""
    
    def __init__(self):
        # Pre-compile regex patterns for performance
        self.time_patterns = [
            (re.compile(r'\b(\d{1,2}):(\d{2})\s*(am|pm)?\b', re.I), self._parse_time),
            (re.compile(r'\b(\d{1,2})\s*(am|pm)\b', re.I), self._parse_time_simple),
            (re.compile(r'\bmidnight\b', re.I), lambda m: (0, 0)),
            (re.compile(r'\bnoon\b', re.I), lambda m: (12, 0)),
            (re.compile(r'\bin\s+(\d+)\s*(minute|minutes|min|hour|hours|hr|day|days)\b', re.I), self._parse_relative_time),
        ]
        
        self.date_patterns = [
            (re.compile(r'\btoday\b', re.I), lambda m: datetime.now().date()),
            (re.compile(r'\btomorrow\b', re.I), lambda m: (datetime.now() + timedelta(days=1)).date()),
            (re.compile(r'\byesterday\b', re.I), lambda m: (datetime.now() - timedelta(days=1)).date()),
            (re.compile(r'\bnext\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b', re.I), self._parse_next_weekday),
            (re.compile(r'\bthis\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b', re.I), self._parse_this_weekday),
        ]
        
        # Use frozenset for faster lookup
        self.weekdays = {
            'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
            'friday': 4, 'saturday': 5, 'sunday': 6
        }
    
    @lru_cache(maxsize=CACHE_SIZE)
    def parse_datetime(self, text: str) -> Optional[datetime]:
        """Parse datetime from text with caching"""
        if not isinstance(text, str) or len(text) > 1000:
            return None
        
        text_lower = text.lower().strip()
        
        # Use dateutil if available for complex parsing
        if DATEUTIL_AVAILABLE:
            try:
                return date_parser.parse(text_lower, fuzzy=True, default=datetime.now())
            except (ValueError, OverflowError):
                pass
        
        # Fallback to pattern matching
        parsed_date = None
        parsed_time = None
        
        # Parse date
        for pattern, parser in self.date_patterns:
            match = pattern.search(text_lower)
            if match:
                try:
                    parsed_date = parser(match)
                    break
                except (ValueError, AttributeError):
                    continue
        
        # Parse time
        for pattern, parser in self.time_patterns:
            match = pattern.search(text_lower)
            if match:
                try:
                    result = parser(match)
                    if isinstance(result, tuple) and len(result) == 2:
                        parsed_time = result
                    elif isinstance(result, datetime):
                        return result
                    break
                except (ValueError, AttributeError):
                    continue
        
        # Combine date and time
        if parsed_date:
            base_date = datetime.combine(parsed_date, datetime.min.time())
            if parsed_time:
                base_date = base_date.replace(hour=parsed_time[0], minute=parsed_time[1])
            return base_date
        
        return None
    
    def _parse_time(self, match) -> Tuple[int, int]:
        """Parse time in HH:MM AM/PM format"""
        hour = int(match.group(1))
        minute = int(match.group(2))
        ampm = match.group(3)
        
        # Validate input
        if not 1 <= hour <= 12 or not 0 <= minute <= 59:
            raise ValueError("Invalid time")
        
        if ampm and ampm.lower() == 'pm' and hour != 12:
            hour += 12
        elif ampm and ampm.lower() == 'am' and hour == 12:
            hour = 0
            
        return (hour, minute)
    
    def _parse_time_simple(self, match) -> Tuple[int, int]:
        """Parse time in H AM/PM format"""
        hour = int(match.group(1))
        ampm = match.group(2)
        
        if not 1 <= hour <= 12:
            raise ValueError("Invalid hour")
        
        if ampm.lower() == 'pm' and hour != 12:
            hour += 12
        elif ampm.lower() == 'am' and hour == 12:
            hour = 0
            
        return (hour, 0)
    
    def _parse_relative_time(self, match) -> datetime:
        """Parse relative time expressions"""
        amount = int(match.group(1))
        unit = match.group(2).lower()
        
        # Validate input
        if amount < 0 or amount > 1000:
            raise ValueError("Invalid amount")
        
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
        if weekday_name not in self.weekdays:
            raise ValueError("Invalid weekday")
            
        target_weekday = self.weekdays[weekday_name]
        today = datetime.now().date()
        days_ahead = target_weekday - today.weekday()
        if days_ahead <= 0:
            days_ahead += 7
            
        return today + timedelta(days=days_ahead)
    
    def _parse_this_weekday(self, match):
        """Parse 'this Monday' etc."""
        weekday_name = match.group(1).lower()
        if weekday_name not in self.weekdays:
            raise ValueError("Invalid weekday")
            
        target_weekday = self.weekdays[weekday_name]
        today = datetime.now().date()
        days_ahead = target_weekday - today.weekday()
        if days_ahead < 0:
            days_ahead += 7
            
        return today + timedelta(days=days_ahead)


class OptimizedCalendarModule(BaseModule):
    """Optimized calendar module with enhanced security and performance"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        
        # Configuration with defaults
        self.db_path = Path(config.get('database_path', 'data/calendar.db'))
        self.reminder_interval = config.get('reminder_check_interval', 60)
        self.max_events_per_query = config.get('max_events_per_query', MAX_EVENTS_QUERY)
        
        # Thread safety
        self.db_lock = threading.RLock()  # Reentrant lock
        self._connection_pool = {}
        self._pool_lock = threading.Lock()
        
        # Optimization components
        self.parser = OptimizedNaturalLanguageParser()
        self.reminder_scheduler = None
        self._event_cache = {}
        self._cache_lock = threading.RLock()
        
        # Monitoring
        self.stats = defaultdict(int)
        self._weak_refs = weakref.WeakSet()
        
        # Performance optimizations
        self._prepared_statements = {}
        self._batch_operations = []
        
    async def initialize(self) -> bool:
        """Initialize the optimized calendar module"""
        try:
            self.log("Initializing optimized calendar module")
            
            # Initialize database with optimizations
            self._init_database_optimized()
            
            # Start optimized reminder scheduler
            if self.reminder_interval > 0:
                self.reminder_scheduler = asyncio.create_task(
                    self._optimized_reminder_scheduler()
                )
            
            self.is_loaded = True
            self.log("Optimized calendar module initialized successfully")
            return True
            
        except Exception as e:
            self.log(f"Failed to initialize calendar module: {e}", "error")
            return False
    
    def _init_database_optimized(self):
        """Initialize database with performance optimizations"""
        with self._get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Enable optimizations
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.execute("PRAGMA cache_size=10000")
            cursor.execute("PRAGMA temp_store=MEMORY")
            cursor.execute("PRAGMA mmap_size=268435456")  # 256MB
            
            # Create optimized events table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    event_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL CHECK(length(title) <= 100),
                    description TEXT CHECK(length(description) <= 1000),
                    start_time REAL NOT NULL,
                    end_time REAL NOT NULL,
                    all_day BOOLEAN DEFAULT FALSE,
                    location TEXT CHECK(length(location) <= 200),
                    reminder_minutes INTEGER DEFAULT 15 CHECK(reminder_minutes >= 0 AND reminder_minutes <= 10080),
                    recurring TEXT DEFAULT 'none' CHECK(recurring IN ('none', 'daily', 'weekly', 'monthly', 'yearly')),
                    recurring_until REAL,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    tags TEXT,
                    event_type TEXT DEFAULT 'meeting' CHECK(event_type IN ('meeting', 'appointment', 'task', 'personal', 'work')),
                    priority TEXT DEFAULT 'medium' CHECK(priority IN ('low', 'medium', 'high', 'urgent')),
                    attendees TEXT,
                    recurring_pattern TEXT,
                    CHECK(start_time < end_time)
                )
            """)
            
            # Create optimized indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_start_time ON events(start_time)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_recurring ON events(recurring)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_priority ON events(priority)")
            
            # Create reminders table with constraints
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS reminders (
                    reminder_id TEXT PRIMARY KEY,
                    event_id TEXT NOT NULL,
                    reminder_time REAL NOT NULL,
                    message TEXT NOT NULL CHECK(length(message) <= 500),
                    delivered BOOLEAN DEFAULT FALSE,
                    delivery_method TEXT DEFAULT 'notification' CHECK(delivery_method IN ('notification', 'voice', 'both')),
                    FOREIGN KEY (event_id) REFERENCES events (event_id) ON DELETE CASCADE
                )
            """)
            
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_reminders_time ON reminders(reminder_time)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_reminders_delivered ON reminders(delivered)")
            
            # Migrate existing data safely
            self._migrate_database_safely(cursor)
            
            conn.commit()
    
    @contextmanager
    def _get_db_connection(self):
        """Get optimized database connection with pooling"""
        thread_id = threading.get_ident()
        
        with self._pool_lock:
            if thread_id not in self._connection_pool:
                conn = sqlite3.connect(
                    str(self.db_path), 
                    timeout=DB_TIMEOUT,
                    check_same_thread=False
                )
                conn.row_factory = sqlite3.Row  # Enable column access by name
                self._connection_pool[thread_id] = conn
            
            conn = self._connection_pool[thread_id]
        
        try:
            yield conn
        except Exception:
            conn.rollback()
            raise
        finally:
            # Keep connection in pool for reuse
            pass
    
    def _migrate_database_safely(self, cursor):
        """Safe database migration with error handling"""
        try:
            # Check existing columns
            cursor.execute("PRAGMA table_info(events)")
            columns = {col[1] for col in cursor.fetchall()}
            
            # Add missing columns with proper error handling
            migrations = [
                ("event_type", "ALTER TABLE events ADD COLUMN event_type TEXT DEFAULT 'meeting'"),
                ("priority", "ALTER TABLE events ADD COLUMN priority TEXT DEFAULT 'medium'"),
                ("attendees", "ALTER TABLE events ADD COLUMN attendees TEXT DEFAULT '[]'"),
                ("recurring_pattern", "ALTER TABLE events ADD COLUMN recurring_pattern TEXT DEFAULT '{}'"),
            ]
            
            for column_name, migration_sql in migrations:
                if column_name not in columns:
                    cursor.execute(migration_sql)
                    self.log(f"Added {column_name} column to events table")
                    
        except Exception as e:
            self.log(f"Database migration error: {e}", "error")
    
    @lru_cache(maxsize=CACHE_SIZE)
    def _get_events_in_range_cached(self, start_time: float, end_time: float, limit: int = MAX_EVENTS_QUERY) -> Tuple[Dict, ...]:
        """Get events in range with caching and security"""
        try:
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Use parameterized query for security
                cursor.execute("""
                    SELECT * FROM events 
                    WHERE start_time >= ? AND start_time <= ?
                    ORDER BY start_time
                    LIMIT ?
                """, (start_time, end_time, limit))
                
                events = []
                for row in cursor.fetchall():
                    # Convert Row to dict and sanitize
                    event_dict = dict(row)
                    
                    # Parse JSON fields safely
                    try:
                        event_dict['tags'] = json.loads(event_dict.get('tags', '[]'))
                    except (json.JSONDecodeError, TypeError):
                        event_dict['tags'] = []
                    
                    try:
                        event_dict['attendees'] = json.loads(event_dict.get('attendees', '[]'))
                    except (json.JSONDecodeError, TypeError):
                        event_dict['attendees'] = []
                    
                    try:
                        event_dict['recurring_pattern'] = json.loads(event_dict.get('recurring_pattern', '{}'))
                    except (json.JSONDecodeError, TypeError):
                        event_dict['recurring_pattern'] = {}
                    
                    events.append(event_dict)
                
                return tuple(events)  # Immutable for caching
                
        except Exception as e:
            self.log(f"Error getting events in range: {e}", "error")
            return tuple()
    
    async def _save_event_optimized(self, event: CalendarEvent) -> bool:
        """Save event with optimized batch operations"""
        try:
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Use prepared statement for better performance
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
                
                # Clear relevant caches
                self._clear_related_caches(event.start_time)
                
                return True
                
        except sqlite3.Error as e:
            self.log(f"Database error saving event: {e}", "error")
            return False
        except Exception as e:
            self.log(f"Error saving event: {e}", "error")
            return False
    
    def _clear_related_caches(self, event_time: float):
        """Clear caches related to a specific time range"""
        # Clear LRU cache
        self._get_events_in_range_cached.cache_clear()
        
        # Clear parser cache for events around this time
        self.parser.parse_datetime.cache_clear()
    
    def parse_recurring_pattern_optimized(self, text: str) -> Dict[str, Any]:
        """Optimized recurring pattern parsing with validation"""
        if not isinstance(text, str) or len(text) > 200:
            return {}
        
        text_lower = text.lower().strip()
        
        # Use more efficient pattern matching
        patterns = {
            'daily': ['daily', 'every day'],
            'weekly': ['weekly', 'every week'],
            'monthly': ['monthly', 'every month'],
            'bi-weekly': ['bi-weekly', 'every two weeks', 'every other week']
        }
        
        # Weekday patterns
        weekday_patterns = {
            f'every {day}': {'type': 'weekly', 'interval': 1, 'days_of_week': [i]}
            for i, day in enumerate(['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'])
        }
        
        # Check weekday patterns first (more specific)
        for pattern, config in weekday_patterns.items():
            if pattern in text_lower:
                return config
        
        # Check general patterns
        for pattern_type, phrases in patterns.items():
            if any(phrase in text_lower for phrase in phrases):
                if pattern_type == 'daily':
                    return {'type': 'daily', 'interval': 1}
                elif pattern_type == 'weekly':
                    return {'type': 'weekly', 'interval': 1, 'days_of_week': [datetime.now().weekday()]}
                elif pattern_type == 'monthly':
                    return {'type': 'monthly', 'interval': 1, 'day_of_month': datetime.now().day}
                elif pattern_type == 'bi-weekly':
                    return {'type': 'weekly', 'interval': 2, 'days_of_week': [datetime.now().weekday()]}
        
        return {}
    
    async def create_recurring_event_optimized(self, base_event: CalendarEvent, pattern: Dict[str, Any], 
                                             end_date: Optional[datetime] = None) -> List[str]:
        """Create recurring events with memory and performance optimizations"""
        if not pattern:
            return []
        
        created_events = []
        
        # Limit the number of instances to prevent memory issues
        if not end_date:
            end_date = datetime.fromtimestamp(base_event.start_time) + timedelta(days=MAX_RECURRING_INSTANCES)
        
        current_dt = datetime.fromtimestamp(base_event.start_time)
        pattern_type = pattern.get('type', 'none')
        interval = max(1, min(pattern.get('interval', 1), 52))  # Reasonable limits
        
        instances_created = 0
        max_instances = min(MAX_RECURRING_INSTANCES, 1000)  # Hard limit
        
        try:
            if pattern_type == 'daily':
                while current_dt <= end_date and instances_created < max_instances:
                    if current_dt.timestamp() > base_event.start_time:
                        new_event = self._create_recurring_instance_optimized(base_event, current_dt, pattern)
                        if await self._save_event_optimized(new_event):
                            created_events.append(new_event.event_id)
                            instances_created += 1
                    
                    current_dt += timedelta(days=interval)
            
            elif pattern_type == 'weekly':
                days_of_week = pattern.get('days_of_week', [current_dt.weekday()])
                days_of_week = [d for d in days_of_week if 0 <= d <= 6]  # Validate
                
                for target_weekday in days_of_week:
                    temp_dt = current_dt
                    days_ahead = target_weekday - temp_dt.weekday()
                    if days_ahead < 0:
                        days_ahead += 7
                    temp_dt += timedelta(days=days_ahead)
                    
                    week_instances = 0
                    while temp_dt <= end_date and week_instances < max_instances // len(days_of_week):
                        if temp_dt.timestamp() > base_event.start_time:
                            new_event = self._create_recurring_instance_optimized(base_event, temp_dt, pattern)
                            if await self._save_event_optimized(new_event):
                                created_events.append(new_event.event_id)
                                week_instances += 1
                        
                        temp_dt += timedelta(weeks=interval)
            
            elif pattern_type == 'monthly':
                day_of_month = max(1, min(pattern.get('day_of_month', current_dt.day), 31))
                
                while current_dt <= end_date and instances_created < max_instances:
                    try:
                        # Handle month boundaries safely
                        if current_dt.month == 12:
                            next_month_dt = current_dt.replace(year=current_dt.year + 1, month=1, day=1)
                        else:
                            next_month_dt = current_dt.replace(month=current_dt.month + 1, day=1)
                        
                        # Adjust day for months with fewer days
                        max_day = cal.monthrange(next_month_dt.year, next_month_dt.month)[1]
                        actual_day = min(day_of_month, max_day)
                        next_month_dt = next_month_dt.replace(day=actual_day)
                        
                        if next_month_dt.timestamp() > base_event.start_time and next_month_dt <= end_date:
                            new_event = self._create_recurring_instance_optimized(base_event, next_month_dt, pattern)
                            if await self._save_event_optimized(new_event):
                                created_events.append(new_event.event_id)
                                instances_created += 1
                        
                        current_dt = next_month_dt
                        
                    except ValueError as e:
                        self.log(f"Date calculation error in monthly recurring: {e}", "warning")
                        break
        
        except Exception as e:
            self.log(f"Error creating recurring events: {e}", "error")
        
        self.log(f"Created {len(created_events)} recurring instances")
        return created_events
    
    def _create_recurring_instance_optimized(self, base_event: CalendarEvent, occurrence_dt: datetime, 
                                           pattern: Dict[str, Any]) -> CalendarEvent:
        """Create optimized recurring event instance"""
        # Calculate duration efficiently
        duration = base_event.end_time - base_event.start_time
        
        # Generate secure event ID
        instance_id = hashlib.sha256(
            f"{base_event.event_id}_{occurrence_dt.timestamp()}_{time.time()}".encode()
        ).hexdigest()[:16]  # Shorter but still unique
        
        return CalendarEvent(
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
            tags=base_event.tags.copy(),
            event_type=base_event.event_type,
            priority=base_event.priority,
            attendees=base_event.attendees.copy(),
            recurring_pattern=pattern.copy()
        )
    
    async def handle_recurring_request_optimized(self, text: str) -> Dict[str, Any]:
        """Handle recurring event requests with optimized processing"""
        try:
            # Input validation
            if not isinstance(text, str) or len(text.strip()) < 3:
                return {
                    'success': False,
                    'error': 'Invalid input text',
                    'type': 'validation_error'
                }
            
            if len(text) > 500:  # Prevent abuse
                return {
                    'success': False,
                    'error': 'Input text too long',
                    'type': 'validation_error'
                }
            
            # Parse patterns efficiently
            pattern = self.parse_recurring_pattern_optimized(text)
            if not pattern:
                return {
                    'success': False,
                    'error': 'Could not parse recurring pattern from your request',
                    'type': 'parse_error'
                }
            
            # Parse event details with timeout
            event_title = self._extract_event_title_safe(text)
            event_datetime = self.parser.parse_datetime(text)
            
            if not event_datetime:
                return {
                    'success': False,
                    'error': 'Could not parse date/time from your request',
                    'type': 'parse_error'
                }
            
            # Validate datetime is not too far in the past/future
            now = datetime.now()
            if event_datetime < now - timedelta(days=1) or event_datetime > now + timedelta(days=1095):  # 3 years
                return {
                    'success': False,
                    'error': 'Event date/time is outside acceptable range',
                    'type': 'validation_error'
                }
            
            # Determine event type securely
            event_type = self._determine_event_type_safe(text)
            
            # Create base event with validation
            event_id = hashlib.sha256(f"{event_title}_{event_datetime.timestamp()}_{time.time()}".encode()).hexdigest()[:16]
            end_datetime = event_datetime + timedelta(hours=1)  # Default duration
            
            base_event = CalendarEvent(
                event_id=event_id,
                title=event_title,
                description=f"Recurring event created from: {text[:100]}",
                start_time=event_datetime.timestamp(),
                end_time=end_datetime.timestamp(),
                event_type=event_type,
                recurring=pattern.get('type', 'none'),
                recurring_pattern=pattern
            )
            
            # Save base event
            if not await self._save_event_optimized(base_event):
                return {
                    'success': False,
                    'error': 'Failed to save base event',
                    'type': 'database_error'
                }
            
            # Create recurring instances with limits
            recurring_ids = await self.create_recurring_event_optimized(base_event, pattern)
            
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
                'error': 'Internal error processing recurring event request',
                'type': 'internal_error'
            }
    
    def _extract_event_title_safe(self, text: str) -> str:
        """Safely extract event title with validation"""
        # Remove common schedule words
        keywords_to_remove = ['schedule', 'add', 'create', 'set up', 'book', 'plan', 'daily', 'weekly', 'monthly', 'every', 'recurring']
        
        clean_text = text.lower()
        for keyword in keywords_to_remove:
            clean_text = clean_text.replace(keyword, ' ').strip()
        
        # Remove time/date parts more carefully
        time_words = ['at', 'on', 'tomorrow', 'today', 'next', 'this', 'am', 'pm', "o'clock"]
        words = clean_text.split()
        
        # Find where the time/date part starts
        title_words = []
        for word in words:
            if any(tw in word for tw in time_words) or word.isdigit() or ':' in word:
                break
            if len(word) > 0 and word.isalpha():
                title_words.append(word)
        
        title = ' '.join(title_words[:10]).strip()  # Limit to 10 words
        
        # Validate and sanitize
        if not title or len(title) < 2:
            title = "New Event"
        
        return CalendarEvent._sanitize_string(title.title(), 100)
    
    def _determine_event_type_safe(self, text: str) -> str:
        """Safely determine event type from text"""
        text_lower = text.lower()
        
        type_indicators = {
            'task': ['standup', 'scrum', 'daily', 'checkin'],
            'appointment': ['appointment', 'doctor', 'dentist', 'medical'],
            'personal': ['personal', 'birthday', 'anniversary', 'family'],
            'work': ['work', 'office', 'business', 'professional']
        }
        
        for event_type, indicators in type_indicators.items():
            if any(indicator in text_lower for indicator in indicators):
                return event_type
        
        return 'meeting'  # Default
    
    async def _optimized_reminder_scheduler(self):
        """Optimized reminder scheduler with better error handling"""
        self.log("Starting optimized reminder scheduler")
        
        while self.is_loaded:
            try:
                # Check reminders efficiently
                await self._check_and_deliver_reminders()
                
                # Sleep with cancellation support
                await asyncio.sleep(self.reminder_interval)
                
            except asyncio.CancelledError:
                self.log("Reminder scheduler cancelled")
                break
            except Exception as e:
                self.log(f"Error in reminder scheduler: {e}", "error")
                await asyncio.sleep(min(self.reminder_interval, 60))  # Fallback delay
    
    async def _check_and_deliver_reminders(self):
        """Optimized reminder checking with batch processing"""
        try:
            current_time = time.time()
            
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Get pending reminders efficiently
                cursor.execute("""
                    SELECT reminder_id, event_id, reminder_time, message, delivery_method
                    FROM reminders 
                    WHERE delivered = FALSE AND reminder_time <= ?
                    ORDER BY reminder_time
                    LIMIT 100
                """, (current_time,))
                
                reminders = cursor.fetchall()
                
                if not reminders:
                    return
                
                # Process reminders in batch
                delivered_ids = []
                for reminder in reminders:
                    try:
                        await self._deliver_reminder_optimized(dict(reminder))
                        delivered_ids.append(reminder['reminder_id'])
                    except Exception as e:
                        self.log(f"Error delivering reminder {reminder['reminder_id']}: {e}", "error")
                
                # Update delivered status in batch
                if delivered_ids:
                    placeholders = ','.join('?' * len(delivered_ids))
                    cursor.execute(f"""
                        UPDATE reminders SET delivered = TRUE 
                        WHERE reminder_id IN ({placeholders})
                    """, delivered_ids)
                    
                    conn.commit()
                    self.log(f"Delivered {len(delivered_ids)} reminders")
                
        except Exception as e:
            self.log(f"Error checking reminders: {e}", "error")
    
    async def _deliver_reminder_optimized(self, reminder_data: Dict):
        """Deliver reminder with optimized handling"""
        try:
            # Emit event for other modules to handle
            self.emit_event(EventType.REMINDER_DUE, {
                'reminder_id': reminder_data['reminder_id'],
                'event_id': reminder_data['event_id'],
                'message': CalendarEvent._sanitize_string(reminder_data['message'], 500),
                'delivery_method': reminder_data.get('delivery_method', 'notification'),
                'reminder_time': reminder_data['reminder_time']
            })
            
        except Exception as e:
            self.log(f"Error delivering reminder: {e}", "error")
            raise
    
    async def shutdown(self) -> bool:
        """Optimized shutdown with proper cleanup"""
        try:
            self.log("Shutting down optimized calendar module")
            
            # Cancel reminder scheduler
            if self.reminder_scheduler and not self.reminder_scheduler.done():
                self.reminder_scheduler.cancel()
                try:
                    await asyncio.wait_for(self.reminder_scheduler, timeout=5.0)
                except (asyncio.CancelledError, asyncio.TimeoutError):
                    pass
            
            # Clear caches
            self._get_events_in_range_cached.cache_clear()
            self.parser.parse_datetime.cache_clear()
            self._event_cache.clear()
            
            # Close database connections
            with self._pool_lock:
                for conn in self._connection_pool.values():
                    try:
                        conn.close()
                    except:
                        pass
                self._connection_pool.clear()
            
            self.is_loaded = False
            self.log("Calendar module shutdown complete")
            return True
            
        except Exception as e:
            self.log(f"Error during shutdown: {e}", "error")
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """Get optimized module status with performance metrics"""
        try:
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Get counts efficiently
                cursor.execute("SELECT COUNT(*) as total FROM events")
                total_events = cursor.fetchone()['total']
                
                cursor.execute("SELECT COUNT(*) as upcoming FROM events WHERE start_time > ?", (time.time(),))
                upcoming_events = cursor.fetchone()['upcoming']
                
                cursor.execute("SELECT COUNT(*) as pending FROM reminders WHERE delivered = FALSE")
                pending_reminders = cursor.fetchone()['pending']
            
            return {
                'module': 'calendar_optimized',
                'status': 'active' if self.is_loaded else 'inactive',
                'statistics': {
                    'total_events': total_events,
                    'upcoming_events': upcoming_events,
                    'pending_reminders': pending_reminders,
                    'database_path': str(self.db_path),
                    'cache_size': len(self._event_cache),
                    'connection_pool_size': len(self._connection_pool)
                },
                'capabilities': [
                    'Optimized natural language scheduling',
                    'Smart reminders with batch processing',
                    'Secure event management',
                    'Efficient recurring events',
                    'Performance-tuned database operations',
                    'Memory-efficient caching'
                ],
                'performance_metrics': {
                    'cache_hit_ratio': getattr(self._get_events_in_range_cached, 'cache_info', lambda: None)(),
                    'parser_cache_info': getattr(self.parser.parse_datetime, 'cache_info', lambda: None)()
                }
            }
            
        except Exception as e:
            return {
                'module': 'calendar_optimized',
                'status': 'error',
                'error': str(e)
            }