"""
Visual Calendar Viewer for SAGE
Creates a GUI window showing weekly schedule in a time-grid format
"""

import tkinter as tk
from tkinter import ttk
import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Any
import threading


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


if __name__ == "__main__":
    # Test the calendar viewer
    viewer = WeeklyCalendarViewer()
    viewer.show_weekly_schedule()