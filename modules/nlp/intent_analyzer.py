"""
Enhanced Intent Analyzer - Semantic understanding for natural language commands
"""

import re
import json
import time
from typing import Dict, Any, List, Tuple, Optional
from pathlib import Path
from difflib import SequenceMatcher
import logging


class IntentAnalyzer:
    """Advanced intent recognition with semantic matching and context awareness"""
    
    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger(__name__)
        
        # Intent pattern database
        self.intent_patterns = self._load_intent_patterns()
        
        # Semantic similarity threshold - adjusted for better performance
        self.similarity_threshold = 0.25  # Lower threshold to catch more matches
        self.uncertainty_threshold = 0.15
        
        # Context tracking
        self.conversation_context = []
        self.max_context_turns = 5
        self.context_decay_rate = 0.8
        
        # User learning
        self.user_patterns = {}
        self.learning_enabled = True
        
        # Statistics
        self.stats = {
            'total_analyses': 0,
            'successful_matches': 0,
            'context_uses': 0,
            'learning_adaptations': 0
        }
    
    def _load_intent_patterns(self) -> Dict[str, Any]:
        """Load comprehensive intent patterns"""
        return {
            'schedule_meeting': {
                'primary_patterns': [
                    'schedule', 'book', 'add', 'create', 'set up', 'plan', 
                    'arrange', 'organize', 'setup', 'make'
                ],
                'meeting_types': [
                    'meeting', 'appointment', 'call', 'interview', 'demo',
                    'standup', 'sync', 'catchup', 'review', 'presentation',
                    'conference', 'session', 'gathering', 'discussion'
                ],
                'time_indicators': [
                    'at', 'on', 'for', 'tomorrow', 'today', 'next', 'this',
                    'monday', 'tuesday', 'wednesday', 'thursday', 'friday',
                    'am', 'pm', 'morning', 'afternoon', 'evening'
                ],
                'synonyms': {
                    'schedule': ['book', 'add', 'create', 'set up', 'plan', 'arrange'],
                    'meeting': ['appointment', 'call', 'session', 'conference'],
                    'tomorrow': ['next day', 'the next day'],
                    'today': ['this day', 'right now']
                }
            },
            
            'check_calendar': {
                'primary_patterns': [
                    'do i have', 'what\'s on my', 'check my', 'show me', 
                    'list my', 'display my', 'tell me about'
                ],
                'calendar_terms': [
                    'calendar', 'schedule', 'agenda', 'meetings', 'appointments',
                    'events', 'plans', 'commitments'
                ],
                'time_context': [
                    'today', 'tomorrow', 'this week', 'next week', 'monday',
                    'tuesday', 'wednesday', 'thursday', 'friday', 'weekend'
                ],
                'question_forms': [
                    'am i free', 'am i busy', 'do i have time', 'what meetings',
                    'any appointments', 'free time', 'available', 'busy'
                ],
                'synonyms': {
                    'calendar': ['schedule', 'agenda', 'planner'],
                    'meetings': ['appointments', 'events', 'sessions'],
                    'free': ['available', 'open', 'clear'],
                    'busy': ['occupied', 'booked', 'scheduled']
                }
            },
            
            'modify_meeting': {
                'primary_patterns': [
                    'change', 'move', 'reschedule', 'update', 'modify',
                    'edit', 'cancel', 'delete', 'remove'
                ],
                'context_dependent': True,  # Requires previous scheduling context
                'time_changes': [
                    'to', 'at', 'for', 'make it', 'change to', 'move to'
                ],
                'confirmations': [
                    'yes', 'okay', 'sure', 'correct', 'right', 'exactly'
                ],
                'negations': [
                    'no', 'nope', 'wrong', 'incorrect', 'not right'
                ]
            },
            
            'time_query': {
                'primary_patterns': [
                    'what time', 'current time', 'time is it', 'tell me the time',
                    'what\'s the time', 'time now', 'time please'
                ],
                'location_indicators': [
                    'in', 'at', 'for'
                ]
            },
            
            'greeting': {
                'primary_patterns': [
                    'hello', 'hi', 'hey', 'good morning', 'good afternoon',
                    'good evening', 'howdy', 'greetings'
                ],
                'casual_forms': [
                    'sup', 'what\'s up', 'yo', 'hiya'
                ]
            },
            
            'goodbye': {
                'primary_patterns': [
                    'bye', 'goodbye', 'see you', 'farewell', 'exit',
                    'quit', 'stop', 'end'
                ],
                'casual_forms': [
                    'later', 'catch you later', 'peace', 'cya'
                ]
            },
            
            'help_request': {
                'primary_patterns': [
                    'help', 'help me', 'how do i', 'what can you do',
                    'commands', 'instructions', 'guide'
                ],
                'question_forms': [
                    'how to', 'can you help', 'what are your capabilities'
                ]
            }
        }
    
    def analyze_intent(self, text: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """Analyze intent with multi-level matching and context awareness"""
        try:
            self.stats['total_analyses'] += 1
            start_time = time.time()
            
            # Clean and normalize text
            normalized_text = self._normalize_text(text)
            
            # Level 1: Exact keyword matching
            exact_matches = self._analyze_exact_patterns(normalized_text)
            
            # Level 2: Semantic similarity matching
            semantic_matches = self._analyze_semantic_similarity(normalized_text)
            
            # Level 3: Context-aware scoring
            context_scores = self._apply_context_weighting(normalized_text, context)
            
            # Level 4: User pattern learning
            learned_scores = self._apply_learned_patterns(normalized_text)
            
            # Combine all scoring methods
            final_scores = self._combine_scores(
                exact_matches, semantic_matches, context_scores, learned_scores
            )
            
            # Select best intent with confidence
            result = self._select_best_intent(final_scores, normalized_text)
            
            # Update context and learning
            self._update_context(text, result)
            if self.learning_enabled and result['confidence'] > 0.8:
                self._learn_user_pattern(text, result['intent'])
            
            # Add processing metadata
            result.update({
                'processing_time': time.time() - start_time,
                'analysis_methods': ['exact', 'semantic', 'context', 'learned'],
                'normalized_text': normalized_text
            })
            
            if result['confidence'] > self.similarity_threshold:
                self.stats['successful_matches'] += 1
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error analyzing intent: {e}")
            return {
                'intent': 'error',
                'confidence': 0.0,
                'error': str(e),
                'threshold_met': False
            }
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for better matching"""
        # Convert to lowercase
        text = text.lower().strip()
        
        # Remove punctuation except apostrophes
        text = re.sub(r'[^\w\s\']', ' ', text)
        
        # Normalize contractions
        contractions = {
            'what\'s': 'what is',
            'i\'m': 'i am',
            'don\'t': 'do not',
            'can\'t': 'cannot',
            'won\'t': 'will not',
            'let\'s': 'let us'
        }
        for contraction, expansion in contractions.items():
            text = text.replace(contraction, expansion)
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def _analyze_exact_patterns(self, text: str) -> Dict[str, float]:
        """Analyze using exact keyword pattern matching"""
        scores = {}
        
        for intent, patterns in self.intent_patterns.items():
            score = 0.0
            total_patterns = 0
            
            # Check primary patterns
            if 'primary_patterns' in patterns:
                for pattern in patterns['primary_patterns']:
                    if pattern in text:
                        score += 1.0
                    total_patterns += 1
            
            # Check additional pattern categories
            for category in ['meeting_types', 'calendar_terms', 'time_context', 'question_forms']:
                if category in patterns:
                    for pattern in patterns[category]:
                        if pattern in text:
                            score += 0.8  # Slightly lower weight for secondary patterns
                        total_patterns += 1
            
            # Normalize score
            if total_patterns > 0:
                scores[intent] = score / total_patterns
            
        return scores
    
    def _analyze_semantic_similarity(self, text: str) -> Dict[str, float]:
        """Analyze using semantic similarity and synonyms"""
        scores = {}
        
        for intent, patterns in self.intent_patterns.items():
            max_similarity = 0.0
            
            # Check synonyms if available
            if 'synonyms' in patterns:
                for word in text.split():
                    for synonym_group in patterns['synonyms'].values():
                        for synonym in synonym_group:
                            similarity = self._calculate_similarity(word, synonym)
                            max_similarity = max(max_similarity, similarity)
            
            # Check pattern similarity
            for pattern_category in ['primary_patterns', 'meeting_types', 'calendar_terms']:
                if pattern_category in patterns:
                    for pattern in patterns[pattern_category]:
                        # Word-level similarity
                        for word in text.split():
                            similarity = self._calculate_similarity(word, pattern)
                            max_similarity = max(max_similarity, similarity)
                        
                        # Phrase-level similarity
                        phrase_similarity = self._calculate_similarity(text, pattern)
                        max_similarity = max(max_similarity, phrase_similarity * 0.8)
            
            scores[intent] = max_similarity
        
        return scores
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two text strings"""
        # Use sequence matcher for basic similarity
        similarity = SequenceMatcher(None, text1, text2).ratio()
        
        # Boost score for exact substring matches
        if text2 in text1 or text1 in text2:
            similarity = max(similarity, 0.8)
        
        return similarity
    
    def _apply_context_weighting(self, text: str, context: Optional[Dict]) -> Dict[str, float]:
        """Apply context-aware scoring based on conversation history"""
        scores = {}
        
        if not self.conversation_context:
            return scores
        
        self.stats['context_uses'] += 1
        
        # Check recent context for intent continuity
        recent_intents = [ctx.get('intent') for ctx in self.conversation_context[-3:]]
        
        # Context-dependent intents (like modify_meeting after schedule_meeting)
        for intent, patterns in self.intent_patterns.items():
            context_score = 0.0
            
            if patterns.get('context_dependent', False):
                # This intent depends on previous context
                if intent == 'modify_meeting' and 'schedule_meeting' in recent_intents:
                    context_score = 0.7  # High context boost
                elif 'confirmations' in patterns:
                    # Check for confirmation words
                    for confirmation in patterns['confirmations']:
                        if confirmation in text:
                            context_score = 0.6
                            break
            
            # Time-based context continuity
            if any('time' in ctx.get('entities', {}) for ctx in self.conversation_context[-2:]):
                if intent == 'schedule_meeting' and any(word in text for word in ['yes', 'correct', 'right']):
                    context_score = 0.5
            
            scores[intent] = context_score
        
        return scores
    
    def _apply_learned_patterns(self, text: str) -> Dict[str, float]:
        """Apply user-learned patterns for personalization"""
        scores = {}
        
        if not self.user_patterns:
            return scores
        
        for intent, learned_phrases in self.user_patterns.items():
            max_score = 0.0
            
            for phrase, frequency in learned_phrases.items():
                similarity = self._calculate_similarity(text, phrase)
                # Weight by frequency and recency
                weighted_score = similarity * min(frequency / 10, 1.0)
                max_score = max(max_score, weighted_score)
            
            scores[intent] = max_score * 0.5  # Moderate weight for learned patterns
        
        return scores
    
    def _combine_scores(self, exact: Dict, semantic: Dict, context: Dict, learned: Dict) -> Dict[str, float]:
        """Combine scores from different analysis methods"""
        all_intents = set(exact.keys()) | set(semantic.keys()) | set(context.keys()) | set(learned.keys())
        combined_scores = {}
        
        for intent in all_intents:
            # Enhanced weighted combination with boosting for high scores
            exact_score = exact.get(intent, 0.0)
            semantic_score = semantic.get(intent, 0.0)
            context_score = context.get(intent, 0.0)
            learned_score = learned.get(intent, 0.0)
            
            # Base weighted combination
            base_score = (
                exact_score * 0.5 +      # Increased weight for exact matches
                semantic_score * 0.3 +   # Semantic similarity
                context_score * 0.15 +   # Context awareness
                learned_score * 0.05     # User learning
            )
            
            # Boost high-confidence matches
            if exact_score > 0.3 or semantic_score > 0.7:
                base_score *= 1.5  # 50% boost for strong matches
            
            # Ensure score doesn't exceed 1.0
            combined_scores[intent] = min(base_score, 1.0)
        
        return combined_scores
    
    def _select_best_intent(self, scores: Dict[str, float], text: str) -> Dict[str, Any]:
        """Select the best intent with confidence scoring"""
        if not scores:
            return {
                'intent': 'unknown',
                'confidence': 0.0,
                'all_scores': {},
                'threshold_met': False,
                'suggestion': 'Try rephrasing your request'
            }
        
        # Sort by score
        sorted_intents = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        best_intent, best_score = sorted_intents[0]
        
        # Check if we have a clear winner
        if len(sorted_intents) > 1:
            second_score = sorted_intents[1][1]
            # If top two scores are very close, reduce confidence
            if best_score - second_score < 0.1:
                best_score *= 0.8
        
        # Determine confidence level and response
        threshold_met = best_score >= self.similarity_threshold
        
        result = {
            'intent': best_intent,
            'confidence': best_score,
            'all_scores': scores,
            'threshold_met': threshold_met
        }
        
        # Add suggestions based on confidence
        if not threshold_met:
            if best_score > self.uncertainty_threshold:
                result['suggestion'] = f"Did you mean to {best_intent.replace('_', ' ')}?"
                result['uncertain'] = True
            else:
                result['suggestion'] = "I'm not sure what you meant. Try being more specific."
                result['uncertain'] = True
        
        # Extract entities if high confidence
        if threshold_met:
            result['entities'] = self._extract_entities(text, best_intent)
        
        return result
    
    def _extract_entities(self, text: str, intent: str) -> Dict[str, Any]:
        """Extract relevant entities based on intent"""
        entities = {}
        
        if intent == 'schedule_meeting':
            # Extract time/date entities
            time_patterns = [
                r'\b(\d{1,2}):(\d{2})\s*(am|pm)?\b',
                r'\b(\d{1,2})\s*(am|pm)\b',
                r'\b(tomorrow|today|monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b'
            ]
            
            for pattern in time_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches:
                    entities['time_references'] = matches
                    break
            
            # Extract meeting type
            for meeting_type in self.intent_patterns[intent]['meeting_types']:
                if meeting_type in text:
                    entities['meeting_type'] = meeting_type
                    break
        
        elif intent == 'check_calendar':
            # Extract time context
            for time_ref in self.intent_patterns[intent]['time_context']:
                if time_ref in text:
                    entities['time_context'] = time_ref
                    break
        
        return entities
    
    def _update_context(self, original_text: str, result: Dict[str, Any]):
        """Update conversation context"""
        context_entry = {
            'timestamp': time.time(),
            'text': original_text,
            'intent': result['intent'],
            'confidence': result['confidence'],
            'entities': result.get('entities', {})
        }
        
        self.conversation_context.append(context_entry)
        
        # Limit context size
        if len(self.conversation_context) > self.max_context_turns:
            self.conversation_context.pop(0)
    
    def _learn_user_pattern(self, text: str, intent: str):
        """Learn user's preferred ways of expressing intents"""
        if intent not in self.user_patterns:
            self.user_patterns[intent] = {}
        
        # Store normalized text pattern
        if text in self.user_patterns[intent]:
            self.user_patterns[intent][text] += 1
        else:
            self.user_patterns[intent][text] = 1
        
        self.stats['learning_adaptations'] += 1
        
        # Limit stored patterns per intent
        if len(self.user_patterns[intent]) > 20:
            # Remove least frequent patterns
            sorted_patterns = sorted(
                self.user_patterns[intent].items(), 
                key=lambda x: x[1]
            )
            del self.user_patterns[intent][sorted_patterns[0][0]]
    
    def get_context_summary(self) -> Dict[str, Any]:
        """Get summary of current conversation context"""
        if not self.conversation_context:
            return {'context_length': 0, 'recent_intents': []}
        
        recent_intents = [ctx['intent'] for ctx in self.conversation_context[-3:]]
        return {
            'context_length': len(self.conversation_context),
            'recent_intents': recent_intents,
            'last_confidence': self.conversation_context[-1]['confidence']
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get analyzer statistics"""
        stats = self.stats.copy()
        if stats['total_analyses'] > 0:
            stats['success_rate'] = stats['successful_matches'] / stats['total_analyses']
        else:
            stats['success_rate'] = 0.0
        
        stats['learned_patterns_count'] = sum(len(patterns) for patterns in self.user_patterns.values())
        stats['context_length'] = len(self.conversation_context)
        
        return stats