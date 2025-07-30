"""
Time Utilities for SAGE
Handles time queries with location awareness
"""

import time
import datetime
from typing import Dict, Any, Optional
import requests
import json


class TimeUtils:
    """Utilities for handling time queries"""
    
    def __init__(self):
        self.user_timezone = None
        self.user_location = None
        
    def get_current_time(self, location: Optional[str] = None) -> Dict[str, Any]:
        """Get current time for user's location or specified location"""
        try:
            # If no location specified, use system time
            if not location:
                now = datetime.datetime.now()
                return {
                    'success': True,
                    'time': now.strftime('%I:%M %p'),
                    'date': now.strftime('%A, %B %d, %Y'),
                    'timezone': 'Local Time',
                    'full_datetime': now.strftime('%Y-%m-%d %H:%M:%S'),
                    'location': 'Your current location'
                }
            
            # Try to get time for specific location
            return self._get_time_for_location(location)
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': 'Could not determine current time'
            }
    
    def _get_time_for_location(self, location: str) -> Dict[str, Any]:
        """Get time for a specific location (would need API for full implementation)"""
        # For now, return local time with location note
        # In a full implementation, you'd use a timezone/geolocation API
        
        now = datetime.datetime.now()
        
        return {
            'success': True,
            'time': now.strftime('%I:%M %p'),
            'date': now.strftime('%A, %B %d, %Y'),
            'timezone': 'Local Time',
            'full_datetime': now.strftime('%Y-%m-%d %H:%M:%S'),
            'location': f'Local time (requested: {location})',
            'note': 'Note: This shows your local time. For accurate time zones, internet connection and location services would be needed.'
        }
    
    def get_time_info(self) -> Dict[str, Any]:
        """Get comprehensive time information"""
        now = datetime.datetime.now()
        
        return {
            'current_time': now.strftime('%I:%M:%S %p'),
            'current_date': now.strftime('%A, %B %d, %Y'),
            'iso_format': now.isoformat(),
            'timestamp': time.time(),
            'weekday': now.strftime('%A'),
            'month': now.strftime('%B'),
            'year': now.year,
            'timezone': 'Local Time'
        }
    
    def format_time_response(self, time_data: Dict[str, Any]) -> str:
        """Format time data into a natural language response"""
        if not time_data.get('success', True):
            return f"I'm sorry, I couldn't get the time: {time_data.get('message', 'Unknown error')}"
        
        response = f"The current time is {time_data['time']} on {time_data['date']}"
        
        if time_data.get('location'):
            response += f" ({time_data['location']})"
            
        if time_data.get('note'):
            response += f"\n\n{time_data['note']}"
            
        return response