"""
Prompt Engineering Engine - Advanced prompt management and optimization for SAGE
"""

import asyncio
import json
import time
import re
import hashlib
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict, Counter
import logging
from pathlib import Path


@dataclass
class PromptTemplate:
    """Data class for prompt templates"""
    name: str
    template: str
    variables: List[str]
    category: str = "general"
    description: str = ""
    version: float = 1.0
    created_at: float = None
    usage_count: int = 0
    success_rate: float = 0.0
    avg_response_time: float = 0.0
    tags: List[str] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = time.time()
        if self.tags is None:
            self.tags = []


@dataclass
class PromptContext:
    """Data class for prompt context"""
    user_id: str
    conversation_history: List[str] = None
    user_preferences: Dict[str, Any] = None
    current_intent: str = "unknown"
    session_data: Dict[str, Any] = None
    timestamp: float = None
    
    def __post_init__(self):
        if self.conversation_history is None:
            self.conversation_history = []
        if self.user_preferences is None:
            self.user_preferences = {}
        if self.session_data is None:
            self.session_data = {}
        if self.timestamp is None:
            self.timestamp = time.time()


@dataclass
class PromptMetrics:
    """Data class for prompt performance metrics"""
    prompt_id: str
    template_name: str
    execution_time: float
    success: bool
    response_quality: float = 0.0
    user_satisfaction: float = 0.0
    timestamp: float = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()


class PromptEngine:
    """Advanced prompt engineering and optimization engine"""
    
    def __init__(self, data_dir: str = "data/prompts"):
        self.data_dir = Path(data_dir)
        self.templates: Dict[str, PromptTemplate] = {}
        self.contexts: Dict[str, PromptContext] = {}
        self.few_shot_examples: Dict[str, List[Dict[str, str]]] = defaultdict(list)
        self.metrics: List[PromptMetrics] = []
        self.logger = logging.getLogger(__name__)
        
        # Performance tracking
        self.stats = {
            'total_prompts': 0,
            'successful_prompts': 0,
            'failed_prompts': 0,
            'total_execution_time': 0.0,
            'templates_created': 0,
            'optimizations_applied': 0
        }
        
        # Optimization rules
        self.optimization_rules = [
            {
                'name': 'clarity_enhancement',
                'pattern': r'unclear|ambiguous|confusing',
                'suggestion': 'Add more specific instructions and examples'
            },
            {
                'name': 'length_optimization',
                'pattern': r'.{500,}',
                'suggestion': 'Consider breaking long prompts into shorter, focused sections'
            },
            {
                'name': 'context_enhancement',
                'pattern': r'you are|act as',
                'suggestion': 'Add specific role context and behavioral guidelines'
            },
            {
                'name': 'output_formatting',
                'pattern': r'respond|answer|reply',
                'suggestion': 'Specify desired output format and structure'
            }
        ]
        
    async def initialize(self) -> bool:
        """Initialize the prompt engine"""
        try:
            self.logger.info("Initializing Prompt Engine...")
            
            # Ensure data directory exists
            self.data_dir.mkdir(parents=True, exist_ok=True)
            
            # Load existing templates
            await self._load_templates()
            
            # Load few-shot examples
            await self._load_few_shot_examples()
            
            # Load default templates
            await self._create_default_templates()
            
            self.logger.info("Prompt Engine initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Prompt Engine: {e}")
            return False
    
    async def shutdown(self) -> None:
        """Shutdown the prompt engine"""
        try:
            self.logger.info("Shutting down Prompt Engine...")
            
            # Save templates
            await self._save_templates()
            
            # Save few-shot examples
            await self._save_few_shot_examples()
            
            # Save metrics
            await self._save_metrics()
            
            self.logger.info("Prompt Engine shutdown complete")
            
        except Exception as e:
            self.logger.error(f"Error during Prompt Engine shutdown: {e}")
    
    async def register_template(self, template: PromptTemplate) -> bool:
        """Register a new prompt template"""
        try:
            # Validate template
            if not await self._validate_template(template):
                return False
            
            # Store template
            self.templates[template.name] = template
            self.stats['templates_created'] += 1
            
            self.logger.info(f"Registered prompt template: {template.name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error registering template {template.name}: {e}")
            return False
    
    async def get_template(self, name: str) -> Optional[PromptTemplate]:
        """Get a prompt template by name"""
        return self.templates.get(name)
    
    async def render_prompt(self, template_name: str, variables: Dict[str, Any], 
                          context: Optional[PromptContext] = None) -> str:
        """Render a prompt template with variables and context"""
        try:
            template = self.templates.get(template_name)
            if not template:
                self.logger.error(f"Template {template_name} not found")
                return ""
            
            start_time = time.time()
            
            # Start with base template
            rendered = template.template
            
            # Apply context if provided
            if context:
                rendered = await self._apply_context(rendered, context)
            
            # Apply variables
            for var_name, var_value in variables.items():
                placeholder = f"{{{var_name}}}"
                rendered = rendered.replace(placeholder, str(var_value))
            
            # Apply few-shot examples if available
            if template.category in self.few_shot_examples:
                rendered = await self._apply_few_shot_examples(rendered, template.category)
            
            # Track performance
            execution_time = time.time() - start_time
            await self._record_metrics(template_name, execution_time, True)
            
            # Update template usage
            template.usage_count += 1
            
            self.stats['total_prompts'] += 1
            self.stats['successful_prompts'] += 1
            self.stats['total_execution_time'] += execution_time
            
            return rendered
            
        except Exception as e:
            self.logger.error(f"Error rendering prompt {template_name}: {e}")
            await self._record_metrics(template_name, 0, False)
            self.stats['failed_prompts'] += 1
            return ""
    
    async def set_context(self, session_id: str, context: PromptContext) -> bool:
        """Set context for a session"""
        try:
            self.contexts[session_id] = context
            return True
        except Exception as e:
            self.logger.error(f"Error setting context for session {session_id}: {e}")
            return False
    
    async def get_context(self, session_id: str) -> Optional[PromptContext]:
        """Get context for a session"""
        return self.contexts.get(session_id)
    
    async def analyze_prompt(self, prompt: str) -> Dict[str, Any]:
        """Analyze a prompt and provide optimization suggestions"""
        try:
            analysis = {
                'length': len(prompt),
                'word_count': len(prompt.split()),
                'complexity_score': await self._calculate_complexity(prompt),
                'suggestions': [],
                'detected_patterns': [],
                'readability_score': await self._calculate_readability(prompt)
            }
            
            # Apply optimization rules
            for rule in self.optimization_rules:
                if re.search(rule['pattern'], prompt, re.IGNORECASE):
                    analysis['suggestions'].append({
                        'type': rule['name'],
                        'suggestion': rule['suggestion']
                    })
                    analysis['detected_patterns'].append(rule['name'])
            
            # Check for missing variables
            variables = re.findall(r'\{(\w+)\}', prompt)
            if variables:
                analysis['variables'] = variables
                analysis['suggestions'].append({
                    'type': 'variable_check',
                    'suggestion': f'Ensure variables {variables} are provided during rendering'
                })
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Error analyzing prompt: {e}")
            return {'error': str(e)}
    
    async def add_few_shot_examples(self, category: str, examples: List[Dict[str, str]]) -> bool:
        """Add few-shot examples for a category"""
        try:
            self.few_shot_examples[category].extend(examples)
            self.logger.info(f"Added {len(examples)} few-shot examples for category {category}")
            return True
        except Exception as e:
            self.logger.error(f"Error adding few-shot examples: {e}")
            return False
    
    async def get_few_shot_examples(self, category: str) -> List[Dict[str, str]]:
        """Get few-shot examples for a category"""
        return self.few_shot_examples.get(category, [])
    
    async def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        stats = self.stats.copy()
        
        # Calculate derived metrics
        if stats['total_prompts'] > 0:
            stats['success_rate'] = stats['successful_prompts'] / stats['total_prompts']
            stats['average_execution_time'] = stats['total_execution_time'] / stats['total_prompts']
        else:
            stats['success_rate'] = 0.0
            stats['average_execution_time'] = 0.0
        
        # Add template statistics
        stats['template_count'] = len(self.templates)
        stats['most_used_templates'] = await self._get_most_used_templates()
        stats['category_distribution'] = await self._get_category_distribution()
        
        return stats
    
    async def optimize_prompt(self, prompt: str, target_intent: str = None) -> Dict[str, Any]:
        """Optimize a prompt based on analysis and best practices"""
        try:
            analysis = await self.analyze_prompt(prompt)
            optimized = prompt
            applied_optimizations = []
            
            # Apply optimizations based on analysis
            for suggestion in analysis.get('suggestions', []):
                if suggestion['type'] == 'clarity_enhancement':
                    optimized = await self._enhance_clarity(optimized)
                    applied_optimizations.append('clarity_enhancement')
                elif suggestion['type'] == 'context_enhancement':
                    optimized = await self._enhance_context(optimized, target_intent)
                    applied_optimizations.append('context_enhancement')
                elif suggestion['type'] == 'output_formatting':
                    optimized = await self._add_output_formatting(optimized)
                    applied_optimizations.append('output_formatting')
            
            self.stats['optimizations_applied'] += len(applied_optimizations)
            
            return {
                'original': prompt,
                'optimized': optimized,
                'applied_optimizations': applied_optimizations,
                'improvement_score': await self._calculate_improvement_score(prompt, optimized)
            }
            
        except Exception as e:
            self.logger.error(f"Error optimizing prompt: {e}")
            return {'error': str(e)}
    
    # Private helper methods
    async def _validate_template(self, template: PromptTemplate) -> bool:
        """Validate a prompt template"""
        if not template.name or not template.template:
            return False
        
        # Check for required variables in template
        found_variables = set(re.findall(r'\{(\w+)\}', template.template))
        declared_variables = set(template.variables)
        
        if found_variables != declared_variables:
            self.logger.warning(f"Variable mismatch in template {template.name}")
            # Auto-correct if possible
            template.variables = list(found_variables)
        
        return True
    
    async def _apply_context(self, prompt: str, context: PromptContext) -> str:
        """Apply context to a prompt"""
        try:
            # Add conversation history if available
            if context.conversation_history:
                history = "\n".join(context.conversation_history[-5:])  # Last 5 messages
                prompt = f"Previous conversation:\n{history}\n\n{prompt}"
            
            # Apply user preferences
            if context.user_preferences:
                style = context.user_preferences.get('style', 'helpful')
                length = context.user_preferences.get('length', 'medium')
                
                style_instruction = f"Please respond in a {style} manner with {length} responses."
                prompt = f"{style_instruction}\n\n{prompt}"
            
            return prompt
            
        except Exception as e:
            self.logger.error(f"Error applying context: {e}")
            return prompt
    
    async def _apply_few_shot_examples(self, prompt: str, category: str) -> str:
        """Apply few-shot examples to a prompt"""
        try:
            examples = self.few_shot_examples.get(category, [])
            if not examples:
                return prompt
            
            # Select best examples (up to 3)
            selected_examples = examples[:3]
            
            example_text = "\nHere are some examples:\n"
            for i, example in enumerate(selected_examples, 1):
                example_text += f"\nExample {i}:\n"
                example_text += f"Input: {example['input']}\n"
                example_text += f"Output: {example['output']}\n"
            
            return f"{prompt}{example_text}\n\nNow please respond:"
            
        except Exception as e:
            self.logger.error(f"Error applying few-shot examples: {e}")
            return prompt
    
    async def _record_metrics(self, template_name: str, execution_time: float, success: bool):
        """Record performance metrics"""
        try:
            prompt_id = hashlib.md5(f"{template_name}_{time.time()}".encode()).hexdigest()[:12]
            
            metrics = PromptMetrics(
                prompt_id=prompt_id,
                template_name=template_name,
                execution_time=execution_time,
                success=success
            )
            
            self.metrics.append(metrics)
            
            # Keep only recent metrics (last 1000)
            if len(self.metrics) > 1000:
                self.metrics = self.metrics[-1000:]
                
        except Exception as e:
            self.logger.error(f"Error recording metrics: {e}")
    
    async def _calculate_complexity(self, prompt: str) -> float:
        """Calculate prompt complexity score"""
        try:
            # Simple complexity based on length, sentence structure, vocabulary
            word_count = len(prompt.split())
            sentence_count = len(re.split(r'[.!?]+', prompt))
            avg_sentence_length = word_count / max(sentence_count, 1)
            
            # Normalize to 0-1 scale
            complexity = min(1.0, (avg_sentence_length - 5) / 20)
            return max(0.0, complexity)
            
        except Exception:
            return 0.5  # Default complexity
    
    async def _calculate_readability(self, prompt: str) -> float:
        """Calculate readability score (simplified)"""
        try:
            words = prompt.split()
            sentences = re.split(r'[.!?]+', prompt)
            
            if not words or not sentences:
                return 0.5
            
            avg_words_per_sentence = len(words) / len(sentences)
            avg_chars_per_word = sum(len(word) for word in words) / len(words)
            
            # Simple readability score (higher is more readable)
            score = 1.0 - min(1.0, (avg_words_per_sentence - 15) / 30 + (avg_chars_per_word - 5) / 10)
            return max(0.0, score)
            
        except Exception:
            return 0.5
    
    async def _enhance_clarity(self, prompt: str) -> str:
        """Enhance prompt clarity"""
        enhancements = [
            "Please be specific and clear in your response.",
            "Focus on providing actionable information.",
            "Use examples when helpful."
        ]
        
        return f"{prompt}\n\nGuidelines:\n" + "\n".join(f"- {e}" for e in enhancements)
    
    async def _enhance_context(self, prompt: str, target_intent: str = None) -> str:
        """Enhance context in prompt"""
        if target_intent:
            context_addition = f"\nContext: The user's intent appears to be related to {target_intent}. "
            context_addition += "Please tailor your response accordingly."
            return prompt + context_addition
        return prompt
    
    async def _add_output_formatting(self, prompt: str) -> str:
        """Add output formatting instructions"""
        formatting = "\n\nPlease format your response clearly with:"
        formatting += "\n- Clear structure and organization"
        formatting += "\n- Bullet points or numbered lists when appropriate"
        formatting += "\n- Proper spacing and readability"
        
        return prompt + formatting
    
    async def _calculate_improvement_score(self, original: str, optimized: str) -> float:
        """Calculate improvement score between original and optimized prompts"""
        try:
            original_analysis = await self.analyze_prompt(original)
            optimized_analysis = await self.analyze_prompt(optimized)
            
            # Compare readability and complexity
            original_readability = original_analysis.get('readability_score', 0.5)
            optimized_readability = optimized_analysis.get('readability_score', 0.5)
            
            improvement = optimized_readability - original_readability
            return max(0.0, min(1.0, improvement + 0.5))  # Normalize to 0-1
            
        except Exception:
            return 0.0
    
    async def _get_most_used_templates(self) -> List[Dict[str, Any]]:
        """Get most used templates"""
        templates = [(name, template.usage_count) for name, template in self.templates.items()]
        templates.sort(key=lambda x: x[1], reverse=True)
        return [{'name': name, 'usage_count': count} for name, count in templates[:5]]
    
    async def _get_category_distribution(self) -> Dict[str, int]:
        """Get distribution of templates by category"""
        categories = Counter(template.category for template in self.templates.values())
        return dict(categories)
    
    async def _create_default_templates(self):
        """Create default prompt templates"""
        default_templates = [
            PromptTemplate(
                name="assistant_response",
                template="You are SAGE, a helpful AI assistant. {context}\n\nUser request: {query}\n\nPlease provide a helpful and accurate response:",
                variables=["context", "query"],
                category="general",
                description="General assistant response template"
            ),
            PromptTemplate(
                name="error_handling",
                template="I encountered an issue while processing your request: {error_description}\n\nLet me try to help you in a different way. {alternative_approach}",
                variables=["error_description", "alternative_approach"],
                category="error",
                description="Template for handling errors gracefully"
            ),
            PromptTemplate(
                name="clarification_request",
                template="I want to make sure I understand your request correctly. You mentioned: {user_input}\n\nCould you please clarify: {clarification_needed}?",
                variables=["user_input", "clarification_needed"],
                category="clarification",
                description="Template for requesting clarification"
            ),
            PromptTemplate(
                name="task_completion",
                template="I've completed the task: {task_description}\n\nResult: {result}\n\nIs there anything else you'd like me to help you with?",
                variables=["task_description", "result"],
                category="completion",
                description="Template for task completion responses"
            )
        ]
        
        for template in default_templates:
            if template.name not in self.templates:
                await self.register_template(template)
    
    async def _load_templates(self):
        """Load templates from disk"""
        try:
            templates_file = self.data_dir / "templates.json"
            if templates_file.exists():
                with open(templates_file, 'r') as f:
                    data = json.load(f)
                    
                for template_data in data:
                    template = PromptTemplate(**template_data)
                    self.templates[template.name] = template
                    
                self.logger.info(f"Loaded {len(self.templates)} prompt templates")
        except Exception as e:
            self.logger.error(f"Error loading templates: {e}")
    
    async def _save_templates(self):
        """Save templates to disk"""
        try:
            templates_file = self.data_dir / "templates.json"
            data = [asdict(template) for template in self.templates.values()]
            
            with open(templates_file, 'w') as f:
                json.dump(data, f, indent=2)
                
            self.logger.info(f"Saved {len(self.templates)} prompt templates")
        except Exception as e:
            self.logger.error(f"Error saving templates: {e}")
    
    async def _load_few_shot_examples(self):
        """Load few-shot examples from disk"""
        try:
            examples_file = self.data_dir / "few_shot_examples.json"
            if examples_file.exists():
                with open(examples_file, 'r') as f:
                    self.few_shot_examples = defaultdict(list, json.load(f))
                    
                total_examples = sum(len(examples) for examples in self.few_shot_examples.values())
                self.logger.info(f"Loaded {total_examples} few-shot examples")
        except Exception as e:
            self.logger.error(f"Error loading few-shot examples: {e}")
    
    async def _save_few_shot_examples(self):
        """Save few-shot examples to disk"""
        try:
            examples_file = self.data_dir / "few_shot_examples.json"
            
            with open(examples_file, 'w') as f:
                json.dump(dict(self.few_shot_examples), f, indent=2)
                
            total_examples = sum(len(examples) for examples in self.few_shot_examples.values())
            self.logger.info(f"Saved {total_examples} few-shot examples")
        except Exception as e:
            self.logger.error(f"Error saving few-shot examples: {e}")
    
    async def _save_metrics(self):
        """Save performance metrics to disk"""
        try:
            metrics_file = self.data_dir / "metrics.json"
            data = [asdict(metric) for metric in self.metrics[-100:]]  # Save last 100 metrics
            
            with open(metrics_file, 'w') as f:
                json.dump(data, f, indent=2)
                
            self.logger.info(f"Saved {len(data)} performance metrics")
        except Exception as e:
            self.logger.error(f"Error saving metrics: {e}")


__all__ = ['PromptEngine', 'PromptTemplate', 'PromptContext', 'PromptMetrics']