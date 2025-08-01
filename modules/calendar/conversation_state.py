"""
Conversation State Manager - Track interactive calendar conversations
"""

import time
import json
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from pathlib import Path
import logging


@dataclass
class ConversationState:
    """State tracking for interactive conversations"""
    conversation_id: str
    user_id: str
    intent: str
    current_step: int
    total_steps: int
    context: Dict[str, Any]
    created_at: float
    last_interaction: float
    completed: bool = False


class ConversationStateManager:
    """Manage conversation states for interactive calendar operations"""
    
    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger(__name__)
        
        # Active conversations
        self.active_conversations: Dict[str, ConversationState] = {}
        
        # Configuration
        self.conversation_timeout = 300  # 5 minutes
        self.max_conversations_per_user = 3
        
        # Statistics
        self.stats = {
            'conversations_started': 0,
            'conversations_completed': 0,
            'conversations_abandoned': 0,
            'average_completion_time': 0.0
        }
    
    def start_conversation(self, conversation_id: str, user_id: str, intent: str, context: Dict[str, Any]) -> bool:
        """Start a new conversation"""
        try:
            # Clean up old conversations for this user
            self._cleanup_user_conversations(user_id)
            
            # Check user conversation limit
            user_conversations = [conv for conv in self.active_conversations.values() 
                                if conv.user_id == user_id and not conv.completed]
            
            if len(user_conversations) >= self.max_conversations_per_user:
                self.logger.warning(f"User {user_id} has too many active conversations")
                return False
            
            # Create new conversation state
            now = time.time()
            conversation = ConversationState(
                conversation_id=conversation_id,
                user_id=user_id,
                intent=intent,
                current_step=0,
                total_steps=len(context.get('missing_info', [])),
                context=context,
                created_at=now,
                last_interaction=now
            )
            
            self.active_conversations[conversation_id] = conversation
            self.stats['conversations_started'] += 1
            
            self.logger.info(f"Started conversation {conversation_id} for user {user_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start conversation: {e}")
            return False
    
    def update_conversation(self, conversation_id: str, step_data: Dict[str, Any]) -> bool:
        """Update conversation state after user response"""
        try:
            if conversation_id not in self.active_conversations:
                self.logger.warning(f"Conversation {conversation_id} not found")
                return False
            
            conversation = self.active_conversations[conversation_id]
            
            # Update step and context
            if 'current_step' in step_data:
                conversation.current_step = step_data['current_step']
            
            if 'context_updates' in step_data:
                conversation.context.update(step_data['context_updates'])
            
            conversation.last_interaction = time.time()
            
            # Check if conversation is complete
            if conversation.current_step >= conversation.total_steps:
                self._complete_conversation(conversation_id)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update conversation {conversation_id}: {e}")
            return False
    
    def get_conversation(self, conversation_id: str) -> Optional[ConversationState]:
        """Get conversation state"""
        if conversation_id in self.active_conversations:
            conversation = self.active_conversations[conversation_id]
            
            # Check if conversation has timed out
            if time.time() - conversation.last_interaction > self.conversation_timeout:
                self._abandon_conversation(conversation_id)
                return None
            
            return conversation
        
        return None
    
    def complete_conversation(self, conversation_id: str, result: Dict[str, Any]) -> bool:
        """Mark conversation as completed"""
        try:
            if conversation_id not in self.active_conversations:
                return False
            
            conversation = self.active_conversations[conversation_id]
            conversation.completed = True
            conversation.context['completion_result'] = result
            conversation.last_interaction = time.time()
            
            # Update statistics
            completion_time = conversation.last_interaction - conversation.created_at
            self._update_completion_stats(completion_time)
            
            self.logger.info(f"Completed conversation {conversation_id}")
            
            # Clean up after a delay (keep for a short time for reference)
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to complete conversation {conversation_id}: {e}")
            return False
    
    def abandon_conversation(self, conversation_id: str, reason: str = "timeout") -> bool:
        """Mark conversation as abandoned"""
        return self._abandon_conversation(conversation_id, reason)
    
    def _complete_conversation(self, conversation_id: str):
        """Internal method to complete conversation"""
        if conversation_id in self.active_conversations:
            conversation = self.active_conversations[conversation_id]
            conversation.completed = True
            
            completion_time = time.time() - conversation.created_at
            self._update_completion_stats(completion_time)
            
            self.stats['conversations_completed'] += 1
    
    def _abandon_conversation(self, conversation_id: str, reason: str = "timeout") -> bool:
        """Internal method to abandon conversation"""
        try:
            if conversation_id in self.active_conversations:
                conversation = self.active_conversations[conversation_id]
                conversation.context['abandonment_reason'] = reason
                
                del self.active_conversations[conversation_id]
                self.stats['conversations_abandoned'] += 1
                
                self.logger.info(f"Abandoned conversation {conversation_id}: {reason}")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to abandon conversation {conversation_id}: {e}")
            return False
    
    def _cleanup_user_conversations(self, user_id: str):
        """Clean up old conversations for a user"""
        now = time.time()
        to_remove = []
        
        for conv_id, conversation in self.active_conversations.items():
            if conversation.user_id == user_id:
                # Remove completed conversations older than 1 minute
                if conversation.completed and (now - conversation.last_interaction) > 60:
                    to_remove.append(conv_id)
                # Remove timed out conversations
                elif (now - conversation.last_interaction) > self.conversation_timeout:
                    to_remove.append(conv_id)
        
        for conv_id in to_remove:
            if conv_id in self.active_conversations:
                if self.active_conversations[conv_id].completed:
                    del self.active_conversations[conv_id]
                else:
                    self._abandon_conversation(conv_id, "timeout")
    
    def _update_completion_stats(self, completion_time: float):
        """Update completion time statistics"""
        completed = self.stats['conversations_completed']
        current_avg = self.stats['average_completion_time']
        
        # Calculate new average
        new_avg = (current_avg * completed + completion_time) / (completed + 1)
        self.stats['average_completion_time'] = new_avg
    
    def cleanup_expired_conversations(self):
        """Clean up all expired conversations"""
        now = time.time()
        expired = []
        
        for conv_id, conversation in self.active_conversations.items():
            if now - conversation.last_interaction > self.conversation_timeout:
                expired.append(conv_id)
        
        for conv_id in expired:
            self._abandon_conversation(conv_id, "expired")
        
        if expired:
            self.logger.info(f"Cleaned up {len(expired)} expired conversations")
    
    def get_user_conversations(self, user_id: str) -> List[ConversationState]:
        """Get all active conversations for a user"""
        return [conv for conv in self.active_conversations.values() 
                if conv.user_id == user_id and not conv.completed]
    
    def get_conversation_summary(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Get summary of conversation state"""
        conversation = self.get_conversation(conversation_id)
        if not conversation:
            return None
        
        return {
            'conversation_id': conversation.conversation_id,
            'intent': conversation.intent,
            'progress': f"{conversation.current_step}/{conversation.total_steps}",
            'duration': time.time() - conversation.created_at,
            'context_keys': list(conversation.context.keys()),
            'completed': conversation.completed
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get conversation statistics"""
        stats = self.stats.copy()
        stats.update({
            'active_conversations': len(self.active_conversations),
            'completion_rate': (
                stats['conversations_completed'] / 
                max(stats['conversations_started'], 1)
            ) * 100
        })
        
        return stats
    
    def save_state(self, file_path: str) -> bool:
        """Save conversation states to file"""
        try:
            state_data = {
                'conversations': {
                    conv_id: asdict(conv) 
                    for conv_id, conv in self.active_conversations.items()
                },
                'statistics': self.stats
            }
            
            with open(file_path, 'w') as f:
                json.dump(state_data, f, indent=2)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save conversation state: {e}")
            return False
    
    def load_state(self, file_path: str) -> bool:
        """Load conversation states from file"""
        try:
            if not Path(file_path).exists():
                return False
            
            with open(file_path, 'r') as f:
                state_data = json.load(f)
            
            # Restore conversations
            for conv_id, conv_data in state_data.get('conversations', {}).items():
                conversation = ConversationState(**conv_data)
                
                # Only restore non-expired conversations
                if time.time() - conversation.last_interaction < self.conversation_timeout:
                    self.active_conversations[conv_id] = conversation
            
            # Restore statistics
            if 'statistics' in state_data:
                self.stats.update(state_data['statistics'])
            
            self.logger.info(f"Loaded {len(self.active_conversations)} conversation states")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to load conversation state: {e}")
            return False