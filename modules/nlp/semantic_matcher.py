"""
Semantic Matcher - Advanced pattern matching with fuzzy logic and similarity scoring
"""

import re
import json
from typing import Dict, List, Tuple, Any, Optional
from difflib import SequenceMatcher
from pathlib import Path
import logging


class SemanticMatcher:
    """Advanced semantic matching with fuzzy logic, synonyms, and pattern recognition"""
    
    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger(__name__)
        
        # Similarity thresholds
        self.exact_match_threshold = 0.95
        self.fuzzy_match_threshold = 0.75
        self.partial_match_threshold = 0.6
        
        # Load synonym database
        self.synonyms = self._load_synonyms()
        
        # Common word variations and typos
        self.common_variations = self._load_variations()
        
        # Statistics
        self.stats = {
            'exact_matches': 0,
            'fuzzy_matches': 0,
            'partial_matches': 0,
            'synonym_matches': 0,
            'total_comparisons': 0
        }
    
    def _load_synonyms(self) -> Dict[str, List[str]]:
        """Load comprehensive synonym database"""
        return {
            # Scheduling actions
            'schedule': ['book', 'add', 'create', 'set up', 'plan', 'arrange', 'organize', 'setup', 'make'],
            'cancel': ['delete', 'remove', 'drop', 'abort', 'terminate', 'end'],
            'change': ['modify', 'update', 'edit', 'alter', 'adjust', 'revise'],
            'move': ['reschedule', 'shift', 'transfer', 'relocate'],
            
            # Meeting types
            'meeting': ['appointment', 'session', 'conference', 'gathering', 'discussion'],
            'call': ['phone call', 'video call', 'conference call', 'conversation'],
            'interview': ['screening', 'discussion', 'evaluation', 'assessment'],
            'standup': ['daily', 'scrum', 'sync', 'check-in', 'status meeting'],
            'review': ['evaluation', 'assessment', 'analysis', 'examination'],
            
            # Time references
            'tomorrow': ['next day', 'the next day', 'following day'],
            'today': ['this day', 'right now', 'currently'],
            'morning': ['am', 'early', 'before noon'],
            'afternoon': ['pm', 'after noon', 'later'],
            'evening': ['night', 'late', 'after work'],
            
            # Calendar terms
            'calendar': ['schedule', 'agenda', 'planner', 'diary'],
            'schedule': ['agenda', 'timetable', 'program', 'itinerary'],
            'busy': ['occupied', 'booked', 'scheduled', 'unavailable'],
            'free': ['available', 'open', 'clear', 'unoccupied'],
            
            # Question words
            'what': ['which', 'what kind of', 'what type of'],
            'when': ['what time', 'at what time', 'what day'],
            'where': ['what location', 'at what place', 'in which place'],
            
            # Confirmation words
            'yes': ['yeah', 'yep', 'sure', 'okay', 'correct', 'right', 'exactly'],
            'no': ['nope', 'nah', 'wrong', 'incorrect', 'not right', 'negative'],
            
            # Location types
            'online': ['virtual', 'remote', 'digital', 'web-based'],
            'office': ['workplace', 'work', 'building', 'headquarters'],
            'home': ['house', 'residence', 'remote'],
        }
    
    def _load_variations(self) -> Dict[str, List[str]]:
        """Load common variations and typos"""
        return {
            # Common typos
            'schedule': ['schedual', 'scedule', 'shedule'],
            'meeting': ['meting', 'meating', 'meetng'],
            'tomorrow': ['tommorow', 'tommorrow', 'tomorow'],
            'appointment': ['apointment', 'appointement'],
            'calendar': ['calender', 'calandar'],
            
            # Informal variations
            'what is': ['whats', 'what\'s'],
            'do i have': ['do i got', 'have i got'],
            'set up': ['setup', 'set-up'],
            'check my': ['check out my', 'look at my'],
        }
    
    def find_matches(self, text: str, patterns: List[str], match_type: str = 'best') -> List[Dict[str, Any]]:
        """Find matches between text and patterns with different matching strategies"""
        matches = []
        self.stats['total_comparisons'] += len(patterns)
        
        for pattern in patterns:
            match_result = self._calculate_match_score(text, pattern)
            if match_result['score'] > 0:
                matches.append({
                    'pattern': pattern,
                    'score': match_result['score'],
                    'match_type': match_result['type'],
                    'explanation': match_result['explanation']
                })
        
        # Sort by score (highest first)
        matches.sort(key=lambda x: x['score'], reverse=True)
        
        if match_type == 'best':
            return matches[:1] if matches else []
        elif match_type == 'top3':
            return matches[:3]
        else:
            return matches
    
    def _calculate_match_score(self, text: str, pattern: str) -> Dict[str, Any]:
        """Calculate comprehensive match score between text and pattern"""
        text_lower = text.lower().strip()
        pattern_lower = pattern.lower().strip()
        
        # 1. Exact match
        if text_lower == pattern_lower:
            self.stats['exact_matches'] += 1
            return {
                'score': 1.0,
                'type': 'exact',
                'explanation': 'Exact match'
            }
        
        # 2. Exact substring match
        if pattern_lower in text_lower or text_lower in pattern_lower:
            score = 0.95
            self.stats['exact_matches'] += 1
            return {
                'score': score,
                'type': 'substring',
                'explanation': 'Exact substring match'
            }
        
        # 3. Synonym match
        synonym_score = self._check_synonym_match(text_lower, pattern_lower)
        if synonym_score > 0:
            self.stats['synonym_matches'] += 1
            return {
                'score': synonym_score,
                'type': 'synonym',
                'explanation': 'Synonym match found'
            }
        
        # 4. Fuzzy string similarity
        similarity = SequenceMatcher(None, text_lower, pattern_lower).ratio()
        
        if similarity >= self.fuzzy_match_threshold:
            self.stats['fuzzy_matches'] += 1
            return {
                'score': similarity,
                'type': 'fuzzy',
                'explanation': f'Fuzzy match with {similarity:.2f} similarity'
            }
        
        # 5. Partial word matching
        partial_score = self._check_partial_match(text_lower, pattern_lower)
        if partial_score >= self.partial_match_threshold:
            self.stats['partial_matches'] += 1
            return {
                'score': partial_score,
                'type': 'partial',
                'explanation': 'Partial word match'
            }
        
        # 6. Variation/typo checking
        variation_score = self._check_variations(text_lower, pattern_lower)
        if variation_score > 0:
            return {
                'score': variation_score,
                'type': 'variation',
                'explanation': 'Common variation or typo match'
            }
        
        return {
            'score': 0.0,
            'type': 'no_match',
            'explanation': 'No significant match found'
        }
    
    def _check_synonym_match(self, text: str, pattern: str) -> float:
        """Check for synonym matches between text and pattern"""
        text_words = set(text.split())
        pattern_words = set(pattern.split())
        
        max_score = 0.0
        
        # Check each word in text against pattern synonyms
        for text_word in text_words:
            for pattern_word in pattern_words:
                # Direct synonym check
                if text_word in self.synonyms.get(pattern_word, []):
                    max_score = max(max_score, 0.9)
                elif pattern_word in self.synonyms.get(text_word, []):
                    max_score = max(max_score, 0.9)
                
                # Cross-synonym check (both words are synonyms of same root)
                for root_word, synonyms in self.synonyms.items():
                    if text_word in synonyms and pattern_word in synonyms:
                        max_score = max(max_score, 0.85)
        
        return max_score
    
    def _check_partial_match(self, text: str, pattern: str) -> float:
        """Check for partial word matches"""
        text_words = text.split()
        pattern_words = pattern.split()
        
        matches = 0
        total_words = max(len(text_words), len(pattern_words))
        
        for text_word in text_words:
            for pattern_word in pattern_words:
                # Check if words are similar enough
                similarity = SequenceMatcher(None, text_word, pattern_word).ratio()
                if similarity >= 0.7:  # 70% similarity threshold for individual words
                    matches += 1
                    break
        
        if total_words == 0:
            return 0.0
        
        return matches / total_words
    
    def _check_variations(self, text: str, pattern: str) -> float:
        """Check for common variations and typos"""
        # Check if text contains any known variations of pattern words
        for correct_word, variations in self.common_variations.items():
            if correct_word in pattern:
                for variation in variations:
                    if variation in text:
                        return 0.8  # High score for recognized variations
        
        # Check reverse (pattern contains variations of text words)
        text_words = text.split()
        for text_word in text_words:
            if text_word in self.common_variations:
                for variation in self.common_variations[text_word]:
                    if variation in pattern:
                        return 0.8
        
        return 0.0
    
    def expand_with_synonyms(self, text: str) -> List[str]:
        """Expand text with synonyms for broader matching"""
        expanded = [text]
        words = text.split()
        
        # Generate variations by replacing words with synonyms
        for i, word in enumerate(words):
            if word in self.synonyms:
                for synonym in self.synonyms[word]:
                    new_text = words.copy()
                    new_text[i] = synonym
                    expanded.append(' '.join(new_text))
        
        return expanded
    
    def normalize_text(self, text: str) -> str:
        """Normalize text for better matching"""
        # Convert to lowercase
        text = text.lower().strip()
        
        # Replace known variations with standard forms
        for standard, variations in self.common_variations.items():
            for variation in variations:
                text = text.replace(variation, standard)
        
        # Remove punctuation except apostrophes
        text = re.sub(r'[^\w\s\']', ' ', text)
        
        # Normalize contractions
        contractions = {
            'what\'s': 'what is',
            'i\'m': 'i am',
            'don\'t': 'do not',
            'can\'t': 'cannot',
            'won\'t': 'will not'
        }
        for contraction, expansion in contractions.items():
            text = text.replace(contraction, expansion)
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def find_best_pattern_match(self, text: str, pattern_groups: Dict[str, List[str]]) -> Tuple[str, Dict[str, Any]]:
        """Find the best matching pattern group for given text"""
        best_group = None
        best_match = {'score': 0.0}
        
        for group_name, patterns in pattern_groups.items():
            matches = self.find_matches(text, patterns, match_type='best')
            if matches and matches[0]['score'] > best_match['score']:
                best_group = group_name
                best_match = matches[0]
        
        return best_group, best_match
    
    def calculate_context_similarity(self, current_text: str, context_history: List[str]) -> float:
        """Calculate similarity with recent context for better understanding"""
        if not context_history:
            return 0.0
        
        max_similarity = 0.0
        
        # Check similarity with recent context
        for i, context_text in enumerate(reversed(context_history[-3:])):  # Last 3 entries
            similarity = SequenceMatcher(None, current_text, context_text).ratio()
            # Weight more recent context higher
            weighted_similarity = similarity * (0.8 ** i)
            max_similarity = max(max_similarity, weighted_similarity)
        
        return max_similarity
    
    def extract_key_phrases(self, text: str) -> List[str]:
        """Extract key phrases that might be important for intent recognition"""
        # Simple key phrase extraction
        key_phrases = []
        
        # Find multi-word patterns that commonly appear together
        common_phrases = [
            'set up', 'check out', 'look at', 'what time', 'do i have',
            'am i free', 'schedule meeting', 'book appointment'
        ]
        
        text_lower = text.lower()
        for phrase in common_phrases:
            if phrase in text_lower:
                key_phrases.append(phrase)
        
        # Extract potential time references
        time_patterns = [
            r'\b\d{1,2}:\d{2}\s*(am|pm)?\b',
            r'\b\d{1,2}\s*(am|pm)\b',
            r'\b(tomorrow|today|monday|tuesday|wednesday|thursday|friday)\b'
        ]
        
        for pattern in time_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            key_phrases.extend(matches if isinstance(matches[0] if matches else '', str) else [' '.join(match) for match in matches])
        
        return key_phrases
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get matching statistics"""
        stats = self.stats.copy()
        
        if stats['total_comparisons'] > 0:
            stats['exact_match_rate'] = stats['exact_matches'] / stats['total_comparisons']
            stats['fuzzy_match_rate'] = stats['fuzzy_matches'] / stats['total_comparisons']
            stats['partial_match_rate'] = stats['partial_matches'] / stats['total_comparisons']
            stats['synonym_match_rate'] = stats['synonym_matches'] / stats['total_comparisons']
        
        return stats