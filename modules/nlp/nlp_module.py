"""
NLP Module - Natural Language Processing with Ollama Integration
"""

import asyncio
import logging
import json
import time
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path

from modules import BaseModule, EventType, Event
from modules.time_utils import TimeUtils
from .intent_analyzer import IntentAnalyzer
from .semantic_matcher import SemanticMatcher

# Try to import HTTP client for Ollama API
try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    httpx = None
    HTTPX_AVAILABLE = False

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    requests = None
    REQUESTS_AVAILABLE = False


class NLPModule(BaseModule):
    """Natural Language Processing module with Ollama integration"""
    
    def __init__(self, name: str = "nlp"):
        super().__init__(name)
        
        # Will be set by plugin manager
        self.module_config = None
        
        # Default configuration (will be overridden by actual config)
        self.enabled = True
        self.provider = 'ollama'
        self.model = 'phi3:mini'
        self.temperature = 0.7
        self.max_tokens = 1000
        self.context_window = 4000
        self.ollama_host = 'http://127.0.0.1:11434'
        self.ollama_timeout = 30
        self.context_timeout = 1800
        self.memory_size = 10
        self.confidence_threshold = 0.8
        self.fallback_enabled = True
        
        # State
        self.is_initialized = False
        self.conversation_context = []
        self.user_preferences = {}
        self.session_memory = {}
        
        # HTTP client for API calls
        self.http_client = None
        
        # Prompt engine for advanced prompt management
        self.prompt_engine = None
        
        # LLM response cache for performance optimization
        self.llm_cache = None
        
        # Time utilities
        self.time_utils = TimeUtils()
        
        # Enhanced NLP components
        self.intent_analyzer = None
        self.semantic_matcher = None
        
        # Statistics
        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'average_response_time': 0.0,
            'context_length': 0,
            'memory_usage': 0,
            'intents_processed': 0,
            'model_switches': 0
        }
        
    async def initialize(self) -> bool:
        """Initialize the NLP module"""
        try:
            self.log("Initializing NLP module...")
            
            # Load configuration
            self._load_config()
            
            if not self.enabled:
                self.log("NLP module disabled")
                return True
                
            # Check dependencies
            if not self._check_dependencies():
                return False
                
            # Initialize HTTP client
            await self._initialize_http_client()
            
            # Test Ollama connection
            if self.provider == 'ollama':
                if not await self._test_ollama_connection():
                    self.log("Ollama connection failed, but continuing initialization", "warning")
                    
            # Initialize conversation context
            self._initialize_context()
            
            # Initialize prompt engine
            await self._initialize_prompt_engine()
            
            # Initialize LLM cache
            await self._initialize_llm_cache()
            
            # Initialize enhanced NLP components
            await self._initialize_enhanced_nlp()
            
            # Load user preferences
            await self._load_user_preferences()
            
            self.is_initialized = True
            self.is_loaded = True
            self.log("NLP module initialized successfully")
            return True
            
        except Exception as e:
            self.log(f"Failed to initialize NLP module: {e}", "error")
            return False
            
    async def shutdown(self):
        """Shutdown the NLP module"""
        try:
            self.log("Shutting down NLP module...")
            
            # Save user preferences
            await self._save_user_preferences()
            
            # Shutdown prompt engine
            if self.prompt_engine:
                await self.prompt_engine.shutdown()
            
            # Shutdown LLM cache
            if self.llm_cache:
                await self.llm_cache.shutdown()
            
            # Close HTTP client
            if self.http_client:
                await self.http_client.aclose()
                
            self.is_initialized = False
            self.is_loaded = False
            self.log("NLP module shutdown complete")
            
        except Exception as e:
            self.log(f"Error during NLP module shutdown: {e}", "error")
            
    async def handle_event(self, event: Event) -> Optional[Any]:
        """Handle events from other modules"""
        try:
            if event.type == EventType.INTENT_PARSED:
                return await self._handle_intent_parsed(event)
            elif event.type == EventType.VOICE_COMMAND:
                return await self._handle_voice_command(event)
            else:
                self.log(f"Unhandled event type: {event.type}", "warning")
                return None
                
        except Exception as e:
            self.log(f"Error handling event {event.type}: {e}", "error")
            return None
            
    async def process_text(self, text: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """Process natural language text and generate response"""
        try:
            start_time = time.time()
            self.stats['total_requests'] += 1
            
            if not self.is_initialized:
                raise RuntimeError("NLP module not initialized")
                
            # Check for time queries first
            time_response = self._handle_time_query(text)
            if time_response:
                response_time = time.time() - start_time
                self._update_stats(response_time, True)
                
                return {
                    'success': True,
                    'response': {'text': time_response},
                    'context': context or {},
                    'processing_time': response_time,
                    'model_used': 'time_utils',
                    'provider': 'local',
                    'cached': False
                }
            
            # Check for calendar queries
            calendar_response = await self._handle_calendar_query(text)
            if calendar_response:
                response_time = time.time() - start_time
                self._update_stats(response_time, True)
                
                return {
                    'success': True,
                    'response': {'text': calendar_response},
                    'context': context or {},
                    'processing_time': response_time,
                    'model_used': 'calendar_utils',
                    'provider': 'local',
                    'cached': False
                }
            
            # Check for scheduling requests
            schedule_response = await self._handle_schedule_request(text)
            if schedule_response:
                response_time = time.time() - start_time
                self._update_stats(response_time, True)
                
                return {
                    'success': True,
                    'response': {'text': schedule_response},
                    'context': context or {},
                    'processing_time': response_time,
                    'model_used': 'calendar_scheduling',
                    'provider': 'local',
                    'cached': False
                }
            
            # Prepare context
            full_context = self._prepare_context(text, context)
            
            # Check cache first
            cached_response = None
            cache_metadata = {
                'model': self.model,
                'provider': self.provider,
                'temperature': self.temperature,
                'max_tokens': self.max_tokens
            }
            
            if self.llm_cache:
                cached_response = await self.llm_cache.get(text, cache_metadata)
            
            if cached_response:
                # Return cached response
                response_time = time.time() - start_time
                self._update_stats(response_time, True)
                
                return {
                    'success': True,
                    'response': {'text': cached_response},
                    'context': full_context,
                    'processing_time': response_time,
                    'model_used': self.model,
                    'provider': self.provider,
                    'cached': True
                }
            
            # Generate response based on provider
            if self.provider == 'ollama':
                response = await self._generate_ollama_response(text, full_context)
            else:
                response = await self._generate_fallback_response(text, full_context)
            
            # Cache the response
            if self.llm_cache and response.get('text'):
                await self.llm_cache.set(text, response['text'], cache_metadata)
                
            # Update conversation context
            self._update_context(text, response.get('text', ''))
            
            # Update statistics
            response_time = time.time() - start_time
            self._update_stats(response_time, True)
            
            return {
                'success': True,
                'response': response,
                'context': full_context,
                'processing_time': response_time,
                'model_used': self.model,
                'provider': self.provider,
                'cached': False
            }
            
        except Exception as e:
            self.log(f"Error processing text: {e}", "error")
            self.stats['failed_requests'] += 1
            
            # Return fallback response
            return {
                'success': False,
                'error': str(e),
                'response': {'text': "I'm sorry, I'm having trouble processing that right now."},
                'context': context or {},
                'processing_time': time.time() - start_time if 'start_time' in locals() else 0,
                'model_used': self.model,
                'provider': self.provider
            }
            
    async def analyze_intent(self, text: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """Analyze the intent of user input with enhanced semantic understanding"""
        try:
            if self.intent_analyzer:
                # Use enhanced intent analyzer
                result = self.intent_analyzer.analyze_intent(text, context)
                self.stats['intents_processed'] += 1
                return result
            else:
                # Fallback to basic intent analysis
                return await self._analyze_intent_basic(text)
                
        except Exception as e:
            self.log(f"Error analyzing intent: {e}", "error")
            return {
                'intent': 'error',
                'confidence': 0.0,
                'all_scores': {},
                'threshold_met': False,
                'error': str(e)
            }
            
    async def get_available_models(self) -> List[str]:
        """Get list of available models from Ollama"""
        try:
            if self.provider != 'ollama' or not self.http_client:
                return [self.model]
                
            response = await self.http_client.get(f"{self.ollama_host}/api/tags")
            
            if response.status_code == 200:
                data = response.json()
                models = [model['name'] for model in data.get('models', [])]
                return models
            else:
                self.log(f"Failed to get models: {response.status_code}", "warning")
                return [self.model]
                
        except Exception as e:
            self.log(f"Error getting available models: {e}", "error")
            return [self.model]
            
    async def switch_model(self, model_name: str) -> bool:
        """Switch to a different model"""
        try:
            available_models = await self.get_available_models()
            
            if model_name in available_models:
                old_model = self.model
                self.model = model_name
                self.stats['model_switches'] += 1
                
                self.log(f"Switched model from {old_model} to {model_name}")
                return True
            else:
                self.log(f"Model {model_name} not available", "warning")
                return False
                
        except Exception as e:
            self.log(f"Error switching model: {e}", "error")
            return False
            
    def get_status(self) -> Dict[str, Any]:
        """Get NLP module status"""
        return {
            'initialized': self.is_initialized,
            'enabled': self.enabled,
            'provider': self.provider,
            'model': self.model,
            'temperature': self.temperature,
            'max_tokens': self.max_tokens,
            'context_window': self.context_window,
            'ollama_host': self.ollama_host,
            'context_length': len(self.conversation_context),
            'memory_size': self.memory_size,
            'dependencies': {
                'httpx': HTTPX_AVAILABLE,
                'requests': REQUESTS_AVAILABLE
            },
            'statistics': self.stats.copy()
        }
        
    # Private helper methods
    def _load_config(self):
        """Load configuration from module config"""
        if self.config:
            self.enabled = self.config.get('enabled', True)
            
            # LLM Configuration
            llm_config = self.config.get('llm', {})
            self.provider = llm_config.get('provider', 'ollama')
            self.model = llm_config.get('model', 'phi3:mini')
            self.temperature = llm_config.get('temperature', 0.7)
            self.max_tokens = llm_config.get('max_tokens', 1000)
            self.context_window = llm_config.get('context_window', 4000)
            
            # Ollama Configuration
            self.ollama_host = self.config.get('ollama_host', 'http://127.0.0.1:11434')
            self.ollama_timeout = self.config.get('ollama_timeout', 30)
            
            # Context Management
            context_config = self.config.get('context', {})
            self.context_timeout = context_config.get('context_timeout', 1800)
            self.memory_size = context_config.get('memory_size', 10)
            
            # Intent Recognition
            intent_config = self.config.get('intent', {})
            self.confidence_threshold = intent_config.get('confidence_threshold', 0.8)
            self.fallback_enabled = intent_config.get('fallback_enabled', True)
    
    def _check_dependencies(self) -> bool:
        """Check if required dependencies are available"""
        if not HTTPX_AVAILABLE and not REQUESTS_AVAILABLE:
            self.log("No HTTP client available. Install httpx or requests", "error")
            self.log("Install with: pip install httpx")
            return False
        return True
        
    async def _initialize_http_client(self):
        """Initialize HTTP client for API calls"""
        if HTTPX_AVAILABLE:
            self.http_client = httpx.AsyncClient(timeout=self.ollama_timeout)
            self.log("Initialized httpx client")
        elif REQUESTS_AVAILABLE:
            # Fallback to requests (synchronous)
            self.log("Using requests client (synchronous fallback)")
        else:
            raise RuntimeError("No HTTP client available")
            
    async def _test_ollama_connection(self) -> bool:
        """Test connection to Ollama service"""
        try:
            if not self.http_client:
                return False
                
            response = await self.http_client.get(f"{self.ollama_host}/api/tags")
            
            if response.status_code == 200:
                self.log("Ollama connection successful")
                return True
            else:
                self.log(f"Ollama connection failed: {response.status_code}", "warning")
                return False
                
        except Exception as e:
            self.log(f"Ollama connection test failed: {e}", "warning")
            return False
            
    def _initialize_context(self):
        """Initialize conversation context"""
        self.conversation_context = []
        self.session_memory = {
            'start_time': time.time(),
            'user_name': None,
            'preferences': {},
            'topic_history': []
        }
        
    async def _load_user_preferences(self):
        """Load user preferences from storage"""
        try:
            prefs_file = Path("data/user_preferences.json")
            if prefs_file.exists():
                with open(prefs_file, 'r') as f:
                    self.user_preferences = json.load(f)
                self.log("User preferences loaded")
        except Exception as e:
            self.log(f"Could not load user preferences: {e}", "warning")
            
    async def _save_user_preferences(self):
        """Save user preferences to storage"""
        try:
            prefs_file = Path("data/user_preferences.json")
            prefs_file.parent.mkdir(exist_ok=True)
            
            with open(prefs_file, 'w') as f:
                json.dump(self.user_preferences, f, indent=2)
            self.log("User preferences saved")
        except Exception as e:
            self.log(f"Could not save user preferences: {e}", "warning")
            
    def _prepare_context(self, text: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """Prepare context for LLM processing"""
        full_context = {
            'user_input': text,
            'conversation_history': self.conversation_context[-5:],  # Last 5 exchanges
            'session_memory': self.session_memory,
            'user_preferences': self.user_preferences,
            'timestamp': time.time()
        }
        
        if context:
            full_context.update(context)
            
        return full_context
        
    async def _generate_ollama_response(self, text: str, context: Dict) -> Dict[str, Any]:
        """Generate response using Ollama"""
        try:
            if not self.http_client:
                raise RuntimeError("HTTP client not initialized")
                
            # Prepare the prompt with context
            system_prompt = self._build_system_prompt(context)
            
            payload = {
                "model": self.model,
                "prompt": f"{system_prompt}\n\nUser: {text}\nAssistant:",
                "options": {
                    "temperature": self.temperature,
                    "num_predict": self.max_tokens
                },
                "stream": False
            }
            
            response = await self.http_client.post(
                f"{self.ollama_host}/api/generate",
                json=payload
            )
            
            if response.status_code == 200:
                data = response.json()
                response_text = data.get('response', '').strip()
                
                return {
                    'text': response_text,
                    'model': self.model,
                    'tokens_used': len(response_text.split()),
                    'ollama_data': data
                }
            else:
                raise RuntimeError(f"Ollama API error: {response.status_code}")
                
        except Exception as e:
            self.log(f"Ollama response generation failed: {e}", "error")
            return await self._generate_fallback_response(text, context)
            
    async def _generate_fallback_response(self, text: str, context: Dict) -> Dict[str, Any]:
        """Generate fallback response when Ollama is unavailable"""
        # Simple rule-based responses
        text_lower = text.lower()
        
        if any(word in text_lower for word in ['hello', 'hi', 'hey']):
            response_text = "Hello! I'm SAGE, your AI assistant. How can I help you today?"
        elif any(word in text_lower for word in ['bye', 'goodbye']):
            response_text = "Goodbye! Have a great day!"
        elif '?' in text:
            response_text = "That's an interesting question. I'd need my full language model to give you a proper answer."
        else:
            response_text = "I understand you're trying to communicate with me. My language processing is currently limited."
            
        return {
            'text': response_text,
            'model': 'fallback',
            'tokens_used': len(response_text.split()),
            'fallback': True
        }
        
    def _build_system_prompt(self, context: Dict) -> str:
        """Build system prompt with context"""
        prompt_parts = [
            "You are SAGE, a Smart Adaptive General Executive AI assistant.",
            "You are helpful, knowledgeable, and friendly.",
            "Keep responses concise but informative."
        ]
        
        # Add conversation history if available
        if context.get('conversation_history'):
            prompt_parts.append("\nRecent conversation:")
            for exchange in context['conversation_history'][-3:]:
                prompt_parts.append(f"User: {exchange.get('user', '')}")
                prompt_parts.append(f"Assistant: {exchange.get('assistant', '')}")
                
        # Add user preferences if available
        if context.get('user_preferences'):
            prefs = context['user_preferences']
            if prefs:
                prompt_parts.append(f"\nUser preferences: {json.dumps(prefs, indent=2)}")
                
        return "\n".join(prompt_parts)
        
    def _update_context(self, user_input: str, assistant_response: str):
        """Update conversation context"""
        exchange = {
            'timestamp': time.time(),
            'user': user_input,
            'assistant': assistant_response
        }
        
        self.conversation_context.append(exchange)
        
        # Limit context size
        if len(self.conversation_context) > self.memory_size:
            self.conversation_context.pop(0)
            
        self.stats['context_length'] = len(self.conversation_context)
        
    def _update_stats(self, response_time: float, success: bool):
        """Update processing statistics"""
        if success:
            self.stats['successful_requests'] += 1
            
        # Update average response time
        total_requests = self.stats['total_requests']
        current_avg = self.stats['average_response_time']
        self.stats['average_response_time'] = (
            (current_avg * (total_requests - 1) + response_time) / total_requests
        )
        
    async def _handle_intent_parsed(self, event: Event) -> Optional[Any]:
        """Handle parsed intent events"""
        try:
            text = event.data.get('text', '')
            intent = event.data.get('intent', 'unknown')
            confidence = event.data.get('confidence', 0.0)
            
            self.log(f"Processing intent: {intent} for text: '{text}'")
            
            # Process the text with LLM
            response = await self.process_text(text, {
                'intent': intent,
                'confidence': confidence,
                'source': event.source_module
            })
            
            # Emit LLM response event
            if response.get('success'):
                self.emit_event(EventType.LLM_RESPONSE, {
                    'original_text': text,
                    'response': response['response'],
                    'intent': intent,
                    'confidence': confidence,
                    'processing_time': response.get('processing_time', 0)
                })
                
            return response
            
        except Exception as e:
            self.log(f"Error handling intent parsed event: {e}", "error")
            return None
            
    async def _handle_voice_command(self, event: Event) -> Optional[Any]:
        """Handle voice command events"""
        try:
            command = event.data.get('command', '')
            confidence = event.data.get('confidence', 0.0)
            
            self.log(f"Processing voice command: '{command}' (confidence: {confidence:.2f})")
            
            # Analyze intent first with enhanced analyzer
            intent_result = await self.analyze_intent(command, {
                'source': 'voice',
                'confidence': confidence
            })
            
            # Process with LLM
            response = await self.process_text(command, {
                'intent': intent_result.get('intent', 'unknown'),
                'intent_confidence': intent_result.get('confidence', 0.0),
                'voice_confidence': confidence,
                'source': 'voice',
                'context_summary': self.intent_analyzer.get_context_summary() if self.intent_analyzer else {}
            })
            
            return response
            
        except Exception as e:
            self.log(f"Error handling voice command event: {e}", "error")
            return None
    
    async def _initialize_prompt_engine(self):
        """Initialize the prompt engineering engine"""
        try:
            from .prompt_engine import PromptEngine
            
            self.prompt_engine = PromptEngine()
            await self.prompt_engine.initialize()
            
            self.log("Prompt engine initialized successfully")
            
        except Exception as e:
            self.log(f"Failed to initialize prompt engine: {e}", "warning")
            self.prompt_engine = None
    
    async def _initialize_llm_cache(self):
        """Initialize the LLM response cache"""
        try:
            from .llm_cache import LLMCache, CacheConfig
            
            # Create cache configuration
            cache_config = CacheConfig(
                max_size=1000,
                ttl_seconds=3600,
                similarity_threshold=0.85,
                enable_similarity_matching=True,
                persistent=True,
                cache_file="llm_cache.json"
            )
            
            self.llm_cache = LLMCache(cache_config)
            await self.llm_cache.initialize()
            
            self.log("LLM cache initialized successfully")
            
        except Exception as e:
            self.log(f"Failed to initialize LLM cache: {e}", "warning")
            self.llm_cache = None
    
    def _handle_time_query(self, text: str) -> Optional[str]:
        """Handle time-related queries"""
        try:
            text_lower = text.lower().strip()
            
            # Check for time-related keywords
            time_keywords = [
                'what time is it', 'current time', 'what time', 'time is it',
                'what\'s the time', 'tell me the time', 'time now', 'whats the time',
                'what is the time', 'tell time', 'current time is', 'time please'
            ]
            
            location_keywords = ['in', 'at', 'for']
            
            # Check if this is a time query
            is_time_query = any(keyword in text_lower for keyword in time_keywords)
            
            if is_time_query:
                # Extract location if specified
                location = None
                for loc_keyword in location_keywords:
                    if loc_keyword in text_lower:
                        # Try to extract location after the keyword
                        parts = text_lower.split(loc_keyword)
                        if len(parts) > 1:
                            location = parts[-1].strip()
                            break
                
                # Get time information
                time_data = self.time_utils.get_current_time(location)
                return self.time_utils.format_time_response(time_data)
            
            return None
            
        except Exception as e:
            return f"Sorry, I had trouble getting the time: {e}"
    
    async def _handle_calendar_query(self, text: str) -> Optional[str]:
        """Handle calendar-related queries"""
        try:
            text_lower = text.lower().strip()
            
            # Calendar query keywords
            check_keywords = [
                'do i have', 'any meetings', 'meetings scheduled', 'what meetings',
                'my calendar', 'my schedule', 'scheduled for', 'events today',
                'events tomorrow', 'meetings today', 'meetings tomorrow'
            ]
            
            # Check if this is a calendar query
            is_calendar_query = any(keyword in text_lower for keyword in check_keywords)
            
            if is_calendar_query:
                # Get calendar module to actually check the database
                calendar_module = None
                if hasattr(self, 'event_bus') and self.event_bus and hasattr(self.event_bus, 'subscribers'):
                    # Try to find calendar module through event bus subscribers
                    for event_type, subscribers in self.event_bus.subscribers.items():
                        for subscriber in subscribers:
                            if hasattr(subscriber, 'name') and subscriber.name == 'calendar':
                                calendar_module = subscriber
                                break
                        if calendar_module:
                            break
                
                # If we found the calendar module, check the actual database
                if calendar_module:
                    try:
                        # Get events for the requested timeframe
                        if 'tomorrow' in text_lower:
                            # Calculate tomorrow's date range
                            import datetime
                            tomorrow = datetime.datetime.now() + datetime.timedelta(days=1)
                            start_time = tomorrow.replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
                            end_time = tomorrow.replace(hour=23, minute=59, second=59, microsecond=999999).timestamp()
                            
                            events = await calendar_module._get_events_in_range(start_time, end_time)
                            
                            if events:
                                event_list = []
                                for event in events:
                                    event_time = time.strftime('%I:%M %p', time.localtime(event['start_time']))
                                    event_list.append(f"• {event['title']} at {event_time}")
                                
                                return f"You have {len(events)} meeting{'s' if len(events) != 1 else ''} tomorrow:\n" + "\n".join(event_list)
                            else:
                                return "You don't have any meetings scheduled for tomorrow."
                                
                        elif 'today' in text_lower:
                            # Calculate today's date range
                            import datetime
                            today = datetime.datetime.now()
                            start_time = today.replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
                            end_time = today.replace(hour=23, minute=59, second=59, microsecond=999999).timestamp()
                            
                            events = await calendar_module._get_events_in_range(start_time, end_time)
                            
                            if events:
                                event_list = []
                                for event in events:
                                    event_time = time.strftime('%I:%M %p', time.localtime(event['start_time']))
                                    event_list.append(f"• {event['title']} at {event_time}")
                                
                                return f"You have {len(events)} meeting{'s' if len(events) != 1 else ''} today:\n" + "\n".join(event_list)
                            else:
                                return "You don't have any meetings scheduled for today."
                        else:
                            return "I can check your calendar for today or tomorrow. Try asking 'Do I have meetings tomorrow?' or 'What's on my schedule today?'"
                            
                    except Exception as e:
                        return f"I had trouble checking your calendar: {e}"
                
                # Fallback if calendar module not accessible
                if 'tomorrow' in text_lower:
                    return "Let me check your calendar for tomorrow... I don't see any scheduled meetings for tomorrow yet. Would you like to schedule something?"
                elif 'today' in text_lower:
                    return "Checking your calendar for today... You don't have any meetings scheduled for today."
                else:
                    return "I can help you check your calendar or schedule new meetings. Try asking 'Do I have meetings tomorrow?' or 'Schedule meeting at 2pm'."
                
            return None
            
        except Exception as e:
            return f"Sorry, I had trouble checking your calendar: {e}"
    
    async def _handle_schedule_request(self, text: str) -> Optional[str]:
        """Handle scheduling requests and actually create calendar events"""
        try:
            text_lower = text.lower().strip()
            
            # Scheduling keywords  
            schedule_keywords = [
                'schedule', 'add meeting', 'book appointment', 'create event',
                'set up meeting', 'plan meeting', 'add event', 'book meeting',
                'schedule meeting', 'add appointment', 'create meeting'
            ]
            
            # Check if this is a scheduling request
            is_schedule_request = any(keyword in text_lower for keyword in schedule_keywords)
            
            if is_schedule_request:
                # Get the calendar module from plugin manager
                calendar_module = None
                if hasattr(self, 'event_bus') and self.event_bus and hasattr(self.event_bus, 'subscribers'):
                    # Try to find calendar module through event bus subscribers
                    for event_type, subscribers in self.event_bus.subscribers.items():
                        for subscriber in subscribers:
                            if hasattr(subscriber, 'name') and subscriber.name == 'calendar':
                                calendar_module = subscriber
                                break
                        if calendar_module:
                            break
                
                # If we found the calendar module, use it to create the event
                if calendar_module and hasattr(calendar_module, 'handle_natural_language'):
                    result = await calendar_module.handle_natural_language(text)
                    
                    if result.get('success') and result.get('event_created'):
                        event = result.get('event', {})
                        return f"✅ Successfully scheduled: {event.get('title')} for {event.get('start_time')}. You'll get a reminder {event.get('reminder', '15 minutes before')}."
                    else:
                        return f"I understood you want to schedule something, but I need more details. Try: 'Schedule team meeting tomorrow at 2pm'"
                
                # Fallback if calendar module not accessible
                return "I can help you schedule events! Try saying: 'Schedule meeting tomorrow at 2pm' or 'Add appointment Friday at 10am'"
                
            return None
            
        except Exception as e:
            return f"Sorry, I had trouble with scheduling: {e}"
    
    async def _initialize_enhanced_nlp(self):
        """Initialize enhanced NLP components"""
        try:
            # Initialize intent analyzer
            self.intent_analyzer = IntentAnalyzer(logger=self.logger)
            self.log("Enhanced intent analyzer initialized")
            
            # Initialize semantic matcher
            self.semantic_matcher = SemanticMatcher(logger=self.logger)
            self.log("Semantic matcher initialized")
            
        except Exception as e:
            self.log(f"Failed to initialize enhanced NLP components: {e}", "warning")
            self.intent_analyzer = None
            self.semantic_matcher = None
    
    async def _analyze_intent_basic(self, text: str) -> Dict[str, Any]:
        """Basic fallback intent analysis"""
        text_lower = text.lower().strip()
        
        # Define basic intent patterns
        intent_patterns = {
            'greeting': ['hello', 'hi', 'hey', 'good morning', 'good afternoon', 'good evening'],
            'goodbye': ['bye', 'goodbye', 'see you', 'farewell', 'exit', 'quit'],
            'question': ['what', 'how', 'why', 'when', 'where', 'who', 'which'],
            'schedule_meeting': ['schedule', 'book', 'add meeting', 'create meeting'],
            'check_calendar': ['do i have', 'what meetings', 'my calendar', 'my schedule'],
            'time': ['time', 'date', 'today', 'tomorrow', 'yesterday'],
        }
        
        # Calculate confidence scores
        intent_scores = {}
        for intent, patterns in intent_patterns.items():
            score = 0
            for pattern in patterns:
                if pattern in text_lower:
                    score += 1
                    
            if score > 0:
                intent_scores[intent] = score / len(patterns)
                
        # Find best intent
        if intent_scores:
            best_intent = max(intent_scores, key=intent_scores.get)
            confidence = intent_scores[best_intent]
            
            return {
                'intent': best_intent,
                'confidence': confidence,
                'all_scores': intent_scores,
                'threshold_met': confidence >= self.confidence_threshold
            }
        else:
            return {
                'intent': 'unknown',
                'confidence': 0.0,
                'all_scores': {},
                'threshold_met': False
            }