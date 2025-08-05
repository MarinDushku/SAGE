"""
Conversation State Manager for SAGE Voice Interactions
Handles different conversation states and transitions for natural voice flow
"""

import asyncio
import time
import logging
from typing import Dict, Any, Optional, Callable
from enum import Enum


class ConversationState(Enum):
    """Conversation states for voice interactions"""
    SLEEPING = "sleeping"           # Needs wake word to activate
    LISTENING = "listening"         # Actively listening for commands
    CONFIRMING = "confirming"       # Asking for confirmation
    EXECUTING = "executing"         # Processing command
    WAITING_RESPONSE = "waiting"    # Waiting for yes/no response


class ConversationManager:
    """Manages conversation state and flow for natural voice interactions"""
    
    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger(__name__)
        
        # Current state
        self.current_state = ConversationState.SLEEPING
        self.state_changed_at = time.time()
        
        # Configuration
        self.conversation_timeout = 30.0  # 30 seconds of silence returns to sleeping
        self.confirmation_timeout = 20.0  # 20 seconds to respond to confirmation (increased from 10)
        self.wake_words = ['sage', 'hey sage', 'computer', 'hey computer']
        
        # State tracking
        self.last_interaction = time.time()
        self.pending_command = None
        self.pending_command_data = None
        self.confirmation_callback = None
        
        # Conversational memory for suggestions and context
        self.pending_suggestion = None  # What SAGE suggested
        self.suggestion_context = None  # Context about the suggestion
        self.last_response = None       # SAGE's last response
        self.conversation_history = []  # Short-term conversation history
        
        # Callbacks for state changes
        self.state_callbacks: Dict[ConversationState, Callable] = {}
        
        # Timeout task
        self.timeout_task = None
        
        self.log("Conversation manager initialized")
    
    def log(self, message: str, level: str = "info"):
        """Enhanced logging with conversation state prefix"""
        if self.logger:
            getattr(self.logger, level)(f"[CONVERSATION] {message}")
        else:
            print(f"[CONVERSATION-{level.upper()}] {message}")
    
    def get_current_state(self) -> ConversationState:
        """Get the current conversation state"""
        return self.current_state
    
    def set_state(self, new_state: ConversationState, reason: str = ""):
        """Change conversation state and trigger callbacks"""
        if new_state == self.current_state:
            return
            
        old_state = self.current_state
        self.current_state = new_state
        self.state_changed_at = time.time()
        
        self.log(f"State changed: {old_state.value} → {new_state.value} ({reason})")
        
        # Cancel existing timeout
        if self.timeout_task and not self.timeout_task.done():
            self.timeout_task.cancel()
            
        # Set up new timeout based on state
        if new_state == ConversationState.LISTENING:
            self.timeout_task = asyncio.create_task(self._conversation_timeout())
        elif new_state == ConversationState.CONFIRMING:
            self.timeout_task = asyncio.create_task(self._confirmation_timeout())
            
        # Trigger state callback
        if new_state in self.state_callbacks:
            try:
                callback = self.state_callbacks[new_state]
                if asyncio.iscoroutinefunction(callback):
                    asyncio.create_task(callback(old_state, new_state, reason))
                else:
                    callback(old_state, new_state, reason)
            except Exception as e:
                self.log(f"Error in state callback: {e}", "error")
    
    def register_state_callback(self, state: ConversationState, callback: Callable):
        """Register callback for specific state changes"""
        self.state_callbacks[state] = callback
        self.log(f"Registered callback for {state.value} state")
    
    def update_interaction(self):
        """Update last interaction timestamp"""
        self.last_interaction = time.time()
    
    def process_voice_input(self, text: str, confidence: float) -> Dict[str, Any]:
        """Process voice input based on current conversation state"""
        self.update_interaction()
        text_lower = text.lower().strip()
        
        self.log(f"Processing voice input in {self.current_state.value} state: '{text}'")
        
        if self.current_state == ConversationState.SLEEPING:
            return self._handle_sleeping_input(text, text_lower, confidence)
            
        elif self.current_state == ConversationState.LISTENING:
            return self._handle_listening_input(text, text_lower, confidence)
            
        elif self.current_state == ConversationState.CONFIRMING:
            return self._handle_confirmation_input(text, text_lower, confidence)
            
        elif self.current_state == ConversationState.WAITING_RESPONSE:
            return self._handle_waiting_input(text, text_lower, confidence)
            
        else:
            self.log(f"Unexpected state: {self.current_state.value}", "warning")
            return {"action": "ignore", "reason": "unexpected_state"}
    
    def _handle_sleeping_input(self, text: str, text_lower: str, confidence: float) -> Dict[str, Any]:
        """Handle input when in sleeping state (requires wake word)"""
        wake_word_detected = False
        command_text = text_lower
        
        # Check for wake words
        for wake_word in self.wake_words:
            if wake_word in text_lower:
                wake_word_detected = True
                command_text = text_lower.replace(wake_word, '').strip()
                break
        
        if wake_word_detected:
            if command_text:
                # Wake word + command in one go
                self.set_state(ConversationState.LISTENING, "wake word with command")
                return {
                    "action": "process_command",
                    "command": command_text,
                    "original_text": text,
                    "confidence": confidence
                }
            else:
                # Just wake word
                self.set_state(ConversationState.LISTENING, "wake word detected")
                return {
                    "action": "acknowledge_wake",
                    "response": "Yes? What can I help you with?"
                }
        else:
            # No wake word - ignore
            return {"action": "ignore", "reason": "no_wake_word"}
    
    def _handle_listening_input(self, text: str, text_lower: str, confidence: float) -> Dict[str, Any]:
        """Handle input when actively listening (no wake word needed)"""
        # Process any command directly
        return {
            "action": "process_command",
            "command": text_lower,
            "original_text": text,
            "confidence": confidence
        }
    
    def _handle_confirmation_input(self, text: str, text_lower: str, confidence: float) -> Dict[str, Any]:
        """Handle input when waiting for confirmation"""
        # Check for positive/negative responses
        positive_responses = ['yes', 'yeah', 'yep', 'sure', 'okay', 'ok', 'confirm', 'do it', 'go ahead']
        negative_responses = ['no', 'nope', 'cancel', 'don\'t', 'stop', 'never mind']
        
        for positive in positive_responses:
            if positive in text_lower:
                self.set_state(ConversationState.EXECUTING, "confirmation accepted")
                return {
                    "action": "execute_command",
                    "command": self.pending_command,
                    "command_data": self.pending_command_data
                }
        
        for negative in negative_responses:
            if negative in text_lower:
                self.set_state(ConversationState.LISTENING, "confirmation rejected")
                return {
                    "action": "cancel_command",
                    "response": "Okay, cancelled. What else can I help you with?"
                }
        
        # Unclear response - ask again
        return {
            "action": "clarify",
            "response": "I didn't understand. Please say yes or no."
        }
    
    def _handle_waiting_input(self, text: str, text_lower: str, confidence: float) -> Dict[str, Any]:
        """Handle input when waiting for specific response"""
        # Similar to confirmation but more flexible
        return self._handle_confirmation_input(text, text_lower, confidence)
    
    def request_confirmation(self, command: str, command_data: Dict[str, Any], confirmation_message: str):
        """Request confirmation for a command"""
        self.pending_command = command
        self.pending_command_data = command_data
        self.set_state(ConversationState.CONFIRMING, "requesting confirmation")
        
        self.log(f"Requesting confirmation for: {command}")
        return confirmation_message
    
    def command_completed(self, success: bool = True):
        """Mark command as completed and return to listening"""
        if success:
            self.set_state(ConversationState.LISTENING, "command completed successfully")
        else:
            self.set_state(ConversationState.LISTENING, "command failed")
        
        # Clear pending command
        self.pending_command = None
        self.pending_command_data = None
    
    def force_sleep(self, reason: str = "manual"):
        """Force conversation to sleep state"""
        self.set_state(ConversationState.SLEEPING, f"forced sleep: {reason}")
    
    async def _conversation_timeout(self):
        """Handle conversation timeout - return to sleeping after inactivity"""
        try:
            await asyncio.sleep(self.conversation_timeout)
            
            # Check if we're still in the same state and enough time has passed
            if (self.current_state == ConversationState.LISTENING and 
                time.time() - self.last_interaction >= self.conversation_timeout):
                
                self.set_state(ConversationState.SLEEPING, "conversation timeout")
                
        except asyncio.CancelledError:
            pass  # Normal when state changes
    
    async def _confirmation_timeout(self):
        """Handle confirmation timeout - return to listening if no response"""
        try:
            await asyncio.sleep(self.confirmation_timeout)
            
            if self.current_state == ConversationState.CONFIRMING:
                self.set_state(ConversationState.LISTENING, "confirmation timeout")
                
        except asyncio.CancelledError:
            pass  # Normal when state changes
    
    def store_suggestion(self, suggestion_text: str, suggestion_data: Dict[str, Any]):
        """Store a suggestion that SAGE made to the user"""
        self.pending_suggestion = suggestion_text
        self.suggestion_context = suggestion_data
        self.last_response = suggestion_text
        self.log(f"Stored suggestion: {suggestion_text}")
        
        # Add to conversation history
        self.add_to_history("SAGE", suggestion_text)
    
    def add_to_history(self, speaker: str, text: str):
        """Add a message to conversation history"""
        self.conversation_history.append({
            "speaker": speaker,
            "text": text,
            "timestamp": time.time()
        })
        
        # Keep only last 10 exchanges
        if len(self.conversation_history) > 20:  # 10 exchanges (user + SAGE each)
            self.conversation_history = self.conversation_history[-20:]
    
    def get_pending_suggestion(self) -> Optional[Dict[str, Any]]:
        """Get the current pending suggestion if any"""
        if self.pending_suggestion and self.suggestion_context:
            return {
                "suggestion_text": self.pending_suggestion,
                "context": self.suggestion_context
            }
        return None
    
    def clear_suggestion(self):
        """Clear the pending suggestion"""
        self.pending_suggestion = None
        self.suggestion_context = None
        self.log("Cleared pending suggestion")
    
    def is_affirmative_response(self, user_input: str) -> bool:
        """Check if user input is an affirmative response (yes, sure, ok, etc.)"""
        affirmative_words = [
            'yes', 'yeah', 'yep', 'sure', 'ok', 'okay', 'alright', 'sounds good',
            'that works', 'perfect', 'good', 'fine', 'absolutely', 'definitely',
            'correct', 'right', 'agreed', 'accept', 'confirm', 'do it', 'please'
        ]
        
        user_lower = user_input.lower().strip()
        return any(word in user_lower for word in affirmative_words)
    
    def is_negative_response(self, user_input: str) -> bool:
        """Check if user input is a negative response (no, cancel, etc.)"""
        negative_words = [
            'no', 'nope', 'nah', 'cancel', 'nevermind', 'never mind', 'stop',
            'abort', 'decline', 'reject', 'not now', 'later', 'maybe later',
            'wrong', 'incorrect', 'that\'s wrong', 'not right'
        ]
        
        user_lower = user_input.lower().strip()
        return any(word in user_lower for word in negative_words)
    
    def get_conversation_history(self, limit: int = 10) -> list:
        """Get recent conversation history"""
        return self.conversation_history[-limit*2:] if self.conversation_history else []
    
    def get_status(self) -> Dict[str, Any]:
        """Get current conversation manager status"""
        return {
            "current_state": self.current_state.value,
            "state_duration": time.time() - self.state_changed_at,
            "last_interaction": self.last_interaction,
            "time_since_interaction": time.time() - self.last_interaction,
            "pending_command": self.pending_command,
            "has_timeout_task": self.timeout_task and not self.timeout_task.done(),
            "conversation_timeout": self.conversation_timeout,
            "confirmation_timeout": self.confirmation_timeout
        }
    
    def get_state_description(self) -> str:
        """Get human-readable state description"""
        descriptions = {
            ConversationState.SLEEPING: "Sleeping (say wake word to activate)",
            ConversationState.LISTENING: "Listening for commands",
            ConversationState.CONFIRMING: "Waiting for confirmation",
            ConversationState.EXECUTING: "Processing command",
            ConversationState.WAITING_RESPONSE: "Waiting for response"
        }
        return descriptions.get(self.current_state, "Unknown state")
    
    async def shutdown(self):
        """Shutdown conversation manager"""
        if self.timeout_task and not self.timeout_task.done():
            self.timeout_task.cancel()
            
        self.log("Conversation manager shutdown complete")