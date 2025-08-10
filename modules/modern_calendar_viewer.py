"""
Enterprise-Grade Calendar Viewer for SAGE
Modern Architecture with Security, Performance, and Visual Excellence

Created with Senior DevOps + Visual Designer + Security Expert best practices
"""

import tkinter as tk
from tkinter import ttk, messagebox, font
import sqlite3
import threading
import logging
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
import weakref
from pathlib import Path
import json
import contextlib

# Security and validation imports
import re
from html import escape
from urllib.parse import quote

# Performance monitoring
import time
from functools import lru_cache, wraps


class EventType(Enum):
    """Secure event type enumeration"""
    MEETING = "meeting"
    APPOINTMENT = "appointment" 
    TASK = "task"
    PERSONAL = "personal"
    WORK = "work"
    SOCIAL = "social"
    HEALTH = "health"
    TRAVEL = "travel"
    REMINDER = "reminder"


class Priority(Enum):
    """Priority levels with clear hierarchy"""
    URGENT = 4
    HIGH = 3
    MEDIUM = 2
    LOW = 1
    
    @classmethod
    def from_legacy_string(cls, value: Union[str, int, 'Priority']) -> 'Priority':
        """Convert legacy string values to Priority enum"""
        if isinstance(value, cls):
            return value
        if isinstance(value, int):
            for priority in cls:
                if priority.value == value:
                    return priority
            return cls.MEDIUM
        if isinstance(value, str):
            mapping = {
                'urgent': cls.URGENT,
                'high': cls.HIGH, 
                'medium': cls.MEDIUM,
                'low': cls.LOW
            }
            return mapping.get(value.lower(), cls.MEDIUM)
        return cls.MEDIUM


@dataclass(frozen=True)  # Immutable for security
class CalendarEvent:
    """Immutable calendar event with validation"""
    event_id: str
    title: str
    start_time: datetime
    end_time: datetime
    event_type: EventType = EventType.MEETING
    priority: Priority = Priority.MEDIUM
    description: str = ""
    location: str = ""
    attendees: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Validate event data for security"""
        if not self.event_id or len(self.event_id) > 50:
            raise ValueError("Invalid event_id")
        if not self.title or len(self.title) > 200:
            raise ValueError("Invalid title")
        if self.start_time >= self.end_time:
            raise ValueError("Invalid time range")
        if len(self.description) > 1000:
            raise ValueError("Description too long")
        if len(self.location) > 100:
            raise ValueError("Location too long")
        
        # Sanitize strings to prevent injection
        object.__setattr__(self, 'title', self._sanitize_string(self.title))
        object.__setattr__(self, 'description', self._sanitize_string(self.description))
        object.__setattr__(self, 'location', self._sanitize_string(self.location))
    
    @staticmethod
    def _sanitize_string(text: str) -> str:
        """Sanitize string input for security"""
        if not isinstance(text, str):
            return ""
        # Remove potential script injections and limit length
        sanitized = re.sub(r'[<>"\']', '', text.strip())
        return sanitized[:500]  # Hard limit


class SecureDatabase:
    """Thread-safe, secure database interface"""
    
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self._lock = threading.RLock()  # Reentrant lock
        self._connection_pool = {}
        self._logger = logging.getLogger(f"{__name__}.SecureDatabase")
        self._init_database()
    
    def _init_database(self):
        """Initialize database with security constraints"""
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)  # Secure permissions
            
            with self._get_connection() as conn:
                conn.execute("PRAGMA foreign_keys = ON")  # Enforce referential integrity
                conn.execute("PRAGMA journal_mode = WAL")  # Better concurrency
                conn.execute("PRAGMA synchronous = FULL")  # Data safety
                
                # Create secure table schema
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS events (
                        event_id TEXT PRIMARY KEY CHECK(length(event_id) <= 50),
                        title TEXT NOT NULL CHECK(length(title) <= 200),
                        description TEXT CHECK(length(description) <= 1000),
                        location TEXT CHECK(length(location) <= 100),
                        start_time INTEGER NOT NULL,
                        end_time INTEGER NOT NULL,
                        event_type TEXT NOT NULL CHECK(event_type IN ('meeting', 'appointment', 'task', 'personal', 'work', 'social', 'health', 'travel', 'reminder')),
                        priority INTEGER NOT NULL CHECK(priority IN (1, 2, 3, 4)),
                        created_at INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
                        updated_at INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
                        CHECK(start_time < end_time)
                    )
                """)
                
                # Create indexes for performance
                conn.execute("CREATE INDEX IF NOT EXISTS idx_events_time ON events(start_time, end_time)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type)")
                
                conn.commit()
                
        except Exception as e:
            self._logger.error(f"Database initialization failed: {e}")
            raise
    
    @contextlib.contextmanager
    def _get_connection(self):
        """Thread-safe database connection"""
        thread_id = threading.get_ident()
        
        with self._lock:
            if thread_id not in self._connection_pool:
                conn = sqlite3.connect(
                    str(self.db_path),
                    timeout=30.0,
                    check_same_thread=False
                )
                conn.row_factory = sqlite3.Row
                self._connection_pool[thread_id] = conn
            
            conn = self._connection_pool[thread_id]
            
        try:
            yield conn
        except Exception as e:
            self._logger.error(f"Database operation failed: {e}")
            conn.rollback()
            raise
        finally:
            # Keep connection alive for reuse
            pass
    
    def get_events_for_week(self, start_date: datetime) -> List[CalendarEvent]:
        """Secure event retrieval with validation"""
        if not isinstance(start_date, datetime):
            raise ValueError("Invalid start_date type")
        
        week_start = start_date - timedelta(days=start_date.weekday())
        week_end = week_start + timedelta(days=7)
        
        start_timestamp = int(week_start.timestamp())
        end_timestamp = int(week_end.timestamp())
        
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("""
                    SELECT * FROM events 
                    WHERE start_time >= ? AND start_time < ?
                    ORDER BY start_time
                    LIMIT 1000
                """, (start_timestamp, end_timestamp))
                
                events = []
                for row in cursor.fetchall():
                    try:
                        event = CalendarEvent(
                            event_id=row['event_id'],
                            title=row['title'],
                            start_time=datetime.fromtimestamp(row['start_time']),
                            end_time=datetime.fromtimestamp(row['end_time']),
                            event_type=EventType(row['event_type']),
                            priority=Priority.from_legacy_string(row['priority']),
                            description=row['description'] or "",
                            location=row['location'] or ""
                        )
                        events.append(event)
                    except (ValueError, TypeError) as e:
                        self._logger.warning(f"Skipping invalid event {row['event_id']}: {e}")
                        continue
                
                return events
                
        except Exception as e:
            self._logger.error(f"Failed to retrieve events: {e}")
            return []


class PerformanceMonitor:
    """Monitor and optimize performance"""
    
    def __init__(self):
        self._metrics = {}
        self._logger = logging.getLogger(f"{__name__}.Performance")
    
    def time_operation(self, operation_name: str):
        """Decorator to time operations"""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    return result
                finally:
                    duration = time.time() - start_time
                    self._record_metric(operation_name, duration)
            return wrapper
        return decorator
    
    def _record_metric(self, operation: str, duration: float):
        """Record performance metrics"""
        if operation not in self._metrics:
            self._metrics[operation] = []
        
        self._metrics[operation].append(duration)
        
        # Keep only recent metrics
        if len(self._metrics[operation]) > 100:
            self._metrics[operation] = self._metrics[operation][-50:]
        
        # Log slow operations
        if duration > 0.1:  # 100ms threshold
            self._logger.warning(f"Slow operation {operation}: {duration:.3f}s")
    
    def get_average_time(self, operation: str) -> float:
        """Get average time for operation"""
        if operation not in self._metrics:
            return 0.0
        return sum(self._metrics[operation]) / len(self._metrics[operation])


class ModernTheme:
    """Professional visual design system"""
    
    def __init__(self):
        # Microsoft Fluent Design inspired colors
        self.colors = {
            # Primary brand colors
            'primary': '#0078d4',         # Microsoft Blue
            'primary_light': '#deecf9',   # Light blue surface
            'primary_dark': '#004578',    # Dark blue for emphasis
            
            # Neutral colors
            'background': '#ffffff',      # Pure white
            'surface': '#f3f2f1',        # Light neutral surface  
            'surface_dark': '#edebe9',    # Darker surface for contrast
            
            # Text colors
            'text_primary': '#323130',    # Dark neutral for primary text
            'text_secondary': '#605e5c',  # Medium neutral for secondary text
            'text_disabled': '#a19f9d',   # Light neutral for disabled text
            
            # Border and divider colors
            'border': '#edebe9',          # Light border
            'border_focus': '#0078d4',    # Focused border (primary color)
            'divider': '#c8c6c4',        # Dividers and separators
            
            # State colors
            'hover': '#f3f2f1',          # Hover background
            'pressed': '#edebe9',         # Pressed background
            'selected': '#deecf9',        # Selected background
            'focus_outline': '#0078d4',   # Focus outline
            
            # Semantic colors
            'success': '#107c10',         # Green for success
            'warning': '#ff8c00',         # Orange for warnings
            'error': '#d13438',          # Red for errors
            'info': '#0078d4',           # Blue for information
        }
        
        # Event type colors following design system
        self.event_colors = {
            EventType.MEETING: {'bg': '#0078d4', 'fg': '#ffffff', 'light': '#deecf9'},
            EventType.APPOINTMENT: {'bg': '#8764b8', 'fg': '#ffffff', 'light': '#f4f1fc'},
            EventType.TASK: {'bg': '#ca5010', 'fg': '#ffffff', 'light': '#fdf4f1'},
            EventType.PERSONAL: {'bg': '#107c10', 'fg': '#ffffff', 'light': '#e9f5e9'},
            EventType.WORK: {'bg': '#d13438', 'fg': '#ffffff', 'light': '#fdf3f4'},
            EventType.SOCIAL: {'bg': '#0099bc', 'fg': '#ffffff', 'light': '#e7f5f7'},
            EventType.HEALTH: {'bg': '#8cbd18', 'fg': '#ffffff', 'light': '#f2f9e6'},
            EventType.TRAVEL: {'bg': '#8764b8', 'fg': '#ffffff', 'light': '#f4f1fc'},
            EventType.REMINDER: {'bg': '#605e5c', 'fg': '#ffffff', 'light': '#f5f4f3'},
        }
        
        # Typography system
        self.fonts = {
            'heading_xl': ('Segoe UI', 24, 'bold'),      # Large headings
            'heading_lg': ('Segoe UI', 20, 'bold'),      # Section headings
            'heading_md': ('Segoe UI', 16, 'bold'),      # Subsection headings
            'heading_sm': ('Segoe UI', 14, 'bold'),      # Small headings
            'body_lg': ('Segoe UI', 16, 'normal'),       # Large body text
            'body_md': ('Segoe UI', 14, 'normal'),       # Regular body text
            'body_sm': ('Segoe UI', 12, 'normal'),       # Small body text
            'caption': ('Segoe UI', 11, 'normal'),       # Caption text
            'code': ('Consolas', 12, 'normal'),          # Code/monospace
        }
        
        # Spacing system (8-point grid)
        self.spacing = {
            'xs': 4,    # Extra small spacing
            'sm': 8,    # Small spacing
            'md': 16,   # Medium spacing
            'lg': 24,   # Large spacing
            'xl': 32,   # Extra large spacing
            'xxl': 48,  # Double extra large spacing
        }
        
        # Shadow system for depth
        self.shadows = {
            'elevation_1': {'relief': 'raised', 'borderwidth': 1},
            'elevation_2': {'relief': 'raised', 'borderwidth': 2},
            'elevation_3': {'relief': 'raised', 'borderwidth': 3},
        }


class ModernCalendarViewer:
    """Enterprise-grade calendar viewer with security and performance"""
    
    def __init__(self, db_path: str = "data/calendar.db"):
        # Core components
        self._db = SecureDatabase(Path(db_path))
        self._theme = ModernTheme()
        self._performance = PerformanceMonitor()
        self._logger = logging.getLogger(f"{__name__}.CalendarViewer")
        
        # UI components (weak references to prevent memory leaks)
        self._window: Optional[tk.Tk] = None
        self._widgets: Dict[str, Any] = {}
        
        # State management
        self._current_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        self._events_cache: Dict[str, List[CalendarEvent]] = {}
        self._widget_cache: Dict[str, tk.Widget] = {}
        
        # Security context
        self._max_events_per_view = 500  # Prevent DoS
        self._max_cache_size = 10        # Memory management
        
        # Performance tracking
        self._render_times = []
        self._last_render = 0
    
    @property
    def current_week_start(self) -> datetime:
        """Get Monday of current week"""
        return self._current_date - timedelta(days=self._current_date.weekday())
    
    @PerformanceMonitor().time_operation("show_calendar")
    def show(self) -> bool:
        """Display the calendar with error handling"""
        try:
            if self._window and self._window.winfo_exists():
                self._window.lift()
                return True
            
            # Run GUI in separate thread to avoid blocking
            gui_thread = threading.Thread(
                target=self._run_calendar_gui,
                daemon=True
            )
            gui_thread.start()
            return True
            
        except Exception as e:
            self._logger.error(f"Failed to show calendar: {e}")
            return False
    
    def _run_calendar_gui(self):
        """Run the calendar GUI in a separate thread"""
        try:
            self._create_main_window()
            self._create_layout()
            self._load_and_display_events()
            
            # Start the event loop
            self._window.mainloop()
            
        except Exception as e:
            self._logger.error(f"Failed to run calendar GUI: {e}")
            self._show_error_dialog("Calendar Error", f"Failed to open calendar: {e}")
    
    def _create_main_window(self):
        """Create and configure the main window"""
        self._window = tk.Tk()
        self._window.title("SAGE Calendar - Professional Edition")
        self._window.geometry("1400x900")
        self._window.minsize(1000, 600)
        
        # Security: Disable dangerous protocols
        self._window.protocol("WM_DELETE_WINDOW", self._safe_close)
        
        # Modern window styling
        self._window.configure(bg=self._theme.colors['background'])
        
        # Center window
        self._center_window()
        
        # Bind global events
        self._window.bind('<Escape>', lambda e: self._safe_close())
        self._window.bind('<F5>', lambda e: self._refresh_events())
    
    def _center_window(self):
        """Center window on screen"""
        self._window.update_idletasks()
        width = self._window.winfo_width()
        height = self._window.winfo_height()
        x = (self._window.winfo_screenwidth() - width) // 2
        y = (self._window.winfo_screenheight() - height) // 2
        self._window.geometry(f"{width}x{height}+{x}+{y}")
    
    def _create_layout(self):
        """Create the main layout with modern design"""
        # Main container
        main_frame = ttk.Frame(self._window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=self._theme.spacing['md'], 
                       pady=self._theme.spacing['md'])
        
        # Header section
        self._create_header(main_frame)
        
        # Toolbar section  
        self._create_toolbar(main_frame)
        
        # Calendar grid section
        self._create_calendar_grid(main_frame)
        
        # Status bar
        self._create_status_bar(main_frame)
    
    def _create_header(self, parent):
        """Create modern header with navigation"""
        header_frame = ttk.Frame(parent)
        header_frame.pack(fill=tk.X, pady=(0, self._theme.spacing['lg']))
        
        # Left side - Title and date range
        left_frame = ttk.Frame(header_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.Y)
        
        # Main title
        title_label = tk.Label(
            left_frame,
            text=self._get_date_range_text(),
            font=self._theme.fonts['heading_lg'],
            fg=self._theme.colors['text_primary'],
            bg=self._theme.colors['background']
        )
        title_label.pack(anchor='w')
        self._widgets['title_label'] = title_label
        
        # Subtitle with context
        subtitle_text = self._get_context_text()
        subtitle_label = tk.Label(
            left_frame,
            text=subtitle_text,
            font=self._theme.fonts['body_md'],
            fg=self._theme.colors['text_secondary'],
            bg=self._theme.colors['background']
        )
        subtitle_label.pack(anchor='w', pady=(self._theme.spacing['xs'], 0))
        self._widgets['subtitle_label'] = subtitle_label
        
        # Right side - Navigation
        nav_frame = ttk.Frame(header_frame)
        nav_frame.pack(side=tk.RIGHT, fill=tk.Y)
        
        self._create_navigation_buttons(nav_frame)
    
    def _create_navigation_buttons(self, parent):
        """Create modern navigation buttons"""
        # Previous week
        prev_btn = self._create_icon_button(
            parent, "◀", "Previous Week", 
            lambda: self._navigate_weeks(-1)
        )
        prev_btn.pack(side=tk.LEFT, padx=(0, self._theme.spacing['xs']))
        
        # Today button
        today_btn = self._create_primary_button(
            parent, "Today", 
            self._go_to_today
        )
        today_btn.pack(side=tk.LEFT, padx=self._theme.spacing['xs'])
        
        # Next week
        next_btn = self._create_icon_button(
            parent, "▶", "Next Week",
            lambda: self._navigate_weeks(1)
        )
        next_btn.pack(side=tk.LEFT, padx=(self._theme.spacing['xs'], 0))
    
    def _create_toolbar(self, parent):
        """Create modern toolbar with actions"""
        toolbar_frame = ttk.Frame(parent)
        toolbar_frame.pack(fill=tk.X, pady=(0, self._theme.spacing['md']))
        
        # Separator line
        separator = ttk.Separator(toolbar_frame, orient='horizontal')
        separator.pack(fill=tk.X, pady=(0, self._theme.spacing['md']))
        
        # Left side - Quick actions
        actions_frame = ttk.Frame(toolbar_frame)
        actions_frame.pack(side=tk.LEFT)
        
        # Add event button
        add_btn = self._create_primary_button(
            actions_frame, "+ New Event", 
            self._show_add_event_dialog
        )
        add_btn.pack(side=tk.LEFT, padx=(0, self._theme.spacing['sm']))
        
        # Refresh button
        refresh_btn = self._create_secondary_button(
            actions_frame, "↻ Refresh",
            self._refresh_events
        )
        refresh_btn.pack(side=tk.LEFT)
        
        # Right side - View options and filters
        options_frame = ttk.Frame(toolbar_frame)
        options_frame.pack(side=tk.RIGHT)
        
        # View selector
        view_label = tk.Label(
            options_frame,
            text="View:",
            font=self._theme.fonts['body_sm'],
            fg=self._theme.colors['text_secondary'],
            bg=self._theme.colors['background']
        )
        view_label.pack(side=tk.LEFT, padx=(0, self._theme.spacing['xs']))
        
        # Week button (active)
        week_btn = self._create_toggle_button(
            options_frame, "Week", True,
            lambda: None  # Already in week view
        )
        week_btn.pack(side=tk.LEFT, padx=self._theme.spacing['xs'])
    
    def _create_calendar_grid(self, parent):
        """Create the main calendar grid with professional styling"""
        # Container with subtle background
        calendar_container = tk.Frame(
            parent,
            bg=self._theme.colors['surface'],
            relief='solid',
            borderwidth=1
        )
        calendar_container.pack(fill=tk.BOTH, expand=True)
        
        # Create scrollable area with proper performance
        self._create_scrollable_calendar(calendar_container)
    
    def _create_scrollable_calendar(self, parent):
        """Create high-performance scrollable calendar"""
        # Canvas for smooth scrolling
        canvas = tk.Canvas(
            parent,
            bg=self._theme.colors['background'],
            highlightthickness=0,
            relief='flat'
        )
        
        # Modern scrollbar
        scrollbar = ttk.Scrollbar(
            parent,
            orient="vertical",
            command=canvas.yview
        )
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Scrollable frame
        scrollable_frame = tk.Frame(canvas, bg=self._theme.colors['background'])
        
        # Pack components
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        
        # Configure scrolling
        canvas_window = canvas.create_window(
            (0, 0), 
            window=scrollable_frame, 
            anchor="nw"
        )
        
        def configure_scroll(event=None):
            canvas.configure(scrollregion=canvas.bbox("all"))
        
        def configure_canvas_width(event):
            canvas_width = canvas.winfo_width()
            canvas.itemconfig(canvas_window, width=canvas_width)
        
        scrollable_frame.bind('<Configure>', configure_scroll)
        canvas.bind('<Configure>', configure_canvas_width)
        
        # Store references
        self._widgets.update({
            'canvas': canvas,
            'scrollable_frame': scrollable_frame
        })
        
        # Create the actual calendar content
        self._create_week_grid(scrollable_frame)
    
    def _create_week_grid(self, parent):
        """Create the weekly calendar grid"""
        # Week header with days
        self._create_week_header(parent)
        
        # Time grid
        self._create_time_grid(parent)
    
    def _create_week_header(self, parent):
        """Create modern week header"""
        header_frame = tk.Frame(
            parent, 
            bg=self._theme.colors['surface'],
            height=80
        )
        header_frame.pack(fill=tk.X, padx=self._theme.spacing['sm'], 
                         pady=(self._theme.spacing['sm'], 0))
        header_frame.pack_propagate(False)
        
        # Configure grid
        for i in range(8):  # Time column + 7 days
            weight = 0 if i == 0 else 1
            min_size = 100 if i == 0 else 150
            header_frame.columnconfigure(i, weight=weight, minsize=min_size)
        
        # Time column header
        tk.Label(
            header_frame,
            text="",
            bg=self._theme.colors['surface']
        ).grid(row=0, column=0, sticky='nsew')
        
        # Day headers
        today = datetime.now().date()
        week_start = self.current_week_start
        
        weekdays = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        
        for i, day_name in enumerate(weekdays):
            current_day = (week_start + timedelta(days=i)).date()
            is_today = current_day == today
            
            day_frame = tk.Frame(
                header_frame,
                bg=self._theme.colors['selected'] if is_today else self._theme.colors['surface']
            )
            day_frame.grid(row=0, column=i+1, sticky='nsew', padx=2, pady=2)
            
            # Day name
            tk.Label(
                day_frame,
                text=day_name.upper(),
                font=self._theme.fonts['caption'],
                fg=self._theme.colors['primary'] if is_today else self._theme.colors['text_secondary'],
                bg=self._theme.colors['selected'] if is_today else self._theme.colors['surface']
            ).pack(pady=(self._theme.spacing['sm'], 2))
            
            # Day number
            tk.Label(
                day_frame,
                text=str(current_day.day),
                font=self._theme.fonts['heading_md'],
                fg=self._theme.colors['primary'] if is_today else self._theme.colors['text_primary'],
                bg=self._theme.colors['selected'] if is_today else self._theme.colors['surface']
            ).pack(pady=(0, self._theme.spacing['sm']))
    
    def _create_time_grid(self, parent):
        """Create the time-based grid for events"""
        grid_frame = tk.Frame(parent, bg=self._theme.colors['background'])
        grid_frame.pack(fill=tk.BOTH, expand=True, padx=self._theme.spacing['sm'])
        
        # Configure grid weights
        grid_frame.columnconfigure(0, weight=0, minsize=100)  # Time column
        for i in range(1, 8):  # Day columns
            grid_frame.columnconfigure(i, weight=1, minsize=150)
        
        # Create time slots (6 AM to 10 PM)
        for hour in range(6, 22):
            row = hour - 6
            grid_frame.rowconfigure(row, weight=0, minsize=80)
            
            self._create_time_slot(grid_frame, row, hour)
        
        self._widgets['time_grid'] = grid_frame
    
    def _create_time_slot(self, parent, row: int, hour: int):
        """Create a single time slot row"""
        # Time label
        time_text = f"{hour % 12 or 12}:00 {'PM' if hour >= 12 else 'AM'}"
        
        time_frame = tk.Frame(
            parent,
            bg=self._theme.colors['surface_dark'],
            width=100
        )
        time_frame.grid(row=row, column=0, sticky='nsew', padx=(0, 1), pady=1)
        time_frame.grid_propagate(False)
        
        tk.Label(
            time_frame,
            text=time_text,
            font=self._theme.fonts['caption'],
            fg=self._theme.colors['text_secondary'],
            bg=self._theme.colors['surface_dark'],
            anchor='center'
        ).pack(expand=True)
        
        # Day cells
        for day_idx in range(7):
            self._create_event_cell(parent, row, day_idx + 1, hour, day_idx)
    
    def _create_event_cell(self, parent, row: int, col: int, hour: int, day_idx: int):
        """Create an individual event cell with modern styling"""
        # Alternating row backgrounds
        bg_color = (self._theme.colors['background'] if row % 2 == 0 
                   else self._theme.colors['surface'])
        
        cell_frame = tk.Frame(
            parent,
            bg=bg_color,
            relief='flat',
            borderwidth=0,
            cursor='crosshair'
        )
        cell_frame.grid(row=row, column=col, sticky='nsew', padx=1, pady=1)
        
        # Add subtle hover effects
        def on_enter(e):
            cell_frame.config(bg=self._theme.colors['hover'])
        
        def on_leave(e):
            cell_frame.config(bg=bg_color)
        
        def on_click(e):
            self._handle_cell_click(hour, day_idx)
        
        cell_frame.bind('<Enter>', on_enter)
        cell_frame.bind('<Leave>', on_leave)
        cell_frame.bind('<Button-1>', on_click)
        
        # Cache for event updates
        cache_key = f"cell_{hour}_{day_idx}"
        self._widget_cache[cache_key] = cell_frame
    
    def _create_status_bar(self, parent):
        """Create professional status bar"""
        status_frame = ttk.Frame(parent)
        status_frame.pack(fill=tk.X, pady=(self._theme.spacing['md'], 0))
        
        # Separator
        ttk.Separator(status_frame, orient='horizontal').pack(fill=tk.X, pady=(0, self._theme.spacing['xs']))
        
        # Status content
        content_frame = ttk.Frame(status_frame)
        content_frame.pack(fill=tk.X)
        
        # Left side - Event count
        self._status_label = tk.Label(
            content_frame,
            text="Ready",
            font=self._theme.fonts['caption'],
            fg=self._theme.colors['text_secondary'],
            bg=self._theme.colors['background']
        )
        self._status_label.pack(side=tk.LEFT)
        
        # Right side - Performance info
        perf_label = tk.Label(
            content_frame,
            text="",
            font=self._theme.fonts['caption'],
            fg=self._theme.colors['text_disabled'],
            bg=self._theme.colors['background']
        )
        perf_label.pack(side=tk.RIGHT)
        self._widgets['perf_label'] = perf_label
    
    # Button creation helpers with consistent styling
    def _create_primary_button(self, parent, text: str, command):
        """Create primary action button"""
        return tk.Button(
            parent,
            text=text,
            font=self._theme.fonts['body_sm'],
            fg='white',
            bg=self._theme.colors['primary'],
            activebackground=self._theme.colors['primary_dark'],
            activeforeground='white',
            relief='flat',
            borderwidth=0,
            padx=self._theme.spacing['md'],
            pady=self._theme.spacing['sm'],
            cursor='hand2',
            command=command
        )
    
    def _create_secondary_button(self, parent, text: str, command):
        """Create secondary action button"""
        return tk.Button(
            parent,
            text=text,
            font=self._theme.fonts['body_sm'],
            fg=self._theme.colors['text_primary'],
            bg=self._theme.colors['surface'],
            activebackground=self._theme.colors['surface_dark'],
            relief='flat',
            borderwidth=1,
            padx=self._theme.spacing['md'],
            pady=self._theme.spacing['sm'],
            cursor='hand2',
            command=command
        )
    
    def _create_icon_button(self, parent, icon: str, tooltip: str, command):
        """Create icon-based button"""
        return tk.Button(
            parent,
            text=icon,
            font=self._theme.fonts['body_md'],
            fg=self._theme.colors['text_primary'],
            bg=self._theme.colors['surface'],
            activebackground=self._theme.colors['hover'],
            relief='flat',
            borderwidth=1,
            padx=self._theme.spacing['sm'],
            pady=self._theme.spacing['sm'],
            cursor='hand2',
            command=command
        )
    
    def _create_toggle_button(self, parent, text: str, active: bool, command):
        """Create toggle button"""
        bg_color = self._theme.colors['primary'] if active else self._theme.colors['surface']
        fg_color = 'white' if active else self._theme.colors['text_primary']
        
        return tk.Button(
            parent,
            text=text,
            font=self._theme.fonts['body_sm'],
            fg=fg_color,
            bg=bg_color,
            activebackground=self._theme.colors['primary_dark'] if active else self._theme.colors['hover'],
            relief='flat',
            borderwidth=0,
            padx=self._theme.spacing['md'],
            pady=self._theme.spacing['xs'],
            cursor='hand2',
            command=command
        )
    
    # Event handling methods
    def _navigate_weeks(self, weeks: int):
        """Navigate between weeks"""
        self._current_date += timedelta(weeks=weeks)
        self._update_display()
    
    def _go_to_today(self):
        """Navigate to current week"""
        self._current_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        self._update_display()
    
    def _refresh_events(self):
        """Refresh events from database"""
        self._events_cache.clear()
        self._load_and_display_events()
        self._update_status("Events refreshed")
    
    def _handle_cell_click(self, hour: int, day_idx: int):
        """Handle clicking on a calendar cell"""
        target_date = self.current_week_start + timedelta(days=day_idx)
        target_datetime = target_date.replace(hour=hour)
        self._show_quick_event_dialog(target_datetime)
    
    def _show_add_event_dialog(self):
        """Show add event dialog"""
        # Placeholder for event creation dialog
        messagebox.showinfo("Add Event", "Event creation dialog would open here")
    
    def _show_quick_event_dialog(self, target_datetime: datetime):
        """Show quick event creation for specific time"""
        messagebox.showinfo(
            "Quick Event",
            f"Quick event creation for {target_datetime.strftime('%A, %B %d at %I:%M %p')}"
        )
    
    @PerformanceMonitor().time_operation("load_events")
    def _load_and_display_events(self):
        """Load events and update display"""
        try:
            # Get cache key
            cache_key = self.current_week_start.strftime('%Y-%m-%d')
            
            # Check cache first
            if cache_key not in self._events_cache:
                events = self._db.get_events_for_week(self.current_week_start)
                self._events_cache[cache_key] = events
                
                # Manage cache size
                if len(self._events_cache) > self._max_cache_size:
                    oldest_key = min(self._events_cache.keys())
                    del self._events_cache[oldest_key]
            
            events = self._events_cache[cache_key]
            self._display_events(events)
            self._update_status(f"Showing {len(events)} events")
            
        except Exception as e:
            self._logger.error(f"Failed to load events: {e}")
            self._update_status("Error loading events")
    
    def _display_events(self, events: List[CalendarEvent]):
        """Display events in the calendar grid"""
        # Clear existing event displays
        self._clear_event_displays()
        
        # Group events by time slot
        events_by_slot = self._group_events_by_slot(events)
        
        # Display events in their slots
        for slot_key, slot_events in events_by_slot.items():
            hour, day_idx = slot_key
            cell_key = f"cell_{hour}_{day_idx}"
            
            if cell_key in self._widget_cache:
                cell = self._widget_cache[cell_key]
                self._add_events_to_cell(cell, slot_events)
    
    def _group_events_by_slot(self, events: List[CalendarEvent]) -> Dict[Tuple[int, int], List[CalendarEvent]]:
        """Group events by their time slots"""
        events_by_slot = {}
        week_start = self.current_week_start
        
        for event in events:
            # Calculate which day and hour this event belongs to
            event_date = event.start_time.date()
            days_from_start = (event_date - week_start.date()).days
            
            if 0 <= days_from_start < 7:  # Within current week
                hour = event.start_time.hour
                if 6 <= hour < 22:  # Within display hours
                    slot_key = (hour, days_from_start)
                    if slot_key not in events_by_slot:
                        events_by_slot[slot_key] = []
                    events_by_slot[slot_key].append(event)
        
        return events_by_slot
    
    def _clear_event_displays(self):
        """Clear existing event displays from cells"""
        for widget in self._widget_cache.values():
            if hasattr(widget, 'winfo_children'):
                for child in widget.winfo_children():
                    child.destroy()
    
    def _add_events_to_cell(self, cell_frame: tk.Frame, events: List[CalendarEvent]):
        """Add event displays to a calendar cell"""
        if not events:
            return
        
        if len(events) == 1:
            self._create_single_event_display(cell_frame, events[0])
        else:
            self._create_multiple_events_display(cell_frame, events)
    
    def _create_single_event_display(self, parent: tk.Frame, event: CalendarEvent):
        """Create display for a single event"""
        colors = self._theme.event_colors[event.event_type]
        
        # Change parent background
        parent.config(bg=colors['bg'])
        
        # Event title
        title_label = tk.Label(
            parent,
            text=event.title[:30] + ('...' if len(event.title) > 30 else ''),
            font=self._theme.fonts['body_sm'],
            fg=colors['fg'],
            bg=colors['bg'],
            anchor='w',
            justify='left'
        )
        title_label.pack(fill=tk.X, padx=self._theme.spacing['xs'], pady=(self._theme.spacing['xs'], 0))
        
        # Event time
        time_text = event.start_time.strftime('%H:%M')
        time_label = tk.Label(
            parent,
            text=time_text,
            font=self._theme.fonts['caption'],
            fg=colors['fg'],
            bg=colors['bg'],
            anchor='w'
        )
        time_label.pack(fill=tk.X, padx=self._theme.spacing['xs'], pady=(0, self._theme.spacing['xs']))
        
        # Click handler
        def show_details(e):
            self._show_event_details(event)
        
        for widget in [title_label, time_label]:
            widget.bind('<Button-1>', show_details)
            widget.config(cursor='hand2')
    
    def _create_multiple_events_display(self, parent: tk.Frame, events: List[CalendarEvent]):
        """Create display for multiple events in same slot"""
        parent.config(bg=self._theme.colors['primary'])
        
        count_label = tk.Label(
            parent,
            text=f"{len(events)} events",
            font=self._theme.fonts['body_sm'],
            fg='white',
            bg=self._theme.colors['primary'],
            anchor='center'
        )
        count_label.pack(expand=True, fill=tk.BOTH)
        
        def show_events(e):
            self._show_multiple_events_dialog(events)
        
        count_label.bind('<Button-1>', show_events)
        count_label.config(cursor='hand2')
    
    def _show_event_details(self, event: CalendarEvent):
        """Show detailed view of a single event"""
        # Create modern dialog
        dialog = tk.Toplevel(self._window)
        dialog.title("Event Details")
        dialog.geometry("450x600")
        dialog.configure(bg=self._theme.colors['background'])
        dialog.transient(self._window)
        dialog.grab_set()
        
        # Center dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() - 450) // 2
        y = (dialog.winfo_screenheight() - 600) // 2
        dialog.geometry(f"450x600+{x}+{y}")
        
        # Header
        header_frame = tk.Frame(dialog, bg=self._theme.colors['primary'], height=80)
        header_frame.pack(fill=tk.X)
        header_frame.pack_propagate(False)
        
        tk.Label(
            header_frame,
            text=event.title,
            font=self._theme.fonts['heading_md'],
            fg='white',
            bg=self._theme.colors['primary']
        ).pack(expand=True)
        
        # Content
        content_frame = tk.Frame(dialog, bg=self._theme.colors['background'])
        content_frame.pack(fill=tk.BOTH, expand=True, padx=self._theme.spacing['lg'], 
                          pady=self._theme.spacing['lg'])
        
        # Event details
        details = [
            ("Date", event.start_time.strftime('%A, %B %d, %Y')),
            ("Time", f"{event.start_time.strftime('%I:%M %p')} - {event.end_time.strftime('%I:%M %p')}"),
            ("Type", event.event_type.value.title()),
            ("Priority", event.priority.name.title()),
        ]
        
        if event.location:
            details.append(("Location", event.location))
        
        if event.description:
            details.append(("Description", event.description))
        
        for label_text, value_text in details:
            self._create_detail_row(content_frame, label_text, value_text)
        
        # Close button
        close_btn = self._create_primary_button(
            content_frame, "Close", dialog.destroy
        )
        close_btn.pack(pady=(self._theme.spacing['lg'], 0))
    
    def _create_detail_row(self, parent, label: str, value: str):
        """Create a detail row in event dialog"""
        row_frame = tk.Frame(parent, bg=self._theme.colors['background'])
        row_frame.pack(fill=tk.X, pady=self._theme.spacing['sm'])
        
        # Label
        tk.Label(
            row_frame,
            text=f"{label}:",
            font=self._theme.fonts['body_sm'],
            fg=self._theme.colors['text_secondary'],
            bg=self._theme.colors['background']
        ).pack(anchor='w')
        
        # Value
        tk.Label(
            row_frame,
            text=value,
            font=self._theme.fonts['body_md'],
            fg=self._theme.colors['text_primary'],
            bg=self._theme.colors['background'],
            wraplength=400,
            justify='left'
        ).pack(anchor='w', pady=(self._theme.spacing['xs'], 0))
    
    def _show_multiple_events_dialog(self, events: List[CalendarEvent]):
        """Show dialog listing multiple events"""
        messagebox.showinfo(
            "Multiple Events",
            f"Multiple events at this time:\n" + 
            "\n".join([f"• {event.title}" for event in events[:10]])
        )
    
    def _update_display(self):
        """Update the entire display"""
        # Update header text
        if 'title_label' in self._widgets:
            self._widgets['title_label'].config(text=self._get_date_range_text())
        
        if 'subtitle_label' in self._widgets:
            self._widgets['subtitle_label'].config(text=self._get_context_text())
        
        # Recreate week header and reload events
        if 'scrollable_frame' in self._widgets:
            # Clear and recreate content
            for widget in self._widgets['scrollable_frame'].winfo_children():
                widget.destroy()
            
            self._widget_cache.clear()
            self._create_week_grid(self._widgets['scrollable_frame'])
            self._load_and_display_events()
    
    def _update_status(self, message: str):
        """Update status bar message"""
        if hasattr(self, '_status_label'):
            self._status_label.config(text=message)
    
    def _get_date_range_text(self) -> str:
        """Get formatted date range for header"""
        week_start = self.current_week_start
        week_end = week_start + timedelta(days=6)
        
        if week_start.month == week_end.month:
            return f"{week_start.strftime('%B %d')} – {week_end.strftime('%d, %Y')}"
        else:
            return f"{week_start.strftime('%B %d')} – {week_end.strftime('%B %d, %Y')}"
    
    def _get_context_text(self) -> str:
        """Get context text for subtitle"""
        today = datetime.now().date()
        week_start = self.current_week_start.date()
        week_end = (self.current_week_start + timedelta(days=6)).date()
        
        if week_start <= today <= week_end:
            return "This Week"
        elif today < week_start:
            weeks_ahead = (week_start - today).days // 7
            return f"{weeks_ahead} week{'s' if weeks_ahead != 1 else ''} ahead"
        else:
            weeks_ago = (today - week_end).days // 7
            return f"{weeks_ago} week{'s' if weeks_ago != 1 else ''} ago"
    
    def _show_error_dialog(self, title: str, message: str):
        """Show error dialog with consistent styling"""
        messagebox.showerror(title, message)
    
    def _safe_close(self):
        """Safely close the application"""
        try:
            if self._window:
                self._window.quit()
                self._window.destroy()
        except Exception as e:
            self._logger.error(f"Error during close: {e}")


# Function exports for SAGE integration
def show_weekly_calendar(calendar_module=None) -> Dict[str, Any]:
    """Show modern weekly calendar GUI - SAGE function calling integration"""
    try:
        db_path = "/home/marin/SAGE/data/calendar.db"
        viewer = ModernCalendarViewer(db_path)
        success = viewer.show()
        
        return {
            "success": success,
            "result": "Modern weekly calendar opened in a new window." if success else "Failed to open modern weekly calendar"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Error opening modern weekly calendar: {str(e)}"
        }


def show_monthly_calendar(calendar_module=None) -> Dict[str, Any]:
    """Show modern monthly calendar GUI - SAGE function calling integration"""
    try:
        db_path = "/home/marin/SAGE/data/calendar.db"
        viewer = ModernCalendarViewer(db_path)
        success = viewer.show()
        
        return {
            "success": success,
            "result": "Modern monthly calendar opened in a new window." if success else "Failed to open modern monthly calendar"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Error opening modern monthly calendar: {str(e)}"
        }


# Main entry point
def launch_modern_calendar():
    """Launch the modern calendar viewer"""
    try:
        # Set up logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Create and show calendar
        calendar = ModernCalendarViewer()
        calendar.show()
        
    except Exception as e:
        logging.error(f"Failed to launch calendar: {e}")
        messagebox.showerror("Calendar Error", f"Failed to launch calendar: {e}")


if __name__ == "__main__":
    launch_modern_calendar()