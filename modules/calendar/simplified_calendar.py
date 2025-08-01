"""
Simplified Calendar Module - Natural language meeting scheduling with conversation flow
"""

import asyncio
import logging
import time
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime, timedelta

from modules import BaseModule, EventType, Event
from .meeting_manager import MeetingManager
from .conversation_state import ConversationStateManager


class SimplifiedCalendarModule(BaseModule):
    """Simplified calendar module with conversational meeting creation"""
    
    def __init__(self, name: str = "calendar"):
        super().__init__(name)
        
        # Core components
        self.meeting_manager = None
        self.conversation_manager = None
        
        # Conversation tracking
        self._user_conversations = {}  # user_id -> conversation_id
        
        # Statistics
        self.stats = {
            'meetings_created': 0,
            'conversations_started': 0,
            'conversations_completed': 0,
            'calendar_queries': 0
        }
    
    async def initialize(self) -> bool:
        """Initialize the simplified calendar module"""
        try:
            self.log("Initializing Simplified Calendar Module...")
            
            # Initialize meeting manager
            db_path = Path("data/calendar.db")
            self.meeting_manager = MeetingManager(str(db_path), logger=self.logger)
            
            # Initialize conversation manager
            self.conversation_manager = ConversationStateManager(logger=self.logger)
            
            # Subscribe to relevant events
            self.subscribe_events([
                EventType.VOICE_COMMAND,
                EventType.INTENT_PARSED,
                EventType.LLM_RESPONSE
            ])
            
            self.is_loaded = True
            self.log("Simplified Calendar Module initialized successfully")
            return True
            
        except Exception as e:
            self.log(f"Failed to initialize Simplified Calendar Module: {e}", "error")
            return False
    
    async def shutdown(self) -> None:
        """Shutdown the calendar module"""
        self.log("Shutting down Simplified Calendar Module...")
        
        # Clean up any pending conversations
        if self.conversation_manager:
            self.conversation_manager.cleanup_expired_conversations()
        
        self.is_loaded = False
        self.log("Simplified Calendar Module shutdown complete")
    
    async def handle_event(self, event: Event) -> Optional[Any]:
        """Handle events from other modules"""
        try:
            if event.type == EventType.INTENT_PARSED:
                intent = event.data.get('intent', '')
                confidence = event.data.get('confidence', 0.0)
                text = event.data.get('text', '')
                
                if confidence > 0.4 and self._is_calendar_intent(intent, text):
                    return await self._handle_calendar_request(text, intent, event.data)
                    
            elif event.type == EventType.VOICE_COMMAND:
                command = event.data.get('command', '').lower()
                if any(keyword in command for keyword in ['schedule', 'meeting', 'calendar', 'appointment']):
                    return await self._handle_calendar_request(command, 'schedule_meeting', event.data)
                elif any(keyword in command for keyword in ['what', 'do i have', 'show me', 'check']):
                    return await self._handle_calendar_request(command, 'check_calendar', event.data)
            
        except Exception as e:
            self.log(f"Error handling event: {e}", "error")
        
        return None
    
    def _is_calendar_intent(self, intent: str, text: str) -> bool:
        """Check if intent is calendar-related"""
        calendar_intents = ['schedule_meeting', 'check_calendar', 'modify_meeting']
        calendar_keywords = [
            'schedule', 'meeting', 'appointment', 'calendar', 'agenda',
            'tomorrow', 'today', 'next week', 'what\'s on', 'do i have'
        ]
        
        return (intent in calendar_intents or 
                any(keyword in text.lower() for keyword in calendar_keywords))
    
    async def _handle_calendar_request(self, text: str, intent: str, event_data: Dict) -> Dict[str, Any]:
        """Handle calendar-related requests"""
        try:
            user_id = event_data.get('user_id', 'default')
            
            # Check if this is continuing an existing conversation
            if user_id in self._user_conversations:
                conversation_id = self._user_conversations[user_id]
                conversation = self.conversation_manager.get_conversation(conversation_id)
                
                if conversation and not conversation.completed:
                    return await self._continue_conversation(conversation_id, text)
            
            # Handle different types of requests
            if intent == 'check_calendar' or any(word in text.lower() for word in ['what', 'do i have', 'show', 'list']):
                return await self._handle_calendar_query(text)
            elif intent == 'schedule_meeting' or any(word in text.lower() for word in ['schedule', 'book', 'add', 'create', 'plan']):
                return await self._handle_meeting_creation(text, user_id)
            else:
                # Default to meeting creation for ambiguous requests
                return await self._handle_meeting_creation(text, user_id)
                
        except Exception as e:
            self.log(f"Error handling calendar request: {e}", "error")
            return {
                'success': False,
                'error': f"Calendar error: {str(e)}",
                'type': 'calendar_error'
            }
    
    async def _handle_meeting_creation(self, text: str, user_id: str) -> Dict[str, Any]:
        """Handle meeting creation with conversational flow"""
        try:
            result = await self.meeting_manager.create_meeting_from_text(text, user_id)
            
            if result['success'] and result.get('needs_followup'):
                # Start conversation tracking
                conversation_id = result['conversation_id']
                self._user_conversations[user_id] = conversation_id
                
                # Track conversation in state manager
                self.conversation_manager.start_conversation(
                    conversation_id, user_id, 'schedule_meeting', result
                )
                
                self.stats['conversations_started'] += 1
                
                return {
                    'success': True,
                    'type': 'meeting_followup',
                    'message': result['question'],
                    'conversation_id': conversation_id,
                    'parsed_info': result.get('parsed_info', {}),
                    'needs_response': True
                }
            
            elif result['success'] and not result.get('needs_followup'):
                # Meeting created successfully
                self.stats['meetings_created'] += 1
                
                # Emit schedule updated event
                self.emit_event(EventType.SCHEDULE_UPDATED, {
                    'action': 'created',
                    'meeting_id': result['meeting_id'],
                    'meeting': result['meeting']
                })
                
                return {
                    'success': True,
                    'type': 'meeting_created',
                    'message': result['confirmation'],
                    'meeting_id': result['meeting_id']
                }
            
            else:
                return {
                    'success': False,
                    'type': 'meeting_error',
                    'error': result.get('error', 'Unknown error creating meeting')
                }
                
        except Exception as e:
            self.log(f"Error creating meeting: {e}", "error")
            return {
                'success': False,
                'type': 'meeting_error',
                'error': f"Failed to create meeting: {str(e)}"
            }
    
    async def _continue_conversation(self, conversation_id: str, user_response: str) -> Dict[str, Any]:
        """Continue an ongoing meeting creation conversation"""
        try:
            result = await self.meeting_manager.continue_conversation(conversation_id, user_response)
            
            if result['success'] and result.get('needs_followup'):
                # Continue conversation
                return {
                    'success': True,
                    'type': 'meeting_followup',
                    'message': result['question'],
                    'conversation_id': conversation_id,
                    'field_updated': result.get('field_updated'),
                    'needs_response': True
                }
            
            elif result['success'] and not result.get('needs_followup'):
                # Meeting creation completed
                user_id = self._get_user_id_for_conversation(conversation_id)
                if user_id:
                    del self._user_conversations[user_id]
                
                self.conversation_manager.complete_conversation(conversation_id, result)
                self.stats['conversations_completed'] += 1
                self.stats['meetings_created'] += 1
                
                # Emit schedule updated event
                self.emit_event(EventType.SCHEDULE_UPDATED, {
                    'action': 'created',
                    'meeting_id': result['meeting_id'],
                    'meeting': result['meeting']
                })
                
                return {
                    'success': True,
                    'type': 'meeting_created',
                    'message': result['confirmation'],
                    'meeting_id': result['meeting_id']
                }
            
            else:
                return {
                    'success': False,
                    'type': 'conversation_error',
                    'error': result.get('error', 'Error in conversation')
                }
                
        except Exception as e:
            self.log(f"Error continuing conversation: {e}", "error")
            return {
                'success': False,
                'type': 'conversation_error',
                'error': f"Conversation error: {str(e)}"
            }
    
    async def _handle_calendar_query(self, text: str) -> Dict[str, Any]:
        """Handle calendar queries (what do I have scheduled?)"""
        try:
            self.stats['calendar_queries'] += 1
            
            # Determine time range
            today = datetime.now().date()
            
            if 'tomorrow' in text.lower():
                target_date = today + timedelta(days=1)
                period = "tomorrow"
                meetings = await self.meeting_manager.get_meetings_for_date(target_date.strftime('%Y-%m-%d'))
            elif 'today' in text.lower():
                target_date = today
                period = "today"
                meetings = await self.meeting_manager.get_meetings_for_date(target_date.strftime('%Y-%m-%d'))
            elif 'week' in text.lower():
                start_date = today
                end_date = today + timedelta(days=7)
                period = "this week"
                meetings = await self.meeting_manager.get_meetings_in_range(
                    start_date.strftime('%Y-%m-%d'),
                    end_date.strftime('%Y-%m-%d')
                )
            else:
                # Default to today
                target_date = today
                period = "today"
                meetings = await self.meeting_manager.get_meetings_for_date(target_date.strftime('%Y-%m-%d'))
            
            if not meetings:
                return {
                    'success': True,
                    'type': 'calendar_query',
                    'message': f"You don't have any meetings scheduled for {period}.",
                    'meetings': [],
                    'period': period
                }
            
            # Format meetings for response
            meeting_list = []
            for meeting in meetings:
                # Parse time for display
                meeting_time = datetime.strptime(meeting['time'], '%H:%M')
                formatted_time = meeting_time.strftime('%I:%M %p').lstrip('0')
                
                meeting_info = {
                    'title': meeting['title'],
                    'time': formatted_time,
                    'type': meeting['meeting_type'],
                    'location': meeting['location'] if meeting['location'] else None
                }
                meeting_list.append(meeting_info)
            
            # Create response message
            message = f"You have {len(meetings)} meeting{'s' if len(meetings) != 1 else ''} {period}:\n"
            for meeting in meeting_list:
                location_info = ""
                if meeting['type'] == 'online' and meeting['location']:
                    location_info = f" ({meeting['location']})"
                elif meeting['type'] == 'phone':
                    location_info = " (Phone call)"
                elif meeting['location']:
                    location_info = f" at {meeting['location']}"
                
                message += f"• {meeting['title']} at {meeting['time']}{location_info}\n"
            
            return {
                'success': True,
                'type': 'calendar_query',
                'message': message.strip(),
                'meetings': meeting_list,
                'period': period,
                'count': len(meetings)
            }
            
        except Exception as e:
            self.log(f"Error handling calendar query: {e}", "error")
            return {
                'success': False,
                'type': 'calendar_error',
                'error': f"Failed to retrieve calendar: {str(e)}"
            }
    
    def _get_user_id_for_conversation(self, conversation_id: str) -> Optional[str]:
        """Get user ID for a conversation"""
        for user_id, conv_id in self._user_conversations.items():
            if conv_id == conversation_id:
                return user_id
        return None
    
    def get_status(self) -> Dict[str, Any]:
        """Get module status"""
        try:
            # Get statistics from meeting manager
            meeting_stats = self.meeting_manager.get_statistics() if self.meeting_manager else {}
            
            # Get conversation statistics
            conversation_stats = self.conversation_manager.get_statistics() if self.conversation_manager else {}
            
            return {
                'module': 'simplified_calendar',
                'status': 'active' if self.is_loaded else 'inactive',
                'statistics': {
                    **self.stats,
                    **meeting_stats,
                    **conversation_stats
                },
                'active_conversations': len(self._user_conversations),
                'capabilities': [
                    'Natural language meeting scheduling',
                    'Interactive follow-up questions',
                    'Simplified meeting management',
                    'Calendar queries',
                    'Conversational interface'
                ]
            }
            
        except Exception as e:
            return {
                'module': 'simplified_calendar',
                'status': 'error',
                'error': str(e)
            }