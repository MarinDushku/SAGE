"""
Meeting Manager - Simplified calendar system with conversational interface
"""

import sqlite3
import time
import json
import hashlib
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
from datetime import datetime, timedelta, date
from dataclasses import dataclass, asdict
import logging
import threading


@dataclass
class Meeting:
    """Simplified meeting data structure"""
    id: Optional[int] = None
    title: str = ""
    date: str = ""              # YYYY-MM-DD format
    time: str = ""              # HH:MM format (24-hour)
    meeting_type: str = "in_person"  # online, in_person, phone
    location: str = ""          # Physical location or meeting link
    duration: int = 60          # Duration in minutes
    reminder_minutes: int = 15  # Reminder time before meeting
    notes: str = ""
    created_at: Optional[str] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()


class MeetingManager:
    """Simplified meeting management with conversational interface"""
    
    def __init__(self, db_path: str = "data/calendar.db", logger=None):
        self.db_path = Path(db_path)
        self.db_lock = threading.Lock()
        self.logger = logger or logging.getLogger(__name__)
        
        # Conversation state for follow-up questions
        self.pending_meetings = {}  # Temporary storage for incomplete meetings
        self.conversation_states = {}  # Track conversation context per user
        
        # Statistics
        self.stats = {
            'meetings_created': 0,
            'meetings_modified': 0,
            'meetings_deleted': 0,
            'follow_up_conversations': 0
        }
        
        # Initialize database
        self._init_database()
    
    def _init_database(self):
        """Initialize the simplified meetings database"""
        try:
            # Ensure directory exists
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            
            with self.db_lock:
                conn = sqlite3.connect(str(self.db_path))
                cursor = conn.cursor()
                
                # Create simplified meetings table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS meetings (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title TEXT NOT NULL,
                        date TEXT NOT NULL,
                        time TEXT NOT NULL,
                        meeting_type TEXT DEFAULT 'in_person',
                        location TEXT DEFAULT '',
                        duration INTEGER DEFAULT 60,
                        reminder_minutes INTEGER DEFAULT 15,
                        notes TEXT DEFAULT '',
                        created_at TEXT NOT NULL
                    )
                """)
                
                # Create index for faster date queries
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_meetings_date 
                    ON meetings (date)
                """)
                
                # Create index for date range queries
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_meetings_datetime 
                    ON meetings (date, time)
                """)
                
                conn.commit()
                conn.close()
                
            self.logger.info("Meetings database initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize meetings database: {e}")
            raise
    
    async def create_meeting_from_text(self, user_input: str, user_id: str = "default") -> Dict[str, Any]:
        """Create meeting from natural language with interactive follow-up"""
        try:
            # Parse the basic information from text
            parsed_info = self._parse_meeting_info(user_input)
            
            # Check what information is missing
            missing_info = self._check_missing_info(parsed_info)
            
            if missing_info:
                # Start interactive conversation
                conversation_id = self._generate_conversation_id(user_id)
                
                # Store partial meeting info
                self.pending_meetings[conversation_id] = {
                    'meeting_info': parsed_info,
                    'missing_info': missing_info,
                    'user_id': user_id,
                    'original_text': user_input,
                    'step': 0
                }
                
                # Ask first follow-up question
                question = self._generate_follow_up_question(missing_info[0], parsed_info)
                
                self.stats['follow_up_conversations'] += 1
                
                return {
                    'success': True,
                    'needs_followup': True,
                    'conversation_id': conversation_id,
                    'question': question,
                    'parsed_info': parsed_info,
                    'missing_info': missing_info
                }
            else:
                # All information available, create meeting directly
                meeting = Meeting(**parsed_info)
                meeting_id = await self._save_meeting(meeting)
                
                if meeting_id:
                    self.stats['meetings_created'] += 1
                    
                    return {
                        'success': True,
                        'needs_followup': False,
                        'meeting_id': meeting_id,
                        'meeting': meeting,
                        'confirmation': self._generate_confirmation(meeting)
                    }
                else:
                    return {
                        'success': False,
                        'error': 'Failed to save meeting to database'
                    }
                    
        except Exception as e:
            self.logger.error(f"Error creating meeting from text: {e}")
            return {
                'success': False,
                'error': f'Failed to process meeting request: {str(e)}'
            }
    
    async def continue_conversation(self, conversation_id: str, user_response: str) -> Dict[str, Any]:
        """Continue interactive meeting creation conversation"""
        try:
            if conversation_id not in self.pending_meetings:
                return {
                    'success': False,
                    'error': 'Conversation not found or expired'
                }
            
            pending = self.pending_meetings[conversation_id]
            meeting_info = pending['meeting_info']
            missing_info = pending['missing_info']
            current_step = pending['step']
            
            # Process the user's response for current missing info
            current_field = missing_info[current_step]
            processed_value = self._process_field_response(current_field, user_response, meeting_info)
            
            if processed_value is not None:
                meeting_info[current_field] = processed_value
                pending['step'] += 1
                
                # Check if we have more questions
                if pending['step'] < len(missing_info):
                    # Ask next question
                    next_field = missing_info[pending['step']]
                    question = self._generate_follow_up_question(next_field, meeting_info)
                    
                    return {
                        'success': True,
                        'needs_followup': True,
                        'conversation_id': conversation_id,
                        'question': question,
                        'field_updated': current_field,
                        'value_set': processed_value
                    }
                else:
                    # All information collected, create meeting
                    meeting = Meeting(**meeting_info)
                    meeting_id = await self._save_meeting(meeting)
                    
                    # Clean up pending conversation
                    del self.pending_meetings[conversation_id]
                    
                    if meeting_id:
                        self.stats['meetings_created'] += 1
                        
                        return {
                            'success': True,
                            'needs_followup': False,
                            'meeting_id': meeting_id,
                            'meeting': meeting,
                            'confirmation': self._generate_confirmation(meeting)
                        }
                    else:
                        return {
                            'success': False,
                            'error': 'Failed to save meeting to database'
                        }
            else:
                # Invalid response, ask again
                question = self._generate_follow_up_question(current_field, meeting_info, retry=True)
                return {
                    'success': True,
                    'needs_followup': True,
                    'conversation_id': conversation_id,
                    'question': question,
                    'error': 'Invalid response, please try again'
                }
                
        except Exception as e:
            self.logger.error(f"Error continuing conversation: {e}")
            return {
                'success': False,
                'error': f'Conversation error: {str(e)}'
            }
    
    def _parse_meeting_info(self, text: str) -> Dict[str, Any]:
        """Parse meeting information from natural language"""
        info = {
            'title': '',
            'date': '',
            'time': '',
            'meeting_type': 'in_person',
            'location': '',
            'duration': 60,
            'reminder_minutes': 15,
            'notes': f'Created from: {text}'
        }
        
        text_lower = text.lower().strip()
        
        # Extract title (basic approach)
        title = self._extract_title(text_lower)
        if title:
            info['title'] = title
        
        # Extract date
        parsed_date = self._extract_date(text_lower)
        if parsed_date:
            info['date'] = parsed_date
        
        # Extract time
        parsed_time = self._extract_time(text_lower)
        if parsed_time:
            info['time'] = parsed_time
        
        # Extract meeting type
        meeting_type = self._extract_meeting_type(text_lower)
        if meeting_type:
            info['meeting_type'] = meeting_type
        
        # Extract location hints
        location = self._extract_location(text_lower)
        if location:
            info['location'] = location
        
        return info
    
    def _extract_title(self, text: str) -> str:
        """Extract meeting title from text"""
        import re
        
        text_lower = text.lower()
        
        # First, try to extract compound titles (multiple words that go together)
        compound_titles = [
            'team meeting', 'team standup', 'daily standup', 'doctor appointment',
            'zoom call', 'video call', 'phone call', 'online interview',
            'job interview', 'client meeting', 'project review'
        ]
        
        for compound in compound_titles:
            if compound in text_lower:
                return compound.title()
        
        # Remove common scheduling words but preserve context
        scheduling_words = [
            'schedule', 'book', 'add', 'create', 'set up', 'plan', 'arrange'
        ]
        
        # Remove time-related words
        time_words = [
            'tomorrow', 'today', 'monday', 'tuesday', 'wednesday', 'thursday',
            'friday', 'saturday', 'sunday', 'next week', 'this week', 'next',
            'at', 'pm', 'am', 'o\'clock', 'morning', 'afternoon', 'evening',
            'with'  # Remove 'with' to avoid "interview with john" -> "interview john"
        ]
        
        # Remove time patterns first
        text_clean = re.sub(r'\b\d{1,2}:\d{2}\s*(am|pm)?\b', '', text_lower)
        text_clean = re.sub(r'\b\d{1,2}\s*(am|pm)\b', '', text_clean)
        
        words = text_clean.split()
        title_words = []
        
        skip_words = set(scheduling_words + time_words)
        
        # Process words, keeping meaningful combinations
        for i, word in enumerate(words):
            # Skip scheduling and time words
            if word in skip_words:
                continue
            # Skip standalone digits
            if word.isdigit():
                continue
                
            title_words.append(word)
        
        title = ' '.join(title_words).strip()
        
        # Clean up the title
        title = re.sub(r'\s+', ' ', title)  # Remove extra spaces
        
        # If we have a reasonable title, use it
        if title and len(title) >= 3:
            # Handle special cases
            if 'doctor' in title and 'appointment' not in title:
                title = title.replace('doctor', 'doctor appointment')
            elif 'zoom' in title and 'call' not in title and 'meeting' not in title:
                title = title.replace('zoom', 'zoom call')
            elif 'interview' in title and len(title.split()) == 1:
                title = 'Interview'
            
            return title.title()
        
        # Fallback to context-based inference
        if 'interview' in text_lower:
            return 'Interview'
        elif 'standup' in text_lower or 'daily' in text_lower:
            return 'Daily Standup'
        elif 'review' in text_lower:
            return 'Review Meeting'
        elif 'team' in text_lower:
            return 'Team Meeting'
        elif 'doctor' in text_lower:
            return 'Doctor Appointment'
        elif 'appointment' in text_lower:
            return 'Appointment'
        elif 'call' in text_lower:
            return 'Call'
        elif 'meeting' in text_lower:
            return 'Meeting'
        else:
            return 'Meeting'
    
    def _extract_date(self, text: str) -> str:
        """Extract date from text and convert to YYYY-MM-DD format"""
        today = datetime.now().date()
        
        # Handle relative dates
        if 'tomorrow' in text:
            target_date = today + timedelta(days=1)
            return target_date.strftime('%Y-%m-%d')
        elif 'today' in text:
            return today.strftime('%Y-%m-%d')
        elif 'next week' in text:
            # Default to next Monday
            days_until_monday = (7 - today.weekday()) % 7
            if days_until_monday == 0:
                days_until_monday = 7
            target_date = today + timedelta(days=days_until_monday)
            return target_date.strftime('%Y-%m-%d')
        
        # Handle weekdays
        weekdays = {
            'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
            'friday': 4, 'saturday': 5, 'sunday': 6
        }
        
        for day_name, day_num in weekdays.items():
            if day_name in text:
                # Find next occurrence of this weekday
                days_ahead = day_num - today.weekday()
                if days_ahead <= 0:  # Target day already happened this week
                    days_ahead += 7
                target_date = today + timedelta(days=days_ahead)
                return target_date.strftime('%Y-%m-%d')
        
        # Handle "in X days"
        import re
        days_pattern = r'in (\d+) days?'
        match = re.search(days_pattern, text)
        if match:
            days = int(match.group(1))
            target_date = today + timedelta(days=days)
            return target_date.strftime('%Y-%m-%d')
        
        return ''  # No date found
    
    def _extract_time(self, text: str) -> str:
        """Extract time from text and convert to HH:MM format (24-hour)"""
        import re
        
        # Pattern for HH:MM AM/PM
        time_pattern = r'\b(\d{1,2}):(\d{2})\s*(am|pm)\b'
        match = re.search(time_pattern, text)
        if match:
            hour = int(match.group(1))
            minute = int(match.group(2))
            ampm = match.group(3).lower()
            
            # Convert to 24-hour format
            if ampm == 'pm' and hour != 12:
                hour += 12
            elif ampm == 'am' and hour == 12:
                hour = 0
                
            return f"{hour:02d}:{minute:02d}"
        
        # Pattern for H AM/PM
        simple_time_pattern = r'\b(\d{1,2})\s*(am|pm)\b'
        match = re.search(simple_time_pattern, text)
        if match:
            hour = int(match.group(1))
            ampm = match.group(2).lower()
            
            if ampm == 'pm' and hour != 12:
                hour += 12
            elif ampm == 'am' and hour == 12:
                hour = 0
                
            return f"{hour:02d}:00"
        
        # Handle special times
        if 'noon' in text:
            return '12:00'
        elif 'midnight' in text:
            return '00:00'
        elif 'morning' in text and not any(word in text for word in ['am', 'pm']):
            return '09:00'  # Default morning time
        elif 'afternoon' in text and not any(word in text for word in ['am', 'pm']):
            return '14:00'  # Default afternoon time
        elif 'evening' in text and not any(word in text for word in ['am', 'pm']):
            return '18:00'  # Default evening time
        
        return ''  # No time found
    
    def _extract_meeting_type(self, text: str) -> str:
        """Extract meeting type from text"""
        if any(word in text for word in ['online', 'virtual', 'zoom', 'teams', 'meet', 'video']):
            return 'online'
        elif any(word in text for word in ['phone', 'call', 'dial']):
            return 'phone'
        else:
            return 'in_person'  # Default
    
    def _extract_location(self, text: str) -> str:
        """Extract location hints from text"""
        # Online meeting platforms
        if 'zoom' in text:
            return 'Zoom meeting'
        elif 'teams' in text:
            return 'Microsoft Teams'
        elif 'meet' in text:
            return 'Google Meet'
        elif 'webex' in text:
            return 'WebEx'
        
        # Physical locations
        if 'office' in text:
            return 'Office'
        elif 'conference room' in text:
            return 'Conference Room'
        elif 'home' in text:
            return 'Home'
        
        return ''
    
    def _check_missing_info(self, meeting_info: Dict[str, Any]) -> List[str]:
        """Check what required information is missing"""
        missing = []
        
        if not meeting_info.get('title'):
            missing.append('title')
        if not meeting_info.get('date'):
            missing.append('date')
        if not meeting_info.get('time'):
            missing.append('time')
        if meeting_info.get('meeting_type') == 'online' and not meeting_info.get('location'):
            missing.append('online_location')
        
        return missing
    
    def _generate_follow_up_question(self, field: str, meeting_info: Dict, retry: bool = False) -> str:
        """Generate appropriate follow-up question for missing field"""
        prefix = "I didn't understand that. " if retry else ""
        
        if field == 'title':
            return f"{prefix}What would you like to call this meeting?"
        elif field == 'date':
            return f"{prefix}What date should I schedule this for? (e.g., 'tomorrow', 'Friday', 'next week')"
        elif field == 'time':
            return f"{prefix}What time works for you? (e.g., '2pm', '10:30am', '14:00')"
        elif field == 'online_location':
            return f"{prefix}Since this is an online meeting, do you have a meeting link or should I note it as 'Online meeting'?"
        else:
            return f"{prefix}I need more information about the {field}."
    
    def _process_field_response(self, field: str, response: str, meeting_info: Dict) -> Optional[str]:
        """Process user response for a specific field"""
        response = response.strip()
        
        if field == 'title':
            if len(response) > 0:
                return response.title()
        elif field == 'date':
            parsed_date = self._extract_date(response.lower())
            if parsed_date:
                return parsed_date
        elif field == 'time':
            parsed_time = self._extract_time(response.lower())
            if parsed_time:
                return parsed_time
        elif field == 'online_location':
            if response.lower() in ['no', 'none', 'n']:
                return 'Online meeting'
            elif len(response) > 3:
                return response
            else:
                return 'Online meeting'
        
        return None
    
    def _generate_confirmation(self, meeting: Meeting) -> str:
        """Generate confirmation message for created meeting"""
        # Format date nicely
        meeting_date = datetime.strptime(meeting.date, '%Y-%m-%d')
        formatted_date = meeting_date.strftime('%A, %B %d')
        
        # Format time nicely
        meeting_time = datetime.strptime(meeting.time, '%H:%M')
        formatted_time = meeting_time.strftime('%I:%M %p').lstrip('0')
        
        # Build confirmation message
        confirmation = f"✅ Meeting scheduled: '{meeting.title}' on {formatted_date} at {formatted_time}"
        
        if meeting.meeting_type == 'online':
            confirmation += f" (Online"
            if meeting.location and meeting.location != 'Online meeting':
                confirmation += f" - {meeting.location}"
            confirmation += ")"
        elif meeting.meeting_type == 'phone':
            confirmation += " (Phone call)"
        elif meeting.location:
            confirmation += f" at {meeting.location}"
        
        if meeting.reminder_minutes > 0:
            confirmation += f". You'll get a reminder {meeting.reminder_minutes} minutes before."
        
        return confirmation
    
    def _generate_conversation_id(self, user_id: str) -> str:
        """Generate unique conversation ID"""
        timestamp = str(int(time.time()))
        content = f"{user_id}_{timestamp}"
        return hashlib.md5(content.encode()).hexdigest()[:12]
    
    async def _save_meeting(self, meeting: Meeting) -> Optional[int]:
        """Save meeting to database"""
        try:
            with self.db_lock:
                conn = sqlite3.connect(str(self.db_path))
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO meetings 
                    (title, date, time, meeting_type, location, duration, reminder_minutes, notes, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    meeting.title, meeting.date, meeting.time, meeting.meeting_type,
                    meeting.location, meeting.duration, meeting.reminder_minutes,
                    meeting.notes, meeting.created_at
                ))
                
                meeting_id = cursor.lastrowid
                conn.commit()
                conn.close()
                
                self.logger.info(f"Meeting saved: {meeting.title} on {meeting.date} at {meeting.time}")
                return meeting_id
                
        except Exception as e:
            self.logger.error(f"Failed to save meeting: {e}")
            return None
    
    async def get_meetings_for_date(self, target_date: str) -> List[Dict[str, Any]]:
        """Get all meetings for a specific date"""
        try:
            with self.db_lock:
                conn = sqlite3.connect(str(self.db_path))
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT * FROM meetings 
                    WHERE date = ? 
                    ORDER BY time
                """, (target_date,))
                
                columns = [description[0] for description in cursor.description]
                meetings = [dict(zip(columns, row)) for row in cursor.fetchall()]
                
                conn.close()
                return meetings
                
        except Exception as e:
            self.logger.error(f"Failed to get meetings for date {target_date}: {e}")
            return []
    
    async def get_meetings_in_range(self, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """Get meetings within date range"""
        try:
            with self.db_lock:
                conn = sqlite3.connect(str(self.db_path))
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT * FROM meetings 
                    WHERE date >= ? AND date <= ?
                    ORDER BY date, time
                """, (start_date, end_date))
                
                columns = [description[0] for description in cursor.description]
                meetings = [dict(zip(columns, row)) for row in cursor.fetchall()]
                
                conn.close()
                return meetings
                
        except Exception as e:
            self.logger.error(f"Failed to get meetings in range {start_date} to {end_date}: {e}")
            return []
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get meeting manager statistics"""
        try:
            with self.db_lock:
                conn = sqlite3.connect(str(self.db_path))
                cursor = conn.cursor()
                
                # Count total meetings
                cursor.execute("SELECT COUNT(*) FROM meetings")
                total_meetings = cursor.fetchone()[0]
                
                # Count upcoming meetings
                today = datetime.now().date().strftime('%Y-%m-%d')
                cursor.execute("SELECT COUNT(*) FROM meetings WHERE date >= ?", (today,))
                upcoming_meetings = cursor.fetchone()[0]
                
                conn.close()
                
            stats = self.stats.copy()
            stats.update({
                'total_meetings': total_meetings,
                'upcoming_meetings': upcoming_meetings,
                'pending_conversations': len(self.pending_meetings)
            })
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Failed to get statistics: {e}")
            return self.stats.copy()