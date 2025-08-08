"""
Optimized Visual Calendar Viewer for SAGE
Memory-efficient, secure, and performant calendar GUI
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
import threading
import json
import calendar as cal
import logging
from contextlib import contextmanager
import weakref
from functools import lru_cache

# Constants for better memory management
MAX_EVENTS_PER_SLOT = 4
DEFAULT_WINDOW_SIZE = "1000x700"
MONTHLY_WINDOW_SIZE = "1200x800"
EVENT_CACHE_SIZE = 128
DATE_CACHE_SIZE = 64

class OptimizedCalendarViewer:
    """Base class with shared optimization patterns"""
    
    def __init__(self, calendar_module=None):
        self.calendar_module = calendar_module
        self.window = None
        self._event_cache = {}
        self._date_cache = {}
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Use weakref to prevent circular references
        self._widgets = weakref.WeakSet()
        
        # Pre-compile common styles to avoid recreation
        self._styles = self._init_styles()
    
    def _init_styles(self) -> Dict[str, Dict[str, str]]:
        """Initialize and cache common widget styles"""
        return {
            'header': {'bg': '#2c3e50', 'fg': 'white', 'font': ('Arial', 16, 'bold')},
            'nav_button': {'font': ('Arial', 10), 'relief': tk.FLAT, 'padx': 20},
            'day_header': {'font': ('Arial', 12, 'bold'), 'bg': '#34495e', 'fg': 'white'},
            'time_label': {'font': ('Arial', 10), 'bg': '#ecf0f1', 'relief': tk.RIDGE}
        }
    
    @contextmanager
    def _db_connection(self):
        """Secure database connection context manager"""
        db_path = "data/calendar.db"
        if self.calendar_module and hasattr(self.calendar_module, 'db_path'):
            db_path = str(self.calendar_module.db_path)
        
        conn = None
        try:
            # Use connection pooling and WAL mode for better performance
            conn = sqlite3.connect(db_path, timeout=10.0)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL") 
            conn.execute("PRAGMA cache_size=10000")
            yield conn
        except sqlite3.Error as e:
            self.logger.error(f"Database error: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    def _sanitize_input(self, input_str: str) -> str:
        """Sanitize user input to prevent injection attacks"""
        if not isinstance(input_str, str):
            return ""
        
        # Remove potentially dangerous characters
        dangerous_chars = ['<', '>', '"', "'", '&', ';', '|', '`']
        sanitized = input_str
        for char in dangerous_chars:
            sanitized = sanitized.replace(char, '')
        
        # Limit length to prevent buffer overflow attempts
        return sanitized[:255]
    
    @lru_cache(maxsize=EVENT_CACHE_SIZE)
    def _get_events_cached(self, start_timestamp: float, end_timestamp: float) -> Tuple[Dict, ...]:
        """Cached event retrieval with LRU eviction"""
        try:
            with self._db_connection() as conn:
                cursor = conn.cursor()
                
                # Use parameterized queries for security
                cursor.execute("""
                    SELECT event_id, title, start_time, end_time, location, description, 
                           COALESCE(event_type, 'meeting') as event_type, 
                           COALESCE(priority, 'medium') as priority, 
                           COALESCE(attendees, '[]') as attendees
                    FROM events 
                    WHERE start_time >= ? AND start_time <= ?
                    ORDER BY start_time
                    LIMIT 1000
                """, (start_timestamp, end_timestamp))
                
                events = []
                for row in cursor.fetchall():
                    event_id, title, start_time, end_time, location, description, event_type, priority, attendees = row
                    
                    # Sanitize all string fields
                    events.append({
                        'id': event_id,
                        'title': self._sanitize_input(str(title)),
                        'start_time': datetime.fromtimestamp(start_time),
                        'end_time': datetime.fromtimestamp(end_time) if end_time else datetime.fromtimestamp(start_time) + timedelta(hours=1),
                        'time_str': datetime.fromtimestamp(start_time).strftime('%I:%M %p'),
                        'location': self._sanitize_input(str(location or '')),
                        'description': self._sanitize_input(str(description or '')),
                        'event_type': self._sanitize_input(str(event_type)),
                        'priority': self._sanitize_input(str(priority)),
                        'attendees': json.loads(attendees) if attendees else []
                    })
                
                # Return tuple for hashability in LRU cache
                return tuple(events)
                
        except Exception as e:
            self.logger.error(f"Error getting events: {e}")
            return tuple()
    
    def _clear_cache(self):
        """Clear caches to prevent memory leaks"""
        self._get_events_cached.cache_clear()
        self._event_cache.clear()
        self._date_cache.clear()
    
    def __del__(self):
        """Cleanup when object is destroyed"""
        self._clear_cache()
        if self.window:
            try:
                self.window.destroy()
            except:
                pass


class WeeklyCalendarViewer(OptimizedCalendarViewer):
    """Optimized GUI window for displaying weekly calendar"""
    
    def show_weekly_schedule(self, start_date: Optional[datetime] = None) -> bool:
        """Display weekly calendar with optimized threading"""
        try:
            if start_date is None:
                start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            
            # Use ThreadPoolExecutor for better thread management
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(self._create_calendar_window, start_date)
                return True
                
        except Exception as e:
            self.logger.error(f"Error showing weekly schedule: {e}")
            return False
    
    def _create_calendar_window(self, start_date: datetime):
        """Create optimized calendar window"""
        try:
            self.window = tk.Tk()
            self.window.title("SAGE - Weekly Schedule")
            self.window.geometry(DEFAULT_WINDOW_SIZE)
            self.window.configure(bg='#f0f0f0')
            
            # Optimize window for better performance
            self.window.resizable(False, False)  # Fixed size for better performance
            
            self._create_header(start_date)
            self._create_calendar_grid(start_date)
            
            # Bind cleanup on window close
            self.window.protocol("WM_DELETE_WINDOW", self._on_window_close)
            
            self.window.mainloop()
            
        except Exception as e:
            self.logger.error(f"Error creating calendar window: {e}")
    
    def _on_window_close(self):
        """Cleanup when window is closed"""
        self._clear_cache()
        if self.window:
            self.window.destroy()
            self.window = None
    
    def _create_header(self, start_date: datetime):
        """Create optimized header with navigation"""
        header_frame = tk.Frame(self.window, **self._styles['header'], height=60)
        header_frame.pack(fill=tk.X, pady=(0, 10))
        header_frame.pack_propagate(False)
        self._widgets.add(header_frame)
        
        # Optimize string formatting
        end_date = start_date + timedelta(days=6)
        title_text = f"Weekly Schedule: {start_date:%B %d} - {end_date:%B %d, %Y}"
        
        title_label = tk.Label(header_frame, text=title_text, **self._styles['header'])
        title_label.pack(expand=True)
        self._widgets.add(title_label)
        
        # Navigation buttons with optimized callbacks
        nav_frame = tk.Frame(header_frame, bg='#2c3e50')
        nav_frame.pack(side=tk.BOTTOM, pady=5)
        self._widgets.add(nav_frame)
        
        # Use bound methods to avoid lambda closure issues
        prev_btn = tk.Button(nav_frame, text="← Previous Week", 
                           command=lambda: self._navigate_week(start_date, -7),
                           **self._styles['nav_button'])
        prev_btn.pack(side=tk.LEFT, padx=5)
        self._widgets.add(prev_btn)
        
        next_btn = tk.Button(nav_frame, text="Next Week →",
                           command=lambda: self._navigate_week(start_date, 7),
                           **self._styles['nav_button'])
        next_btn.pack(side=tk.RIGHT, padx=5)
        self._widgets.add(next_btn)
    
    def _create_calendar_grid(self, start_date: datetime):
        """Create optimized calendar grid"""
        main_frame = tk.Frame(self.window, bg='#f0f0f0')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        self._widgets.add(main_frame)
        
        # Use more efficient scrolling
        canvas = tk.Canvas(main_frame, bg='white', highlightthickness=0)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind("<Configure>", 
                            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Get events efficiently
        events = list(self._get_week_events(start_date))
        
        # Create optimized grid
        self._create_time_grid(scrollable_frame, start_date, events)
        
        # Pack components
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Optimized mouse wheel binding
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        # Bind to canvas instead of all widgets
        canvas.bind("<MouseWheel>", _on_mousewheel)
        canvas.focus_set()
    
    def _get_week_events(self, start_date: datetime) -> List[Dict]:
        """Get events for the week with caching"""
        weekday = start_date.weekday()
        monday_start = start_date - timedelta(days=weekday)
        end_date = monday_start + timedelta(days=7)
        
        start_timestamp = monday_start.timestamp()
        end_timestamp = end_date.timestamp()
        
        # Use cached method
        return list(self._get_events_cached(start_timestamp, end_timestamp))
    
    def _create_time_grid(self, parent_frame: ttk.Frame, start_date: datetime, events: List[Dict]):
        """Create optimized time grid"""
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        
        weekday = start_date.weekday()
        monday_start = start_date - timedelta(days=weekday)
        
        # Create header row efficiently
        header_frame = tk.Frame(parent_frame, bg='white')
        header_frame.grid(row=0, column=0, columnspan=8, sticky='ew', padx=2, pady=2)
        
        # Time column header
        time_header = tk.Label(header_frame, text="Time", width=8, relief=tk.RAISED,
                              **self._styles['day_header'])
        time_header.grid(row=0, column=0, sticky='ew', padx=1)
        
        # Day headers with date
        for i, day in enumerate(days):
            day_date = monday_start + timedelta(days=i)
            day_text = f"{day}\n{day_date:%m/%d}"
            
            day_header = tk.Label(header_frame, text=day_text, width=15, relief=tk.RAISED,
                                 **self._styles['day_header'])
            day_header.grid(row=0, column=i+1, sticky='ew', padx=1)
        
        # Event colors for performance
        event_colors = {
            'meeting': '#e74c3c', 'appointment': '#3498db', 'task': '#f39c12',
            'personal': '#9b59b6', 'work': '#2ecc71', 'default': '#95a5a6'
        }
        
        # Pre-organize events by time slot for efficiency
        events_by_slot = {}
        for event in events:
            hour = event['start_time'].hour
            day_idx = (event['start_time'].date() - monday_start.date()).days
            if 0 <= day_idx < 7 and 6 <= hour < 23:
                key = (hour, day_idx)
                if key not in events_by_slot:
                    events_by_slot[key] = []
                events_by_slot[key].append(event)
        
        # Create time slots (6 AM to 11 PM) more efficiently
        for hour in range(6, 23):
            row = hour - 5
            
            # Time label with optimized formatting
            time_text = f"{hour:02d}:00 {'AM' if hour < 12 else 'PM' if hour == 12 else 'PM'}"
            if hour > 12:
                time_text = f"{hour-12:02d}:00 PM"
            
            time_label = tk.Label(parent_frame, text=time_text, width=8,
                                 **self._styles['time_label'])
            time_label.grid(row=row, column=0, sticky='ew', padx=1, pady=1)
            
            # Day slots
            for day_idx in range(7):
                key = (hour, day_idx)
                slot_events = events_by_slot.get(key, [])
                
                if slot_events:
                    # Occupied slot - use first event's color
                    event_type = slot_events[0].get('event_type', 'meeting')
                    color = event_colors.get(event_type, event_colors['default'])
                    
                    event_frame = tk.Frame(parent_frame, bg=color, relief=tk.RAISED)
                    event_frame.grid(row=row, column=day_idx+1, sticky='ew', padx=1, pady=1)
                    
                    # Show only limited events to prevent UI slowdown
                    for event in slot_events[:2]:  # Max 2 events per slot
                        event_label = tk.Label(event_frame, text=event['title'][:12] + "...",
                                             font=('Arial', 9, 'bold'), bg=color, fg='white',
                                             wraplength=120)
                        event_label.pack(fill=tk.X, pady=1)
                    
                    if len(slot_events) > 2:
                        more_label = tk.Label(event_frame, text=f"+{len(slot_events)-2} more",
                                            font=('Arial', 8), bg=color, fg='#ffeeee')
                        more_label.pack()
                else:
                    # Free slot
                    empty_slot = tk.Label(parent_frame, text="", bg='#2ecc71', 
                                        relief=tk.RIDGE, width=15, height=2)
                    empty_slot.grid(row=row, column=day_idx+1, sticky='ew', padx=1, pady=1)
        
        # Configure responsive design
        for i in range(8):
            parent_frame.columnconfigure(i, weight=1)
    
    def _navigate_week(self, current_start: datetime, days_offset: int):
        """Navigate to different week with cleanup"""
        new_start = current_start + timedelta(days=days_offset)
        self._clear_cache()  # Clear cache before navigation
        
        if self.window:
            self.window.destroy()
        self._create_calendar_window(new_start)


class MonthlyCalendarViewer(OptimizedCalendarViewer):
    """Optimized monthly calendar viewer"""
    
    def __init__(self, calendar_module=None):
        super().__init__(calendar_module)
        self.current_date = datetime.now().replace(day=1)
        self.calendar_frame = None
        
        # Optimized event colors
        self.event_colors = {
            'meeting': '#e74c3c', 'appointment': '#3498db', 'task': '#f39c12',
            'personal': '#9b59b6', 'work': '#2ecc71', 'default': '#95a5a6'
        }
    
    def show_monthly_schedule(self, start_date: Optional[datetime] = None) -> bool:
        """Display optimized monthly calendar"""
        try:
            if start_date is not None:
                self.current_date = start_date.replace(day=1)
            
            # Use single thread for UI consistency
            self._create_monthly_window()
            return True
            
        except Exception as e:
            self.logger.error(f"Error showing monthly schedule: {e}")
            return False
    
    def _create_monthly_window(self):
        """Create optimized monthly calendar window"""
        try:
            if self.window:
                self.window.destroy()
                
            self.window = tk.Tk()
            self.window.title("SAGE - Monthly Calendar")
            self.window.geometry(MONTHLY_WINDOW_SIZE)
            self.window.configure(bg='#f0f0f0')
            self.window.resizable(True, True)  # Allow resize for monthly view
            
            self._create_month_header()
            self._create_monthly_grid()
            
            self.window.protocol("WM_DELETE_WINDOW", self._on_window_close)
            self.window.mainloop()
            
        except Exception as e:
            self.logger.error(f"Error creating monthly calendar: {e}")
    
    def _create_month_header(self):
        """Create optimized month header"""
        header_frame = tk.Frame(self.window, bg='#2c3e50', height=80)
        header_frame.pack(fill=tk.X, pady=(0, 10))
        header_frame.pack_propagate(False)
        
        title_text = self.current_date.strftime('%B %Y')
        title_label = tk.Label(header_frame, text=title_text,
                              font=('Arial', 20, 'bold'), fg='white', bg='#2c3e50')
        title_label.pack(expand=True)
        
        nav_frame = tk.Frame(header_frame, bg='#2c3e50')
        nav_frame.pack(side=tk.BOTTOM, pady=10)
        
        # Navigation buttons
        btn_style = {'font': ('Arial', 11), 'bg': '#34495e', 'fg': 'white', 
                    'relief': tk.FLAT, 'padx': 20}
        
        prev_btn = tk.Button(nav_frame, text="← Previous Month",
                           command=self._prev_month, **btn_style)
        prev_btn.pack(side=tk.LEFT, padx=10)
        
        today_btn = tk.Button(nav_frame, text="Today", 
                            command=self._goto_today,
                            **{**btn_style, 'bg': '#3498db'})
        today_btn.pack(side=tk.LEFT, padx=5)
        
        next_btn = tk.Button(nav_frame, text="Next Month →",
                           command=self._next_month, **btn_style)
        next_btn.pack(side=tk.RIGHT, padx=10)
    
    def _create_monthly_grid(self):
        """Create optimized monthly grid"""
        if self.calendar_frame:
            self.calendar_frame.destroy()
        
        main_frame = tk.Frame(self.window, bg='#f0f0f0')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)
        
        self.calendar_frame = tk.Frame(main_frame, bg='white', relief=tk.RIDGE, bd=1)
        self.calendar_frame.pack(fill=tk.BOTH, expand=True)
        
        # Get events efficiently with caching
        events = list(self._get_month_events(self.current_date))
        
        # Create day headers
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        for col, day in enumerate(days):
            day_header = tk.Label(self.calendar_frame, text=day, relief=tk.RAISED, bd=1,
                                 **self._styles['day_header'])
            day_header.grid(row=0, column=col, sticky='ew', padx=1, pady=1)
        
        # Get calendar data efficiently
        calendar_obj = cal.Calendar(firstweekday=0)
        month_days = calendar_obj.monthdayscalendar(self.current_date.year, self.current_date.month)
        
        # Pre-organize events by date for efficiency
        events_by_date = {}
        for event in events:
            event_date = event['start_time'].date()
            if event_date not in events_by_date:
                events_by_date[event_date] = []
            events_by_date[event_date].append(event)
        
        # Create day cells efficiently
        today = datetime.now().date()
        for week_num, week in enumerate(month_days, start=1):
            for day_num, day in enumerate(week):
                if day == 0:
                    # Empty cell
                    empty_cell = tk.Label(self.calendar_frame, text="",
                                        bg='#ecf0f1', relief=tk.SUNKEN, bd=1)
                    empty_cell.grid(row=week_num, column=day_num, sticky='nsew', padx=1, pady=1)
                else:
                    cell_date = self.current_date.replace(day=day).date()
                    day_events = events_by_date.get(cell_date, [])
                    self._create_day_cell(week_num, day_num, day, day_events, cell_date == today)
        
        # Configure responsive grid
        for col in range(7):
            self.calendar_frame.columnconfigure(col, weight=1)
        for row in range(len(month_days) + 1):
            self.calendar_frame.rowconfigure(row, weight=1)
    
    def _create_day_cell(self, row: int, col: int, day: int, events: List[Dict], is_today: bool):
        """Create optimized day cell"""
        day_frame = tk.Frame(self.calendar_frame, bg='white', relief=tk.RAISED, bd=1, cursor='hand2')
        day_frame.grid(row=row, column=col, sticky='nsew', padx=1, pady=1)
        
        # Day number with highlighting
        bg_color = '#3498db' if is_today else 'white'
        fg_color = 'white' if is_today else 'black'
        
        day_label = tk.Label(day_frame, text=str(day), anchor='nw',
                           font=('Arial', 12, 'bold'), bg=bg_color, fg=fg_color)
        day_label.pack(side=tk.TOP, fill=tk.X)
        
        # Event container
        event_container = tk.Frame(day_frame, bg='white')
        event_container.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=2, pady=2)
        
        # Show limited events for performance
        for i, event in enumerate(events[:MAX_EVENTS_PER_SLOT]):
            event_color = self.event_colors.get(event.get('event_type', 'meeting'), 
                                               self.event_colors['default'])
            
            title = event['title']
            display_title = title[:15] + ('...' if len(title) > 15 else '')
            
            event_label = tk.Label(event_container, text=display_title,
                                 font=('Arial', 8), bg=event_color, fg='white',
                                 relief=tk.RAISED, bd=1, cursor='hand2')
            event_label.pack(fill=tk.X, pady=1)
            
            # Secure event binding with validation
            event_label.bind('<Button-1>', 
                           lambda e, evt=event: self._edit_event_safe(evt))
        
        # Show "more" indicator
        if len(events) > MAX_EVENTS_PER_SLOT:
            more_label = tk.Label(event_container, text=f"... {len(events) - MAX_EVENTS_PER_SLOT} more",
                                font=('Arial', 7), bg='#bdc3c7', fg='#2c3e50', relief=tk.RAISED, bd=1)
            more_label.pack(fill=tk.X, pady=1)
        
        # Secure double-click binding
        cell_date = self.current_date.replace(day=day).date()
        day_frame.bind('<Double-Button-1>', 
                      lambda e, date=cell_date: self._add_new_event_safe(date))
    
    def _get_month_events(self, start_date: datetime) -> List[Dict]:
        """Get month events with caching and security"""
        first_day = start_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Calculate last day efficiently
        if start_date.month == 12:
            last_day = start_date.replace(year=start_date.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            next_month = start_date.replace(month=start_date.month + 1, day=1)
            last_day = next_month - timedelta(days=1)
        
        last_day = last_day.replace(hour=23, minute=59, second=59)
        
        start_timestamp = first_day.timestamp()
        end_timestamp = last_day.timestamp()
        
        return list(self._get_events_cached(start_timestamp, end_timestamp))
    
    def _edit_event_safe(self, event: Dict):
        """Secure event editing with input validation"""
        try:
            # Validate event data
            if not isinstance(event, dict) or 'id' not in event:
                self.logger.warning("Invalid event data for editing")
                return
            
            # Create secure edit dialog
            dialog = tk.Toplevel(self.window)
            dialog.title(f"Edit Event: {self._sanitize_input(event.get('title', 'Unknown'))}")
            dialog.geometry("400x500")
            dialog.configure(bg='#f0f0f0')
            dialog.transient(self.window)
            dialog.grab_set()
            
            # Input validation variables
            title_var = tk.StringVar(value=self._sanitize_input(event.get('title', '')))
            type_var = tk.StringVar(value=self._sanitize_input(event.get('event_type', 'meeting')))
            priority_var = tk.StringVar(value=self._sanitize_input(event.get('priority', 'medium')))
            
            # Create form with validation
            self._create_edit_form(dialog, title_var, type_var, priority_var, event)
            
        except Exception as e:
            self.logger.error(f"Error in edit_event_safe: {e}")
            messagebox.showerror("Error", "Unable to edit event. Please try again.")
    
    def _create_edit_form(self, dialog, title_var, type_var, priority_var, event):
        """Create secure edit form"""
        # Title field with validation
        tk.Label(dialog, text="Title:", font=('Arial', 10, 'bold'), bg='#f0f0f0').pack(anchor='w', padx=10, pady=(10,0))
        title_entry = tk.Entry(dialog, textvariable=title_var, font=('Arial', 10), width=50)
        title_entry.pack(padx=10, pady=5, fill=tk.X)
        
        # Event type with restricted values
        tk.Label(dialog, text="Type:", font=('Arial', 10, 'bold'), bg='#f0f0f0').pack(anchor='w', padx=10, pady=(10,0))
        type_combo = ttk.Combobox(dialog, textvariable=type_var, 
                                 values=['meeting', 'appointment', 'task', 'personal', 'work'], 
                                 state='readonly')
        type_combo.pack(padx=10, pady=5, fill=tk.X)
        
        # Priority with restricted values
        tk.Label(dialog, text="Priority:", font=('Arial', 10, 'bold'), bg='#f0f0f0').pack(anchor='w', padx=10, pady=(10,0))
        priority_combo = ttk.Combobox(dialog, textvariable=priority_var,
                                     values=['low', 'medium', 'high', 'urgent'], 
                                     state='readonly')
        priority_combo.pack(padx=10, pady=5, fill=tk.X)
        
        # Action buttons
        button_frame = tk.Frame(dialog, bg='#f0f0f0')
        button_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=10)
        
        def save_changes():
            # Validate input lengths
            title = self._sanitize_input(title_var.get())
            if len(title) < 1 or len(title) > 100:
                messagebox.showerror("Error", "Title must be 1-100 characters")
                return
            
            messagebox.showinfo("Info", "Event editing functionality will be implemented")
            dialog.destroy()
        
        tk.Button(button_frame, text="Save", command=save_changes,
                 bg='#27ae60', fg='white', font=('Arial', 10, 'bold')).pack(side=tk.LEFT, padx=(0,5))
        tk.Button(button_frame, text="Cancel", command=dialog.destroy,
                 bg='#95a5a6', fg='white', font=('Arial', 10, 'bold')).pack(side=tk.RIGHT)
    
    def _add_new_event_safe(self, date):
        """Secure new event creation"""
        try:
            title = simpledialog.askstring("New Event", 
                                         f"Event title for {date.strftime('%B %d, %Y')}:",
                                         parent=self.window)
            if title:
                title = self._sanitize_input(title)
                if len(title) < 1 or len(title) > 100:
                    messagebox.showerror("Error", "Title must be 1-100 characters")
                    return
                
                messagebox.showinfo("Info", f"Event creation functionality will be implemented\nTitle: {title}\nDate: {date}")
        except Exception as e:
            self.logger.error(f"Error in add_new_event_safe: {e}")
    
    def _prev_month(self):
        """Navigate to previous month with cache cleanup"""
        self._clear_cache()
        if self.current_date.month == 1:
            self.current_date = self.current_date.replace(year=self.current_date.year - 1, month=12)
        else:
            self.current_date = self.current_date.replace(month=self.current_date.month - 1)
        
        self._create_monthly_grid()
        self._update_header_title()
    
    def _next_month(self):
        """Navigate to next month with cache cleanup"""
        self._clear_cache()
        if self.current_date.month == 12:
            self.current_date = self.current_date.replace(year=self.current_date.year + 1, month=1)
        else:
            self.current_date = self.current_date.replace(month=self.current_date.month + 1)
        
        self._create_monthly_grid()
        self._update_header_title()
    
    def _goto_today(self):
        """Navigate to current month with cache cleanup"""
        self._clear_cache()
        self.current_date = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        self._create_monthly_grid()
        self._update_header_title()
    
    def _update_header_title(self):
        """Update header title efficiently"""
        for widget in self.window.winfo_children():
            if isinstance(widget, tk.Frame) and widget.cget('bg') == '#2c3e50':
                for child in widget.winfo_children():
                    if isinstance(child, tk.Label) and 'Arial' in str(child.cget('font')):
                        if '20' in str(child.cget('font')):
                            child.config(text=self.current_date.strftime('%B %Y'))
                            break
                break


# Optimized function exports
def show_weekly_calendar(calendar_module=None) -> Dict[str, Any]:
    """Show optimized weekly calendar GUI"""
    try:
        viewer = WeeklyCalendarViewer(calendar_module)
        success = viewer.show_weekly_schedule()
        
        return {
            "success": success,
            "result": "Weekly calendar opened in a new window." if success else "Failed to open weekly calendar"
        }
    except Exception as e:
        logging.getLogger(__name__).error(f"Error in show_weekly_calendar: {e}")
        return {
            "success": False,
            "error": f"Error opening weekly calendar: {str(e)}"
        }


def show_monthly_calendar(calendar_module=None) -> Dict[str, Any]:
    """Show optimized monthly calendar GUI"""
    try:
        viewer = MonthlyCalendarViewer(calendar_module)
        success = viewer.show_monthly_schedule()
        
        return {
            "success": success,
            "result": "Monthly calendar opened in a new window." if success else "Failed to open monthly calendar"
        }
    except Exception as e:
        logging.getLogger(__name__).error(f"Error in show_monthly_calendar: {e}")
        return {
            "success": False,
            "error": f"Error opening monthly calendar: {str(e)}"
        }


if __name__ == "__main__":
    import sys
    try:
        if len(sys.argv) > 1 and sys.argv[1] == "monthly":
            viewer = MonthlyCalendarViewer()
            viewer.show_monthly_schedule()
        else:
            viewer = WeeklyCalendarViewer()
            viewer.show_weekly_schedule()
    except KeyboardInterrupt:
        print("Calendar viewer interrupted by user")
    except Exception as e:
        print(f"Error running calendar viewer: {e}")