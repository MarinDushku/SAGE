"""
Visual Calendar Viewer for SAGE
Creates a GUI window showing weekly schedule in a time-grid format
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Any
import threading
import json
import calendar as cal  # Rename to avoid conflict with modules/calendar package


class WeeklyCalendarViewer:
    """GUI window for displaying weekly calendar in a grid format"""
    
    def __init__(self, calendar_module=None):
        self.calendar_module = calendar_module
        self.window = None
        self.tree = None
        
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
        """Create and display the calendar window"""
        try:
            # Create main window
            self.window = tk.Tk()
            self.window.title("SAGE - Weekly Schedule")
            self.window.geometry("1000x700")
            self.window.configure(bg='#f0f0f0')
            
            # Create header with week navigation
            self._create_header(start_date)
            
            # Create the calendar grid
            self._create_calendar_grid(start_date)
            
            # Start the GUI event loop
            self.window.mainloop()
            
        except Exception as e:
            print(f"Error creating calendar window: {e}")
    
    def _create_header(self, start_date: datetime):
        """Create header with week navigation and title"""
        header_frame = tk.Frame(self.window, bg='#2c3e50', height=60)
        header_frame.pack(fill=tk.X, pady=(0, 10))
        header_frame.pack_propagate(False)
        
        # Week title
        end_date = start_date + timedelta(days=6)
        title_text = f"Weekly Schedule: {start_date.strftime('%B %d')} - {end_date.strftime('%B %d, %Y')}"
        
        title_label = tk.Label(
            header_frame, 
            text=title_text,
            font=('Arial', 16, 'bold'),
            fg='white',
            bg='#2c3e50'
        )
        title_label.pack(expand=True)
        
        # Navigation buttons (for future enhancement)
        nav_frame = tk.Frame(header_frame, bg='#2c3e50')
        nav_frame.pack(side=tk.BOTTOM, pady=5)
        
        prev_btn = tk.Button(
            nav_frame,
            text="← Previous Week",
            font=('Arial', 10),
            command=lambda: self._navigate_week(start_date, -7)
        )
        prev_btn.pack(side=tk.LEFT, padx=5)
        
        next_btn = tk.Button(
            nav_frame,
            text="Next Week →",
            font=('Arial', 10),
            command=lambda: self._navigate_week(start_date, 7)
        )
        next_btn.pack(side=tk.RIGHT, padx=5)
    
    def _create_calendar_grid(self, start_date: datetime):
        """Create the main calendar grid with time slots and events"""
        # Main container
        main_frame = tk.Frame(self.window, bg='#f0f0f0')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Create scrollable canvas
        canvas = tk.Canvas(main_frame, bg='white')
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Get events for the week
        events = self._get_week_events(start_date)
        
        # Create the grid
        self._create_time_grid(scrollable_frame, start_date, events)
        
        # Pack scrollable components
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Bind mouse wheel to canvas
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
    
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
        """Get all events for the week starting from start_date"""
        try:
            events = []
            
            # Adjust to Monday of the current week
            weekday = start_date.weekday()  # Monday = 0, Sunday = 6
            monday_start = start_date - timedelta(days=weekday)
            end_date = monday_start + timedelta(days=7)
            
            # Get database path
            db_path = "data/calendar.db"
            if self.calendar_module and hasattr(self.calendar_module, 'db_path'):
                db_path = self.calendar_module.db_path
            
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                
                start_timestamp = monday_start.timestamp()
                end_timestamp = end_date.timestamp()
                
                cursor.execute("""
                    SELECT event_id, title, start_time, end_time, location, description
                    FROM events 
                    WHERE start_time >= ? AND start_time < ?
                    ORDER BY start_time
                """, (start_timestamp, end_timestamp))
                
                for row in cursor.fetchall():
                    event_id, title, start_time, end_time, location, description = row
                    
                    start_dt = datetime.fromtimestamp(start_time)
                    end_dt = datetime.fromtimestamp(end_time) if end_time else start_dt + timedelta(hours=1)
                    
                    events.append({
                        'id': event_id,
                        'title': title,
                        'start_time': start_dt,
                        'end_time': end_dt,
                        'time_str': start_dt.strftime('%I:%M %p'),
                        'location': location,
                        'description': description
                    })
            
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