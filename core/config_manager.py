"""
Configuration Manager - Centralized configuration for SAGE
"""

import yaml
import json
import os
from typing import Dict, Any, Optional, Union
from pathlib import Path
import logging
from copy import deepcopy


class ConfigManager:
    """Manages configuration for SAGE and its modules"""
    
    def __init__(self, config_file: str = "config.yaml"):
        self.config_file = Path(config_file)
        self.config: Dict[str, Any] = {}
        self.module_configs: Dict[str, Dict[str, Any]] = {}
        self.logger = logging.getLogger(__name__)
        
        # Default configuration
        self.default_config = {
            "core": {
                "log_level": "INFO",
                "max_workers": 4,
                "event_queue_size": 1000,
                "resource_monitor_interval": 30
            },
            "performance": {
                "max_memory_mb": 1000,
                "max_cpu_percent": 80,
                "cache_size_mb": 200,
                "model_loading_timeout": 60
            },
            "modules": {
                "auto_load": [
                    "voice",
                    "nlp", 
                    "calendar"
                ],
                "optional": [
                    "vision",
                    "web_tools",
                    "fabrication"
                ]
            }
        }
        
    def load_config(self) -> bool:
        """Load configuration from file"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    if self.config_file.suffix.lower() == '.json':
                        loaded_config = json.load(f)
                    else:
                        loaded_config = yaml.safe_load(f)
                        
                self.config = self._merge_configs(self.default_config, loaded_config or {})
                self.logger.info(f"Loaded configuration from {self.config_file}")
            else:
                self.config = deepcopy(self.default_config)
                self.save_config()
                self.logger.info("Created default configuration file")
                
            # Load module-specific configurations
            self._load_module_configs()
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {e}")
            self.config = deepcopy(self.default_config)
            return False
            
    def save_config(self) -> bool:
        """Save current configuration to file"""
        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                if self.config_file.suffix.lower() == '.json':
                    json.dump(self.config, f, indent=2)
                else:
                    yaml.dump(self.config, f, default_flow_style=False, indent=2)
                    
            self.logger.info(f"Saved configuration to {self.config_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save configuration: {e}")
            return False
            
    def _load_module_configs(self) -> None:
        """Load configuration files for individual modules"""
        modules_dir = Path("modules")
        
        if not modules_dir.exists():
            return
            
        for module_dir in modules_dir.iterdir():
            if not module_dir.is_dir():
                continue
                
            config_files = list(module_dir.glob("*_config.yaml")) + list(module_dir.glob("*_config.json"))
            
            for config_file in config_files:
                try:
                    with open(config_file, 'r', encoding='utf-8') as f:
                        if config_file.suffix.lower() == '.json':
                            module_config = json.load(f)
                        else:
                            module_config = yaml.safe_load(f)
                            
                    self.module_configs[module_dir.name] = module_config
                    self.logger.debug(f"Loaded config for module {module_dir.name}")
                    
                except Exception as e:
                    self.logger.warning(f"Failed to load config for {module_dir.name}: {e}")
                    
    def _merge_configs(self, default: Dict, loaded: Dict) -> Dict:
        """Recursively merge two configuration dictionaries"""
        result = deepcopy(default)
        
        for key, value in loaded.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = deepcopy(value)
                
        return result
        
    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value using dot notation"""
        keys = key.split('.')
        value = self.config
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
            
    def set(self, key: str, value: Any) -> None:
        """Set a configuration value using dot notation"""
        keys = key.split('.')
        config = self.config
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
            
        config[keys[-1]] = value
        
    def get_module_config(self, module_name: str) -> Dict[str, Any]:
        """Get configuration for a specific module"""
        # First check module-specific config files
        if module_name in self.module_configs:
            base_config = deepcopy(self.module_configs[module_name])
        else:
            base_config = {}
            
        # Then check main config file for module overrides
        main_config = self.get(f"modules.{module_name}", {})
        
        return self._merge_configs(base_config, main_config)
        
    def set_module_config(self, module_name: str, config: Dict[str, Any]) -> None:
        """Set configuration for a specific module"""
        self.set(f"modules.{module_name}", config)
        
    def get_core_config(self) -> Dict[str, Any]:
        """Get core system configuration"""
        return self.get("core", {})
        
    def get_performance_config(self) -> Dict[str, Any]:
        """Get performance-related configuration"""
        return self.get("performance", {})
        
    def is_module_auto_load(self, module_name: str) -> bool:
        """Check if a module should be auto-loaded"""
        auto_load_modules = self.get("modules.auto_load", [])
        return module_name in auto_load_modules
        
    def get_auto_load_modules(self) -> list:
        """Get list of modules to auto-load"""
        return self.get("modules.auto_load", [])
        
    def validate_config(self) -> Dict[str, list]:
        """Validate current configuration and return issues"""
        issues = {
            "errors": [],
            "warnings": []
        }
        
        # Check required fields
        required_fields = [
            "core.log_level",
            "performance.max_memory_mb",
            "modules.auto_load"
        ]
        
        for field in required_fields:
            if self.get(field) is None:
                issues["errors"].append(f"Missing required field: {field}")
                
        # Check data types and ranges
        memory_limit = self.get("performance.max_memory_mb")
        if memory_limit and (not isinstance(memory_limit, int) or memory_limit <= 0):
            issues["errors"].append("performance.max_memory_mb must be a positive integer")
            
        cpu_limit = self.get("performance.max_cpu_percent")
        if cpu_limit and (not isinstance(cpu_limit, (int, float)) or cpu_limit <= 0 or cpu_limit > 100):
            issues["errors"].append("performance.max_cpu_percent must be between 0 and 100")
            
        # Check log level
        log_level = self.get("core.log_level")
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if log_level and log_level not in valid_levels:
            issues["warnings"].append(f"Invalid log level: {log_level}. Valid levels: {valid_levels}")
            
        return issues
        
    def create_example_module_config(self, module_name: str) -> Dict[str, Any]:
        """Create an example configuration for a module"""
        examples = {
            "voice": {
                "recognition": {
                    "engine": "google",  # google, whisper, vosk
                    "language": "en-US",
                    "timeout": 5,
                    "phrase_time_limit": 10
                },
                "synthesis": {
                    "engine": "pyttsx3",
                    "voice": "default",
                    "rate": 200,
                    "volume": 0.8
                },
                "wake_word": {
                    "enabled": True,
                    "keyword": "sage",
                    "sensitivity": 0.5
                }
            },
            "nlp": {
                "llm": {
                    "provider": "ollama",  # ollama, gpt4all
                    "model": "phi3:mini",
                    "temperature": 0.7,
                    "max_tokens": 1000,
                    "context_window": 4000
                },
                "intent": {
                    "confidence_threshold": 0.8,
                    "fallback_enabled": True
                }
            },
            "vision": {
                "face_recognition": {
                    "enabled": True,
                    "tolerance": 0.6,
                    "model": "hog"  # hog, cnn
                },
                "object_detection": {
                    "model": "yolov8n",
                    "confidence": 0.5,
                    "device": "cpu"
                }
            }
        }
        
        return examples.get(module_name, {
            "enabled": True,
            "debug": False,
            "cache_enabled": True
        })