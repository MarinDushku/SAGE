"""
Plugin Manager - Dynamic module loading and management for SAGE
"""

import asyncio
import importlib
import importlib.util
import sys
import os
from typing import Dict, List, Type, Optional, Any
from pathlib import Path
import logging

from modules import BaseModule, EventType


class PluginManager:
    """Manages dynamic loading and lifecycle of SAGE modules"""
    
    def __init__(self, modules_path: str = "modules"):
        self.modules_path = Path(modules_path)
        self.loaded_modules: Dict[str, BaseModule] = {}
        self.module_classes: Dict[str, Type[BaseModule]] = {}
        self.dependency_graph: Dict[str, List[str]] = {}
        self.logger = logging.getLogger(__name__)
        self.event_bus = None
        self.config_manager = None
        
    def set_dependencies(self, event_bus, config_manager, cache_manager=None, logger=None):
        """Set core dependencies for modules"""
        self.event_bus = event_bus
        self.config_manager = config_manager
        self.cache_manager = cache_manager
        self.module_logger = logger
        
    def discover_modules(self) -> List[str]:
        """Discover available modules in the modules directory"""
        modules = []
        
        if not self.modules_path.exists():
            self.logger.warning(f"Modules path {self.modules_path} does not exist")
            return modules
            
        for module_dir in self.modules_path.iterdir():
            if (module_dir.is_dir() and 
                not module_dir.name.startswith('_') and
                (module_dir / '__init__.py').exists()):
                modules.append(module_dir.name)
                
        self.logger.info(f"Discovered modules: {modules}")
        return modules
        
    def load_module_class(self, module_name: str) -> Optional[Type[BaseModule]]:
        """Load a module class dynamically"""
        try:
            # Import the module package
            module_path = f"modules.{module_name}"
            module = importlib.import_module(module_path)
            
            # Look for a class that inherits from BaseModule
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type) and 
                    issubclass(attr, BaseModule) and 
                    attr != BaseModule):
                    self.module_classes[module_name] = attr
                    self.logger.info(f"Loaded module class {attr.__name__} for {module_name}")
                    return attr
                    
            self.logger.warning(f"No BaseModule subclass found in {module_name}")
            return None
            
        except ImportError as e:
            self.logger.error(f"Failed to import module {module_name}: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Error loading module class {module_name}: {e}")
            return None
            
    async def load_module(self, module_name: str, config: Optional[Dict[str, Any]] = None) -> bool:
        """Load and initialize a specific module"""
        if module_name in self.loaded_modules:
            self.logger.info(f"Module {module_name} already loaded")
            return True
            
        # Load the module class if not already loaded
        if module_name not in self.module_classes:
            module_class = self.load_module_class(module_name)
            if not module_class:
                return False
        else:
            module_class = self.module_classes[module_name]
            
        try:
            # Create module instance
            module_instance = module_class(module_name)
            
            # Set dependencies
            module_instance.event_bus = self.event_bus
            module_instance.config = config or self.config_manager.get_module_config(module_name)
            module_instance.cache = self.cache_manager
            module_instance.logger = self.module_logger
            
            # Initialize the module
            success = await module_instance.initialize()
            if not success:
                self.logger.error(f"Module {module_name} initialization failed")
                return False
                
            # Register with event bus
            if self.event_bus and module_instance.subscribed_events:
                for event_type in module_instance.subscribed_events:
                    self.event_bus.subscribe(event_type, module_instance)
                    
            self.loaded_modules[module_name] = module_instance
            
            # Emit module loaded event
            if self.event_bus:
                from modules import Event, EventType
                event = Event(
                    type=EventType.MODULE_LOADED,
                    data={"module_name": module_name},
                    source_module="plugin_manager"
                )
                self.event_bus.emit(event)
                
            self.logger.info(f"Successfully loaded module: {module_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to load module {module_name}: {e}")
            return False
            
    async def unload_module(self, module_name: str) -> bool:
        """Unload a specific module"""
        if module_name not in self.loaded_modules:
            self.logger.warning(f"Module {module_name} not loaded")
            return False
            
        try:
            module_instance = self.loaded_modules[module_name]
            
            # Unsubscribe from events
            if self.event_bus:
                for event_type in module_instance.subscribed_events:
                    self.event_bus.unsubscribe(event_type, module_instance)
                    
            # Shutdown the module
            await module_instance.shutdown()
            
            # Remove from loaded modules
            del self.loaded_modules[module_name]
            
            # Emit module unloaded event
            if self.event_bus:
                from modules import Event, EventType
                event = Event(
                    type=EventType.MODULE_UNLOADED,
                    data={"module_name": module_name},
                    source_module="plugin_manager"
                )
                self.event_bus.emit(event)
                
            self.logger.info(f"Successfully unloaded module: {module_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to unload module {module_name}: {e}")
            return False
            
    async def load_all_modules(self, module_list: Optional[List[str]] = None) -> Dict[str, bool]:
        """Load all discovered modules or a specific list"""
        if module_list is None:
            module_list = self.discover_modules()
            
        results = {}
        
        # Sort by dependencies (simplified - load in alphabetical order for now)
        module_list.sort()
        
        for module_name in module_list:
            result = await self.load_module(module_name)
            results[module_name] = result
            
            if not result:
                self.logger.warning(f"Failed to load module {module_name}")
                
        return results
        
    async def unload_all_modules(self) -> None:
        """Unload all loaded modules"""
        module_names = list(self.loaded_modules.keys())
        
        for module_name in module_names:
            await self.unload_module(module_name)
            
    async def reload_module(self, module_name: str) -> bool:
        """Reload a specific module"""
        if module_name in self.loaded_modules:
            await self.unload_module(module_name)
            
        # Clear the module class cache to force reload
        if module_name in self.module_classes:
            del self.module_classes[module_name]
            
        # Clear from sys.modules to force reimport
        module_path = f"modules.{module_name}"
        if module_path in sys.modules:
            del sys.modules[module_path]
            
        return await self.load_module(module_name)
        
    def get_module(self, module_name: str) -> Optional[BaseModule]:
        """Get a loaded module instance"""
        return self.loaded_modules.get(module_name)
        
    def is_module_loaded(self, module_name: str) -> bool:
        """Check if a module is loaded"""
        return module_name in self.loaded_modules
        
    def get_loaded_modules(self) -> List[str]:
        """Get list of loaded module names"""
        return list(self.loaded_modules.keys())
        
    async def get_module_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all modules"""
        status = {}
        
        for name, module in self.loaded_modules.items():
            try:
                resource_usage = await module.get_resource_usage()
                status[name] = {
                    "loaded": module.is_loaded,
                    "subscribed_events": [e.value for e in module.subscribed_events],
                    **resource_usage
                }
            except Exception as e:
                status[name] = {
                    "loaded": False,
                    "error": str(e)
                }
                
        return status