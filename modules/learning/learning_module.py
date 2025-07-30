"""
Learning Module - Adaptive learning and optimization system for SAGE
"""

import asyncio
import json
import sqlite3
import time
import hashlib
import logging
from typing import Dict, Any, Optional, List, Tuple, Set
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from collections import defaultdict, Counter
import threading

from modules import BaseModule, EventType, Event

# Try to import ML libraries
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    np = None
    NUMPY_AVAILABLE = False

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.cluster import KMeans
    from sklearn.metrics.pairwise import cosine_similarity
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False


@dataclass
class UserInteraction:
    """Data class for user interactions"""
    timestamp: float
    user_input: str
    intent: str
    intent_confidence: float
    response: str
    success: bool
    feedback_score: Optional[float] = None
    response_time: float = 0.0
    source_module: str = "unknown"
    context: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.context is None:
            self.context = {}


@dataclass
class UserPreference:
    """Data class for user preferences"""
    preference_id: str
    category: str
    key: str
    value: Any
    confidence: float
    last_updated: float
    usage_count: int = 0
    source: str = "learned"


@dataclass
class CommandPattern:
    """Data class for command patterns"""
    pattern_id: str
    command_type: str
    pattern: str
    frequency: int
    success_rate: float
    average_response_time: float
    last_used: float
    optimizations: List[str] = None
    
    def __post_init__(self):
        if self.optimizations is None:
            self.optimizations = []


@dataclass
class MistakeRecord:
    """Data class for mistake tracking"""
    mistake_id: str
    error_type: str
    original_input: str
    expected_output: str
    actual_output: str
    correction: str
    timestamp: float
    corrected: bool = False
    correction_success: bool = False


class LearningModule(BaseModule):
    """Adaptive learning system for SAGE"""
    
    def __init__(self, name: str = "learning"):
        super().__init__(name)
        
        # Configuration will be loaded from config
        self.enabled = True
        self.command_optimization = True
        self.mistake_learning = True
        self.preference_tracking = True
        self.anonymize_data = True
        self.local_only = True
        self.database_type = "sqlite"
        self.retention_days = 90
        
        # Database and storage
        self.db_path = Path("data/learning.db")
        self.db_connection = None
        self.db_lock = threading.Lock()
        
        # In-memory caches for performance
        self.interactions_cache = []
        self.preferences_cache = {}
        self.patterns_cache = {}
        self.mistakes_cache = {}
        self._pending_interactions = {}  # For correlating events
        
        # Learning engines
        self.preference_engine = None
        self.pattern_engine = None
        self.mistake_engine = None
        self.optimization_engine = None
        
        # ML components
        self.vectorizer = None
        self.clusterer = None
        
        # Statistics and metrics
        self.stats = {
            'total_interactions': 0,
            'preferences_learned': 0,
            'patterns_identified': 0,
            'mistakes_corrected': 0,
            'optimizations_applied': 0,
            'learning_accuracy': 0.0,
            'prediction_accuracy': 0.0,
            'cache_hit_rate': 0.0,
            'data_points_processed': 0,
            'learning_sessions': 0,
            'user_satisfaction_score': 0.0
        }
        
        # Event subscriptions
        self.subscribed_events = [
            EventType.VOICE_COMMAND,
            EventType.INTENT_PARSED,
            EventType.LLM_RESPONSE,
            EventType.ERROR_OCCURRED
        ]
        
    async def initialize(self) -> bool:
        """Initialize the learning module"""
        try:
            self.log("Initializing learning module...")
            
            # Load configuration
            self._load_config()
            
            if not self.enabled:
                self.log("Learning module disabled")
                return True
                
            # Initialize database
            await self._initialize_database()
            
            # Load cached data
            await self._load_cached_data()
            
            # Initialize learning engines
            await self._initialize_learning_engines()
            
            # Initialize ML components if available
            if SKLEARN_AVAILABLE and NUMPY_AVAILABLE:
                await self._initialize_ml_components()
                
            # Subscribe to events
            self.subscribe_events(self.subscribed_events)
            
            self.is_initialized = True
            self.is_loaded = True
            self.log("Learning module initialized successfully")
            return True
            
        except Exception as e:
            self.log(f"Failed to initialize learning module: {e}", "error")
            return False
            
    async def shutdown(self):
        """Shutdown the learning module"""
        try:
            self.log("Shutting down learning module...")
            
            # Save cached data
            await self._save_cached_data()
            
            # Close database connection
            if self.db_connection:
                with self.db_lock:
                    self.db_connection.close()
                    
            self.is_initialized = False
            self.is_loaded = False
            self.log("Learning module shutdown complete")
            
        except Exception as e:
            self.log(f"Error during learning module shutdown: {e}", "error")
            
    async def handle_event(self, event: Event) -> Optional[Any]:
        """Handle events from other modules"""
        try:
            if not self.is_initialized or not self.enabled:
                return None
                
            if event.type == EventType.VOICE_COMMAND:
                return await self._handle_voice_command(event)
            elif event.type == EventType.INTENT_PARSED:
                return await self._handle_intent_parsed(event)
            elif event.type == EventType.LLM_RESPONSE:
                return await self._handle_llm_response(event)
            elif event.type == EventType.ERROR_OCCURRED:
                return await self._handle_system_error(event)
            else:
                self.log(f"Unhandled event type: {event.type}", "warning")
                return None
                
        except Exception as e:
            self.log(f"Error handling event {event.type}: {e}", "error")
            return None
            
    async def learn_from_interaction(self, interaction: UserInteraction) -> Dict[str, Any]:
        """Learn from a user interaction"""
        try:
            if not self.enabled:
                return {'success': False, 'reason': 'Learning disabled'}
                
            # Anonymize data if configured
            if self.anonymize_data:
                interaction = self._anonymize_interaction(interaction)
                
            # Store interaction
            await self._store_interaction(interaction)
            
            # Update statistics
            self.stats['total_interactions'] += 1
            self.stats['data_points_processed'] += 1
            
            learning_results = {}
            
            # Learn user preferences
            if self.preference_tracking:
                pref_results = await self._learn_preferences(interaction)
                learning_results['preferences'] = pref_results
                
            # Learn command patterns
            if self.command_optimization:
                pattern_results = await self._learn_patterns(interaction)
                learning_results['patterns'] = pattern_results
                
            # Learn from mistakes if applicable
            if self.mistake_learning and not interaction.success:
                mistake_results = await self._learn_from_mistake(interaction)
                learning_results['mistakes'] = mistake_results
                
            # Apply optimizations
            optimization_results = await self._apply_optimizations(interaction)
            learning_results['optimizations'] = optimization_results
            
            return {
                'success': True,
                'interaction_id': self._generate_interaction_id(interaction),
                'learning_results': learning_results,
                'stats_updated': True
            }
            
        except Exception as e:
            self.log(f"Error learning from interaction: {e}", "error")
            return {'success': False, 'error': str(e)}
            
    async def get_user_preferences(self, category: Optional[str] = None) -> Dict[str, Any]:
        """Get learned user preferences"""
        try:
            if category:
                return {k: v for k, v in self.preferences_cache.items() 
                       if v.category == category}
            else:
                return {k: asdict(v) for k, v in self.preferences_cache.items()}
                
        except Exception as e:
            self.log(f"Error getting user preferences: {e}", "error")
            return {}
            
    async def predict_user_intent(self, user_input: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Predict user intent based on learned patterns"""
        try:
            if not self.enabled or not self.patterns_cache:
                return {'intent': 'unknown', 'confidence': 0.0, 'source': 'no_learning'}
                
            # Simple pattern matching for now
            input_lower = user_input.lower()
            best_match = None
            best_score = 0.0
            
            for pattern_id, pattern in self.patterns_cache.items():
                # Calculate similarity score
                pattern_words = set(pattern.pattern.lower().split())
                input_words = set(input_lower.split())
                
                if pattern_words and input_words:
                    intersection = len(pattern_words.intersection(input_words))
                    union = len(pattern_words.union(input_words))
                    similarity = intersection / union if union > 0 else 0.0
                    
                    # Weight by frequency and success rate
                    score = similarity * (pattern.frequency / 100) * pattern.success_rate
                    
                    if score > best_score:
                        best_score = score
                        best_match = pattern
                        
            if best_match and best_score > 0.3:
                return {
                    'intent': best_match.command_type,
                    'confidence': best_score,
                    'source': 'learned_patterns',
                    'pattern_id': best_match.pattern_id,
                    'usage_frequency': best_match.frequency
                }
            else:
                return {'intent': 'unknown', 'confidence': 0.0, 'source': 'no_match'}
                
        except Exception as e:
            self.log(f"Error predicting user intent: {e}", "error")
            return {'intent': 'error', 'confidence': 0.0, 'source': 'error'}
            
    async def get_command_optimizations(self, command_type: str) -> List[str]:
        """Get optimizations for a specific command type"""
        try:
            optimizations = []
            
            for pattern in self.patterns_cache.values():
                if pattern.command_type == command_type:
                    optimizations.extend(pattern.optimizations)
                    
            return list(set(optimizations))  # Remove duplicates
            
        except Exception as e:
            self.log(f"Error getting command optimizations: {e}", "error")
            return []
            
    async def provide_feedback(self, interaction_id: str, feedback_score: float, 
                             feedback_text: Optional[str] = None) -> bool:
        """Provide feedback on an interaction"""
        try:
            # Find interaction in cache or database
            for interaction in self.interactions_cache:
                if self._generate_interaction_id(interaction) == interaction_id:
                    interaction.feedback_score = feedback_score
                    
                    # Update learning based on feedback
                    if feedback_score < 0.5:  # Negative feedback
                        await self._handle_negative_feedback(interaction, feedback_text)
                    elif feedback_score > 0.8:  # Positive feedback
                        await self._handle_positive_feedback(interaction)
                        
                    # Update user satisfaction score
                    self._update_satisfaction_score(feedback_score)
                    
                    self.log(f"Feedback received for interaction {interaction_id}: {feedback_score}")
                    return True
                    
            self.log(f"Interaction {interaction_id} not found for feedback", "warning")
            return False
            
        except Exception as e:
            self.log(f"Error providing feedback: {e}", "error")
            return False
            
    def get_learning_insights(self) -> Dict[str, Any]:
        """Get insights from the learning system"""
        try:
            insights = {
                'statistics': self.stats.copy(),
                'top_patterns': self._get_top_patterns(),
                'preference_categories': self._get_preference_categories(),
                'common_mistakes': self._get_common_mistakes(),
                'optimization_suggestions': self._get_optimization_suggestions(),
                'learning_trends': self._get_learning_trends(),
                'user_behavior_analysis': self._analyze_user_behavior()
            }
            
            return insights
            
        except Exception as e:
            self.log(f"Error getting learning insights: {e}", "error")
            return {'error': str(e)}
            
    def get_status(self) -> Dict[str, Any]:
        """Get learning module status"""
        return {
            'initialized': self.is_initialized,
            'enabled': self.enabled,
            'command_optimization': self.command_optimization,
            'mistake_learning': self.mistake_learning,
            'preference_tracking': self.preference_tracking,
            'anonymize_data': self.anonymize_data,
            'local_only': self.local_only,
            'database_type': self.database_type,
            'retention_days': self.retention_days,
            'cache_sizes': {
                'interactions': len(self.interactions_cache),
                'preferences': len(self.preferences_cache),
                'patterns': len(self.patterns_cache),
                'mistakes': len(self.mistakes_cache)
            },
            'dependencies': {
                'numpy': NUMPY_AVAILABLE,
                'sklearn': SKLEARN_AVAILABLE
            },
            'statistics': self.stats.copy()
        }
        
    # Private helper methods
    def _load_config(self):
        """Load configuration from module config"""
        if self.config:
            self.enabled = self.config.get('enabled', True)
            self.command_optimization = self.config.get('command_optimization', True)
            self.mistake_learning = self.config.get('mistake_learning', True)
            self.preference_tracking = self.config.get('preference_tracking', True)
            
            # Privacy settings
            privacy_config = self.config.get('privacy', {})
            self.anonymize_data = privacy_config.get('anonymize_data', True)
            self.local_only = privacy_config.get('local_only', True)
            
            # Storage settings
            storage_config = self.config.get('storage', {})
            self.database_type = storage_config.get('database', 'sqlite')
            self.retention_days = storage_config.get('retention_days', 90)
            
    async def _initialize_database(self):
        """Initialize the learning database"""
        try:
            # Create data directory
            self.db_path.parent.mkdir(exist_ok=True)
            
            # Initialize SQLite database
            with self.db_lock:
                self.db_connection = sqlite3.connect(str(self.db_path), check_same_thread=False)
                self.db_connection.row_factory = sqlite3.Row
                
                # Create tables
                await self._create_database_tables()
                
            self.log("Learning database initialized")
            
        except Exception as e:
            self.log(f"Error initializing database: {e}", "error")
            raise
            
    async def _create_database_tables(self):
        """Create database tables for learning data"""
        tables = {
            'interactions': '''
                CREATE TABLE IF NOT EXISTS interactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    interaction_id TEXT UNIQUE,
                    timestamp REAL,
                    user_input TEXT,
                    intent TEXT,
                    intent_confidence REAL,
                    response TEXT,
                    success BOOLEAN,
                    feedback_score REAL,
                    response_time REAL,
                    source_module TEXT,
                    context TEXT,
                    anonymized BOOLEAN DEFAULT FALSE
                )
            ''',
            'preferences': '''
                CREATE TABLE IF NOT EXISTS preferences (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    preference_id TEXT UNIQUE,
                    category TEXT,
                    key TEXT,
                    value TEXT,
                    confidence REAL,
                    last_updated REAL,
                    usage_count INTEGER DEFAULT 0,
                    source TEXT DEFAULT 'learned'
                )
            ''',
            'patterns': '''
                CREATE TABLE IF NOT EXISTS patterns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pattern_id TEXT UNIQUE,
                    command_type TEXT,
                    pattern TEXT,
                    frequency INTEGER DEFAULT 1,
                    success_rate REAL DEFAULT 1.0,
                    average_response_time REAL DEFAULT 0.0,
                    last_used REAL,
                    optimizations TEXT
                )
            ''',
            'mistakes': '''
                CREATE TABLE IF NOT EXISTS mistakes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    mistake_id TEXT UNIQUE,
                    error_type TEXT,
                    original_input TEXT,
                    expected_output TEXT,
                    actual_output TEXT,
                    correction TEXT,
                    timestamp REAL,
                    corrected BOOLEAN DEFAULT FALSE,
                    correction_success BOOLEAN DEFAULT FALSE
                )
            '''
        }
        
        cursor = self.db_connection.cursor()
        for table_name, table_sql in tables.items():
            cursor.execute(table_sql)
            
        # Create indexes for better performance
        indexes = [
            'CREATE INDEX IF NOT EXISTS idx_interactions_timestamp ON interactions(timestamp)',
            'CREATE INDEX IF NOT EXISTS idx_preferences_category ON preferences(category)',
            'CREATE INDEX IF NOT EXISTS idx_patterns_command_type ON patterns(command_type)',
            'CREATE INDEX IF NOT EXISTS idx_mistakes_error_type ON mistakes(error_type)'
        ]
        
        for index_sql in indexes:
            cursor.execute(index_sql)
            
        self.db_connection.commit()
        
    async def _load_cached_data(self):
        """Load frequently used data into memory caches"""
        try:
            with self.db_lock:
                cursor = self.db_connection.cursor()
                
                # Load recent interactions
                cursor.execute('''
                    SELECT * FROM interactions 
                    ORDER BY timestamp DESC 
                    LIMIT 1000
                ''')
                
                for row in cursor.fetchall():
                    interaction = UserInteraction(
                        timestamp=row['timestamp'],
                        user_input=row['user_input'],
                        intent=row['intent'],
                        intent_confidence=row['intent_confidence'],
                        response=row['response'],
                        success=bool(row['success']),
                        feedback_score=row['feedback_score'],
                        response_time=row['response_time'],
                        source_module=row['source_module'],
                        context=json.loads(row['context']) if row['context'] else {}
                    )
                    self.interactions_cache.append(interaction)
                    
                # Load preferences
                cursor.execute('SELECT * FROM preferences')
                for row in cursor.fetchall():
                    pref = UserPreference(
                        preference_id=row['preference_id'],
                        category=row['category'],
                        key=row['key'],
                        value=json.loads(row['value']),
                        confidence=row['confidence'],
                        last_updated=row['last_updated'],
                        usage_count=row['usage_count'],
                        source=row['source']
                    )
                    self.preferences_cache[row['preference_id']] = pref
                    
                # Load patterns
                cursor.execute('SELECT * FROM patterns')
                for row in cursor.fetchall():
                    pattern = CommandPattern(
                        pattern_id=row['pattern_id'],
                        command_type=row['command_type'],
                        pattern=row['pattern'],
                        frequency=row['frequency'],
                        success_rate=row['success_rate'],
                        average_response_time=row['average_response_time'],
                        last_used=row['last_used'],
                        optimizations=json.loads(row['optimizations']) if row['optimizations'] else []
                    )
                    self.patterns_cache[row['pattern_id']] = pattern
                    
                # Load mistakes
                cursor.execute('SELECT * FROM mistakes ORDER BY timestamp DESC LIMIT 500')
                for row in cursor.fetchall():
                    mistake = MistakeRecord(
                        mistake_id=row['mistake_id'],
                        error_type=row['error_type'],
                        original_input=row['original_input'],
                        expected_output=row['expected_output'],
                        actual_output=row['actual_output'],
                        correction=row['correction'],
                        timestamp=row['timestamp'],
                        corrected=bool(row['corrected']),
                        correction_success=bool(row['correction_success'])
                    )
                    self.mistakes_cache[row['mistake_id']] = mistake
                    
            self.log(f"Loaded cached data: {len(self.interactions_cache)} interactions, "
                    f"{len(self.preferences_cache)} preferences, {len(self.patterns_cache)} patterns, "
                    f"{len(self.mistakes_cache)} mistakes")
                    
        except Exception as e:
            self.log(f"Error loading cached data: {e}", "error")
            
    async def _save_cached_data(self):
        """Save cached data to database"""
        try:
            with self.db_lock:
                cursor = self.db_connection.cursor()
                
                # Save interactions (only new ones not in DB)
                for interaction in self.interactions_cache[-100:]:  # Save last 100 interactions
                    interaction_id = self._generate_interaction_id(interaction)
                    cursor.execute('''
                        INSERT OR REPLACE INTO interactions 
                        (interaction_id, timestamp, user_input, intent, intent_confidence, 
                         response, success, feedback_score, response_time, source_module, context, anonymized)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        interaction_id, interaction.timestamp, interaction.user_input,
                        interaction.intent, interaction.intent_confidence, interaction.response,
                        interaction.success, interaction.feedback_score, interaction.response_time,
                        interaction.source_module, json.dumps(interaction.context), self.anonymize_data
                    ))
                    
                # Save preferences
                for pref in self.preferences_cache.values():
                    cursor.execute('''
                        INSERT OR REPLACE INTO preferences 
                        (preference_id, category, key, value, confidence, last_updated, usage_count, source)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        pref.preference_id, pref.category, pref.key, json.dumps(pref.value),
                        pref.confidence, pref.last_updated, pref.usage_count, pref.source
                    ))
                    
                # Save patterns
                for pattern in self.patterns_cache.values():
                    cursor.execute('''
                        INSERT OR REPLACE INTO patterns 
                        (pattern_id, command_type, pattern, frequency, success_rate, 
                         average_response_time, last_used, optimizations)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        pattern.pattern_id, pattern.command_type, pattern.pattern,
                        pattern.frequency, pattern.success_rate, pattern.average_response_time,
                        pattern.last_used, json.dumps(pattern.optimizations)
                    ))
                    
                # Save mistakes
                for mistake in self.mistakes_cache.values():
                    cursor.execute('''
                        INSERT OR REPLACE INTO mistakes 
                        (mistake_id, error_type, original_input, expected_output, 
                         actual_output, correction, timestamp, corrected, correction_success)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        mistake.mistake_id, mistake.error_type, mistake.original_input,
                        mistake.expected_output, mistake.actual_output, mistake.correction,
                        mistake.timestamp, mistake.corrected, mistake.correction_success
                    ))
                    
                self.db_connection.commit()
                
            self.log("Cached data saved to database")
            
        except Exception as e:
            self.log(f"Error saving cached data: {e}", "error")
            
    async def _initialize_learning_engines(self):
        """Initialize learning engines"""
        self.preference_engine = PreferenceEngine(self)
        self.pattern_engine = PatternEngine(self)
        self.mistake_engine = MistakeEngine(self)
        self.optimization_engine = OptimizationEngine(self)
        
        self.log("Learning engines initialized")
        
    async def _initialize_ml_components(self):
        """Initialize machine learning components"""
        if not SKLEARN_AVAILABLE or not NUMPY_AVAILABLE:
            return
            
        try:
            # Initialize TF-IDF vectorizer for text analysis
            self.vectorizer = TfidfVectorizer(
                max_features=1000,
                stop_words='english',
                lowercase=True,
                ngram_range=(1, 2)
            )
            
            # Initialize clustering for pattern recognition
            self.clusterer = KMeans(n_clusters=10, random_state=42, n_init=10)
            
            self.log("ML components initialized")
            
        except Exception as e:
            self.log(f"Error initializing ML components: {e}", "error")
            
    def _generate_interaction_id(self, interaction: UserInteraction) -> str:
        """Generate unique ID for interaction"""
        data = f"{interaction.timestamp}_{interaction.user_input}_{interaction.source_module}"
        return hashlib.md5(data.encode()).hexdigest()[:16]
        
    def _anonymize_interaction(self, interaction: UserInteraction) -> UserInteraction:
        """Anonymize user interaction data"""
        if not self.anonymize_data:
            return interaction
            
        # Simple anonymization - replace personal info with placeholders
        anonymized_input = interaction.user_input
        anonymized_response = interaction.response
        
        # This is a basic implementation - in production, use proper anonymization
        import re
        
        # Remove potential personal information patterns
        patterns = [
            (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]'),
            (r'\b\d{3}-?\d{3}-?\d{4}\b', '[PHONE]'),
            (r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b', '[CARD]'),
            (r'\b[A-Z][a-z]+ [A-Z][a-z]+\b', '[NAME]')
        ]
        
        for pattern, replacement in patterns:
            anonymized_input = re.sub(pattern, replacement, anonymized_input)
            anonymized_response = re.sub(pattern, replacement, anonymized_response)
            
        # Create new interaction with anonymized data
        return UserInteraction(
            timestamp=interaction.timestamp,
            user_input=anonymized_input,
            intent=interaction.intent,
            intent_confidence=interaction.intent_confidence,
            response=anonymized_response,
            success=interaction.success,
            feedback_score=interaction.feedback_score,
            response_time=interaction.response_time,
            source_module=interaction.source_module,
            context=interaction.context.copy()
        )
        
    async def _store_interaction(self, interaction: UserInteraction):
        """Store interaction in cache and database"""
        self.interactions_cache.append(interaction)
        
        # Keep cache size manageable
        if len(self.interactions_cache) > 2000:
            self.interactions_cache = self.interactions_cache[-1000:]
            
    # Event handlers
    async def _handle_voice_command(self, event: Event) -> Optional[Any]:
        """Handle voice command events"""
        try:
            command = event.data.get('command', '')
            confidence = event.data.get('confidence', 0.0)
            
            # Create interaction record
            interaction = UserInteraction(
                timestamp=event.timestamp,
                user_input=command,
                intent='voice_command',
                intent_confidence=confidence,
                response='',  # Will be filled by LLM response
                success=True,  # Assume success until proven otherwise
                source_module='voice'
            )
            
            # Store for later correlation with response
            self._pending_interactions[event.timestamp] = interaction
            
            return None
            
        except Exception as e:
            self.log(f"Error handling voice command: {e}", "error")
            return None
            
    async def _handle_intent_parsed(self, event: Event) -> Optional[Any]:
        """Handle intent parsed events"""
        try:
            text = event.data.get('text', '')
            intent = event.data.get('intent', 'unknown')
            confidence = event.data.get('confidence', 0.0)
            source = event.data.get('source', 'unknown')
            
            # Update pending interaction or create new one
            interaction = None
            for pending_interaction in self._pending_interactions.values():
                if pending_interaction.user_input == text:
                    pending_interaction.intent = intent
                    pending_interaction.intent_confidence = confidence
                    interaction = pending_interaction
                    break
                    
            if not interaction:
                interaction = UserInteraction(
                    timestamp=event.timestamp,
                    user_input=text,
                    intent=intent,
                    intent_confidence=confidence,
                    response='',
                    success=True,
                    source_module=source
                )
                self._pending_interactions[event.timestamp] = interaction
                
            return None
            
        except Exception as e:
            self.log(f"Error handling intent parsed: {e}", "error")
            return None
            
    async def _handle_llm_response(self, event: Event) -> Optional[Any]:
        """Handle LLM response events"""
        try:
            original_text = event.data.get('original_text', '')
            response = event.data.get('response', {})
            response_text = response.get('text', '') if isinstance(response, dict) else str(response)
            processing_time = event.data.get('processing_time', 0.0)
            intent = event.data.get('intent', 'unknown')
            
            # Find matching pending interaction
            interaction = None
            for timestamp, pending_interaction in list(self._pending_interactions.items()):
                if pending_interaction.user_input == original_text:
                    pending_interaction.response = response_text
                    pending_interaction.response_time = processing_time
                    pending_interaction.intent = intent
                    interaction = pending_interaction
                    del self._pending_interactions[timestamp]
                    break
                    
            if not interaction:
                # Create new interaction if not found
                interaction = UserInteraction(
                    timestamp=event.timestamp,
                    user_input=original_text,
                    intent=intent,
                    intent_confidence=0.0,
                    response=response_text,
                    success=True,
                    response_time=processing_time,
                    source_module='nlp'
                )
                
            # Learn from this interaction
            await self.learn_from_interaction(interaction)
            
            return None
            
        except Exception as e:
            self.log(f"Error handling LLM response: {e}", "error")
            return None
            
    async def _handle_system_error(self, event: Event) -> Optional[Any]:
        """Handle system error events"""
        try:
            error = event.data.get('error', '')
            component = event.data.get('component', 'unknown')
            
            # Create mistake record
            mistake = MistakeRecord(
                mistake_id=self._generate_mistake_id(error, component),
                error_type=component,
                original_input=event.data.get('original_input', ''),
                expected_output='success',
                actual_output=f'error: {error}',
                correction='',
                timestamp=event.timestamp,
                corrected=False
            )
            
            self.mistakes_cache[mistake.mistake_id] = mistake
            self.stats['mistakes_corrected'] += 1
            
            # Try to learn from this error
            if self.mistake_learning:
                await self._learn_from_error(mistake)
                
            return None
            
        except Exception as e:
            self.log(f"Error handling system error: {e}", "error")
            return None
            
    # Learning methods
    async def _learn_preferences(self, interaction: UserInteraction) -> Dict[str, Any]:
        """Learn user preferences from interaction"""
        if self.preference_engine:
            return await self.preference_engine.learn_from_interaction(interaction)
        return {'learned': False, 'reason': 'No preference engine'}
        
    async def _learn_patterns(self, interaction: UserInteraction) -> Dict[str, Any]:
        """Learn command patterns from interaction"""
        if self.pattern_engine:
            return await self.pattern_engine.learn_from_interaction(interaction)
        return {'learned': False, 'reason': 'No pattern engine'}
        
    async def _learn_from_mistake(self, interaction: UserInteraction) -> Dict[str, Any]:
        """Learn from interaction mistakes"""
        if self.mistake_engine:
            return await self.mistake_engine.learn_from_interaction(interaction)
        return {'learned': False, 'reason': 'No mistake engine'}
        
    async def _apply_optimizations(self, interaction: UserInteraction) -> Dict[str, Any]:
        """Apply learned optimizations"""
        if self.optimization_engine:
            return await self.optimization_engine.apply_optimizations(interaction)
        return {'applied': False, 'reason': 'No optimization engine'}
        
    async def _handle_negative_feedback(self, interaction: UserInteraction, feedback_text: Optional[str]):
        """Handle negative feedback"""
        # Create mistake record for negative feedback
        mistake = MistakeRecord(
            mistake_id=self._generate_mistake_id(interaction.user_input, 'negative_feedback'),
            error_type='negative_feedback',
            original_input=interaction.user_input,
            expected_output=feedback_text or 'better_response',
            actual_output=interaction.response,
            correction='',
            timestamp=time.time(),
            corrected=False
        )
        
        self.mistakes_cache[mistake.mistake_id] = mistake
        
    async def _handle_positive_feedback(self, interaction: UserInteraction):
        """Handle positive feedback"""
        # Reinforce successful patterns
        if interaction.intent != 'unknown':
            pattern_id = f"{interaction.intent}_{hashlib.md5(interaction.user_input.encode()).hexdigest()[:8]}"
            
            if pattern_id in self.patterns_cache:
                pattern = self.patterns_cache[pattern_id]
                pattern.frequency += 1
                pattern.success_rate = min(1.0, pattern.success_rate + 0.1)
            else:
                pattern = CommandPattern(
                    pattern_id=pattern_id,
                    command_type=interaction.intent,
                    pattern=interaction.user_input,
                    frequency=1,
                    success_rate=1.0,
                    average_response_time=interaction.response_time,
                    last_used=interaction.timestamp
                )
                self.patterns_cache[pattern_id] = pattern
                
    async def _learn_from_error(self, mistake: MistakeRecord):
        """Learn from system errors"""
        # Implement error learning logic
        self.log(f"Learning from error: {mistake.error_type}")
        
    def _generate_mistake_id(self, input_text: str, error_type: str) -> str:
        """Generate unique ID for mistake"""
        data = f"{input_text}_{error_type}_{time.time()}"
        return hashlib.md5(data.encode()).hexdigest()[:16]
        
    def _update_satisfaction_score(self, feedback_score: float):
        """Update user satisfaction score"""
        current_score = self.stats['user_satisfaction_score']
        total_interactions = max(1, self.stats['total_interactions'])
        
        # Calculate running average
        self.stats['user_satisfaction_score'] = (
            (current_score * (total_interactions - 1) + feedback_score) / total_interactions
        )
        
    def _get_top_patterns(self) -> List[Dict[str, Any]]:
        """Get top command patterns"""
        patterns = sorted(
            self.patterns_cache.values(),
            key=lambda p: p.frequency * p.success_rate,
            reverse=True
        )
        
        return [asdict(p) for p in patterns[:10]]
        
    def _get_top_patterns(self) -> List[Dict[str, Any]]:
        """Get top command patterns by frequency"""
        top_patterns = sorted(
            self.patterns_cache.values(),
            key=lambda p: p.frequency,
            reverse=True
        )[:10]
        
        return [
            {
                'pattern': pattern.pattern,
                'command_type': pattern.command_type,
                'frequency': pattern.frequency,
                'success_rate': pattern.success_rate,
                'avg_response_time': pattern.average_response_time
            }
            for pattern in top_patterns
        ]
    
    def _get_preference_categories(self) -> Dict[str, int]:
        """Get count of preferences by category"""
        categories = defaultdict(int)
        for pref in self.preferences_cache.values():
            categories[pref.category] += 1
        return dict(categories)
        
    def _get_common_mistakes(self) -> List[Dict[str, Any]]:
        """Get most common mistakes"""
        mistake_types = Counter(m.error_type for m in self.mistakes_cache.values())
        return [{'error_type': k, 'count': v} for k, v in mistake_types.most_common(10)]
        
    def _get_optimization_suggestions(self) -> List[str]:
        """Get optimization suggestions"""
        suggestions = []
        
        # Analyze patterns for optimization opportunities
        for pattern in self.patterns_cache.values():
            if pattern.success_rate < 0.8:
                suggestions.append(f"Improve success rate for {pattern.command_type} commands")
            if pattern.average_response_time > 2.0:
                suggestions.append(f"Optimize response time for {pattern.command_type} commands")
                
        return list(set(suggestions))[:5]
        
    def _get_learning_trends(self) -> Dict[str, Any]:
        """Get learning trends"""
        try:
            current_time = time.time()
            recent_interactions = []
            
            for i in self.interactions_cache:
                # Handle both UserInteraction objects and cached interactions
                timestamp = i.timestamp if hasattr(i, 'timestamp') else float(i.get('timestamp', 0))
                if timestamp > current_time - 86400:  # Last 24h
                    recent_interactions.append(i)
        
            return {
                'interactions_last_24h': len(recent_interactions),
                'average_intent_confidence': np.mean([
                    i.intent_confidence if hasattr(i, 'intent_confidence') else float(i.get('intent_confidence', 0.0))
                    for i in recent_interactions
                ]) if recent_interactions and NUMPY_AVAILABLE else 0.0,
                'success_rate_last_24h': np.mean([
                    1.0 if (i.success if hasattr(i, 'success') else i.get('success', False)) else 0.0
                    for i in recent_interactions
                ]) if recent_interactions and NUMPY_AVAILABLE else 0.0
            }
        except Exception as e:
            return {
                'interactions_last_24h': 0,
                'average_intent_confidence': 0.0,
                'success_rate_last_24h': 0.0,
                'error': str(e)
            }
        
    def _analyze_user_behavior(self) -> Dict[str, Any]:
        """Analyze user behavior patterns"""
        try:
            if not self.interactions_cache:
                return {'analysis': 'No data available'}
                
            # Most common intents
            intents = Counter(
                i.intent if hasattr(i, 'intent') else i.get('intent', 'unknown')
                for i in self.interactions_cache
            )
            
            # Most active hours
            hours = Counter(
                datetime.fromtimestamp(
                    i.timestamp if hasattr(i, 'timestamp') else float(i.get('timestamp', 0))
                ).hour for i in self.interactions_cache
            )
            
            return {
                'most_common_intents': dict(intents.most_common(5)),
                'most_active_hours': dict(hours.most_common(5)),
                'total_sessions': len(set(
                    int((i.timestamp if hasattr(i, 'timestamp') else float(i.get('timestamp', 0))) // 3600)
                    for i in self.interactions_cache
                ))  # Rough session count
            }
        except Exception as e:
            return {
                'analysis': 'Error analyzing user behavior',
                'error': str(e)
            }


# Learning engine classes
class PreferenceEngine:
    """Engine for learning user preferences"""
    
    def __init__(self, learning_module):
        self.learning_module = learning_module
        self.preference_patterns = {
            'time_preferences': ['morning', 'afternoon', 'evening', 'night'],
            'communication_style': ['formal', 'casual', 'brief', 'detailed'],
            'response_length': ['short', 'medium', 'long'],
            'topic_interests': []
        }
        
    async def learn_from_interaction(self, interaction: UserInteraction) -> Dict[str, Any]:
        """Learn preferences from user interaction"""
        try:
            learned_prefs = []
            
            # Learn time preferences
            hour = datetime.fromtimestamp(interaction.timestamp).hour
            time_category = self._get_time_category(hour)
            
            pref_id = f"time_preference_{time_category}"
            if pref_id in self.learning_module.preferences_cache:
                pref = self.learning_module.preferences_cache[pref_id]
                pref.usage_count += 1
                pref.confidence = min(1.0, pref.confidence + 0.05)
                pref.last_updated = time.time()
            else:
                pref = UserPreference(
                    preference_id=pref_id,
                    category='time_preference',
                    key=time_category,
                    value=hour,
                    confidence=0.1,
                    last_updated=time.time(),
                    usage_count=1
                )
                self.learning_module.preferences_cache[pref_id] = pref
                
            learned_prefs.append(pref_id)
            
            # Learn communication style from response length
            response_length = len(interaction.response.split()) if interaction.response else 0
            style = 'brief' if response_length < 20 else 'detailed' if response_length > 100 else 'medium'
            
            pref_id = f"communication_style_{style}"
            if pref_id in self.learning_module.preferences_cache:
                pref = self.learning_module.preferences_cache[pref_id]
                pref.usage_count += 1
                pref.confidence = min(1.0, pref.confidence + 0.03)
            else:
                pref = UserPreference(
                    preference_id=pref_id,
                    category='communication_style',
                    key='response_length',
                    value=style,
                    confidence=0.1,
                    last_updated=time.time(),
                    usage_count=1
                )
                self.learning_module.preferences_cache[pref_id] = pref
                
            learned_prefs.append(pref_id)
            
            # Learn topic interests from intent
            if interaction.intent not in ['unknown', 'error']:
                pref_id = f"topic_interest_{interaction.intent}"
                if pref_id in self.learning_module.preferences_cache:
                    pref = self.learning_module.preferences_cache[pref_id]
                    pref.usage_count += 1
                    pref.confidence = min(1.0, pref.confidence + 0.02)
                else:
                    pref = UserPreference(
                        preference_id=pref_id,
                        category='topic_interest',
                        key='intent',
                        value=interaction.intent,
                        confidence=0.1,
                        last_updated=time.time(),
                        usage_count=1
                    )
                    self.learning_module.preferences_cache[pref_id] = pref
                    
                learned_prefs.append(pref_id)
                
            self.learning_module.stats['preferences_learned'] += len(learned_prefs)
            
            return {
                'learned': True,
                'preferences_updated': learned_prefs,
                'total_preferences': len(self.learning_module.preferences_cache)
            }
            
        except Exception as e:
            self.learning_module.log(f"Error learning preferences: {e}", "error")
            return {'learned': False, 'error': str(e)}
            
    def _get_time_category(self, hour: int) -> str:
        """Get time category from hour"""
        if 6 <= hour < 12:
            return 'morning'
        elif 12 <= hour < 17:
            return 'afternoon'
        elif 17 <= hour < 21:
            return 'evening'
        else:
            return 'night'


class PatternEngine:
    """Engine for learning command patterns"""
    
    def __init__(self, learning_module):
        self.learning_module = learning_module
        
    async def learn_from_interaction(self, interaction: UserInteraction) -> Dict[str, Any]:
        """Learn command patterns from interaction"""
        try:
            if interaction.intent == 'unknown':
                return {'learned': False, 'reason': 'Unknown intent'}
                
            # Generate pattern ID
            pattern_text = interaction.user_input.lower().strip()
            pattern_id = f"{interaction.intent}_{hashlib.md5(pattern_text.encode()).hexdigest()[:8]}"
            
            if pattern_id in self.learning_module.patterns_cache:
                # Update existing pattern
                pattern = self.learning_module.patterns_cache[pattern_id]
                pattern.frequency += 1
                pattern.last_used = interaction.timestamp
                
                # Update success rate
                if interaction.success:
                    pattern.success_rate = (pattern.success_rate * 0.9) + (1.0 * 0.1)
                else:
                    pattern.success_rate = (pattern.success_rate * 0.9) + (0.0 * 0.1)
                    
                # Update average response time
                if interaction.response_time > 0:
                    pattern.average_response_time = (
                        (pattern.average_response_time * 0.8) + (interaction.response_time * 0.2)
                    )
                    
            else:
                # Create new pattern
                pattern = CommandPattern(
                    pattern_id=pattern_id,
                    command_type=interaction.intent,
                    pattern=pattern_text,
                    frequency=1,
                    success_rate=1.0 if interaction.success else 0.0,
                    average_response_time=interaction.response_time,
                    last_used=interaction.timestamp,
                    optimizations=[]
                )
                self.learning_module.patterns_cache[pattern_id] = pattern
                self.learning_module.stats['patterns_identified'] += 1
                
            # Generate optimizations
            if pattern.frequency > 5:
                await self._generate_optimizations(pattern)
                
            return {
                'learned': True,
                'pattern_id': pattern_id,
                'frequency': pattern.frequency,
                'success_rate': pattern.success_rate
            }
            
        except Exception as e:
            self.learning_module.log(f"Error learning patterns: {e}", "error")
            return {'learned': False, 'error': str(e)}
            
    async def _generate_optimizations(self, pattern: CommandPattern):
        """Generate optimizations for a pattern"""
        try:
            optimizations = []
            
            if pattern.success_rate < 0.7:
                optimizations.append("improve_intent_recognition")
                
            if pattern.average_response_time > 3.0:
                optimizations.append("optimize_response_time")
                
            if pattern.frequency > 20:
                optimizations.append("cache_frequent_response")
                
            pattern.optimizations = list(set(pattern.optimizations + optimizations))
            
        except Exception as e:
            self.learning_module.log(f"Error generating optimizations: {e}", "error")


class MistakeEngine:
    """Engine for learning from mistakes"""
    
    def __init__(self, learning_module):
        self.learning_module = learning_module
        
    async def learn_from_interaction(self, interaction: UserInteraction) -> Dict[str, Any]:
        """Learn from interaction mistakes"""
        try:
            if interaction.success:
                return {'learned': False, 'reason': 'Interaction was successful'}
                
            # Create mistake record
            mistake_id = self.learning_module._generate_mistake_id(
                interaction.user_input, 'interaction_failure'
            )
            
            mistake = MistakeRecord(
                mistake_id=mistake_id,
                error_type='interaction_failure',
                original_input=interaction.user_input,
                expected_output='successful_response',
                actual_output=interaction.response,
                correction='',
                timestamp=interaction.timestamp,
                corrected=False
            )
            
            self.learning_module.mistakes_cache[mistake_id] = mistake
            
            # Analyze common failure patterns
            await self._analyze_failure_patterns(mistake)
            
            return {
                'learned': True,
                'mistake_id': mistake_id,
                'error_type': mistake.error_type
            }
            
        except Exception as e:
            self.learning_module.log(f"Error learning from mistakes: {e}", "error")
            return {'learned': False, 'error': str(e)}
            
    async def _analyze_failure_patterns(self, mistake: MistakeRecord):
        """Analyze patterns in failures"""
        try:
            # Count similar mistakes
            similar_mistakes = [
                m for m in self.learning_module.mistakes_cache.values()
                if m.error_type == mistake.error_type and m.mistake_id != mistake.mistake_id
            ]
            
            if len(similar_mistakes) > 3:
                # Pattern detected
                self.learning_module.log(
                    f"Failure pattern detected: {mistake.error_type} ({len(similar_mistakes)} occurrences)",
                    "warning"
                )
                
        except Exception as e:
            self.learning_module.log(f"Error analyzing failure patterns: {e}", "error")


class OptimizationEngine:
    """Engine for applying optimizations"""
    
    def __init__(self, learning_module):
        self.learning_module = learning_module
        
    async def apply_optimizations(self, interaction: UserInteraction) -> Dict[str, Any]:
        """Apply learned optimizations to interaction"""
        try:
            applied_optimizations = []
            
            # Find relevant patterns
            relevant_patterns = [
                p for p in self.learning_module.patterns_cache.values()
                if p.command_type == interaction.intent and p.optimizations
            ]
            
            for pattern in relevant_patterns:
                for optimization in pattern.optimizations:
                    if optimization not in applied_optimizations:
                        await self._apply_optimization(optimization, interaction)
                        applied_optimizations.append(optimization)
                        
            if applied_optimizations:
                self.learning_module.stats['optimizations_applied'] += len(applied_optimizations)
                
            return {
                'applied': len(applied_optimizations) > 0,
                'optimizations': applied_optimizations
            }
            
        except Exception as e:
            self.learning_module.log(f"Error applying optimizations: {e}", "error")
            return {'applied': False, 'error': str(e)}
            
    async def _apply_optimization(self, optimization: str, interaction: UserInteraction):
        """Apply specific optimization"""
        try:
            if optimization == "improve_intent_recognition":
                # Log suggestion for intent recognition improvement
                self.learning_module.log(
                    f"Optimization suggestion: Improve intent recognition for '{interaction.user_input}'"
                )
                
            elif optimization == "optimize_response_time":
                # Log suggestion for response time optimization
                self.learning_module.log(
                    f"Optimization suggestion: Optimize response time for {interaction.intent} commands"
                )
                
            elif optimization == "cache_frequent_response":
                # Log suggestion for response caching
                self.learning_module.log(
                    f"Optimization suggestion: Cache responses for frequent {interaction.intent} commands"
                )
                
        except Exception as e:
            self.learning_module.log(f"Error applying optimization {optimization}: {e}", "error")