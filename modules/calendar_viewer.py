"""
Modern Visual Calendar Viewer for SAGE
Creates a beautiful GUI window showing weekly/monthly schedule with modern design
Inspired by Google Calendar and Outlook Calendar aesthetics
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, font
import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Any
import threading
import json
import calendar as cal  # Rename to avoid conflict with modules/calendar package


class WeeklyCalendarViewer:
    """Modern GUI window for displaying weekly calendar with beautiful design"""
    
    def __init__(self, calendar_module=None):
        self.calendar_module = calendar_module
        self.window = None
        self.main_frame = None
        self.calendar_canvas = None
        self.current_start_date = None
        
        # Modern color palette inspired by Google Calendar
        self.colors = {
            'primary': '#1a73e8',        # Google Blue
            'primary_light': '#e8f0fe',   # Light blue background
            'secondary': '#34a853',       # Google Green
            'background': '#ffffff',      # Pure white
            'surface': '#f8f9fa',         # Light gray surface
            'border': '#e0e0e0',         # Light border
            'text_primary': '#202124',    # Dark gray text
            'text_secondary': '#5f6368',  # Medium gray text
            'hover': '#f1f3f4',          # Hover background
            'shadow': '#00000010',        # Subtle shadow
        }
        
        # Modern event colors (softer, more appealing)
        self.event_colors = {
            'meeting': {'bg': '#1a73e8', 'text': '#ffffff', 'light': '#e8f0fe'},      # Blue
            'appointment': {'bg': '#9c27b0', 'text': '#ffffff', 'light': '#f3e5f5'},  # Purple
            'task': {'bg': '#ff9800', 'text': '#ffffff', 'light': '#fff3e0'},         # Orange
            'personal': {'bg': '#4caf50', 'text': '#ffffff', 'light': '#e8f5e8'},     # Green
            'work': {'bg': '#f44336', 'text': '#ffffff', 'light': '#ffebee'},         # Red
            'social': {'bg': '#00bcd4', 'text': '#ffffff', 'light': '#e0f2f1'},       # Cyan
            'health': {'bg': '#8bc34a', 'text': '#ffffff', 'light': '#f1f8e9'},       # Light green
            'default': {'bg': '#757575', 'text': '#ffffff', 'light': '#f5f5f5'}       # Gray
        }
        
        # Performance optimization - Cache frequently accessed data and widgets
        self.events_cache = {}
        self.widget_cache = {}  # Cache widgets for reuse
        self.grid_widgets = {}  # Store current grid widgets by position
        self.last_week_key = None
        self.last_refresh = 0
        
        # Virtualization - only create widgets that are visible
        self.visible_hours = list(range(6, 22))  # 6 AM to 10 PM
        self.grid_created = False
        
        # Modern fonts
        self.fonts = {
            'title': ('Segoe UI', 20, 'bold'),
            'subtitle': ('Segoe UI', 12, 'bold'), 
            'body': ('Segoe UI', 10, 'normal'),
            'small': ('Segoe UI', 9, 'normal'),
            'time': ('Segoe UI', 9, 'bold')
        }
        
    def show_weekly_schedule(self, start_date: datetime = None) -> bool:
        """Display weekly calendar starting from given date (default: today)"""
        try:
            if start_date is None:
                start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            
            # Run GUI in separate thread to avoid blocking
            gui_thread = threading.Thread(
                target=self._create_calendar_window,
                args=(start_date,),
                daemon=True
            )
            gui_thread.start()
            return True
            
        except Exception as e:
            print(f"Error showing weekly schedule: {e}")
            return False
    
    def _create_calendar_window(self, start_date: datetime):
        """Create and display the modern calendar window"""
        try:
            self.current_start_date = start_date
            
            # Create main window with modern styling
            self.window = tk.Tk()
            self.window.title("SAGE Calendar - Weekly View")
            self.window.geometry("1400x900")
            self.window.configure(bg=self.colors['background'])
            self.window.minsize(1200, 700)
            
            # Remove window decorations for modern look (optional)
            # self.window.overrideredirect(False)
            
            # Configure modern styling
            style = ttk.Style()
            style.theme_use('clam')
            
            # Create main container
            self.main_frame = tk.Frame(self.window, bg=self.colors['background'])
            self.main_frame.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)
            
            # Create header with navigation
            self._create_modern_header()
            
            # Create toolbar with quick actions
            self._create_toolbar()
            
            # Create the modern calendar grid
            self._create_modern_calendar_grid()
            
            # Add subtle shadow effect to window
            self.window.wm_attributes("-topmost", False)
            
            # Bind window resize event for smooth resizing
            self.window.bind('<Configure>', self._on_window_resize)
            
            # Center window on screen
            self._center_window()
            
            # Start the GUI event loop
            self.window.mainloop()
            
        except Exception as e:
            print(f"Error creating modern calendar window: {e}")
    
    def _center_window(self):
        """Center the window on screen"""
        self.window.update_idletasks()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        pos_x = (self.window.winfo_screenwidth() // 2) - (width // 2)
        pos_y = (self.window.winfo_screenheight() // 2) - (height // 2)
        self.window.geometry(f"{width}x{height}+{pos_x}+{pos_y}")
    
    def _on_window_resize(self, event):
        """Handle window resize naturally like desktop apps"""
        # Only handle resize events for the main window
        if event.widget == self.window:
            # Canvas will handle resizing naturally through configure bindings
            pass
    
    def _create_modern_header(self):
        """Create modern header with elegant navigation"""
        # Header container with subtle shadow
        header_frame = tk.Frame(
            self.main_frame, 
            bg=self.colors['background'], 
            height=80
        )
        header_frame.pack(fill=tk.X, padx=20, pady=(20, 0))
        header_frame.pack_propagate(False)
        
        # Add subtle separator line
        separator = tk.Frame(header_frame, bg=self.colors['border'], height=1)
        separator.pack(side=tk.BOTTOM, fill=tk.X, pady=(10, 0))
        
        # Title section
        title_frame = tk.Frame(header_frame, bg=self.colors['background'])
        title_frame.pack(side=tk.LEFT, fill=tk.Y)
        
        # Calculate week range
        end_date = self.current_start_date + timedelta(days=6)
        
        # Main title
        if self.current_start_date.month == end_date.month:
            title_text = f"{self.current_start_date.strftime('%B %d')} – {end_date.strftime('%d, %Y')}"
        else:
            title_text = f"{self.current_start_date.strftime('%B %d')} – {end_date.strftime('%B %d, %Y')}"
            
        self.header_title_label = tk.Label(
            title_frame,
            text=title_text,
            font=self.fonts['title'],
            fg=self.colors['text_primary'],
            bg=self.colors['background'],
            anchor='w'
        )
        self.header_title_label.pack(anchor='w', pady=(10, 5))
        
        # Subtitle
        today = datetime.now()
        if self._is_current_week(self.current_start_date, today):
            subtitle_text = "This Week"
        else:
            days_diff = (self.current_start_date - today).days
            if days_diff > 0:
                subtitle_text = f"{days_diff // 7} weeks ahead"
            else:
                subtitle_text = f"{abs(days_diff) // 7} weeks ago"
        
        self.header_subtitle_label = tk.Label(
            title_frame,
            text=subtitle_text,
            font=self.fonts['small'],
            fg=self.colors['text_secondary'],
            bg=self.colors['background'],
            anchor='w'
        )
        self.header_subtitle_label.pack(anchor='w')
        
        # Navigation section
        nav_frame = tk.Frame(header_frame, bg=self.colors['background'])
        nav_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(20, 0))
        
        # Navigation buttons with modern styling
        self._create_nav_button(nav_frame, "‹", "Previous Week", lambda: self._navigate_week(-7), 'left')
        self._create_nav_button(nav_frame, "Today", "Go to Today", self._go_to_today, 'center')
        self._create_nav_button(nav_frame, "›", "Next Week", lambda: self._navigate_week(7), 'right')
    
    def _is_current_week(self, week_start, today):
        """Check if the given week contains today"""
        week_end = week_start + timedelta(days=6)
        return week_start.date() <= today.date() <= week_end.date()
    
    def _create_nav_button(self, parent, text, tooltip, command, position):
        """Create a modern navigation button"""
        btn = tk.Button(
            parent,
            text=text,
            font=self.fonts['body'] if text == "Today" else ('Segoe UI', 14, 'normal'),
            fg=self.colors['text_primary'],
            bg=self.colors['surface'],
            border=0,
            relief='flat',
            cursor='hand2',
            padx=15 if text == "Today" else 10,
            pady=8,
            command=command
        )
        
        # Add hover effects
        def on_enter(e):
            btn.config(bg=self.colors['hover'])
        def on_leave(e):
            btn.config(bg=self.colors['surface'])
        
        btn.bind("<Enter>", on_enter)
        btn.bind("<Leave>", on_leave)
        
        if position == 'left':
            btn.pack(side=tk.LEFT, padx=(0, 2))
        elif position == 'right':
            btn.pack(side=tk.LEFT, padx=(2, 0))
        else:
            btn.pack(side=tk.LEFT, padx=2)
    
    def _create_toolbar(self):
        """Create modern toolbar with quick actions"""
        toolbar_frame = tk.Frame(self.main_frame, bg=self.colors['surface'], height=50)
        toolbar_frame.pack(fill=tk.X, padx=20, pady=(15, 0))
        toolbar_frame.pack_propagate(False)
        
        # Quick actions section
        actions_frame = tk.Frame(toolbar_frame, bg=self.colors['surface'])
        actions_frame.pack(side=tk.LEFT, fill=tk.Y, pady=10)
        
        # Add event button
        add_btn = tk.Button(
            actions_frame,
            text="+ Add Event",
            font=self.fonts['body'],
            fg='white',
            bg=self.colors['primary'],
            border=0,
            relief='flat',
            cursor='hand2',
            padx=20,
            pady=6,
            command=self._add_event_dialog
        )
        add_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # View toggle buttons
        view_frame = tk.Frame(toolbar_frame, bg=self.colors['surface'])
        view_frame.pack(side=tk.RIGHT, fill=tk.Y, pady=10)
        
        # Week view button (active)
        week_btn = tk.Button(
            view_frame,
            text="Week",
            font=self.fonts['small'],
            fg='white',
            bg=self.colors['primary'],
            border=0,
            relief='flat',
            cursor='hand2',
            padx=15,
            pady=6
        )
        week_btn.pack(side=tk.LEFT, padx=2)
        
        # Month view button
        month_btn = tk.Button(
            view_frame,
            text="Month",
            font=self.fonts['small'],
            fg=self.colors['text_secondary'],
            bg=self.colors['background'],
            border=0,
            relief='flat',
            cursor='hand2',
            padx=15,
            pady=6,
            command=self._switch_to_month_view
        )
        month_btn.pack(side=tk.LEFT, padx=2)
    
    def _create_modern_calendar_grid(self):
        """Create natural scrolling calendar with proper desktop app behavior"""
        # Main calendar container  
        calendar_container = tk.Frame(self.main_frame, bg=self.colors['background'])
        calendar_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=(15, 20))
        
        # Create canvas but with proper native scrolling behavior
        self.calendar_canvas = tk.Canvas(
            calendar_container,
            bg=self.colors['background'],
            highlightthickness=0,
            border=0,
            relief='flat'
        )
        
        # Native scrollbar that behaves like normal apps
        scrollbar = ttk.Scrollbar(
            calendar_container,
            orient="vertical",
            command=self.calendar_canvas.yview
        )
        self.calendar_canvas.configure(yscrollcommand=scrollbar.set)
        
        # Scrollable frame
        self.scrollable_frame = tk.Frame(self.calendar_canvas, bg=self.colors['background'])
        
        # Pack scrollbar and canvas for natural resizing
        scrollbar.pack(side="right", fill="y")
        self.calendar_canvas.pack(side="left", fill="both", expand=True)
        
        # Create window in canvas
        self.canvas_window = self.calendar_canvas.create_window(
            0, 0, 
            anchor="nw", 
            window=self.scrollable_frame
        )
        
        # Natural scrolling and resizing behavior
        def configure_scroll_region(event=None):
            self.calendar_canvas.configure(scrollregion=self.calendar_canvas.bbox("all"))
        
        def configure_canvas_width(event):
            # Make the canvas window the same width as the canvas
            canvas_width = self.calendar_canvas.winfo_width()
            self.calendar_canvas.itemconfig(self.canvas_window, width=canvas_width)
        
        # Bind for natural behavior
        self.scrollable_frame.bind('<Configure>', configure_scroll_region)
        self.calendar_canvas.bind('<Configure>', configure_canvas_width)
        
        # Native mouse wheel scrolling (Windows-like behavior)
        def _on_mousewheel(event):
            self.calendar_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        # Bind to main window for global scrolling
        self.window.bind("<MouseWheel>", _on_mousewheel)
        
        # Get events and create calendar
        events = self._get_week_events(self.current_start_date)
        self._create_modern_time_grid(self.scrollable_frame, events)
        
        # Update scroll region after content is created
        self.scrollable_frame.update_idletasks()
        configure_scroll_region()
    
    def _create_modern_time_grid(self, parent_frame, events):
        """Optimized time grid creation with batch operations"""
        # Adjust to Monday of the current week
        weekday = self.current_start_date.weekday()
        monday_start = self.current_start_date - timedelta(days=weekday)
        
        # Pre-calculate event slots for efficiency
        events_by_slot = self._preprocess_events_by_slot(events, monday_start)
        
        # Create header efficiently
        self._create_efficient_header(parent_frame, monday_start)
        
        # Create main grid with batch operations
        self._create_efficient_grid(parent_frame, monday_start, events_by_slot)
    
    def _preprocess_events_by_slot(self, events, monday_start):
        """Pre-calculate which events belong to which time slots for efficiency"""
        events_by_slot = {}
        
        for hour in range(6, 22):  # 6 AM to 10 PM
            for day in range(7):  # 7 days
                slot_datetime = monday_start + timedelta(days=day, hours=hour)
                slot_end = slot_datetime + timedelta(hours=1)
                
                slot_key = (day, hour)
                events_by_slot[slot_key] = []
                
                for event in events:
                    if (event['start_time'] < slot_end and event['end_time'] > slot_datetime):
                        events_by_slot[slot_key].append(event)
        
        return events_by_slot
    
    def _create_efficient_header(self, parent_frame, monday_start):
        """Create header with widget caching for updates"""
        weekdays = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN']
        today = datetime.now().date()
        
        # Header frame
        header_frame = tk.Frame(parent_frame, bg=self.colors['background'], height=60)
        header_frame.pack(fill=tk.X, pady=(0, 10))
        header_frame.pack_propagate(False)
        
        # Configure columns once
        header_frame.columnconfigure(0, weight=0, minsize=80)
        for i in range(1, 8):
            header_frame.columnconfigure(i, weight=1)
        
        # Time column spacer
        tk.Frame(header_frame, bg=self.colors['background']).grid(row=0, column=0)
        
        # Day headers with caching
        for i, day_name in enumerate(weekdays):
            day_date = monday_start + timedelta(days=i)
            is_today = day_date.date() == today
            
            bg_color = self.colors['primary_light'] if is_today else self.colors['background']
            text_color = self.colors['primary'] if is_today else self.colors['text_primary']
            
            # Single label with both day and date
            day_text = f"{day_name}\n{day_date.day}"
            
            day_label = tk.Label(
                header_frame,
                text=day_text,
                font=('Segoe UI', 11, 'bold'),
                fg=text_color,
                bg=bg_color,
                relief='flat'
            )
            day_label.grid(row=0, column=i+1, sticky='ew', padx=2, pady=5)
            
            # Cache for fast updates
            self.widget_cache[f"day_header_{i}"] = day_label
    
    def _create_efficient_grid(self, parent_frame, monday_start, events_by_slot):
        """Create grid with optimized widget management"""
        # Main grid frame
        grid_frame = tk.Frame(parent_frame, bg=self.colors['background'])
        grid_frame.pack(fill=tk.BOTH, expand=True)
        
        # Configure all columns and rows in batch
        grid_frame.columnconfigure(0, weight=0, minsize=80)
        for i in range(1, 8):
            grid_frame.columnconfigure(i, weight=1, minsize=120)
        
        for i in range(16):  # 16 hours (6 AM to 10 PM)
            grid_frame.rowconfigure(i, weight=0, minsize=60)
        
        # Create time slots efficiently
        for i, hour in enumerate(range(6, 22)):
            self._create_efficient_time_row(grid_frame, i, hour, monday_start, events_by_slot)
    
    def _create_efficient_time_row(self, parent, row, hour, monday_start, events_by_slot):
        """Create a single time row with minimal widget creation"""
        # Time label
        time_text = f"{hour % 12 or 12} {'PM' if hour >= 12 else 'AM'}"
        
        time_label = tk.Label(
            parent,
            text=time_text,
            font=self.fonts['small'],
            fg=self.colors['text_secondary'],
            bg=self.colors['background'],
            anchor='e'
        )
        time_label.grid(row=row, column=0, sticky='e', padx=(0, 10), pady=2)
        
        # Create day cells efficiently
        bg_color = self.colors['surface'] if row % 2 == 1 else self.colors['background']
        
        for day_idx in range(7):
            slot_events = events_by_slot.get((day_idx, hour), [])
            
            if slot_events:
                self._create_efficient_event_cell(parent, row, day_idx + 1, slot_events, bg_color)
            else:
                self._create_efficient_empty_cell(parent, row, day_idx + 1, bg_color)
    
    def _create_efficient_event_cell(self, parent, row, col, events, bg_color):
        """Create event cell with minimal widgets"""
        # Use single frame with text combining multiple events
        if len(events) == 1:
            event = events[0]
            colors = self.event_colors.get(event['event_type'], self.event_colors['default'])
            
            cell_frame = tk.Frame(parent, bg=colors['bg'], height=60, cursor='hand2')
            cell_frame.grid(row=row, column=col, sticky='nsew', padx=2, pady=1)
            cell_frame.grid_propagate(False)
            
            # Single label with event info
            event_text = f"{event['title'][:20]}\n{event['time_str']}"
            
            tk.Label(
                cell_frame,
                text=event_text,
                font=('Segoe UI', 8),
                fg=colors['text'],
                bg=colors['bg'],
                justify='left'
            ).pack(anchor='w', padx=4, pady=2)
            
            # Bind click event
            cell_frame.bind("<Button-1>", lambda e: self._show_event_details(event))
            
        else:
            # Multiple events - show count
            cell_frame = tk.Frame(parent, bg=self.colors['primary'], height=60, cursor='hand2')
            cell_frame.grid(row=row, column=col, sticky='nsew', padx=2, pady=1)
            cell_frame.grid_propagate(False)
            
            tk.Label(
                cell_frame,
                text=f"{len(events)} events\n{events[0]['time_str']}",
                font=('Segoe UI', 8, 'bold'),
                fg='white',
                bg=self.colors['primary']
            ).pack(expand=True)
    
    def _create_efficient_empty_cell(self, parent, row, col, bg_color):
        """Create empty cell with minimal overhead"""
        cell_frame = tk.Frame(parent, bg=bg_color, height=60, cursor='crosshair')
        cell_frame.grid(row=row, column=col, sticky='nsew', padx=2, pady=1)
        cell_frame.grid_propagate(False)
        
        # Add subtle border for alternate rows
        if row % 2 == 1:
            tk.Frame(cell_frame, bg=self.colors['border'], height=1).pack(side=tk.BOTTOM, fill=tk.X)
        
        # Hover effect only
        def on_hover(e):
            cell_frame.config(bg=self.colors['hover'])
        def on_leave(e):
            cell_frame.config(bg=bg_color)
        
        cell_frame.bind("<Enter>", on_hover)
        cell_frame.bind("<Leave>", on_leave)
    
    def _create_time_row(self, parent, hour, monday_start, events):
        """Create a single time row with modern styling"""
        row = hour - 6
        
        # Time label with modern styling
        time_frame = tk.Frame(
            parent,
            bg=self.colors['background'],
            width=80
        )
        time_frame.grid(row=row, column=0, sticky='nsew', padx=(0, 10))
        time_frame.grid_propagate(False)
        
        # Format time
        if hour == 0:
            time_text = "12 AM"
        elif hour < 12:
            time_text = f"{hour} AM"
        elif hour == 12:
            time_text = "12 PM"
        else:
            time_text = f"{hour-12} PM"
        
        time_label = tk.Label(
            time_frame,
            text=time_text,
            font=self.fonts['small'],
            fg=self.colors['text_secondary'],
            bg=self.colors['background'],
            anchor='ne'
        )
        time_label.pack(side=tk.RIGHT, padx=10, pady=5)
        
        # Create day slots with alternating background
        bg_color = self.colors['background'] if row % 2 == 0 else self.colors['surface']
        
        for day_idx in range(7):
            slot_date = monday_start + timedelta(days=day_idx)
            slot_datetime = slot_date.replace(hour=hour)
            
            # Get events for this time slot
            slot_events = self._get_events_for_slot(events, slot_datetime)
            
            if slot_events:
                self._create_event_cell(parent, row, day_idx + 1, slot_events, bg_color)
            else:
                self._create_empty_cell(parent, row, day_idx + 1, bg_color, slot_datetime)
    
    def _create_event_cell(self, parent, row, col, events, bg_color):
        """Create a cell with events and caching for updates"""
        cell_frame = tk.Frame(
            parent,
            bg=bg_color,
            relief='flat',
            bd=0,
            height=60
        )
        cell_frame.grid(row=row, column=col, sticky='nsew', padx=2, pady=1)
        cell_frame.grid_propagate(False)
        cell_frame.pack_propagate(False)
        
        for event in events[:2]:  # Show max 2 events per slot
            self._create_event_block(cell_frame, event)
        
        # Show "+N more" if more than 2 events
        if len(events) > 2:
            more_label = tk.Label(
                cell_frame,
                text=f"+{len(events) - 2} more",
                font=('Segoe UI', 8),
                fg=self.colors['text_secondary'],
                bg=bg_color,
                cursor='hand2'
            )
            more_label.pack(anchor='w', padx=5, pady=2)
        
        # Cache this cell for ultra-fast updates
        hour = row + 6  # Convert back to actual hour
        day_idx = col - 1  # Convert back to day index
        self.widget_cache[f"cell_{hour}_{day_idx}"] = cell_frame
    
    def _create_event_block(self, parent, event):
        """Create a beautiful event block"""
        event_type = event.get('event_type', 'meeting')
        colors = self.event_colors.get(event_type, self.event_colors['default'])
        
        # Event frame with rounded corners effect
        event_frame = tk.Frame(
            parent,
            bg=colors['bg'],
            relief='flat',
            bd=0,
            cursor='hand2'
        )
        event_frame.pack(fill=tk.X, padx=3, pady=1)
        
        # Event title
        title_label = tk.Label(
            event_frame,
            text=event['title'][:25] + ('...' if len(event['title']) > 25 else ''),
            font=('Segoe UI', 9, 'bold'),
            fg=colors['text'],
            bg=colors['bg'],
            anchor='w'
        )
        title_label.pack(anchor='w', padx=6, pady=(3, 1))
        
        # Event time
        time_label = tk.Label(
            event_frame,
            text=event['time_str'],
            font=('Segoe UI', 8),
            fg=colors['text'],
            bg=colors['bg'],
            anchor='w'
        )
        time_label.pack(anchor='w', padx=6, pady=(0, 3))
        
        # Add hover effects and click binding
        def on_hover_enter(e):
            event_frame.configure(relief='raised', bd=1)
        
        def on_hover_leave(e):
            event_frame.configure(relief='flat', bd=0)
        
        def on_click(e):
            self._show_event_details(event)
        
        # Bind events to all child widgets
        for widget in [event_frame, title_label, time_label]:
            widget.bind("<Enter>", on_hover_enter)
            widget.bind("<Leave>", on_hover_leave)
            widget.bind("<Button-1>", on_click)
    
    def _create_empty_cell(self, parent, row, col, bg_color, slot_datetime):
        """Create an empty time slot with caching for updates"""
        cell_frame = tk.Frame(
            parent,
            bg=bg_color,
            relief='flat',
            bd=0,
            height=60,
            cursor='crosshair'
        )
        cell_frame.grid(row=row, column=col, sticky='nsew', padx=2, pady=1)
        cell_frame.grid_propagate(False)
        cell_frame.pack_propagate(False)
        
        # Add subtle border on alternate rows
        if row % 2 == 1:
            border_frame = tk.Frame(cell_frame, bg=self.colors['border'], height=1)
            border_frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Store original background for hover effects
        original_bg = bg_color
        
        # Hover effect for adding events
        def on_hover_enter(e):
            cell_frame.configure(bg=self.colors['hover'])
        
        def on_hover_leave(e):
            cell_frame.configure(bg=original_bg)
        
        def on_click(e):
            self._quick_add_event(slot_datetime)
        
        cell_frame.bind("<Enter>", on_hover_enter)
        cell_frame.bind("<Leave>", on_hover_leave)
        cell_frame.bind("<Button-1>", on_click)
        
        # Cache this cell for ultra-fast updates
        hour = row + 6  # Convert back to actual hour
        day_idx = col - 1  # Convert back to day index
        self.widget_cache[f"cell_{hour}_{day_idx}"] = cell_frame
    
    # Modern navigation and utility methods  
    def _navigate_week(self, days_offset):
        """Navigate to a different week"""
        self.current_start_date += timedelta(days=days_offset)
        self._refresh_calendar()
    
    def _go_to_today(self):
        """Navigate to current week"""
        today = datetime.now()
        # Get Monday of current week
        weekday = today.weekday()
        self.current_start_date = today - timedelta(days=weekday)
        self._refresh_calendar()
    
    def _refresh_calendar(self):
        """Smooth refresh without destroying the entire UI"""
        if self.window and hasattr(self, 'header_title_label') and hasattr(self, 'header_subtitle_label'):
            # Update header text only
            self._update_header_text()
            
            # Update calendar grid content only (don't recreate the whole structure)
            self._update_calendar_content()
    
    def _update_header_text(self):
        """Update just the header text without recreating widgets"""
        end_date = self.current_start_date + timedelta(days=6)
        
        # Update main title
        if self.current_start_date.month == end_date.month:
            title_text = f"{self.current_start_date.strftime('%B %d')} – {end_date.strftime('%d, %Y')}"
        else:
            title_text = f"{self.current_start_date.strftime('%B %d')} – {end_date.strftime('%B %d, %Y')}"
        
        self.header_title_label.config(text=title_text)
        
        # Update subtitle
        today = datetime.now()
        if self._is_current_week(self.current_start_date, today):
            subtitle_text = "This Week"
        else:
            days_diff = (self.current_start_date - today).days
            if days_diff > 0:
                subtitle_text = f"{days_diff // 7} weeks ahead"
            else:
                subtitle_text = f"{abs(days_diff) // 7} weeks ago"
        
        self.header_subtitle_label.config(text=subtitle_text)
    
    def _update_calendar_content(self):
        """Ultra-fast calendar update using widget virtualization"""
        if not (hasattr(self, 'calendar_canvas') and hasattr(self, 'scrollable_frame')):
            return
        
        # Get week key for caching
        weekday = self.current_start_date.weekday()
        monday_start = self.current_start_date - timedelta(days=weekday)
        week_key = monday_start.strftime('%Y-%m-%d')
        
        # If same week, just return - no update needed
        if week_key == self.last_week_key:
            return
        
        self.last_week_key = week_key
        
        # Get new events (with caching)
        events = self._get_week_events(self.current_start_date)
        
        if not self.grid_created:
            # First time - create the grid structure
            self._create_virtualized_grid(events)
        else:
            # Update existing grid with new data - MUCH faster
            self._update_virtualized_grid(events)
        
        # Minimal canvas update
        self.scrollable_frame.update_idletasks()
        self.calendar_canvas.configure(scrollregion=self.calendar_canvas.bbox("all"))
    
    def _create_virtualized_grid(self, events):
        """Create the grid structure once - never recreate"""
        # Clear only if needed
        if self.scrollable_frame.winfo_children():
            for widget in self.scrollable_frame.winfo_children():
                widget.destroy()
        
        # Create permanent grid structure
        self._create_modern_time_grid(self.scrollable_frame, events)
        self.grid_created = True
    
    def _update_virtualized_grid(self, events):
        """Update existing grid with new data - no widget recreation"""
        weekday = self.current_start_date.weekday()
        monday_start = self.current_start_date - timedelta(days=weekday)
        
        # Pre-calculate event slots
        events_by_slot = self._preprocess_events_by_slot(events, monday_start)
        
        # Update only the data, not the widgets
        self._update_existing_grid_data(monday_start, events_by_slot)
    
    def _update_existing_grid_data(self, monday_start, events_by_slot):
        """Update grid data without recreating widgets - FASTEST method"""
        today = datetime.now().date()
        
        # Update day headers (if they exist)
        weekdays = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN']
        
        # Update only text content of existing widgets
        for i, day_name in enumerate(weekdays):
            day_date = monday_start + timedelta(days=i)
            is_today = day_date.date() == today
            
            # Find and update existing day header
            widget_key = f"day_header_{i}"
            if widget_key in self.widget_cache:
                day_widget = self.widget_cache[widget_key]
                day_text = f"{day_name}\n{day_date.day}"
                
                # Update colors for today
                bg_color = self.colors['primary_light'] if is_today else self.colors['background']
                text_color = self.colors['primary'] if is_today else self.colors['text_primary']
                
                day_widget.config(text=day_text, bg=bg_color, fg=text_color)
        
        # Update event cells without recreating widgets
        for hour in range(6, 22):
            for day_idx in range(7):
                slot_events = events_by_slot.get((day_idx, hour), [])
                widget_key = f"cell_{hour}_{day_idx}"
                
                if widget_key in self.widget_cache:
                    cell_frame = self.widget_cache[widget_key]
                    
                    # Clear existing event widgets in this cell
                    for child in cell_frame.winfo_children():
                        child.destroy()
                    
                    # Add new event content
                    if slot_events:
                        self._add_events_to_existing_cell(cell_frame, slot_events)
                    else:
                        # Reset to empty cell appearance
                        row = hour - 6
                        bg_color = self.colors['surface'] if row % 2 == 1 else self.colors['background']
                        cell_frame.config(bg=bg_color)
    
    def _add_events_to_existing_cell(self, cell_frame, events):
        """Add events to existing cell widget"""
        if len(events) == 1:
            event = events[0]
            colors = self.event_colors.get(event['event_type'], self.event_colors['default'])
            
            cell_frame.config(bg=colors['bg'])
            
            # Single label with event info
            event_text = f"{event['title'][:20]}\n{event['time_str']}"
            
            event_label = tk.Label(
                cell_frame,
                text=event_text,
                font=('Segoe UI', 8),
                fg=colors['text'],
                bg=colors['bg'],
                justify='left'
            )
            event_label.pack(anchor='w', padx=4, pady=2)
            
            # Bind click event
            event_label.bind("<Button-1>", lambda e: self._show_event_details(event))
            
        else:
            # Multiple events
            cell_frame.config(bg=self.colors['primary'])
            
            multi_label = tk.Label(
                cell_frame,
                text=f"{len(events)} events\n{events[0]['time_str']}",
                font=('Segoe UI', 8, 'bold'),
                fg='white',
                bg=self.colors['primary']
            )
            multi_label.pack(expand=True)
    
    def _show_event_details(self, event):
        """Show detailed event information in a modern dialog"""
        dialog = tk.Toplevel(self.window)
        dialog.title("Event Details")
        dialog.geometry("400x500")
        dialog.configure(bg=self.colors['background'])
        dialog.transient(self.window)
        dialog.grab_set()
        
        # Center the dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (400 // 2)
        y = (dialog.winfo_screenheight() // 2) - (500 // 2)
        dialog.geometry(f"400x500+{x}+{y}")
        
        # Event details content
        start_dt = datetime.fromtimestamp(event['start_time']) if isinstance(event.get('start_time'), (int, float)) else event.get('start_time', datetime.now())
        end_dt = datetime.fromtimestamp(event['end_time']) if isinstance(event.get('end_time'), (int, float)) else event.get('end_time', start_dt + timedelta(hours=1))
        
        # Title
        title_label = tk.Label(
            dialog,
            text=event.get('title', 'Untitled Event'),
            font=('Segoe UI', 16, 'bold'),
            fg=self.colors['text_primary'],
            bg=self.colors['background']
        )
        title_label.pack(pady=20)
        
        # Details frame
        details_frame = tk.Frame(dialog, bg=self.colors['background'])
        details_frame.pack(fill=tk.BOTH, expand=True, padx=30, pady=10)
        
        details = [
            ("Date", start_dt.strftime('%A, %B %d, %Y')),
            ("Time", f"{start_dt.strftime('%I:%M %p')} - {end_dt.strftime('%I:%M %p')}"),
            ("Type", event.get('event_type', 'meeting').title()),
            ("Location", event.get('location', 'No location specified')),
            ("Description", event.get('description', 'No description'))
        ]
        
        for label, value in details:
            row_frame = tk.Frame(details_frame, bg=self.colors['background'])
            row_frame.pack(fill=tk.X, pady=8)
            
            label_widget = tk.Label(
                row_frame,
                text=f"{label}:",
                font=('Segoe UI', 10, 'bold'),
                fg=self.colors['text_secondary'],
                bg=self.colors['background']
            )
            label_widget.pack(anchor='w')
            
            value_widget = tk.Label(
                row_frame,
                text=value,
                font=('Segoe UI', 10),
                fg=self.colors['text_primary'],
                bg=self.colors['background'],
                wraplength=340,
                justify='left'
            )
            value_widget.pack(anchor='w', pady=(2, 0))
        
        # Close button
        close_btn = tk.Button(
            dialog,
            text="Close",
            font=self.fonts['body'],
            fg='white',
            bg=self.colors['primary'],
            border=0,
            relief='flat',
            cursor='hand2',
            padx=20,
            pady=8,
            command=dialog.destroy
        )
        close_btn.pack(pady=20)
    
    def _quick_add_event(self, slot_datetime):
        """Quick add event dialog"""
        dialog = tk.Toplevel(self.window)
        dialog.title("Quick Add Event")
        dialog.geometry("350x250")
        dialog.configure(bg=self.colors['background'])
        dialog.transient(self.window)
        dialog.grab_set()
        
        # Center the dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (350 // 2)
        y = (dialog.winfo_screenheight() // 2) - (250 // 2)
        dialog.geometry(f"350x250+{x}+{y}")
        
        # Title
        title_label = tk.Label(
            dialog,
            text=f"New Event - {slot_datetime.strftime('%A, %B %d')}",
            font=('Segoe UI', 14, 'bold'),
            fg=self.colors['text_primary'],
            bg=self.colors['background']
        )
        title_label.pack(pady=20)
        
        # Event title input
        tk.Label(dialog, text="Event Title:", font=self.fonts['body'], 
                fg=self.colors['text_secondary'], bg=self.colors['background']).pack(anchor='w', padx=30)
        
        title_entry = tk.Entry(dialog, font=self.fonts['body'], width=30)
        title_entry.pack(pady=5, padx=30, fill=tk.X)
        title_entry.focus()
        
        # Time input
        tk.Label(dialog, text="Time:", font=self.fonts['body'], 
                fg=self.colors['text_secondary'], bg=self.colors['background']).pack(anchor='w', padx=30, pady=(10, 0))
        
        time_entry = tk.Entry(dialog, font=self.fonts['body'], width=30)
        time_entry.pack(pady=5, padx=30, fill=tk.X)
        time_entry.insert(0, slot_datetime.strftime('%I:%M %p'))
        
        # Buttons
        button_frame = tk.Frame(dialog, bg=self.colors['background'])
        button_frame.pack(pady=20)
        
        def create_event():
            title = title_entry.get().strip()
            if title:
                messagebox.showinfo("Success", f"Event '{title}' would be created!\n(Integration with calendar module needed)")
                dialog.destroy()
            else:
                messagebox.showwarning("Warning", "Please enter an event title")
        
        create_btn = tk.Button(
            button_frame,
            text="Create Event",
            font=self.fonts['body'],
            fg='white',
            bg=self.colors['primary'],
            border=0,
            relief='flat',
            cursor='hand2',
            padx=20,
            pady=8,
            command=create_event
        )
        create_btn.pack(side=tk.LEFT, padx=5)
        
        cancel_btn = tk.Button(
            button_frame,
            text="Cancel",
            font=self.fonts['body'],
            fg=self.colors['text_primary'],
            bg=self.colors['surface'],
            border=0,
            relief='flat',
            cursor='hand2',
            padx=20,
            pady=8,
            command=dialog.destroy
        )
        cancel_btn.pack(side=tk.LEFT, padx=5)
        
        # Enter key binding
        dialog.bind('<Return>', lambda e: create_event())
    
    def _add_event_dialog(self):
        """Show add event dialog"""
        self._quick_add_event(datetime.now().replace(hour=9, minute=0, second=0, microsecond=0))
    
    def _switch_to_month_view(self):
        """Switch to monthly view"""
        if self.window:
            self.window.destroy()
        
        # Launch monthly viewer
        monthly_viewer = MonthlyCalendarViewer(self.calendar_module)
        monthly_viewer.show_monthly_schedule()
    
    def _create_time_grid(self, parent_frame: ttk.Frame, start_date: datetime, events: List[Dict]):
        """Create the time grid with days and hourly slots"""
        # Days of the week - Start from Monday of the current week
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        
        # Adjust start_date to Monday of the week
        weekday = start_date.weekday()  # Monday = 0, Sunday = 6
        monday_start = start_date - timedelta(days=weekday)
        
        # Create header row with days
        header_frame = tk.Frame(parent_frame, bg='white')
        header_frame.grid(row=0, column=0, columnspan=8, sticky='ew', padx=2, pady=2)
        
        # Time column header
        time_header = tk.Label(
            header_frame,
            text="Time",
            font=('Arial', 12, 'bold'),
            bg='#34495e',
            fg='white',
            width=8,
            relief=tk.RAISED
        )
        time_header.grid(row=0, column=0, sticky='ew', padx=1)
        
        # Day headers - Show all 7 days
        for i, day in enumerate(days):
            day_date = monday_start + timedelta(days=i)
            day_text = f"{day}\n{day_date.strftime('%m/%d')}"
            
            day_header = tk.Label(
                header_frame,
                text=day_text,
                font=('Arial', 11, 'bold'),
                bg='#3498db',
                fg='white',
                width=15,
                relief=tk.RAISED
            )
            day_header.grid(row=0, column=i+1, sticky='ew', padx=1)
        
        # Create time slots (6 AM to 11 PM)
        for hour in range(6, 23):
            row = hour - 5  # Start from row 1 (row 0 is header)
            
            # Time label
            time_text = f"{hour:02d}:00"
            if hour < 12:
                time_text += " AM"
            elif hour == 12:
                time_text += " PM"
            else:
                time_text = f"{hour-12:02d}:00 PM"
            
            time_label = tk.Label(
                parent_frame,
                text=time_text,
                font=('Arial', 10),
                bg='#ecf0f1',
                relief=tk.RIDGE,
                width=8
            )
            time_label.grid(row=row, column=0, sticky='ew', padx=1, pady=1)
            
            # Day slots - Create for all 7 days
            for day_idx in range(7):
                slot_date = monday_start + timedelta(days=day_idx)
                slot_datetime = slot_date.replace(hour=hour)
                
                # Check if there are events in this slot
                slot_events = self._get_events_for_slot(events, slot_datetime)
                
                if slot_events:
                    # Occupied slot - RED background
                    event_frame = tk.Frame(parent_frame, bg='#e74c3c', relief=tk.RAISED)
                    event_frame.grid(row=row, column=day_idx+1, sticky='ew', padx=1, pady=1)
                    
                    for event in slot_events:
                        event_label = tk.Label(
                            event_frame,
                            text=event['title'],
                            font=('Arial', 9, 'bold'),
                            bg='#e74c3c',
                            fg='white',
                            wraplength=120
                        )
                        event_label.pack(fill=tk.X, pady=1)
                        
                        # Add time info
                        time_info = tk.Label(
                            event_frame,
                            text=event['time_str'],
                            font=('Arial', 8),
                            bg='#e74c3c',
                            fg='#ffeeee'
                        )
                        time_info.pack()
                else:
                    # Free slot - GREEN background
                    empty_slot = tk.Label(
                        parent_frame,
                        text="",
                        bg='#2ecc71',  # Green for free slots
                        relief=tk.RIDGE,
                        width=15,
                        height=2
                    )
                    empty_slot.grid(row=row, column=day_idx+1, sticky='ew', padx=1, pady=1)
        
        # Configure column weights for responsive design
        for i in range(8):  # 0 for time, 1-7 for days
            parent_frame.columnconfigure(i, weight=1)
    
    def _get_week_events(self, start_date: datetime) -> List[Dict]:
        """Get all events for the week with caching for performance"""
        try:
            # Adjust to Monday of the current week
            weekday = start_date.weekday()
            monday_start = start_date - timedelta(days=weekday)
            cache_key = monday_start.strftime('%Y-%m-%d')
            
            # Check cache first
            if cache_key in self.events_cache:
                return self.events_cache[cache_key]
            
            events = []
            end_date = monday_start + timedelta(days=7)
            
            # Get database path
            db_path = "data/calendar.db"
            if self.calendar_module and hasattr(self.calendar_module, 'db_path'):
                db_path = self.calendar_module.db_path
            
            try:
                with sqlite3.connect(db_path) as conn:
                    cursor = conn.cursor()
                    
                    start_timestamp = monday_start.timestamp()
                    end_timestamp = end_date.timestamp()
                    
                    cursor.execute("""
                        SELECT event_id, title, start_time, end_time, location, description, event_type
                        FROM events 
                        WHERE start_time >= ? AND start_time < ?
                        ORDER BY start_time
                    """, (start_timestamp, end_timestamp))
                    
                    for row in cursor.fetchall():
                        event_id, title, start_time, end_time, location, description, event_type = row
                        
                        start_dt = datetime.fromtimestamp(start_time)
                        end_dt = datetime.fromtimestamp(end_time) if end_time else start_dt + timedelta(hours=1)
                        
                        events.append({
                            'id': event_id,
                            'title': title,
                            'start_time': start_dt,
                            'end_time': end_dt,
                            'time_str': start_dt.strftime('%I:%M %p'),
                            'location': location or '',
                            'description': description or '',
                            'event_type': event_type or 'meeting'
                        })
                    
                    # Cache the result
                    self.events_cache[cache_key] = events
                    
                    # Keep cache size reasonable (last 4 weeks)
                    if len(self.events_cache) > 4:
                        oldest_key = min(self.events_cache.keys())
                        del self.events_cache[oldest_key]
                    
            except sqlite3.Error:
                # Database doesn't exist or has issues, return empty
                pass
            
            return events
            
        except Exception as e:
            print(f"Error getting week events: {e}")
            return []
    
    def _get_events_for_slot(self, events: List[Dict], slot_datetime: datetime) -> List[Dict]:
        """Get events that occur during a specific hour slot"""
        slot_events = []
        slot_end = slot_datetime + timedelta(hours=1)
        
        for event in events:
            # Check if event overlaps with this hour slot
            if (event['start_time'] < slot_end and event['end_time'] > slot_datetime):
                slot_events.append(event)
        
        return slot_events
    
    def _navigate_week(self, current_start: datetime, days_offset: int):
        """Navigate to a different week"""
        new_start = current_start + timedelta(days=days_offset)
        if self.window:
            self.window.destroy()
        self._create_calendar_window(new_start)


# Function to be called from function calling system
def show_weekly_calendar(calendar_module=None) -> Dict[str, Any]:
    """Show weekly calendar GUI - to be called from function registry"""
    try:
        viewer = WeeklyCalendarViewer(calendar_module)
        success = viewer.show_weekly_schedule()
        
        if success:
            return {
                "success": True,
                "result": "Weekly calendar opened in a new window."
            }
        else:
            return {
                "success": False,
                "error": "Failed to open weekly calendar window"
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": f"Error opening weekly calendar: {str(e)}"
        }


class MonthlyCalendarViewer:
    """GUI window for displaying monthly calendar in a grid format"""
    
    def __init__(self, calendar_module=None):
        self.calendar_module = calendar_module
        self.window = None
        self.calendar_frame = None
        self.current_date = datetime.now().replace(day=1)  # First day of current month
        self.event_colors = {
            'meeting': '#e74c3c',      # Red
            'appointment': '#3498db',   # Blue  
            'task': '#f39c12',         # Orange
            'personal': '#9b59b6',     # Purple
            'work': '#2ecc71',         # Green
            'default': '#95a5a6'       # Gray
        }
        
    def show_monthly_schedule(self, start_date: datetime = None) -> bool:
        """Display monthly calendar starting from given date (default: current month)"""
        try:
            if start_date is None:
                start_date = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            
            self.current_date = start_date
            
            # Run GUI in separate thread to avoid blocking
            gui_thread = threading.Thread(
                target=self._create_monthly_window,
                daemon=True
            )
            gui_thread.start()
            return True
            
        except Exception as e:
            print(f"Error showing monthly schedule: {e}")
            return False
    
    def _create_monthly_window(self):
        """Create and display the monthly calendar window"""
        try:
            # Create main window
            self.window = tk.Tk()
            self.window.title("SAGE - Monthly Calendar")
            self.window.geometry("1200x800")
            self.window.configure(bg='#f0f0f0')
            
            # Create header with month navigation
            self._create_month_header()
            
            # Create the calendar grid
            self._create_monthly_grid()
            
            # Start the GUI event loop
            self.window.mainloop()
            
        except Exception as e:
            print(f"Error creating monthly calendar window: {e}")
    
    def _create_month_header(self):
        """Create header with month navigation and title"""
        header_frame = tk.Frame(self.window, bg='#2c3e50', height=80)
        header_frame.pack(fill=tk.X, pady=(0, 10))
        header_frame.pack_propagate(False)
        
        # Month title
        title_text = self.current_date.strftime('%B %Y')
        
        title_label = tk.Label(
            header_frame, 
            text=title_text,
            font=('Arial', 20, 'bold'),
            fg='white',
            bg='#2c3e50'
        )
        title_label.pack(expand=True)
        
        # Navigation buttons
        nav_frame = tk.Frame(header_frame, bg='#2c3e50')
        nav_frame.pack(side=tk.BOTTOM, pady=10)
        
        prev_btn = tk.Button(
            nav_frame,
            text="← Previous Month",
            font=('Arial', 11),
            command=self._prev_month,
            bg='#34495e',
            fg='white',
            relief=tk.FLAT,
            padx=20
        )
        prev_btn.pack(side=tk.LEFT, padx=10)
        
        today_btn = tk.Button(
            nav_frame,
            text="Today",
            font=('Arial', 11),
            command=self._goto_today,
            bg='#3498db',
            fg='white',
            relief=tk.FLAT,
            padx=20
        )
        today_btn.pack(side=tk.LEFT, padx=5)
        
        next_btn = tk.Button(
            nav_frame,
            text="Next Month →",
            font=('Arial', 11),
            command=self._next_month,
            bg='#34495e',
            fg='white',
            relief=tk.FLAT,
            padx=20
        )
        next_btn.pack(side=tk.RIGHT, padx=10)
    
    def _create_monthly_grid(self):
        """Create the main monthly calendar grid"""
        # Clear existing calendar if any
        if self.calendar_frame:
            self.calendar_frame.destroy()
        
        # Main container
        main_frame = tk.Frame(self.window, bg='#f0f0f0')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)
        
        # Calendar frame
        self.calendar_frame = tk.Frame(main_frame, bg='white', relief=tk.RIDGE, bd=1)
        self.calendar_frame.pack(fill=tk.BOTH, expand=True)
        
        # Get events for the month
        events = self._get_month_events(self.current_date)
        
        # Create day headers
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        for col, day in enumerate(days):
            day_header = tk.Label(
                self.calendar_frame,
                text=day,
                font=('Arial', 12, 'bold'),
                bg='#34495e',
                fg='white',
                relief=tk.RAISED,
                bd=1
            )
            day_header.grid(row=0, column=col, sticky='ew', padx=1, pady=1)
        
        # Get calendar data for the month
        calendar_obj = cal.Calendar(firstweekday=0)  # Monday = 0
        month_days = calendar_obj.monthdayscalendar(self.current_date.year, self.current_date.month)
        
        # Create day cells
        for week_num, week in enumerate(month_days, start=1):
            for day_num, day in enumerate(week):
                if day == 0:  # Empty cell (previous/next month)
                    empty_cell = tk.Label(
                        self.calendar_frame,
                        text="",
                        bg='#ecf0f1',
                        relief=tk.SUNKEN,
                        bd=1
                    )
                    empty_cell.grid(row=week_num, column=day_num, sticky='nsew', padx=1, pady=1)
                else:
                    # Create day cell with events
                    self._create_day_cell(week_num, day_num, day, events)
        
        # Configure grid weights for responsive design
        for col in range(7):
            self.calendar_frame.columnconfigure(col, weight=1)
        for row in range(len(month_days) + 1):  # +1 for header
            self.calendar_frame.rowconfigure(row, weight=1)
    
    def _create_day_cell(self, row: int, col: int, day: int, events: List[Dict]):
        """Create a single day cell with events"""
        # Create day frame
        day_frame = tk.Frame(
            self.calendar_frame,
            bg='white',
            relief=tk.RAISED,
            bd=1,
            cursor='hand2'
        )
        day_frame.grid(row=row, column=col, sticky='nsew', padx=1, pady=1)
        
        # Day number label
        today = datetime.now().date()
        cell_date = self.current_date.replace(day=day).date()
        
        # Highlight today
        bg_color = '#3498db' if cell_date == today else 'white'
        fg_color = 'white' if cell_date == today else 'black'
        
        day_label = tk.Label(
            day_frame,
            text=str(day),
            font=('Arial', 12, 'bold'),
            bg=bg_color,
            fg=fg_color,
            anchor='nw'
        )
        day_label.pack(side=tk.TOP, fill=tk.X)
        
        # Get events for this day
        day_events = self._get_events_for_day(events, cell_date)
        
        # Event container with scrolling for many events
        event_container = tk.Frame(day_frame, bg='white')
        event_container.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=2, pady=2)
        
        # Show up to 4 events, then "... N more"
        for i, event in enumerate(day_events[:4]):
            event_color = self.event_colors.get(event.get('event_type', 'meeting'), self.event_colors['default'])
            
            event_label = tk.Label(
                event_container,
                text=event['title'][:15] + ('...' if len(event['title']) > 15 else ''),
                font=('Arial', 8),
                bg=event_color,
                fg='white',
                relief=tk.RAISED,
                bd=1,
                cursor='hand2'
            )
            event_label.pack(fill=tk.X, pady=1)
            
            # Bind click event for editing
            event_label.bind('<Button-1>', lambda e, evt=event: self._edit_event(evt))
            event_label.bind('<Button-3>', lambda e, evt=event: self._event_context_menu(e, evt))
        
        # Show "... N more" if there are more events
        if len(day_events) > 4:
            more_label = tk.Label(
                event_container,
                text=f"... {len(day_events) - 4} more",
                font=('Arial', 7),
                bg='#bdc3c7',
                fg='#2c3e50',
                relief=tk.RAISED,
                bd=1
            )
            more_label.pack(fill=tk.X, pady=1)
        
        # Bind day cell click for adding new events
        day_frame.bind('<Double-Button-1>', lambda e, date=cell_date: self._add_new_event(date))
        day_label.bind('<Double-Button-1>', lambda e, date=cell_date: self._add_new_event(date))
    
    def _get_month_events(self, start_date: datetime) -> List[Dict]:
        """Get all events for the month"""
        try:
            events = []
            
            # Calculate month range
            first_day = start_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if start_date.month == 12:
                last_day = start_date.replace(year=start_date.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                last_day = start_date.replace(month=start_date.month + 1, day=1) - timedelta(days=1)
            last_day = last_day.replace(hour=23, minute=59, second=59)
            
            # Get database path
            db_path = "data/calendar.db"
            if self.calendar_module and hasattr(self.calendar_module, 'db_path'):
                db_path = self.calendar_module.db_path
            
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                
                start_timestamp = first_day.timestamp()
                end_timestamp = last_day.timestamp()
                
                cursor.execute("""
                    SELECT event_id, title, start_time, end_time, location, description, 
                           event_type, priority, attendees
                    FROM events 
                    WHERE start_time >= ? AND start_time <= ?
                    ORDER BY start_time
                """, (start_timestamp, end_timestamp))
                
                for row in cursor.fetchall():
                    event_id, title, start_time, end_time, location, description, event_type, priority, attendees = row
                    
                    start_dt = datetime.fromtimestamp(start_time)
                    end_dt = datetime.fromtimestamp(end_time) if end_time else start_dt + timedelta(hours=1)
                    
                    events.append({
                        'id': event_id,
                        'title': title,
                        'start_time': start_dt,
                        'end_time': end_dt,
                        'time_str': start_dt.strftime('%I:%M %p'),
                        'location': location,
                        'description': description,
                        'event_type': event_type or 'meeting',
                        'priority': priority or 'medium',
                        'attendees': json.loads(attendees) if attendees else []
                    })
            
            return events
            
        except Exception as e:
            print(f"Error getting month events: {e}")
            return []
    
    def _get_events_for_day(self, events: List[Dict], target_date) -> List[Dict]:
        """Get events that occur on a specific day"""
        day_events = []
        
        for event in events:
            if event['start_time'].date() == target_date:
                day_events.append(event)
        
        return sorted(day_events, key=lambda x: x['start_time'])
    
    def _edit_event(self, event: Dict):
        """Open event editing dialog"""
        try:
            # Create edit dialog
            dialog = tk.Toplevel(self.window)
            dialog.title(f"Edit Event: {event['title']}")
            dialog.geometry("400x500")
            dialog.configure(bg='#f0f0f0')
            dialog.transient(self.window)
            dialog.grab_set()
            
            # Title field
            tk.Label(dialog, text="Title:", font=('Arial', 10, 'bold'), bg='#f0f0f0').pack(anchor='w', padx=10, pady=(10,0))
            title_var = tk.StringVar(value=event['title'])
            title_entry = tk.Entry(dialog, textvariable=title_var, font=('Arial', 10), width=50)
            title_entry.pack(padx=10, pady=5, fill=tk.X)
            
            # Event type field
            tk.Label(dialog, text="Type:", font=('Arial', 10, 'bold'), bg='#f0f0f0').pack(anchor='w', padx=10, pady=(10,0))
            type_var = tk.StringVar(value=event.get('event_type', 'meeting'))
            type_combo = ttk.Combobox(dialog, textvariable=type_var, values=['meeting', 'appointment', 'task', 'personal', 'work'], state='readonly')
            type_combo.pack(padx=10, pady=5, fill=tk.X)
            
            # Priority field
            tk.Label(dialog, text="Priority:", font=('Arial', 10, 'bold'), bg='#f0f0f0').pack(anchor='w', padx=10, pady=(10,0))
            priority_var = tk.StringVar(value=event.get('priority', 'medium'))
            priority_combo = ttk.Combobox(dialog, textvariable=priority_var, values=['low', 'medium', 'high', 'urgent'], state='readonly')
            priority_combo.pack(padx=10, pady=5, fill=tk.X)
            
            # Time field
            tk.Label(dialog, text="Time:", font=('Arial', 10, 'bold'), bg='#f0f0f0').pack(anchor='w', padx=10, pady=(10,0))
            time_var = tk.StringVar(value=event['start_time'].strftime('%H:%M'))
            time_entry = tk.Entry(dialog, textvariable=time_var, font=('Arial', 10))
            time_entry.pack(padx=10, pady=5, fill=tk.X)
            
            # Location field
            tk.Label(dialog, text="Location:", font=('Arial', 10, 'bold'), bg='#f0f0f0').pack(anchor='w', padx=10, pady=(10,0))
            location_var = tk.StringVar(value=event.get('location', ''))
            location_entry = tk.Entry(dialog, textvariable=location_var, font=('Arial', 10))
            location_entry.pack(padx=10, pady=5, fill=tk.X)
            
            # Description field
            tk.Label(dialog, text="Description:", font=('Arial', 10, 'bold'), bg='#f0f0f0').pack(anchor='w', padx=10, pady=(10,0))
            desc_text = tk.Text(dialog, height=4, font=('Arial', 10))
            desc_text.pack(padx=10, pady=5, fill=tk.BOTH, expand=True)
            desc_text.insert('1.0', event.get('description', ''))
            
            # Buttons
            button_frame = tk.Frame(dialog, bg='#f0f0f0')
            button_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=10)
            
            def save_changes():
                # TODO: Implement save functionality
                messagebox.showinfo("Info", "Event editing functionality will be implemented")
                dialog.destroy()
            
            def delete_event():
                if messagebox.askyesno("Confirm Delete", f"Delete event '{event['title']}'?"):
                    # TODO: Implement delete functionality
                    messagebox.showinfo("Info", "Event deletion functionality will be implemented")
                    dialog.destroy()
            
            tk.Button(button_frame, text="Save", command=save_changes, bg='#27ae60', fg='white', font=('Arial', 10, 'bold')).pack(side=tk.LEFT, padx=(0,5))
            tk.Button(button_frame, text="Delete", command=delete_event, bg='#e74c3c', fg='white', font=('Arial', 10, 'bold')).pack(side=tk.LEFT, padx=5)
            tk.Button(button_frame, text="Cancel", command=dialog.destroy, bg='#95a5a6', fg='white', font=('Arial', 10, 'bold')).pack(side=tk.RIGHT)
            
        except Exception as e:
            print(f"Error editing event: {e}")
    
    def _event_context_menu(self, event, event_data: Dict):
        """Show context menu for event"""
        context_menu = tk.Menu(self.window, tearoff=0)
        context_menu.add_command(label="Edit", command=lambda: self._edit_event(event_data))
        context_menu.add_command(label="Delete", command=lambda: self._delete_event_confirm(event_data))
        context_menu.add_separator()
        context_menu.add_command(label="Move to...", command=lambda: self._move_event(event_data))
        
        try:
            context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            context_menu.grab_release()
    
    def _add_new_event(self, date):
        """Add new event on double-click"""
        try:
            # Simple dialog for new event
            title = simpledialog.askstring("New Event", f"Event title for {date.strftime('%B %d, %Y')}:")
            if title:
                # TODO: Implement event creation
                messagebox.showinfo("Info", f"Event creation functionality will be implemented\nTitle: {title}\nDate: {date}")
        except Exception as e:
            print(f"Error adding new event: {e}")
    
    def _delete_event_confirm(self, event_data: Dict):
        """Confirm and delete event"""
        if messagebox.askyesno("Confirm Delete", f"Delete event '{event_data['title']}'?"):
            # TODO: Implement delete functionality
            messagebox.showinfo("Info", "Event deletion functionality will be implemented")
    
    def _move_event(self, event_data: Dict):
        """Move event to different date/time"""
        # TODO: Implement drag-and-drop or dialog-based moving
        messagebox.showinfo("Info", "Event moving functionality will be implemented")
    
    def _prev_month(self):
        """Navigate to previous month"""
        if self.current_date.month == 1:
            self.current_date = self.current_date.replace(year=self.current_date.year - 1, month=12)
        else:
            self.current_date = self.current_date.replace(month=self.current_date.month - 1)
        
        self._create_monthly_grid()
        self._update_header_title()
    
    def _next_month(self):
        """Navigate to next month"""
        if self.current_date.month == 12:
            self.current_date = self.current_date.replace(year=self.current_date.year + 1, month=1)
        else:
            self.current_date = self.current_date.replace(month=self.current_date.month + 1)
        
        self._create_monthly_grid()
        self._update_header_title()
    
    def _goto_today(self):
        """Navigate to current month"""
        self.current_date = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        self._create_monthly_grid()
        self._update_header_title()
    
    def _update_header_title(self):
        """Update the header title after navigation"""
        # Find and update the title label
        for widget in self.window.winfo_children():
            if isinstance(widget, tk.Frame) and widget.cget('bg') == '#2c3e50':
                for child in widget.winfo_children():
                    if isinstance(child, tk.Label) and child.cget('font')[1] == 20:
                        child.config(text=self.current_date.strftime('%B %Y'))
                        break
                break


# Enhanced function to be called from function calling system
def show_monthly_calendar(calendar_module=None) -> Dict[str, Any]:
    """Show monthly calendar GUI - to be called from function registry"""
    try:
        viewer = MonthlyCalendarViewer(calendar_module)
        success = viewer.show_monthly_schedule()
        
        if success:
            return {
                "success": True,
                "result": "Monthly calendar opened in a new window."
            }
        else:
            return {
                "success": False,
                "error": "Failed to open monthly calendar window"
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": f"Error opening monthly calendar: {str(e)}"
        }


if __name__ == "__main__":
    # Test the calendar viewers
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "monthly":
        viewer = MonthlyCalendarViewer()
        viewer.show_monthly_schedule()
    else:
        viewer = WeeklyCalendarViewer()
        viewer.show_weekly_schedule()