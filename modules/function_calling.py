"""
Function Calling System for SAGE
Provides LLM with available functions and handles execution
"""

import json
import asyncio
import logging
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
import inspect


class FunctionRegistry:
    """Registry of available functions that the LLM can call"""
    
    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger(__name__)
        self.functions: Dict[str, Dict[str, Any]] = {}
        self.handlers: Dict[str, Callable] = {}
        
        # Register built-in functions
        self._register_builtin_functions()
    
    def _register_builtin_functions(self):
        """Register core system functions"""
        
        # Time functions
        self.register_function(
            "get_current_time",
            description="Get the current time and date",
            parameters={},
            handler=self._get_current_time
        )
        
        self.register_function(
            "get_current_date",
            description="Get the current date",
            parameters={},
            handler=self._get_current_date
        )
        
        # Calendar functions
        self.register_function(
            "lookup_calendar",
            description="Check calendar for events on a specific date or date range",
            parameters={
                "date": {
                    "type": "string",
                    "description": "Date to check (YYYY-MM-DD format or relative like 'today', 'tomorrow')",
                    "required": True
                },
                "time_range": {
                    "type": "string", 
                    "description": "Optional time range like 'morning', 'afternoon', 'evening', or 'all_day'",
                    "required": False
                }
            },
            handler=self._lookup_calendar
        )
        
        self.register_function(
            "add_calendar_event",
            description="Add a new event to the calendar",
            parameters={
                "title": {
                    "type": "string",
                    "description": "Event title/name",
                    "required": True
                },
                "date": {
                    "type": "string",
                    "description": "Event date (YYYY-MM-DD or relative like 'tomorrow')",
                    "required": True
                },
                "time": {
                    "type": "string",
                    "description": "Event time (HH:MM format or relative like '2pm')",
                    "required": False
                },
                "duration": {
                    "type": "string",
                    "description": "Event duration like '1 hour', '30 minutes'",
                    "required": False
                },
                "location": {
                    "type": "string",
                    "description": "Event location or 'online' for virtual events",
                    "required": False
                }
            },
            handler=self._add_calendar_event
        )
        
        # System functions
        self.register_function(
            "get_system_status",
            description="Get current system status and resource usage",
            parameters={},
            handler=self._get_system_status
        )
    
    def register_function(self, name: str, description: str, parameters: Dict, handler: Callable):
        """Register a new function that the LLM can call"""
        self.functions[name] = {
            "name": name,
            "description": description,
            "parameters": parameters
        }
        self.handlers[name] = handler
        self.logger.info(f"Registered function: {name}")
    
    def get_function_catalog(self) -> str:
        """Get a formatted catalog of all available functions for the LLM"""
        catalog = "AVAILABLE FUNCTIONS:\n\n"
        
        for name, func_info in self.functions.items():
            catalog += f"**{name}**\n"
            catalog += f"Description: {func_info['description']}\n"
            
            if func_info['parameters']:
                catalog += "Parameters:\n"
                for param_name, param_info in func_info['parameters'].items():
                    required = "REQUIRED" if param_info.get('required', False) else "optional"
                    catalog += f"  - {param_name} ({param_info['type']}, {required}): {param_info['description']}\n"
            else:
                catalog += "Parameters: None\n"
            catalog += "\n"
        
        return catalog
    
    async def execute_function(self, function_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a function call from the LLM"""
        try:
            if function_name not in self.handlers:
                return {
                    "success": False,
                    "error": f"Function '{function_name}' not found",
                    "available_functions": list(self.functions.keys())
                }
            
            handler = self.handlers[function_name]
            
            # Validate parameters
            func_def = self.functions[function_name]
            validation_result = self._validate_parameters(parameters, func_def['parameters'])
            if not validation_result['valid']:
                return {
                    "success": False,
                    "error": f"Invalid parameters: {validation_result['error']}",
                    "expected_parameters": func_def['parameters']
                }
            
            # Execute function
            if inspect.iscoroutinefunction(handler):
                result = await handler(**parameters)
            else:
                result = handler(**parameters)
            
            return {
                "success": True,
                "result": result,
                "function": function_name,
                "parameters": parameters
            }
            
        except Exception as e:
            self.logger.error(f"Error executing function {function_name}: {e}")
            return {
                "success": False,
                "error": str(e),
                "function": function_name,
                "parameters": parameters
            }
    
    def _validate_parameters(self, provided: Dict[str, Any], expected: Dict[str, Any]) -> Dict[str, Any]:
        """Validate function parameters"""
        try:
            # Check required parameters
            for param_name, param_def in expected.items():
                if param_def.get('required', False) and param_name not in provided:
                    return {
                        "valid": False,
                        "error": f"Required parameter '{param_name}' missing"
                    }
            
            # Check for unknown parameters
            for param_name in provided.keys():
                if param_name not in expected:
                    return {
                        "valid": False,
                        "error": f"Unknown parameter '{param_name}'"
                    }
            
            return {"valid": True}
            
        except Exception as e:
            return {
                "valid": False,
                "error": str(e)
            }
    
    # Built-in function handlers
    
    def _get_current_time(self) -> str:
        """Get current time"""
        now = datetime.now()
        return now.strftime("%I:%M %p")
    
    def _get_current_date(self) -> str:
        """Get current date"""
        now = datetime.now()
        return now.strftime("%A, %B %d, %Y")
    
    async def _lookup_calendar(self, date: str, time_range: Optional[str] = None) -> str:
        """Lookup calendar events"""
        # This would interface with the actual calendar module
        # For now, return a placeholder
        try:
            # Parse relative dates
            target_date = self._parse_relative_date(date)
            date_str = target_date.strftime("%Y-%m-%d")
            
            # Simulate calendar lookup
            if time_range:
                return f"Checking calendar for {date_str} ({time_range}): No events found"
            else:
                return f"Checking calendar for {date_str}: No events found"
                
        except Exception as e:
            return f"Error looking up calendar: {str(e)}"
    
    async def _add_calendar_event(self, title: str, date: str, time: Optional[str] = None, 
                                duration: Optional[str] = None, location: Optional[str] = None) -> str:
        """Add calendar event"""
        try:
            # Parse date and time
            target_date = self._parse_relative_date(date)
            
            event_info = f"Event '{title}' on {target_date.strftime('%Y-%m-%d')}"
            if time:
                event_info += f" at {time}"
            if duration:
                event_info += f" for {duration}"
            if location:
                event_info += f" at {location}"
            
            # This would interface with the actual calendar module
            return f"Successfully scheduled: {event_info}"
            
        except Exception as e:
            return f"Error adding event: {str(e)}"
    
    def _get_system_status(self) -> str:
        """Get system status"""
        # This would interface with the resource monitor
        return "System status: All modules running normally"
    
    def _parse_relative_date(self, date_str: str) -> datetime:
        """Parse relative date strings like 'today', 'tomorrow'"""
        date_lower = date_str.lower()
        now = datetime.now()
        
        if date_lower in ['today']:
            return now
        elif date_lower in ['tomorrow']:
            return now + timedelta(days=1)
        elif date_lower in ['yesterday']:
            return now - timedelta(days=1)
        else:
            # Try to parse as YYYY-MM-DD
            try:
                return datetime.strptime(date_str, "%Y-%m-%d")
            except ValueError:
                # If parsing fails, default to today
                return now


class FunctionCallingProcessor:
    """Process user requests using function calling approach"""
    
    def __init__(self, function_registry: FunctionRegistry, nlp_module=None, logger=None):
        self.function_registry = function_registry
        self.nlp_module = nlp_module
        self.logger = logger or logging.getLogger(__name__)
    
    async def process_request(self, user_input: str) -> Dict[str, Any]:
        """Process user request using function calling"""
        try:
            # Create prompt for LLM
            function_catalog = self.function_registry.get_function_catalog()
            
            # Extremely simple prompt to test LLM capability
            prompt = f"""User said: "{user_input}"

Is this asking for TIME? Reply with JSON:

If YES - time question:
{{"functions_to_call": [{{"function_name": "get_current_time", "parameters": {{}}}}]}}

If NO - not time:
{{"functions_to_call": [], "response": "I don't understand"}}

Your answer:"""

            # Get LLM response
            if self.nlp_module:
                self.logger.info(f"Sending prompt to LLM: {prompt[:200]}...")
                llm_result = await self.nlp_module.process_text(prompt)
                if llm_result.get('success'):
                    response_text = llm_result['response']['text']
                    self.logger.info(f"LLM raw response: {response_text}")
                    return await self._parse_llm_response(response_text, user_input)
                else:
                    self.logger.warning(f"LLM processing failed: {llm_result}")
            else:
                self.logger.warning("No NLP module available for function calling")
            
            # Fallback if NLP module not available
            return await self._fallback_processing(user_input)
            
        except Exception as e:
            self.logger.error(f"Error processing request: {e}")
            return {
                "success": False,
                "error": str(e),
                "fallback_response": "I'm sorry, I had trouble processing your request."
            }
    
    async def _parse_llm_response(self, llm_response: str, original_request: str) -> Dict[str, Any]:
        """Parse LLM response and execute function calls"""
        try:
            # Clean the response
            llm_response = llm_response.strip()
            
            # Try to extract JSON from LLM response
            json_start = llm_response.find('{')
            json_end = llm_response.rfind('}') + 1
            
            if json_start != -1 and json_end > json_start:
                # Extract only the first JSON object (in case LLM returns multiple)
                json_str = llm_response[json_start:json_end]
                
                # Find the end of the first complete JSON object
                brace_count = 0
                first_json_end = json_start
                for i, char in enumerate(llm_response[json_start:], json_start):
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            first_json_end = i + 1
                            break
                
                # Extract only the first JSON object
                first_json = llm_response[json_start:first_json_end]
                self.logger.info(f"Attempting to parse first JSON: {first_json}")
                
                try:
                    parsed = json.loads(first_json)
                    self.logger.info(f"Successfully parsed JSON: {parsed}")
                except json.JSONDecodeError as json_err:
                    self.logger.warning(f"JSON parsing failed: {json_err}")
                    # Try to fix common JSON issues
                    fixed_json = first_json.replace("'", '"')  # Replace single quotes with double quotes
                    try:
                        parsed = json.loads(fixed_json)
                        self.logger.info(f"Fixed and parsed JSON: {parsed}")
                    except json.JSONDecodeError:
                        self.logger.error("Could not fix JSON, falling back")
                        return await self._fallback_processing(original_request)
                
                functions_to_call = parsed.get('functions_to_call', [])
                direct_response = parsed.get('response', '')
                
                # If no functions to call, return direct response
                if not functions_to_call:
                    self.logger.info("No functions to call, returning direct response")
                    return {
                        "success": True,
                        "type": "direct_response",
                        "response": direct_response or "I'm not sure how to help with that."
                    }
                
                # Execute function calls
                self.logger.info(f"Executing {len(functions_to_call)} function(s)")
                results = []
                for func_call in functions_to_call:
                    func_name = func_call.get('function_name')
                    parameters = func_call.get('parameters', {})
                    
                    if func_name:
                        self.logger.info(f"Calling function: {func_name} with parameters: {parameters}")
                        result = await self.function_registry.execute_function(func_name, parameters)
                        results.append({
                            "function": func_name,
                            "parameters": parameters,
                            "result": result
                        })
                
                return {
                    "success": True,
                    "type": "function_calls",
                    "function_results": results,
                    "response": self._generate_response_from_results(results, original_request)
                }
            
            else:
                # Could not find JSON, treat as direct response
                self.logger.warning("No JSON found in LLM response, treating as direct response")
                return {
                    "success": True,
                    "type": "direct_response",
                    "response": llm_response or "I'm not sure how to help with that."
                }
                
        except Exception as e:
            self.logger.error(f"Error parsing LLM response: {e}")
            return await self._fallback_processing(original_request)
    
    def _generate_response_from_results(self, results: List[Dict], original_request: str) -> str:
        """Generate natural response from function call results"""
        if not results:
            return "I couldn't process your request."
        
        responses = []
        for result in results:
            if result['result']['success']:
                responses.append(str(result['result']['result']))
            else:
                responses.append(f"Error: {result['result']['error']}")
        
        return " ".join(responses)
    
    async def _fallback_processing(self, user_input: str) -> Dict[str, Any]:
        """Enhanced fallback processing when LLM parsing fails"""
        self.logger.info(f"Using fallback processing for: '{user_input}'")
        user_lower = user_input.lower()
        
        # Time queries - multiple variations
        time_keywords = ['time', 'what time', 'clock', 'hour', 'minute', 'when is it', 'current time']
        if any(word in user_lower for word in time_keywords):
            self.logger.info("Fallback detected time query")
            result = await self.function_registry.execute_function("get_current_time", {})
            if result['success']:
                return {
                    "success": True,
                    "type": "fallback_function",
                    "response": f"It's currently {result['result']}"
                }
        
        # Date queries
        date_keywords = ['date', 'what date', 'today', 'current date', 'what day']
        if any(word in user_lower for word in date_keywords):
            self.logger.info("Fallback detected date query")
            result = await self.function_registry.execute_function("get_current_date", {})
            if result['success']:
                return {
                    "success": True,
                    "type": "fallback_function", 
                    "response": f"Today is {result['result']}"
                }
        
        # Calendar queries
        calendar_keywords = ['schedule', 'calendar', 'meetings', 'events', 'appointments', 'planned', 'busy']
        if any(word in user_lower for word in calendar_keywords):
            self.logger.info("Fallback detected calendar query")
            # Extract date if possible
            date_param = "today"  # default
            if "tomorrow" in user_lower:
                date_param = "tomorrow"
            elif "yesterday" in user_lower:
                date_param = "yesterday"
                
            result = await self.function_registry.execute_function("lookup_calendar", {"date": date_param})
            if result['success']:
                return {
                    "success": True,
                    "type": "fallback_function",
                    "response": str(result['result'])
                }
        
        self.logger.info("Fallback could not classify request")
        return {
            "success": True,
            "type": "fallback_unknown",
            "response": "I'm not sure how to help with that request."
        }